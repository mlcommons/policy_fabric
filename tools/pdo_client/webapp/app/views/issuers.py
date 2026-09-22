import json
import logging

from django.conf import settings
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

# What the Create Issuer form offers. A wallet key authority is not here: one is
# created for you alongside every external key authority, never on its own.
ISSUER_TYPES = ("manual", "external_key_authority")

KIND_LABELS = {
    "manual": "Manual",
    "external_key_authority": "External Key Authority",
    "wallet_key_authority": "Wallet Key Authority",
}


def _user_manual_issuer_ids(user_name):
    """List the user's "manual" issuer contract ids — signature_authority
    contracts they own that are NOT registered as assets.

    The signature_authority contract type is also reused as the identity
    backing an asset, so the same family appears for both. The asset registry
    is the canonical place that says "this id is an asset," so we use it to
    subtract. The two authorities need no such subtraction: nothing else is
    registered under their families.
    """
    sa_ids = ledger_client.list_signature_authority_ids(user_name)
    if not sa_ids:
        return []
    try:
        asset_ids = {
            parse_did(a["did"])[0] for a in (registry_client.list_assets() or [])
        }
    except Exception:
        logger.exception("Failed to fetch assets while filtering issuers")
        asset_ids = set()
    return [cid for cid in sa_ids if cid not in asset_ids]


def _issuer_ids_by_kind(user_name):
    """This user's issuer contract ids, grouped by kind."""
    return {
        "manual": _user_manual_issuer_ids(user_name),
        "external_key_authority": ledger_client.list_external_key_authority_ids(
            user_name
        ),
        "wallet_key_authority": ledger_client.list_wallet_key_authority_ids(user_name),
    }


def _issuer_card(contract_id, kind, name=None):
    base_did = make_did(contract_id)
    # A manual issuer always signs from its one fixed context, so the DID
    # shown/copied for it is the one credentials are actually issued under —
    # callers never need to know a "signing context" exists at all. The two
    # authorities also sign from a fixed context of their own, but the bare DID
    # names their root key, and a trusted-issuer registration made against the
    # root verifies anything signed below it — so the bare DID is what is shown.
    display_did = (
        make_did(contract_id, settings.POC_SIGNING_CONTEXT_NAME)
        if kind == "manual"
        else base_did
    )
    return {
        "contract_id": contract_id,
        "cid_url": encode_cid(contract_id),
        "name": name if name is not None else naming.get_name(base_did),
        "did": display_did,
        "kind": kind,
        "kind_label": KIND_LABELS.get(kind, kind),
    }


def _issuer_cards(user_name):
    by_kind = _issuer_ids_by_kind(user_name)
    every_id = [cid for ids in by_kind.values() for cid in ids]
    names = naming.get_names([make_did(cid) for cid in every_id])
    return [
        _issuer_card(cid, kind, names[make_did(cid)])
        for kind, ids in by_kind.items()
        for cid in ids
    ]


def _issuer_kind(user_name, contract_id):
    """Return this issuer's kind, or None if ``contract_id`` isn't one of this
    user's issuers."""
    for kind, ids in _issuer_ids_by_kind(user_name).items():
        if contract_id in ids:
            return kind
    return None


def _require_user_issuer(user_name, contract_id):
    """Raise 404 unless ``contract_id`` is one of this user's issuers.
    Returns the issuer's kind."""
    kind = _issuer_kind(user_name, contract_id)
    if kind is None:
        raise Http404(f"issuer not found: {contract_id}")
    return kind


# ============================================================
# Page views (server-rendered)
# ============================================================
class IssuersListView(BaseView):
    """GET: list issuers. POST: create a new issuer (single primary action)."""

    def get(self, request):
        user_name = AppConfig.get_instance().public_key
        issuers = _issuer_cards(user_name)
        return render(request, "issuers/list.html", {"issuers": issuers})

    def post(self, request):
        name = (request.POST.get("name") or "").strip()
        issuer_type = (request.POST.get("issuer_type") or "").strip()
        if not name:
            return redirect_with_msg("/issuers/", "Issuer name is required.", "error")
        if issuer_type not in ISSUER_TYPES:
            return redirect_with_msg("/issuers/", "Select an issuer type.", "error")

        user_name = AppConfig.get_instance().public_key

        # An external key authority arrives with a wallet key authority behind it,
        # and the creation call returns only the one you asked for. Which contract
        # the other is, is answered by noting what was not there a moment ago.
        # The alternative — asking the new authority which issuer it trusts —
        # reads contract state, and that read is served from a 30s cache keyed on
        # the contract's save file, so the first read after creation can pin a
        # pre-registration view of the contract for half a minute. The ledger's
        # own contract index has no such cache and is written when a contract is
        # registered, well before this call returns.
        wkas_before = set()
        if issuer_type == "external_key_authority":
            wkas_before = set(ledger_client.list_wallet_key_authority_ids(user_name))

        try:
            if issuer_type == "manual":
                contract_id = pdo_runner.create_manual_issuer(name, user_name)
            else:
                contract_id = pdo_runner.create_external_key_authority_issuer(
                    name, user_name
                )
        except Exception as e:
            logger.exception("Failed to create issuer")
            return redirect_with_msg(
                "/issuers/", f"Failed to create issuer: {e}", "error"
            )

        naming.set_name(make_did(contract_id), name)

        # Name it after its owner so the two read as a pair in the list; unnamed
        # it would still be listed, just as UNKNOWN.
        if issuer_type == "external_key_authority":
            try:
                new_wkas = (
                    set(ledger_client.list_wallet_key_authority_ids(user_name))
                    - wkas_before
                )
                for wka_id in new_wkas:
                    naming.set_name(make_did(wka_id), f"{name} (wallet keys)")
                if not new_wkas:
                    logger.warning(
                        "No new wallet key authority appeared for %s; it will be "
                        "listed unnamed",
                        contract_id,
                    )
            except Exception:
                logger.exception("Failed to name the wallet key authority")

        return redirect_with_msg("/issuers/", f'Issuer "{name}" created.', "success")


class IssuerDetailView(BaseView):
    """GET-only: render the issuer dashboard. All mutating actions are JSON
    endpoints below."""

    def get(self, request, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        kind = _require_user_issuer(user_name, contract_id)
        issuer = _issuer_card(contract_id, kind)

        vcs, vcs_error = {}, None
        try:
            vcs = pdo_runner.wallet_list_vcs(contract_id, user_name)
        except Exception as e:
            logger.exception("Failed to list issuer VCs")
            vcs_error = str(e)

        # Only manual issuers can sign arbitrary credentials from their
        # (fixed, single) signing context; an external_key_authority's
        # sign_credential does something else entirely (binds a session key
        # to a wallet).
        templates, templates_error = [], None
        if kind == "manual":
            try:
                templates = registry_client.list_credential_templates()
                for t in templates:
                    t["claims_schema_json"] = json.dumps(t.get("claims_schema") or {})
            except Exception as e:
                logger.exception("Failed to fetch credential templates")
                templates_error = str(e)

        return render(
            request,
            "issuers/detail.html",
            {
                "issuer": issuer,
                "vcs": vcs,
                "vcs_error": vcs_error,
                "templates": templates,
                "templates_error": templates_error,
            },
        )


# ============================================================
# JSON endpoints (one logical action each)
# ============================================================
class IssuerAddVCEndpoint(JsonView):
    """POST {vc: {...}} — store a VC in the issuer's credential store."""

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_issuer(user_name, contract_id)
        vc = require(data, "vc")
        if not isinstance(vc, dict):
            raise ValidationError("'vc' must be a JSON object")

        pdo_runner.wallet_add_vc(contract_id, vc, user_name)
        return {"ok": True, "message": "Credential added."}


class IssuerUpdateNameEndpoint(JsonView):
    """POST {name} — set the local display name for this issuer's DID."""

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_issuer(user_name, contract_id)
        name = require(data, "name")

        naming.set_name(make_did(contract_id), name)
        return {"ok": True, "message": "Name updated.", "name": name}


class IssuerSignCredentialEndpoint(JsonView):
    """POST {template_type, subject_did, claims} — sign a VC from the issuer's
    fixed "poc" signing context and store it directly in the subject's
    wallet. Manual issuers only: an external_key_authority's sign_credential
    is a different operation (binding a session key to a wallet), not
    arbitrary VC issuance.
    """

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        kind = _require_user_issuer(user_name, contract_id)
        if kind != "manual":
            raise ValidationError("Only manual issuers can sign credentials.")

        template_type, subject_did = require(data, "template_type", "subject_did")
        claims = data.get("claims") or {}
        if not isinstance(claims, dict):
            raise ValidationError("'claims' must be a JSON object")

        signing_context = settings.POC_SIGNING_CONTEXT_NAME
        subject_contract_id, _ = parse_did(subject_did)
        credential = {
            "type": [template_type],
            "issuer": {"id": make_did(contract_id, signing_context)},
            "credentialSubject": {
                "subject": {
                    "id": make_did(subject_contract_id),
                },
                "claims": claims,
            },
        }

        signed_vc = pdo_runner.sign_credential(
            contract_id,
            signing_context_path=[signing_context],
            credential_dict=credential,
            user_name=user_name,
        )
        # Store the signed credential straight into the subject's wallet.
        pdo_runner.wallet_add_vc(subject_contract_id, signed_vc, user_name)
        return {
            "ok": True,
            "message": f"Credential issued and stored in {subject_did}.",
        }
