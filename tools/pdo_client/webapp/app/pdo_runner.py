"""PDO operations using the decentralized helpers.

Wallets are ``identity.identity`` contracts. Asset identities and "manual"
issuers are ``signature_authority`` contracts (a superset: it inherits
identity's ops and adds signing-context issuance). The op classes behind
``add_vc`` / ``get_vc_list`` / ``get_vp`` / ``register_signing_context`` /
``list_signing_contexts`` are literally the same across ``identity``,
``signature_authority``, and ``external_key_authority`` (each family aliases
the one below it), so the ``signature_authority`` decentralized module below
is used as the one family-agnostic entry point for all of them by contract_id
— only ``sign_credential`` is NOT reusable against an ``external_key_authority``
contract (it's a distinct, non-aliased op there).

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
import pdo.identity.decentralized.identity as identity_contract
import pdo.identity.decentralized.signature_authority as signature_authority
import pdo.rego.decentralized.rego_policy_agent as rego_policy_agent
import pdo.rego.decentralized.rego_token as rego_token
from pdo.identity.plugins.identity import cmd_sign_with_contract_key

from .pdo_state import get_state

logger = logging.getLogger(__name__)
_op_lock = threading.Lock()

PUBLIC_KEY_CREDENTIAL_TYPE = "publicKeyCredential"

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
# Identity ops shared by asset identities and issuers
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


def create_manual_issuer(name, user_name):
    """Create a "manual" issuer: a signature_authority contract the owner
    hand-signs credentials from.

    ``name`` is used verbatim as the contract's on-chain description. The
    issuer is set up with a single fixed signing context
    (``cfg.POC_SIGNING_CONTEXT_NAME``) used for all credentials it signs —
    the webapp doesn't expose signing-context management in the UI.

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


def create_external_key_authority_issuer(name, user_name):
    """Create an external_key_authority issuer. This single call also
    creates and trusts its backing wallet_key_authority (see
    ``cmd_create_external_key_authority``).

    Unlike ``create_signature_authority``, ``cmd_create_external_key_authority``
    takes no ``description`` argument — the eka's (and its wka's) description
    comes fixed from their context templates, so ``name`` is accepted here only
    for call-site symmetry with the other ``create_*`` functions and isn't
    otherwise used.

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
    """Return the wallet's stored VCs as a dict (type → vc)."""
    state = get_state()
    with _op_lock:
        result = signature_authority.get_vc_list(state, contract_id, user_name)
    if isinstance(result, str):
        return json.loads(result) if result else {}
    return result or {}


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
        with open(signed_path) as f:
            return json.load(f)
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


# ============================================================
# Asset policy ops (owner-side)
# ============================================================
def create_asset_policy(description, guardian_url_port, user_name, rego_modules):
    """Create a rego_policy_agent + rego_token, provision the chosen Rego
    subpolicies, and register the policy as a trusted issuer on the token.

    ``rego_modules`` is a list of ``[subpolicy_id, rego_source]`` pairs (the
    policies the owner selected). ``cmd_set_rego_policy`` reads each module from
    a file, so each source is materialized to a temp file first.

    Returns ``{'policy_contract_id', 'token_contract_id'}``.
    """
    state = get_state()

    # materialize the selected subpolicies as files (cmd_set_rego_policy reads paths)
    module_paths = []
    module_args = []
    for subpolicy_id, source in rego_modules:
        path = _tmp_path(".rego")
        with open(path, "w") as f:
            f.write(source)
        module_paths.append(path)
        module_args.append([subpolicy_id, path])

    try:
        with _op_lock:
            policy_id = rego_policy_agent.create_rego_policy_agent(
                state, user_name, description=description
            )
            time.sleep(1)
            rego_policy_agent.set_rego_policy(
                state, policy_id, user_name, module=module_args
            )
            time.sleep(1)
            token_id = rego_token.create_rego_token(
                state, user_name, guardian_url_port
            )
            time.sleep(1)
            rego_token.register_trusted_issuer(
                state,
                token_id,
                policy_id,
                user_name,
                credential_types=["policy_decision"],
                path=["__ISSUER__"],
            )
    finally:
        for path in module_paths:
            _safe_unlink(path)
    return {"policy_contract_id": policy_id, "token_contract_id": token_id}


def set_policy_data(policy_id, policy_data, user_name):
    """Write the policy data dict into a policy agent contract."""
    state = get_state()
    data_path = _tmp_json(policy_data)
    try:
        with _op_lock:
            rego_policy_agent.set_policy_data(
                state, policy_id, user_name, data=data_path
            )
    finally:
        _safe_unlink(data_path)


def get_policy_data(policy_id, user_name):
    """Return the policy agent's current policy data as a dict."""
    state = get_state()
    with _op_lock:
        raw = rego_policy_agent.get_policy_data(state, policy_id, user_name)
    if isinstance(raw, str):
        return json.loads(raw) if raw else {}
    return raw or {}


def register_policy_trusted_issuer(
    policy_id, issuer_id, user_name, *, path, credential_types
):
    """Register a signature authority as a trusted issuer on a policy agent
    for one or more credential types at a given context path.
    """
    state = get_state()
    with _op_lock:
        rego_policy_agent.register_trusted_issuer(
            state,
            policy_id,
            issuer_id,
            user_name,
            path=path,
            credential_types=credential_types,
        )


def list_policy_trusted_issuers(policy_id, user_name):
    """Return the policy agent's registered trusted issuers as a dict."""
    state = get_state()
    with _op_lock:
        raw = rego_policy_agent.list_trusted_issuers(state, policy_id, user_name)
    if isinstance(raw, str):
        return json.loads(raw) if raw else {}
    return raw or {}


def list_token_trusted_issuers(token_id, user_name):
    """Return the rego token's registered trusted issuers as a dict.

    The single entry is the policy agent registered at expose-time; its
    key is the policy agent's contract id.
    """
    state = get_state()
    with _op_lock:
        raw = rego_token.list_trusted_issuers(state, token_id, user_name)
    if isinstance(raw, str):
        return json.loads(raw) if raw else {}
    return raw or {}


def _find_trusted_issuer_for_type(raw_issuers, credential_type):
    """Return the contract_id of the first trusted issuer registered for
    ``credential_type`` in a raw trusted-issuers map (as returned by a
    ``list_trusted_issuers`` call), or ``None`` if none is registered.
    """
    issuers = (
        json.loads(raw_issuers) if isinstance(raw_issuers, str) else (raw_issuers or {})
    )
    return next(
        (
            contract_id
            for contract_id, entries in issuers.items()
            for entry in (entries or [])
            if credential_type in (entry.get("credential_types") or [])
        ),
        None,
    )


# ============================================================
# Asset use ops (consumer-side)
# ============================================================
def _resolve_policy_id(state, token_id, user_name):
    """The policy agent contract id a token names, or ``None`` if it names none.

    The caller must hold ``_op_lock``.
    """
    issuers_raw = rego_token.list_trusted_issuers(state, token_id, user_name)
    issuers = (
        json.loads(issuers_raw) if isinstance(issuers_raw, str) else (issuers_raw or {})
    )
    if not issuers:
        return None
    return next(iter(issuers.keys()))


def get_policy_requirements(token_id, user_name):
    """Return an asset policy's per-role credential requirements.

    Shaped as ``{role: [credential_type, ...]}`` — the union the policy's
    subpolicies declared. Empty if the token names no policy. The consumer needs
    this before presenting anything, since it decides which roles must be filled
    and from where.
    """
    state = get_state()
    with _op_lock:
        policy_id = _resolve_policy_id(state, token_id, user_name)
        if policy_id is None:
            return {}
        requirements = rego_policy_agent.get_requirements(state, policy_id, user_name)
    if isinstance(requirements, str):
        return json.loads(requirements) if requirements else {}
    return requirements or {}


def ensure_public_key_credential(wallet_ids, token_id, user_name, keys_dir_for):
    """Ensure a publicKeyCredential exists wherever the asset's policy expects one.

    A policy asks for the credential under a particular role, and that role's
    wallet is the one that must hold it — so this looks at each role the policy
    requires it for and binds a fresh session key to that role's wallet, through
    the policy's trusted external_key_authority, which stores the issued
    credential directly in the wallet.

    ``wallet_ids`` maps role to wallet contract id; ``keys_dir_for(wallet_id)``
    returns where that wallet's session keys live. No-op for a role whose wallet
    already holds one.

    Returns the list of roles a credential was obtained for. Raises ``ValueError``
    if the credential is required but no trusted issuer is registered for it, or
    if a role that needs one has no wallet.
    """
    state = get_state()
    obtained = []
    with _op_lock:
        policy_id = _resolve_policy_id(state, token_id, user_name)
        if policy_id is None:
            return obtained

        requirements = rego_policy_agent.get_requirements(state, policy_id, user_name)
        roles = [
            role
            for role, types in (requirements or {}).items()
            if PUBLIC_KEY_CREDENTIAL_TYPE in types
        ]
        if not roles:
            return obtained

        eka_id = None
        for role in roles:
            wallet_id = wallet_ids.get(role)
            if not wallet_id:
                raise ValueError(
                    f"The policy requires a {PUBLIC_KEY_CREDENTIAL_TYPE} for the "
                    f"'{role}' role, but no wallet was chosen for it."
                )

            vc_map_raw = signature_authority.get_vc_list(state, wallet_id, user_name)
            vc_map = (
                json.loads(vc_map_raw) if isinstance(vc_map_raw, str) else (vc_map_raw or {})
            )
            if PUBLIC_KEY_CREDENTIAL_TYPE in vc_map:
                continue

            if eka_id is None:
                policy_issuers_raw = rego_policy_agent.list_trusted_issuers(
                    state, policy_id, user_name
                )
                eka_id = _find_trusted_issuer_for_type(
                    policy_issuers_raw, PUBLIC_KEY_CREDENTIAL_TYPE
                )
                if eka_id is None:
                    raise ValueError(
                        "This asset's policy requires a publicKeyCredential, but no "
                        "trusted issuer is registered for it."
                    )

            external_key_authority.bind_external_key(
                state, eka_id, wallet_id, user_name, keys_dir=keys_dir_for(wallet_id)
            )
            time.sleep(1)
            obtained.append(role)

    return obtained


def _issue_policy_decision(state, wallet_ids, token_id, user_name, issued_path):
    """Have an asset's policy judge a presentation, writing the verdict to ``issued_path``.

    1. Read the token's trusted-issuer list to discover the policy agent.
    2. Get the per-role credential requirements from the policy.
    3. Build one VP per role, from that role's wallet, covering that role's types.
    4. Wrap them as the role-keyed presentation the rego_policy_agent expects.
    5. Issue a policy_decision credential from the policy.

    ``wallet_ids`` maps role to wallet contract id. A role is a group of evidence
    about one subject, so each role is presented from the wallet holding that
    subject's credentials — the requester's own wallet for ``User``, the script's
    for ``Script``.

    This is where every policy-gated flow starts; what follows differs only in what
    the resulting capability is handed to. The caller must hold ``_op_lock``.
    """
    presentation_path = _tmp_path(".json")
    vp_paths = []

    try:
        policy_id = _resolve_policy_id(state, token_id, user_name)
        time.sleep(1)
        if policy_id is None:
            raise ValueError("No trusted issuers registered on this token contract.")

        # rego_policy_agent.get_requirements returns { role: [credential_type, ...] }
        requirements = rego_policy_agent.get_requirements(state, policy_id, user_name)
        time.sleep(1)
        if not requirements:
            raise ValueError("This asset's policy declares no credential requirements.")

        presentation = {}
        for role, types in requirements.items():
            wallet_id = wallet_ids.get(role)
            if not wallet_id:
                raise ValueError(f"No wallet was chosen for the '{role}' role.")

            vp_path = _tmp_path(".json")
            vp_paths.append(vp_path)
            signature_authority.get_vp(
                state,
                wallet_id,
                user_name,
                types=sorted(set(types)),
                output_file=vp_path,
            )
            time.sleep(1)
            with open(vp_path) as f:
                presentation[role] = json.load(f)

        with open(presentation_path, "w") as f:
            json.dump(presentation, f)

        rego_policy_agent.issue_policy_credential(
            state,
            policy_id,
            user_name,
            presentation=presentation_path,
            issued_credential=issued_path,
        )
        time.sleep(1)
    finally:
        for vp_path in vp_paths:
            _safe_unlink(vp_path)
        _safe_unlink(presentation_path)


def use_asset(*, wallet_ids, token_id, guardian_url_port, user_name, output_dir=None):
    """Run the consumer download flow against a rego_policy_agent.

    Issues a policy decision credential and redeems the capability it authorizes
    at the guardian, downloading the (encrypted) data.

    Returns ``(output_path, issued_vc_dict)``.
    """
    state = get_state()
    output_dir = output_dir or cfg.DOWNLOAD_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    issued_path = _tmp_path(".json")
    output_path = os.path.join(output_dir, f"download_{os.urandom(4).hex()}.bin")

    try:
        with _op_lock:
            _issue_policy_decision(state, wallet_ids, token_id, user_name, issued_path)
            rego_token.do_operation(
                state,
                token_id,
                user_name,
                guardian_url_port,
                vc_file=issued_path,
                output_file=output_path,
            )

        with open(issued_path) as f:
            issued_vc = json.load(f)
        return output_path, issued_vc
    finally:
        _safe_unlink(issued_path)


def create_capability(*, wallet_ids, token_id, user_name):
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
            _issue_policy_decision(state, wallet_ids, token_id, user_name, issued_path)
            rego_token.create_capability(
                state,
                token_id,
                user_name,
                vc_file=issued_path,
                output_file=capability_path,
            )

        with open(capability_path) as f:
            capability = json.load(f)
        with open(issued_path) as f:
            issued_vc = json.load(f)
        return capability, issued_vc
    finally:
        _safe_unlink(issued_path)
        _safe_unlink(capability_path)
