"""PDO operations using the decentralized helpers.

Wallets are ``identity.identity`` contracts. Asset identities and hand-signing
authorities are ``signature_authority`` contracts (a superset: it inherits
identity's ops and adds signing-context issuance). The op classes behind
``add_vc`` / ``get_vc_list`` / ``get_vp`` / ``register_signing_context`` /
``list_signing_contexts`` are literally the same across ``identity``,
``signature_authority``, and ``external_key_authority`` (each family aliases
the one below it), so the ``signature_authority`` decentralized module below
is used as the one family-agnostic entry point for all of them by contract_id
— only ``sign_credential`` is NOT reusable against an ``external_key_authority``
contract (it's a distinct, non-aliased op there).

An asset's policy and a rule-based authority are both a ``rego_policy_agent``:
one issues policy decisions, the other a fact. System
authorities are the authority family's session-key and wallet-key authorities.

Helpers mutate the shared state when loading contexts, so all calls run
under a single global lock.
"""

import base64
import json
import logging
import os
import tempfile
import threading
import time

# settings (loaded during django.setup()) prepares the PDO environment.
# Read it before importing pdo.* so the env vars are already set.
from django.conf import settings as cfg

_ = cfg.PDO_HOME  # force settings to load (and set os.environ) before pdo.*

import pdo.authority.decentralized.external_key_authority as external_key_authority
import pdo.authority.decentralized.wallet_key_authority as wallet_key_authority
import pdo.identity.decentralized.identity as identity_contract
import pdo.identity.decentralized.signature_authority as signature_authority
import pdo.rego.decentralized.rego_policy_agent as rego_policy_agent
import pdo.rego.decentralized.rego_token as rego_token
from pdo.identity.plugins.identity import cmd_sign_with_contract_key

from .credentials import held_credentials
from .pdo_state import get_state

logger = logging.getLogger(__name__)
_op_lock = threading.Lock()

# What a proof made with a contract's own key says about itself. PDO signs with
# ECDSA over secp384r1 (PDO_DEFAULT_SIGCURVE), which is the scheme every other
# credential in this system is signed with too.
CONTRACT_KEY_PROOF_TYPE = "ecdsa_secp384r1"


def _tmp_json(data):
    fd, path = tempfile.mkstemp(prefix="pdo_op_", suffix=".json", dir=cfg.SCRATCH_DIR)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    return path


def _tmp_path(suffix):
    fd, path = tempfile.mkstemp(prefix="pdo_op_", suffix=suffix, dir=cfg.SCRATCH_DIR)
    os.close(fd)
    return path


def _safe_unlink(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def _as_json(raw):
    """A contract result as a value: the decentralized helpers return either."""
    return json.loads(raw) if isinstance(raw, str) else raw


def _read_json(path):
    with open(path) as f:
        return json.load(f)


# ============================================================
# Wallet ops (identity.identity-backed)
# ============================================================
def create_wallet(name, user_name):
    """Create a wallet, backed by a plain identity.identity contract.

    ``name`` is used verbatim as the contract's on-chain description.

    Returns the contract_id.
    """
    state = get_state()
    with _op_lock:
        return identity_contract.create_identity(state, user_name, description=name)


# ============================================================
# Identity ops shared by asset identities and authorities
# (signature_authority-backed; see the module docstring for why this one
# decentralized module is reused as the family-agnostic entry point)
# ============================================================
def create_asset_identity(name, user_name):
    """Create the identity contract behind an asset, backed by
    signature_authority (unlike a wallet, this is not a user-facing "wallet").

    Returns the contract_id.
    """
    state = get_state()
    with _op_lock:
        return signature_authority.create_signature_authority(
            state, user_name, description=f"asset identity for {name}"
        )


def create_hand_signing_authority(name, user_name):
    """Create a hand-signing authority: a signature_authority contract its
    operator signs credentials from, after their own review.

    ``name`` is used verbatim as the contract's on-chain description. The
    authority signs everything from one fixed signing context
    (``cfg.POC_SIGNING_CONTEXT_NAME``); the webapp does not expose
    signing-context management.

    Returns the contract_id.
    """
    state = get_state()
    with _op_lock:
        contract_id = signature_authority.create_signature_authority(
            state, user_name, description=name
        )
        time.sleep(1)
        signature_authority.register_signing_context(
            state,
            contract_id,
            user_name,
            path=[cfg.POC_SIGNING_CONTEXT_NAME],
            description=name,
            extensible=False,
        )
    return contract_id


def create_session_key_authority(user_name):
    """Create an external_key_authority, which binds session keys to wallets. The
    one call also creates and trusts its wallet_key_authority (see
    ``cmd_create_external_key_authority``), whose description comes fixed from its
    context template.

    Returns the contract_id.
    """
    state = get_state()
    with _op_lock:
        return external_key_authority.create_external_key_authority(state, user_name)


def wallet_add_vc(contract_id, vc_dict, user_name):
    """Add a verifiable credential to a wallet."""
    state = get_state()
    cred_path = _tmp_json(vc_dict)
    try:
        with _op_lock:
            signature_authority.add_vc(
                state, contract_id, user_name, credential_file=cred_path
            )
    finally:
        _safe_unlink(cred_path)


def wallet_list_vcs(contract_id, user_name):
    """Return the wallet's stored VCs, keyed by digest."""
    state = get_state()
    with _op_lock:
        return _as_json(signature_authority.get_vc_list(state, contract_id, user_name))


def wallet_credentials(contract_id, user_name):
    """The wallet's credentials, decoded (``app.credentials.Held``)."""
    return held_credentials(wallet_list_vcs(contract_id, user_name))


def sign_credential(contract_id, signing_context_path, credential_dict, user_name):
    """Sign a credential with the given signing context path on a wallet.

    ``signing_context_path`` is a list of strings (e.g. ``["my_issuer"]``).
    Returns the signed VC dict.
    """
    state = get_state()
    cred_path = _tmp_json(credential_dict)
    signed_path = _tmp_path(".json")
    try:
        with _op_lock:
            signature_authority.sign_credential(
                state,
                contract_id,
                user_name,
                path=signing_context_path,
                credential=cred_path,
                signed_credential=signed_path,
            )
        return _read_json(signed_path)
    finally:
        _safe_unlink(cred_path)
        _safe_unlink(signed_path)


def sign_credential_with_contract_key(contract_id, credential_dict, user_name):
    """Sign a credential with a contract's own, ledger-attested key.

    This is how a *wallet* issues a credential. A wallet is a plain
    ``identity.identity`` contract, so it has no ``sign_credential`` — that op
    belongs to the signature_authority family, and it signs from a registered
    signing context. What every contract does have is the key pair PDO generates
    for it at creation, whose public half the ledger records in the contract's
    metadata; ``sign_with_contract_key`` signs with the private half.

    That is the same key a ``WalletVerifyingKeyCredential`` names, which is what
    makes a self-issued credential worth anything: the policy checks its signature
    against the key an authority independently attested for that wallet, rather
    than against a registered issuer (see the FL-IS policy's
    ``vc_supplied_verification_tasks``).

    The verifiable credential is assembled here rather than inside the contract.
    The signature covers the base64 serialized credential, exactly as
    ``VerifiableCredential::build`` computes it, so what comes back verifies by
    the same code path as anything a contract signed itself.

    Returns the signed VC dict.
    """
    state = get_state()

    serialized = json.dumps(credential_dict, separators=(",", ":"))
    b64_credential = base64.b64encode(serialized.encode("utf-8")).decode("ascii")

    # The command signs the file's bytes, so the file holds the base64 text and
    # nothing else -- a trailing newline would be signed along with it.
    message_path = _tmp_path(".txt")
    signature_path = _tmp_path(".json")
    try:
        with open(message_path, "w") as f:
            f.write(b64_credential)
        with _op_lock:
            # The decentralized modules wrap one command each and none wraps this
            # one; the context they build is identical for every op on a contract
            # addressed by id, so their builder is reused rather than copied.
            signature_authority._invoke_signature_authority(
                state,
                contract_id,
                user_name,
                cmd_sign_with_contract_key,
                message_file=message_path,
                signature_file=signature_path,
            )
        with open(signature_path) as f:
            proof_value = f.read().strip()
    finally:
        _safe_unlink(message_path)
        _safe_unlink(signature_path)

    return {
        "serializedCredential": b64_credential,
        "proof": {
            "type": CONTRACT_KEY_PROOF_TYPE,
            "proofPurpose": "assertion",
            # The contract key sits under no signing context, so the path is
            # empty. A verifier of this credential is handed the key itself
            # rather than deriving it down a registered issuer's tree.
            "verificationMethod": {"id": contract_id, "context_path": []},
            "proofValue": proof_value,
        },
    }


def _presentation(state, wallet_ids, requirements, user_name):
    """One verifiable presentation per role, keyed by role, written to a file.

    A role is presented from the wallet chosen for it, with every stored
    credential of the role's types, whoever it is about: a policy reads only the
    facts about the role's holder, and an authority may read copies of facts about
    others. The caller must hold ``_op_lock``.
    """
    presentation = {}
    for role, types in requirements.items():
        if role not in wallet_ids:
            raise ValueError(f"No wallet was chosen for the '{role}' role.")
        vp_path = _tmp_path(".json")
        try:
            signature_authority.get_vp(
                state,
                wallet_ids[role],
                user_name,
                types=sorted(set(types)),
                output_file=vp_path,
            )
            time.sleep(1)
            presentation[role] = _read_json(vp_path)
        finally:
            _safe_unlink(vp_path)
    return _tmp_json(presentation)


# ============================================================
# Policy agents: an asset's policy, and rule-based authorities
# ============================================================
def create_policy_agent(description, user_name, rego_modules):
    """Create a policy agent and lock in its policy: its ``[module_id, rego_source]``
    modules, one of which declares the type it issues, each written to a file for
    the command that reads it.

    Returns the contract_id.
    """
    state = get_state()
    module_paths = []
    module_args = []
    for module_id, source in rego_modules:
        path = _tmp_path(".rego")
        with open(path, "w") as f:
            f.write(source)
        module_paths.append(path)
        module_args.append([module_id, path])

    try:
        with _op_lock:
            contract_id = rego_policy_agent.create_rego_policy_agent(state, user_name, description=description)
            time.sleep(1)
            rego_policy_agent.set_rego_policy(state, contract_id, user_name, module=module_args)
    finally:
        for path in module_paths:
            _safe_unlink(path)
    return contract_id


def get_rego_policy(agent_id, user_name):
    """``{credential_type, rego_modules, requirements}``."""
    state = get_state()
    with _op_lock:
        return _as_json(rego_policy_agent.get_rego_policy(state, agent_id, user_name))


def set_policy_data(agent_id, policy_data, user_name):
    """Write the policy data, each module's parameters under its module id."""
    state = get_state()
    data_path = _tmp_json(policy_data)
    try:
        with _op_lock:
            rego_policy_agent.set_policy_data(state, agent_id, user_name, data=data_path)
    finally:
        _safe_unlink(data_path)


def get_policy_data(agent_id, user_name):
    state = get_state()
    with _op_lock:
        return _as_json(rego_policy_agent.get_policy_data(state, agent_id, user_name))


def register_trusted_issuer(agent_id, issuer_id, user_name, *, path, credential_types):
    """Have a policy agent accept an authority for some credential types, signed
    from the context at ``path`` or below it."""
    state = get_state()
    with _op_lock:
        rego_policy_agent.register_trusted_issuer(
            state,
            agent_id,
            issuer_id,
            user_name,
            path=path,
            credential_types=credential_types,
        )


def unregister_trusted_issuer(agent_id, issuer_id, user_name, *, credential_types):
    """Withdraw a policy agent's trust in an authority for some credential types."""
    state = get_state()
    with _op_lock:
        rego_policy_agent.unregister_trusted_issuer(
            state, agent_id, user_name, issuer=issuer_id, credential_types=credential_types
        )


def list_trusted_issuers(agent_id, user_name):
    state = get_state()
    with _op_lock:
        return _as_json(rego_policy_agent.list_trusted_issuers(state, agent_id, user_name))


def _issue(state, agent_id, wallet_ids, user_name, request, issued_path):
    """Present the wallets to a policy agent, role by role as its requirements
    name them, with what the requester declares, and write what it issues to
    ``issued_path``. The caller must hold ``_op_lock``."""
    requirements = _as_json(rego_policy_agent.get_requirements(state, agent_id, user_name))
    time.sleep(1)
    presentation_path = _presentation(state, wallet_ids, requirements, user_name)
    try:
        rego_policy_agent.issue_policy_credential(
            state,
            agent_id,
            user_name,
            presentation=presentation_path,
            request=request,
            issued_credential=issued_path,
        )
        time.sleep(1)
    finally:
        _safe_unlink(presentation_path)


def issue_credential(agent_id, wallet_ids, user_name, request):
    """Ask a rule-based authority for the fact it issues, presenting the wallets
    its rule reads; returns the credential."""
    state = get_state()
    issued_path = _tmp_path(".json")
    try:
        with _op_lock:
            _issue(state, agent_id, wallet_ids, user_name, request, issued_path)
        return _read_json(issued_path)
    finally:
        _safe_unlink(issued_path)


def obtain_wallet_key_credential(wka_id, wallet_id, user_name):
    """Have a wallet key authority attest a wallet's ledger-registered key, and
    store the WalletVerifyingKeyCredential in the wallet."""
    state = get_state()
    issued_path = _tmp_path(".json")
    try:
        with _op_lock:
            wallet_context = external_key_authority._setup_wallet_context(
                state, user_name, wallet_id
            )
            wallet_key_authority.sign_credential(
                state, wka_id, user_name, wallet=wallet_context, credential=issued_path
            )
        issued = _read_json(issued_path)
    finally:
        _safe_unlink(issued_path)
    wallet_add_vc(wallet_id, issued, user_name)
    return issued


def bind_session_key(eka_id, wallet_id, user_name, keys_dir):
    """Generate a session key in ``keys_dir`` and have a session-key authority bind
    it to the wallet; the publicKeyCredential lands in the wallet."""
    state = get_state()
    with _op_lock:
        external_key_authority.bind_external_key(
            state, eka_id, wallet_id, user_name, keys_dir=keys_dir
        )
        time.sleep(1)


# ============================================================
# Asset policy ops (owner-side)
# ============================================================
def create_asset_policy(description, guardian_url_port, user_name, rego_modules):
    """Create the asset's policy agent, issuing policy decisions from
    ``rego_modules`` (the cards the owner selected and the delivery module of the
    asset's guardian), and a rego_token that trusts it for them.

    Returns ``{'policy_contract_id', 'token_contract_id'}``.
    """
    policy_id = create_policy_agent(description, user_name, rego_modules)
    state = get_state()
    with _op_lock:
        time.sleep(1)
        token_id = rego_token.create_rego_token(state, user_name, guardian_url_port)
        time.sleep(1)
        rego_token.register_trusted_issuer(
            state,
            token_id,
            policy_id,
            user_name,
            credential_types=["policy_decision"],
            path=["__ISSUER__"],
        )
    return {"policy_contract_id": policy_id, "token_contract_id": token_id}


# ============================================================
# Asset use ops (consumer-side)
# ============================================================
def _resolve_policy_id(state, token_id, user_name):
    """The policy agent contract id a token names: the one issuer it trusts.

    The caller must hold ``_op_lock``.
    """
    issuers = _as_json(rego_token.list_trusted_issuers(state, token_id, user_name))
    if len(issuers) != 1:
        raise ValueError(f"The token {token_id} names {len(issuers)} policies, not one.")
    return next(iter(issuers.keys()))


def resolve_policy_id(token_id, user_name):
    state = get_state()
    with _op_lock:
        return _resolve_policy_id(state, token_id, user_name)


def get_policy_requirements(token_id, user_name):
    """The per-role credential requirements of the policy a token names, which
    the consumer needs before presenting anything: they say which roles must be
    filled and from where."""
    state = get_state()
    with _op_lock:
        policy_id = _resolve_policy_id(state, token_id, user_name)
        return _as_json(rego_policy_agent.get_requirements(state, policy_id, user_name))


def _issue_policy_decision(state, wallet_ids, token_id, user_name, issued_path, request):
    """Have an asset's policy judge a presentation, writing the decision to
    ``issued_path``.

    The token names the policy agent. Each role is presented from the wallet
    chosen for it -- the requester's own for ``User``, the script's for
    ``Script``. ``request`` carries what the requester declares: the project, the
    channel key, the script digest.

    This is where every policy-gated flow starts; what follows differs only in
    what the resulting capability is handed to. The caller must hold ``_op_lock``.
    """
    policy_id = _resolve_policy_id(state, token_id, user_name)
    time.sleep(1)
    _issue(state, policy_id, wallet_ids, user_name, request, issued_path)


def use_asset(*, wallet_ids, token_id, guardian_url_port, user_name, request):
    """Run the consumer download flow.

    Issues a policy decision credential and redeems the capability it authorizes
    at the guardian, downloading the (encrypted) data.

    Returns ``(output_path, issued_vc_dict)``.
    """
    state = get_state()
    os.makedirs(cfg.DOWNLOAD_OUTPUT_DIR, exist_ok=True)

    issued_path = _tmp_path(".json")
    output_path = os.path.join(cfg.DOWNLOAD_OUTPUT_DIR, f"download_{os.urandom(4).hex()}.bin")

    try:
        with _op_lock:
            _issue_policy_decision(state, wallet_ids, token_id, user_name, issued_path, request)
            rego_token.do_operation(
                state,
                token_id,
                user_name,
                guardian_url_port,
                vc_file=issued_path,
                output_file=output_path,
            )
        return output_path, _read_json(issued_path)
    finally:
        _safe_unlink(issued_path)


def create_capability(*, wallet_ids, token_id, user_name, request):
    """Run the consumer flow up to the capability, without redeeming it.

    Used by actions where someone else contacts the guardian: the inference flow
    hands the capability to an FL server, which passes it to the FL client running
    beside the guardian. The capability is bound to the guardian the token names,
    so handing it on does not widen what it authorizes.

    Returns ``(capability_dict, issued_vc_dict)``.
    """
    state = get_state()

    issued_path = _tmp_path(".json")
    capability_path = _tmp_path(".json")

    try:
        with _op_lock:
            _issue_policy_decision(state, wallet_ids, token_id, user_name, issued_path, request)
            rego_token.create_capability(
                state,
                token_id,
                user_name,
                vc_file=issued_path,
                output_file=capability_path,
            )
        return _read_json(capability_path), _read_json(issued_path)
    finally:
        _safe_unlink(issued_path)
        _safe_unlink(capability_path)
