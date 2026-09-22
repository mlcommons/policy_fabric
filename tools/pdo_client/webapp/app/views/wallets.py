import json
import logging

from django.http import Http404
from django.shortcuts import render

from .. import ledger_client, naming, pdo_runner, registry_client
from ..did_utils import make_did, parse_did
from ..models import AppConfig
from ..url_safe_id import decode_cid, encode_cid
from ._helpers import (
    BaseView,
    JsonView,
    ValidationError,
    redirect_with_msg,
    require,
)

logger = logging.getLogger(__name__)


def _user_wallet_ids(user_name):
    """List the user's wallet contract ids (identity.identity contracts)."""
    return ledger_client.list_identity_ids(user_name)


def _require_user_wallet(user_name, contract_id):
    """Raise 404 unless ``contract_id`` is one of this user's wallets."""
    if contract_id not in _user_wallet_ids(user_name):
        raise Http404(f"wallet not found: {contract_id}")


def _wallet_card(contract_id, name=None):
    did = make_did(contract_id)
    return {
        "contract_id": contract_id,
        "cid_url": encode_cid(contract_id),
        "name": name if name is not None else naming.get_name(did),
        "did": did,
    }


# ============================================================
# Page views (server-rendered)
# ============================================================
class WalletsListView(BaseView):
    """GET: list wallets. POST: create a new wallet (single primary action)."""

    def get(self, request):
        user_name = AppConfig.get_instance().public_key
        ids = _user_wallet_ids(user_name)
        names = naming.get_names([make_did(cid) for cid in ids])
        wallets = [_wallet_card(cid, names[make_did(cid)]) for cid in ids]
        return render(request, "wallets/list.html", {"wallets": wallets})

    def post(self, request):
        name = (request.POST.get("name") or "").strip()
        if not name:
            return redirect_with_msg("/wallets/", "Wallet name is required.", "error")

        user_name = AppConfig.get_instance().public_key
        try:
            contract_id = pdo_runner.create_wallet(name, user_name)
        except Exception as e:
            logger.exception("Failed to create wallet")
            return redirect_with_msg(
                "/wallets/", f"Failed to create wallet: {e}", "error"
            )

        naming.set_name(make_did(contract_id), name)
        return redirect_with_msg("/wallets/", f'Wallet "{name}" created.', "success")


class WalletDetailView(BaseView):
    """GET-only: render the wallet dashboard. All mutating actions are JSON
    endpoints (see ``api.py``)."""

    def get(self, request, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_wallet(user_name, contract_id)
        wallet = _wallet_card(contract_id)

        vcs, vcs_error = {}, None
        try:
            vcs = pdo_runner.wallet_list_vcs(contract_id, user_name)
        except Exception as e:
            logger.exception("Failed to list wallet VCs")
            vcs_error = str(e)

        # A wallet can vouch for something itself (see WalletSignCredentialEndpoint),
        # and the templates are what say which claims that assertion may carry.
        templates, templates_error = [], None
        try:
            templates = registry_client.list_credential_templates()
            for t in templates:
                t["claims_schema_json"] = json.dumps(t.get("claims_schema") or {})
        except Exception as e:
            logger.exception("Failed to fetch credential templates")
            templates_error = str(e)

        return render(
            request,
            "wallets/detail.html",
            {
                "wallet": wallet,
                "vcs": vcs,
                "vcs_error": vcs_error,
                "templates": templates,
                "templates_error": templates_error,
            },
        )


# ============================================================
# JSON endpoints (one logical action each)
# ============================================================
class WalletAddVCEndpoint(JsonView):
    """POST {vc: {...}} — store a VC in the wallet."""

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_wallet(user_name, contract_id)
        vc = require(data, "vc")
        if not isinstance(vc, dict):
            raise ValidationError("'vc' must be a JSON object")

        pdo_runner.wallet_add_vc(contract_id, vc, user_name)
        return {"ok": True, "message": "Credential added."}


class WalletSignCredentialEndpoint(JsonView):
    """POST {template_type, subject_did, claims} — the wallet signs a credential
    itself and stores it in the subject's contract.

    This is a wallet asserting something in its own name, not an authority
    vouching for someone else, so it is signed with the wallet's own contract key
    rather than from a signing context (see
    ``pdo_runner.sign_credential_with_contract_key``). Taken alone that is worth
    nothing — anyone can claim anything about themselves. It becomes evidence when
    a policy checks the signature against a key some authority attested for this
    wallet, which is exactly what FL-IS does with a ``ScriptOwnershipCredential``:
    the wallet claims the script, and the claim only counts because the same
    wallet's key is independently vouched for.

    The credential is stored in whatever contract the subject DID names — for an
    ownership claim, the script asset, so the claim travels with the thing it is
    about.
    """

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_wallet(user_name, contract_id)

        template_type, subject_did = require(data, "template_type", "subject_did")
        claims = data.get("claims") or {}
        if not isinstance(claims, dict):
            raise ValidationError("'claims' must be a JSON object")

        subject_contract_id, _ = parse_did(subject_did)
        credential = {
            "type": [template_type],
            # The bare DID: the contract key sits under no signing context, and a
            # policy matching this issuer against other credentials about the same
            # wallet is matching bare DIDs.
            "issuer": {"id": make_did(contract_id)},
            "credentialSubject": {
                "subject": {"id": make_did(subject_contract_id)},
                "claims": claims,
            },
        }

        signed_vc = pdo_runner.sign_credential_with_contract_key(
            contract_id, credential, user_name
        )
        pdo_runner.wallet_add_vc(subject_contract_id, signed_vc, user_name)
        return {
            "ok": True,
            "message": f"Credential signed by this wallet and stored in {subject_did}.",
        }


class WalletUpdateNameEndpoint(JsonView):
    """POST {name} — set the local display name for this wallet's DID."""

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_wallet(user_name, contract_id)
        name = require(data, "name")

        naming.set_name(make_did(contract_id), name)
        return {"ok": True, "message": "Name updated.", "name": name}
