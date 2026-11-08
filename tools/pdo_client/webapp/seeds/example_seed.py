"""Example webapp seed.

Sets up a small download scenario before the dev server starts, so the webapp
comes up with authorities, a wallet, credentials and an exposed asset already in
place. Three users take part:

    vc_issuer   creates a hand-signing authority attesting locations and
                affiliations, and a system authority for session keys, then
                signs data_user's location and affiliation.
    data_user   creates a wallet, which receives those two credentials.
    data_owner  registers an asset ("data1") and exposes it with the GS and IS
                cards, accepting the two authorities for the facts they read.

data_user's session key is not seeded: the readiness checklist marks it
automatic, and the Use flow obtains it from the session-key authority.

It goes through the webapp's own helpers, so everything shows up in the UI
exactly as if it had been done by hand.

Pass it at launch:

    ./run.sh ... --seed seeds/example_seed.py             # bare metal
    docker/run_webapp.sh ... --seed seeds/example_seed.py # docker

`manage.py seed` injects these globals (no runtime import needed): `state`,
`bindings`, `runner` (app.pdo_runner), `settings`. The `TYPE_CHECKING` import
below is only so VS Code / Pylance shows signatures and autocomplete for them;
it is skipped at runtime.

Each user name must match a key copied into PDO_HOME/keys by bootstrap (i.e. a
key in the --keys-folder). Exposing the asset additionally needs the asset
registry and the template registry.
"""

import time
from typing import TYPE_CHECKING

from app import naming, registry_client
from app.did_utils import make_did
from app.models import AppConfig
from app.views import assets, authorities

if TYPE_CHECKING:
    from seed_context import bindings, runner, settings, state  # noqa: F401

VC_ISSUER = "vc_issuer"
DATA_OWNER = "data_owner"
DATA_USER = "data_user"

GUARDIAN_HOST = "192.168.1.223"
GUARDIAN_PORT = "7900"

ALLOWED_COUNTRY = "US"
ALLOWED_INSTITUTION = "did:example:university"


def login(user_name):
    """Configure the webapp identity so the UI lists this user's contracts."""
    config = AppConfig.get_instance()
    config.public_key = user_name
    config.save()
    print(f"Configured webapp identity: {user_name}")


def sign(authority_id, subject_wallet, fact, claims):
    """The hand-signing authority signs a fact about a wallet, from its one context."""
    context = settings.POC_SIGNING_CONTEXT_NAME
    credential = {
        "type": [fact],
        "issuer": {"id": make_did(authority_id, context)},
        "credentialSubject": {"subject": {"id": make_did(subject_wallet)}, "claims": claims},
    }
    return runner.sign_credential(authority_id, [context], credential, VC_ISSUER)


# vc_issuer: one authority of each kind the scenario needs
registry_office = authorities.create_hand_signing(
    "University registry",
    VC_ISSUER,
    ["LocationCredential", "AffiliationCredential"],
    "Checks enrolment records before signing.",
)
session_keys = authorities.create_session_keys("Session keys", VC_ISSUER)
print(f"[vc_issuer] authorities: {registry_office}, {session_keys}")

# data_user: a wallet holding a location and an affiliation
user_wallet = runner.create_wallet("user wallet", DATA_USER)
naming.set_name(make_did(user_wallet), "user wallet")
time.sleep(1)
for fact, claims in (
    ("LocationCredential", {
        "locatedAt": {"street": "1 Main", "zipCode": "00000", "state": "MA", "country": ALLOWED_COUNTRY},
    }),
    ("AffiliationCredential", {"isMemberOf": ALLOWED_INSTITUTION, "typeOfMembership": "member"}),
):
    runner.wallet_add_vc(user_wallet, sign(registry_office, user_wallet, fact, claims), DATA_USER)
    print(f"[data_user] holds {fact}")

# data_owner: register asset "data1" and expose it with GS + IS
asset_id = runner.create_asset_identity("data1", DATA_OWNER)
asset_did = make_did(asset_id)
registry_asset = registry_client.register_asset(
    name="data1",
    did=asset_did,
    metadata={
        "guardian_url": GUARDIAN_HOST,
        "guardian_port": GUARDIAN_PORT,
        "guardian_type": "download",
        "data_source": "/path",
    },
)
registry_client.update_asset_metadata(
    registry_asset["id"],
    {"asset_registry_url": f"{settings.ASSET_REGISTRY_URL.rstrip('/')}/api/assets/{registry_asset['id']}/"},
)

cards = {t["name"]: t for t in registry_client.policy_templates_for("download", "policy")}
gs, is_ = cards["GEOGRAPHICAL-RESTRICTION"], cards["INSTITUTION-SPECIFIC-RESTRICTION"]
registry_did = authorities.directory_did(registry_office, authorities.HAND_SIGNING)
assets.expose(asset_id, asset_did, DATA_OWNER, {
    "cards": [gs["id"], is_["id"]],
    "parameters": {
        str(gs["id"]): {"allowedCountries": [ALLOWED_COUNTRY]},
        str(is_["id"]): {"allowedInstitutions": [ALLOWED_INSTITUTION]},
    },
    "authorities": {
        "LocationCredential": [registry_did],
        "AffiliationCredential": [registry_did],
        "publicKeyCredential": [authorities.directory_did(session_keys, authorities.SYSTEM)],
    },
})
print(f"[data_owner] exposed data1: {asset_did}")

login(DATA_USER)
print("Seed complete.")
