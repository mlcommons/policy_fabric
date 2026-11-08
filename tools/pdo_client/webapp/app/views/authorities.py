"""The Authorities page: the operator's side of establishing facts.

Three kinds of authority, which a policy cannot tell apart:

* **hand-signing** -- a person or office signs after its own review
  (a signature_authority, signing from one fixed context);
* **rule-based** -- a Rego rule over input credentials from authorities it
  accepts (a policy agent whose policy is an authority card);
* **system** -- ledger or cryptographic facts: the session-key authority and the
  wallet key authority created with it.

Every authority is recorded in the directory (the asset registry) when it is
created, with the facts it issues, so owners can find it and accept it.
"""

import logging

from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from .. import ledger_client, naming, pdo_runner, registry_client, schemas, trust
from ..credentials import PUBLIC_KEY, WALLET_KEY, trusted_types
from ..did_utils import DID_PREFIX, make_did, parse_did
from ..models import AppConfig
from ..url_safe_id import decode_cid, encode_cid
from ._helpers import BaseView, JsonView, ValidationError, redirect_with_msg, require

logger = logging.getLogger(__name__)

HAND_SIGNING = "hand-signing"
RULE_BASED = "rule-based"
SYSTEM = "system"

SESSION_KEY_CHECKS = (
    "Binds a session key to a wallet, when the wallet's ledger-registered key signs for it."
)
WALLET_KEY_CHECKS = "Attests the verifying key a wallet is registered with on the ledger."


def _hand_signing_ids(user_name):
    """The user's signature_authority contracts that are not assets.

    The same contract family backs an asset's identity; the asset registry is the
    canonical place that says "this id is an asset", so it is subtracted.
    """
    ids = ledger_client.list_signature_authority_ids(user_name)
    if not ids:
        return []
    assets = {parse_did(a["did"])[0] for a in registry_client.list_assets()}
    return [cid for cid in ids if cid not in assets]


def _rule_based_ids(user_name):
    """The user's policy agents the directory lists as rule-based authorities; the
    others are the policies of their assets."""
    listed = {parse_did(a["did"])[0] for a in registry_client.list_authorities() if a["kind"] == RULE_BASED}
    return [cid for cid in ledger_client.list_policy_agent_ids(user_name) if cid in listed]


def _ids_by_kind(user_name):
    return {
        HAND_SIGNING: _hand_signing_ids(user_name),
        RULE_BASED: _rule_based_ids(user_name),
        SYSTEM: ledger_client.list_external_key_authority_ids(user_name)
        + ledger_client.list_wallet_key_authority_ids(user_name),
    }


def directory_did(contract_id, kind):
    """The DID an authority is trusted under: a hand-signing authority signs from
    its one fixed context, the others from contexts below their root key."""
    if kind == HAND_SIGNING:
        return make_did(contract_id, settings.POC_SIGNING_CONTEXT_NAME)
    return make_did(contract_id)


def _card(contract_id, kind, name):
    """One of the user's authorities, as its directory entry lists it: every
    authority this webapp creates is listed when it is created."""
    did = directory_did(contract_id, kind)
    entry = registry_client.get_authority_by_did(did)
    return {
        "contract_id": contract_id,
        "cid_url": encode_cid(contract_id),
        "name": name,
        "did": did,
        "kind": kind,
        "kind_label": trust.KIND_LABELS[kind],
        "facts": entry["facts"],
        "checks": entry["checks"],
        "directory_id": entry["id"],
        "inputs": entry["inputs"],
    }


def _cards(user_name):
    by_kind = _ids_by_kind(user_name)
    names = naming.get_names([make_did(cid) for ids in by_kind.values() for cid in ids])
    return [_card(cid, kind, names[make_did(cid)]) for kind, ids in by_kind.items() for cid in ids]


def _require_authority(user_name, contract_id):
    """The kind of one of this user's authorities, or 404."""
    for kind, ids in _ids_by_kind(user_name).items():
        if contract_id in ids:
            return kind
    raise Http404(f"authority not found: {contract_id}")


def _record(contract_id, kind, name, user_name, *, facts, checks, inputs, sources, metadata):
    """Name an authority locally and list it in the directory."""
    naming.set_name(make_did(contract_id), name)
    registry_client.register_authority({
        "did": directory_did(contract_id, kind),
        "name": name,
        "kind": kind,
        "operator": user_name,
        "facts": facts,
        "checks": checks,
        "inputs": inputs,
        "sources": sources,
        "metadata": metadata,
    })


# ============================================================
# Creation
# ============================================================
def create_hand_signing(name, user_name, facts, checks):
    contract_id = pdo_runner.create_hand_signing_authority(name, user_name)
    _record(contract_id, HAND_SIGNING, name, user_name,
            facts=facts, checks=checks, inputs={}, sources=[], metadata={})
    return contract_id


def create_session_keys(name, user_name):
    """A session-key authority, and the wallet key authority it comes with.

    The creation returns only the first; the second is found as the wallet key
    authority that was not there a moment ago -- reading it back from the new
    contract's trusted issuers would hit a 30s state cache keyed on its save file.
    """
    before = set(ledger_client.list_wallet_key_authority_ids(user_name))
    contract_id = pdo_runner.create_session_key_authority(user_name)
    _record(contract_id, SYSTEM, name, user_name,
            facts=["publicKeyCredential"], checks=SESSION_KEY_CHECKS, inputs={}, sources=[], metadata={})
    for wka_id in set(ledger_client.list_wallet_key_authority_ids(user_name)) - before:
        _record(wka_id, SYSTEM, f"{name} (wallet keys)", user_name,
                facts=["WalletVerifyingKeyCredential"], checks=WALLET_KEY_CHECKS, inputs={}, sources=[], metadata={})
    return contract_id


def create_rule_based(name, user_name, template_id):
    """A policy agent issuing the card's fact by the card's rule, the rule's
    module id being the card's name."""
    card = registry_client.get_authority_template(template_id)
    if card["parameters_schema"]["properties"]:
        raise ValueError(f"The authority card {card['name']} has parameters, which this page cannot set.")
    contract_id = pdo_runner.create_policy_agent(name, user_name, [[card["name"], card["rego_source"]]])
    pdo_runner.set_policy_data(contract_id, {card["name"]: {}}, user_name)
    _record(contract_id, RULE_BASED, name, user_name, facts=[card["issues"]], checks=card["rule"],
            inputs=card["requirements"], sources=[], metadata={"card": card["name"]})
    return contract_id


# ============================================================
# Pages
# ============================================================
class AuthoritiesListView(BaseView):
    """GET: the user's authorities. POST: create one."""

    def get(self, request):
        user_name = AppConfig.get_instance().public_key
        credential_templates = registry_client.list_credential_templates()
        authority_templates = registry_client.list_authority_templates()
        names = {t["template_type"]: t["display_name"] for t in credential_templates}

        authorities = _cards(user_name)
        for a in authorities:
            a["fact_names"] = [names[t] for t in a["facts"]]
        for t in authority_templates:
            t["issues_name"] = names[t["issues"]]
            t["input_names"] = sorted({names[i] for types in t["requirements"].values() for i in types})

        return render(request, "authorities/list.html", {
            "authorities": authorities,
            # what a person can sign for: not the facts the system establishes,
            # nor the ones requesters sign about themselves
            "attestable": [
                t for t in credential_templates
                if not t["self_asserted"] and t["template_type"] not in (PUBLIC_KEY, WALLET_KEY)
            ],
            "authority_templates": authority_templates,
        })

    def post(self, request):
        name = request.POST.get("name", "").strip()
        kind = request.POST.get("kind", "").strip()
        user_name = AppConfig.get_instance().public_key
        if not name:
            return redirect_with_msg("/authorities/", "An authority needs a name.", "error")

        try:
            if kind == HAND_SIGNING:
                facts = request.POST.getlist("facts")
                checks = request.POST.get("checks", "").strip()
                if not facts:
                    return redirect_with_msg(
                        "/authorities/", "Choose the facts this authority attests.", "error"
                    )
                if not checks:
                    return redirect_with_msg("/authorities/", "Say what this authority checks.", "error")
                create_hand_signing(name, user_name, facts, checks)
            elif kind == RULE_BASED:
                template_id = request.POST.get("template", "")
                if not template_id:
                    return redirect_with_msg("/authorities/", "Choose an authority card.", "error")
                create_rule_based(name, user_name, template_id)
            elif kind == SYSTEM:
                create_session_keys(name, user_name)
            else:
                return redirect_with_msg("/authorities/", "Choose a kind of authority.", "error")
        except Exception as e:
            logger.exception("Failed to create authority")
            return redirect_with_msg("/authorities/", f"Failed to create authority: {e}", "error")

        return redirect_with_msg("/authorities/", f'Authority "{name}" created.', "success")


class AuthorityDetailView(BaseView):
    """GET: one authority. A hand-signing one signs from here; a rule-based one
    shows its locked rule and the authorities it accepts for its inputs."""

    def get(self, request, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        kind = _require_authority(user_name, contract_id)
        authority = _card(contract_id, kind, naming.get_name(make_did(contract_id)))
        ctx = {"authority": authority, "error": None, "wallets": _own_wallets(user_name)}

        templates = registry_client.credential_templates_by_type()
        names = {t: v["display_name"] for t, v in templates.items()}
        authority["fact_names"] = [names[t] for t in authority["facts"]]

        if kind == HAND_SIGNING:
            ctx["sign_templates"] = [
                {
                    "type": t,
                    "name": names[t],
                    "meaning": templates[t]["meaning"],
                    "subject_kinds": templates[t]["subject_kinds"],
                    "schema": templates[t]["json_schema"],
                }
                for t in authority["facts"]
            ]
        elif kind == RULE_BASED:
            try:
                policy = pdo_runner.get_rego_policy(contract_id, user_name)
                trusted = pdo_runner.list_trusted_issuers(contract_id, user_name)
                facts = sorted({t for types in policy["requirements"].values() for t in types})
                [[_, rule_source]] = policy["rego_modules"]
                ctx["rule"] = {"credential_type": policy["credential_type"], "rego_module": rule_source}
                ctx["issued_name"] = names[policy["credential_type"]]
                ctx["needs_project"] = "project" in templates[policy["credential_type"]]["json_schema"]["properties"]
                ctx["trust_rows"] = trust.panel(facts, trusted, registry_client.list_authorities(), names)
            except Exception as e:
                logger.exception("Failed to read the authority's rule")
                ctx["error"] = str(e)
        return render(request, "authorities/detail.html", ctx)


def _own_wallets(user_name):
    ids = ledger_client.list_identity_ids(user_name)
    names = naming.get_names([make_did(cid) for cid in ids])
    return [{"contract_id": cid, "did": make_did(cid), "name": names[make_did(cid)]} for cid in ids]


# ============================================================
# JSON endpoints
# ============================================================
class AuthorityUpdateNameEndpoint(JsonView):
    """POST {name}"""

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        kind = _require_authority(user_name, contract_id)
        name = require(data, "name")
        naming.set_name(make_did(contract_id), name)
        entry = registry_client.get_authority_by_did(directory_did(contract_id, kind))
        registry_client.update_authority(entry["id"], {"name": name})
        return {"ok": True, "message": "Name updated.", "name": name}


class AuthoritySignCredentialEndpoint(JsonView):
    """POST {template_type, subject_did, holder_did, claims} -- a hand-signing
    authority signs one of the facts it attests, after checking the claims against
    the fact's schema, and delivers it to the wallet that should hold it: the
    subject's own, or another (a member holding a copy of a credential about their
    PI, say). The subject may be any DID; the holder is a PDO wallet.
    """

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        if _require_authority(user_name, contract_id) != HAND_SIGNING:
            raise ValidationError("Only hand-signing authorities sign on request.")

        fact, subject_did, holder_did = require(data, "template_type", "subject_did", "holder_did")
        entry = registry_client.get_authority_by_did(directory_did(contract_id, HAND_SIGNING))
        if fact not in entry["facts"]:
            raise ValidationError(f"This authority does not attest {fact}.")

        claims = data.get("claims")
        if not isinstance(claims, dict):
            raise ValidationError("'claims' must be a JSON object")
        problems = schemas.errors(claims, registry_client.credential_templates_by_type()[fact]["json_schema"])
        if problems:
            raise ValidationError("The claims do not fit the fact: " + "; ".join(problems))

        if not subject_did.startswith("did:"):
            raise ValidationError("'subject_did' must be a DID")
        if subject_did.startswith(DID_PREFIX):
            subject_did = make_did(parse_did(subject_did)[0])
        try:
            holder_id, _ = parse_did(holder_did)
        except ValueError:
            raise ValidationError("'holder_did' must be the DID of the wallet that should hold it.")

        context = settings.POC_SIGNING_CONTEXT_NAME
        credential = {
            "type": [fact],
            "issuer": {"id": make_did(contract_id, context)},
            "credentialSubject": {"subject": {"id": subject_did}, "claims": claims},
        }
        signed = pdo_runner.sign_credential(contract_id, [context], credential, user_name)
        pdo_runner.wallet_add_vc(holder_id, signed, user_name)
        return {"ok": True, "message": f"{fact} signed and delivered to {make_did(holder_id)}."}


class AuthorityAcceptEndpoint(JsonView):
    """POST {did, credential_types} -- a rule-based authority accepts an authority
    for some of its inputs."""

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        if _require_authority(user_name, contract_id) != RULE_BASED:
            raise ValidationError("Only rule-based authorities accept other authorities.")
        did = require(data, "did")
        types = data.get("credential_types")
        if not isinstance(types, list) or not types:
            raise ValidationError("'credential_types' must be a non-empty list")
        for issuer_id, path, facts in trust.registrations({t: [did] for t in types}):
            pdo_runner.register_trusted_issuer(
                contract_id, issuer_id, user_name, path=path, credential_types=facts
            )
        _sync_sources(contract_id, user_name)
        return {"ok": True, "message": "Accepted for: " + ", ".join(types)}


class AuthorityWithdrawEndpoint(JsonView):
    """POST {contract_id, credential_types} -- withdraw a rule-based authority's
    trust in another for some of its inputs."""

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        if _require_authority(user_name, contract_id) != RULE_BASED:
            raise ValidationError("Only rule-based authorities accept other authorities.")
        issuer_id = require(data, "contract_id")
        types = data.get("credential_types")
        if not isinstance(types, list) or not types:
            raise ValidationError("'credential_types' must be a non-empty list")
        pdo_runner.unregister_trusted_issuer(
            contract_id, issuer_id, user_name, credential_types=types
        )
        _sync_sources(contract_id, user_name)
        return {"ok": True, "message": "Trust withdrawn."}


def _sync_sources(contract_id, user_name):
    """Mirror a rule-based authority's accepted sources into its directory entry,
    so owners choosing it see whom it trusts."""
    entry = registry_client.get_authority_by_did(directory_did(contract_id, RULE_BASED))
    trusted = pdo_runner.list_trusted_issuers(contract_id, user_name)
    sources = [
        {"did": make_did(issuer_id), "credential_types": sorted(trusted_types(trusted, issuer_id))}
        for issuer_id in sorted(trusted)
    ]
    registry_client.update_authority(entry["id"], {"sources": sources})


class AuthorityIssueEndpoint(JsonView):
    """POST {wallet_id, project} -- present one of the user's wallets to a
    rule-based authority and store what it issues in that wallet. The project is
    named exactly when the issued fact is about one."""

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        if _require_authority(user_name, contract_id) != RULE_BASED:
            raise ValidationError("Only rule-based authorities issue on presentation.")
        wallet_id = require(data, "wallet_id")
        if not ledger_client.user_owns_contract(user_name, wallet_id):
            raise ValidationError(f"wallet not found: {wallet_id}")
        policy = pdo_runner.get_rego_policy(contract_id, user_name)
        issued = registry_client.credential_templates_by_type()[policy["credential_type"]]
        declared = {"project": require(data, "project")} if "project" in issued["json_schema"]["properties"] else {}
        vc = pdo_runner.issue_credential(
            contract_id,
            {role: wallet_id for role in policy["requirements"]},
            user_name,
            declared,
        )
        pdo_runner.wallet_add_vc(wallet_id, vc, user_name)
        return {"ok": True, "message": f"{policy['credential_type']} issued into your wallet."}
