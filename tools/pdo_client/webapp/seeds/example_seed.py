"""Example webapp seed.

Runs a small end-to-end rego-policy flow before the dev server starts, so the
webapp comes up with wallets, credentials, and an exposed asset already in
place. Three users take part:

    vc_issuer   creates a manual issuer (which is set up with the "poc"
                signing context automatically), then issues three verifiable
                credentials (public key / location / affiliation).
    data_user   creates a wallet and stores those three credentials.
    data_owner  registers an asset ("data1") and exposes it behind a
                rego_policy_agent provisioned with the GS + IS subpolicies.

It goes through the webapp's own helpers (`runner` = app.pdo_runner) and the
asset/template registries (`registry_client`), so everything shows up in the
UI exactly as if it had been done by hand.

Pass it at launch:

    ./run.sh ... --seed seeds/example_seed.py             # bare metal
    docker/run_webapp.sh ... --seed seeds/example_seed.py # docker

`manage.py seed` injects these globals (no runtime import needed): `state`,
`bindings`, `runner` (app.pdo_runner), `settings`. The `TYPE_CHECKING` import
below is only so VS Code / Pylance shows signatures and autocomplete for them;
it is skipped at runtime.

Each user name must match a key copied into PDO_HOME/keys by bootstrap (i.e. a
key in the --keys-folder). Exposing the asset additionally needs the asset
registry, the template registry (for the GS/IS rego source), and a guardian
running.
"""

import time
from typing import TYPE_CHECKING

from pdo.authority.session_key import generate_rsa_keypair, load_public_pem

from app import naming, registry_client, session_keys
from app.did_utils import make_did
from app.models import AppConfig

if TYPE_CHECKING:
    from seed_context import bindings, runner, settings, state  # noqa: F401

# -----------------------------------------------------------------
# Participants and fixtures
# -----------------------------------------------------------------
VC_ISSUER = "vc_issuer"
DATA_OWNER = "data_owner"
DATA_USER = "data_user"

SIGNING_CONTEXT = settings.POC_SIGNING_CONTEXT_NAME

GUARDIAN_HOST = "192.168.1.223"
GUARDIAN_PORT = "7900"

# The subpolicies selected for the demo asset and the policy data they read
# (GS "geographical-restriction" -> allowedCountries, IS
# "institution-specific-restriction" -> allowedInstitutions). The template names
# are the policy-card folder names, uppercased, as the registry seeds them.
SELECTED_POLICIES = ["GEOGRAPHICAL-RESTRICTION", "INSTITUTION-SPECIFIC-RESTRICTION"]
ALLOWED_COUNTRY = "US"
ALLOWED_INSTITUTION = "did:example:university"

# Credential types the GS/IS subpolicies require; the data owner trusts the
# vc_issuer's "poc" signing context for all of them.
REQUIRED_CREDENTIAL_TYPES = [
    "publicKeyCredential",
    "LocationCredential",
    "AffiliationCredential",
]

def login(user_name):
    """Configure the webapp identity so the UI lists this user's contracts."""
    config = AppConfig.get_instance()
    config.public_key = user_name
    config.save()
    print(f"Configured webapp identity: {user_name}")


def issue_vc(issuer_wallet, subject_wallet, vc_type, claims):
    """vc_issuer signs a `vc_type` credential for `subject_wallet`.

    Mirrors the webapp's WalletSignCredential endpoint: the credential is
    issued from the "poc" signing context and bound to the subject's DID.
    """
    credential = {
        "type": [vc_type],
        "issuer": {"id": make_did(issuer_wallet, SIGNING_CONTEXT)},
        "credentialSubject": {
            "subject": {"id": make_did(subject_wallet)},
            "claims": claims,
        },
    }
    return runner.sign_credential(
        issuer_wallet,
        signing_context_path=[SIGNING_CONTEXT],
        credential_dict=credential,
        user_name=VC_ISSUER,
    )


# -----------------------------------------------------------------
# vc_issuer: manual issuer (signature_authority), set up with the "poc"
# signing context automatically by create_manual_issuer.
# -----------------------------------------------------------------
issuer_wallet = runner.create_manual_issuer("issuer wallet", VC_ISSUER)
naming.set_name(make_did(issuer_wallet), "issuer wallet")
print(f"[vc_issuer] issuer: {issuer_wallet}")
time.sleep(1)

# -----------------------------------------------------------------
# data_user: wallet
# -----------------------------------------------------------------
user_wallet = runner.create_wallet("user wallet", DATA_USER)
naming.set_name(make_did(user_wallet), "user wallet")
print(f"[data_user] wallet: {user_wallet}")
time.sleep(1)

# data_user generates a session-style RSA key pair by hand (mirroring what an
# external_key_authority would normally generate and bind), written to the
# same place app.session_keys looks when decrypting a download for this
# wallet. Its public key is embedded in the public-key credential below, so
# the guardian encrypts downloaded data to it and data_user can decrypt with
# the matching private key.
user_keys_dir = session_keys.keys_dir(DATA_USER, user_wallet)
generate_rsa_keypair(user_keys_dir)
user_session_public_key = load_public_pem(user_keys_dir)
print("[data_user] generated session key")

# -----------------------------------------------------------------
# vc_issuer -> data_user: public-key, location, and affiliation VCs
# -----------------------------------------------------------------
signed_vcs = {
    "publicKeyCredential": issue_vc(
        issuer_wallet,
        user_wallet,
        "publicKeyCredential",
        {"key": user_session_public_key},
    ),
    "LocationCredential": issue_vc(
        issuer_wallet,
        user_wallet,
        "LocationCredential",
        {
            "locatedAt": {
                "street": "1 Main",
                "zipCode": "00000",
                "state": "MA",
                "country": ALLOWED_COUNTRY,
            }
        },
    ),
    "AffiliationCredential": issue_vc(
        issuer_wallet,
        user_wallet,
        "AffiliationCredential",
        {"isMemberOf": ALLOWED_INSTITUTION, "typeOfMembership": "member"},
    ),
}
for vc_type in signed_vcs:
    print(f"[vc_issuer] issued {vc_type} VC")

# data_user stores each credential in their wallet.
for vc_type, vc in signed_vcs.items():
    runner.wallet_add_vc(user_wallet, vc, DATA_USER)
    print(f"[data_user] stored {vc_type} VC")

# -----------------------------------------------------------------
# data_owner: register asset "data1"
# -----------------------------------------------------------------
asset_contract_id = runner.create_asset_identity("data1", DATA_OWNER)
asset_did = make_did(asset_contract_id)
registry_asset = registry_client.register_asset(
    name="data1",
    did=asset_did,
    metadata={
        "guardian_url": GUARDIAN_HOST,
        "guardian_port": GUARDIAN_PORT,
        "data_source": "/path",
    },
)
registry_pk = registry_asset["id"]
registry_client.update_asset_metadata(
    registry_pk,
    {
        "asset_registry_url": (
            f"{settings.ASSET_REGISTRY_URL.rstrip('/')}/api/assets/{registry_pk}/"
        )
    },
)
print(f"[data_owner] registered asset data1: {asset_did}")

# -----------------------------------------------------------------
# data_owner: expose the asset behind a rego_policy_agent (GS + IS subpolicies)
# -----------------------------------------------------------------
guardian = f"http://{GUARDIAN_HOST}:{GUARDIAN_PORT}"

# pull the selected subpolicies' rego source from the template registry
templates = {t["name"]: t for t in registry_client.list_policy_templates()}
rego_modules = [[name, templates[name]["rego_source"]] for name in SELECTED_POLICIES]

policy = runner.create_asset_policy(
    "Policy for data1", guardian, DATA_OWNER, rego_modules
)

policy_data = {
    "allowedCountries": [ALLOWED_COUNTRY],
    "allowedInstitutions": [ALLOWED_INSTITUTION],
}
runner.set_policy_data(policy["policy_contract_id"], policy_data, DATA_OWNER)

# trust the vc_issuer's "poc" context for the credential types the policy needs,
# so the contract's signature verification of the presented VCs succeeds.
runner.register_policy_trusted_issuer(
    policy["policy_contract_id"],
    issuer_wallet,
    DATA_OWNER,
    path=[SIGNING_CONTEXT],
    credential_types=REQUIRED_CREDENTIAL_TYPES,
)

registry_client.update_asset_metadata_by_did(
    asset_did,
    {
        "policy_contract": make_did(policy["token_contract_id"]),
        "policy_data": policy_data,
    },
)
print(f"[data_owner] exposed data1 (token {policy['token_contract_id']})")

# Land the webapp on the data_user identity (change to whichever user you want
# the browser session to start as).
login(DATA_USER)
print("Seed complete.")
