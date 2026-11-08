"""The pages and endpoints over a fake directory, template registry and ledger.

Run under ``manage.py test`` (see run_tests.sh); plain unittest discovery skips it.
"""

import json
import os
import unittest
from unittest import mock

from django.conf import settings

if not settings.configured and "DJANGO_SETTINGS_MODULE" not in os.environ:
    raise unittest.SkipTest("view tests run under manage.py test (see run_tests.sh)")

from django.test import TestCase  # noqa: E402

from app import action_runners  # noqa: E402
from app.models import AppConfig  # noqa: E402
from app.url_safe_id import encode_cid  # noqa: E402

from .fixtures import held, trusting, vc  # noqa: E402

OWNER = "data_owner"
# contract ids are base64, so their length is a multiple of four
ASSET, WALLET, OFFICE, EKA = "asset001", "wallet01", "office01", "eka00001"
ASSET_DID, WALLET_DID = f"did:pdo:{ASSET}", f"did:pdo:{WALLET}"
TOKEN, POLICY = "token001", "policy01"

LOCATION_SCHEMA = {
    "type": "object",
    "properties": {"locatedAt": {"type": "object", "properties": {"country": {"type": "string"}},
                                 "required": ["country"]}},
    "required": ["locatedAt"],
}
CREDENTIALS = [
    {"id": 1, "template_type": "LocationCredential", "display_name": "Location", "meaning": "Located at.",
     "subject_kinds": ["wallet"], "self_asserted": False, "json_schema": LOCATION_SCHEMA},
    {"id": 2, "template_type": "publicKeyCredential", "display_name": "Session key", "meaning": "A key.",
     "subject_kinds": ["wallet"], "self_asserted": False,
     "json_schema": {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]}},
    {"id": 3, "template_type": "ScriptOwnershipCredential", "display_name": "Script ownership",
     "meaning": "Owned.", "subject_kinds": ["script"], "self_asserted": True,
     "json_schema": {"type": "object", "properties": {"ownedBy": {"type": "string"}}, "required": ["ownedBy"]}},
    {"id": 4, "template_type": "EthicsApprovalCredential", "display_name": "Ethics approval",
     "meaning": "Approved.", "subject_kinds": ["wallet"], "self_asserted": False,
     "json_schema": {"type": "object", "properties": {"project": {"type": "string"}}, "required": ["project"]}},
    {"id": 5, "template_type": "ProjectOwnershipCredential", "display_name": "Project ownership",
     "meaning": "Owns.", "subject_kinds": ["wallet"], "self_asserted": False,
     "json_schema": {"type": "object", "properties": {"Owns": {"type": "string"}}, "required": ["Owns"]}},
]
GS = {
    "id": 1, "name": "GEOGRAPHICAL-RESTRICTION", "kind": "policy", "code": "GS",
    "title": "Geographical restriction", "rule": "The requester is located in an allowed country.",
    "guardian_types": ["download", "inference"], "requirements": {"User": ["LocationCredential"]},
    "parameters_schema": {
        "type": "object",
        "properties": {"allowedCountries": {"type": "array", "items": {"type": "string"}, "minItems": 1}},
        "required": ["allowedCountries"],
    },
    "defaults": {}, "operation": "", "rego_source": "package subpolicy # GS", "readme": "# GS",
}
DELIVERY = {
    "id": 9, "name": "DELIVERY-DOWNLOAD", "kind": "delivery", "code": "", "title": "Download delivery",
    "rule": "Encrypts to the requester's session key.", "guardian_types": ["download"],
    "requirements": {"User": ["publicKeyCredential"]}, "parameters_schema": {}, "defaults": {},
    "operation": "do_download", "rego_source": "package subpolicy # delivery", "readme": "",
}
REGISTRY_OFFICE = {
    "id": 1, "did": f"did:pdo:{OFFICE}#poc", "name": "University registry", "kind": "hand-signing",
    "operator": "vc_issuer", "facts": ["LocationCredential"], "checks": "Checks records.",
    "inputs": {}, "sources": [],
}
SESSION_KEYS = {
    "id": 2, "did": f"did:pdo:{EKA}", "name": "Session keys", "kind": "system", "operator": "vc_issuer",
    "facts": ["publicKeyCredential"], "checks": "", "inputs": {}, "sources": [],
}


class FakeRegistries:
    """The asset registry's assets and directory, and the template registry."""

    def __init__(self, metadata):
        self.asset = {"id": 7, "name": "data1", "did": ASSET_DID, "metadata": dict(metadata)}
        self.directory = [REGISTRY_OFFICE, SESSION_KEYS]
        self.registered = []

    def patches(self):
        policies = [GS, DELIVERY]

        def policy_templates_for(guardian_type, kind):
            return [p for p in policies if guardian_type in p["guardian_types"] and p["kind"] == kind]

        def update(did, changes):
            self.asset["metadata"].update(changes)

        return mock.patch.multiple(
            "app.registry_client",
            get_asset_by_did=mock.Mock(side_effect=lambda did: self.asset),
            list_assets=mock.Mock(side_effect=lambda: [self.asset]),
            update_asset_metadata_by_did=mock.Mock(side_effect=update),
            list_policy_templates=mock.Mock(return_value=policies),
            policy_templates_for=mock.Mock(side_effect=policy_templates_for),
            get_policy_template=mock.Mock(side_effect=lambda pk: {p["id"]: p for p in policies}[int(pk)]),
            list_credential_templates=mock.Mock(return_value=CREDENTIALS),
            list_authorities=mock.Mock(side_effect=lambda: self.directory),
            list_trust_lists=mock.Mock(return_value=[]),
            list_authority_templates=mock.Mock(return_value=[]),
            register_authority=mock.Mock(side_effect=self.registered.append),
            get_authority_by_did=mock.Mock(side_effect=self.authority_by_did),
        )

    def authority_by_did(self, did):
        for a in self.directory + self.registered:
            if a["did"] == did:
                return a
        raise LookupError(did)


def ndjson(response):
    return [json.loads(line) for line in b"".join(response.streaming_content).decode().splitlines()]


class ViewTestCase(TestCase):
    metadata = {"guardian_url": "localhost", "guardian_port": "7900", "guardian_type": "download"}

    def setUp(self):
        config = AppConfig.get_instance()
        config.public_key = OWNER
        config.save()
        self.registries = FakeRegistries(self.metadata)
        for patcher in (
            self.registries.patches(),
            mock.patch("app.identity.list_available_identities", return_value=[OWNER]),
            mock.patch.multiple(
                "app.ledger_client",
                user_owns_contract=mock.Mock(return_value=True),
                list_identity_ids=mock.Mock(return_value=[WALLET]),
                list_signature_authority_ids=mock.Mock(return_value=[ASSET, OFFICE]),
                list_policy_agent_ids=mock.Mock(return_value=[POLICY]),
                list_external_key_authority_ids=mock.Mock(return_value=[EKA]),
                list_wallet_key_authority_ids=mock.Mock(return_value=[]),
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.runner = {
            "create_asset_policy": mock.Mock(
                return_value={"policy_contract_id": POLICY, "token_contract_id": TOKEN}
            ),
            "set_policy_data": mock.Mock(),
            "get_policy_data": mock.Mock(
                return_value={"GEOGRAPHICAL-RESTRICTION": {"allowedCountries": ["US"]}}
            ),
            "register_trusted_issuer": mock.Mock(),
            "unregister_trusted_issuer": mock.Mock(),
            "resolve_policy_id": mock.Mock(return_value=POLICY),
            "get_policy_requirements": mock.Mock(
                return_value={"User": ["LocationCredential", "publicKeyCredential"]}
            ),
            "list_trusted_issuers": mock.Mock(
                return_value={**trusting(OFFICE, ["LocationCredential"]), **trusting(EKA, ["publicKeyCredential"], ())}
            ),
            "wallet_credentials": mock.Mock(return_value=[]),
            "sign_credential": mock.Mock(return_value={"signed": True}),
            "sign_credential_with_contract_key": mock.Mock(return_value={"signed": True}),
            "wallet_add_vc": mock.Mock(),
            "create_hand_signing_authority": mock.Mock(return_value="office02"),
        }
        patcher = mock.patch.multiple("app.pdo_runner", **self.runner)
        patcher.start()
        self.addCleanup(patcher.stop)

    def post(self, url, payload):
        return self.client.post(url, json.dumps(payload), content_type="application/json")


class ExposePanel(ViewTestCase):
    def test_the_panel_offers_the_cards_for_the_guardian_and_the_directory(self):
        response = self.client.get(f"/assets/{encode_cid(ASSET)}/")
        self.assertEqual(response.status_code, 200)
        expose = response.context["expose"]
        self.assertEqual([c["name"] for c in expose["cards"]], ["GEOGRAPHICAL-RESTRICTION"])
        self.assertEqual(expose["delivery"]["name"], "DELIVERY-DOWNLOAD")
        self.assertEqual([a["name"] for a in expose["authorities"]], ["University registry", "Session keys"])
        self.assertContains(response, 'id="expose-data"')

    def expose(self, payload):
        return ndjson(self.post(f"/assets/{encode_cid(ASSET)}/expose/stream/", payload))

    def test_exposing_builds_one_policy_from_the_cards_and_the_delivery_module(self):
        events = self.expose({
            "cards": [GS["id"]],
            "parameters": {str(GS["id"]): {"allowedCountries": ["US"]}},
            "authorities": {"LocationCredential": [REGISTRY_OFFICE["did"]], "publicKeyCredential": [SESSION_KEYS["did"]]},
        })
        self.assertEqual(events[-1]["status"], "done", events)

        _, _, _, modules = self.runner["create_asset_policy"].call_args.args
        self.assertEqual([m[0] for m in modules], ["GEOGRAPHICAL-RESTRICTION", "DELIVERY-DOWNLOAD"])
        self.runner["set_policy_data"].assert_called_once_with(
            POLICY, {"GEOGRAPHICAL-RESTRICTION": {"allowedCountries": ["US"]}, "DELIVERY-DOWNLOAD": {}}, OWNER
        )
        registrations = sorted(
            (c.args[1], tuple(c.kwargs["path"]), tuple(c.kwargs["credential_types"]))
            for c in self.runner["register_trusted_issuer"].call_args_list
        )
        self.assertEqual(registrations, [(EKA, (), ("publicKeyCredential",)),
                                         (OFFICE, ("poc",), ("LocationCredential",))])
        metadata = self.registries.asset["metadata"]
        self.assertEqual(metadata["policy_contract"], f"did:pdo:{TOKEN}")
        self.assertEqual([c["code"] for c in metadata["cards"]], ["GS"])
        self.assertEqual(metadata["delivery"], "DELIVERY-DOWNLOAD")

    def test_a_fact_with_no_accepted_authority_blocks_exposing(self):
        with self.assertLogs("app.views._streaming", "ERROR"):
            events = self.expose({
                "cards": [GS["id"]],
                "parameters": {str(GS["id"]): {"allowedCountries": ["US"]}},
                "authorities": {"LocationCredential": [REGISTRY_OFFICE["did"]], "publicKeyCredential": []},
            })
        self.assertEqual(events[1]["status"], "error")
        self.assertIn("Accept at least one authority for: publicKeyCredential", events[1]["detail"])
        self.runner["create_asset_policy"].assert_not_called()

    def test_every_selected_card_needs_its_parameters(self):
        response = self.post(f"/assets/{encode_cid(ASSET)}/expose/stream/", {
            "cards": [GS["id"]],
            "parameters": {},
            "authorities": {"LocationCredential": [REGISTRY_OFFICE["did"]], "publicKeyCredential": [SESSION_KEYS["did"]]},
        })
        self.assertEqual(response.status_code, 400)
        self.runner["create_asset_policy"].assert_not_called()

    def test_parameters_that_do_not_fit_the_card_block_exposing(self):
        with self.assertLogs("app.views._streaming", "ERROR"):
            events = self.expose({
                "cards": [GS["id"]],
                "parameters": {str(GS["id"]): {"allowedCountries": []}},
                "authorities": {"LocationCredential": [REGISTRY_OFFICE["did"]],
                                "publicKeyCredential": [SESSION_KEYS["did"]]},
            })
        self.assertEqual(events[1]["status"], "error")
        self.assertIn("GS", events[1]["detail"])
        self.runner["create_asset_policy"].assert_not_called()


class ExposedDashboard(ViewTestCase):
    metadata = {
        **ViewTestCase.metadata,
        "policy_contract": f"did:pdo:{TOKEN}",
        "cards": [{"name": "GEOGRAPHICAL-RESTRICTION", "code": "GS", "title": "Geographical restriction",
                   "rule": "Allowed countries."}],
        "delivery": "DELIVERY-DOWNLOAD",
    }

    def test_trust_is_shown_by_name_and_kind(self):
        response = self.client.get(f"/assets/{encode_cid(ASSET)}/")
        self.assertEqual(response.status_code, 200)
        rows = {r["type"]: r for r in response.context["trust_rows"]}
        self.assertEqual([a["name"] for a in rows["LocationCredential"]["accepted"]], ["University registry"])
        self.assertEqual(rows["publicKeyCredential"]["accepted"][0]["kind_label"], "System")
        self.assertContains(response, 'data-action="withdraw"')
        self.assertEqual(response.context["cards"][0]["values"], {"allowedCountries": ["US"]})

    def test_accepting_an_authority_registers_its_signing_context(self):
        response = self.post(f"/api/assets/{encode_cid(ASSET)}/accept-authority/",
                             {"did": "did:pdo:other001#poc", "credential_types": ["LocationCredential"]})
        self.assertEqual(response.status_code, 200, response.content)
        self.runner["register_trusted_issuer"].assert_called_once_with(
            POLICY, "other001", OWNER, path=["poc"], credential_types=["LocationCredential"]
        )

    def test_withdrawing_trust(self):
        response = self.post(f"/api/assets/{encode_cid(ASSET)}/withdraw-authority/",
                             {"contract_id": OFFICE, "credential_types": ["LocationCredential"]})
        self.assertEqual(response.status_code, 200, response.content)
        self.runner["unregister_trusted_issuer"].assert_called_once_with(
            POLICY, OFFICE, OWNER, credential_types=["LocationCredential"]
        )

    def test_policy_data_is_checked_against_each_card(self):
        url = f"/api/assets/{encode_cid(ASSET)}/update-policy-data/"
        bad = self.post(url, {"policy_data": {"GEOGRAPHICAL-RESTRICTION": {"allowedCountries": "US"}}})
        self.assertEqual(bad.status_code, 400)
        missing = self.post(url, {"policy_data": {}})
        self.assertEqual(missing.status_code, 400)
        good = self.post(url, {"policy_data": {"GEOGRAPHICAL-RESTRICTION": {"allowedCountries": ["CA"]}}})
        self.assertEqual(good.status_code, 200)
        self.runner["set_policy_data"].assert_called_once_with(
            POLICY, {"GEOGRAPHICAL-RESTRICTION": {"allowedCountries": ["CA"]}, "DELIVERY-DOWNLOAD": {}}, OWNER
        )

    def test_the_checklist_reports_each_fact(self):
        location = vc("LocationCredential", WALLET_DID, {"locatedAt": {"country": "US"}}, signer=OFFICE)
        self.runner["wallet_credentials"].return_value = held(location)
        response = self.post("/api/assets/checklist/", {"asset_did": ASSET_DID, "wallets": {"User": WALLET}})
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        statuses = {r["type"]: (r["name"], r["status"], r["via"]) for r in body["rows"]}
        self.assertEqual(statuses, {
            "LocationCredential": ("Location", "held", None),
            "publicKeyCredential": ("Session key", "automatic", "Session keys"),
        })
        self.assertTrue(body["ready"])
        self.assertFalse(body["needs_project"])

    def test_a_fact_about_a_project_asks_for_one(self):
        self.runner["get_policy_requirements"].return_value = {"User": ["EthicsApprovalCredential"]}
        ownership = vc("ProjectOwnershipCredential", "did:pdo:pi000001", {"Owns": "did:example:p1"}, signer=OFFICE)
        self.runner["wallet_credentials"].return_value = held(ownership)
        body = self.post("/api/assets/checklist/", {"asset_did": ASSET_DID, "wallets": {"User": WALLET}}).json()
        self.assertTrue(body["needs_project"])
        self.assertEqual(body["projects"], ["did:example:p1"])

    def test_using_it_without_naming_the_project_is_refused(self):
        self.runner["get_policy_requirements"].return_value = {"User": ["EthicsApprovalCredential"]}
        runner = action_runners.build_runner(
            user_name=OWNER, asset_did=ASSET_DID, metadata=self.registries.asset["metadata"],
            wallets={"User": WALLET}, params={},
        )
        with self.assertRaisesRegex(ValueError, "name the project"):
            runner.run()


class Authorities(ViewTestCase):
    def test_the_list_offers_only_facts_a_person_signs(self):
        response = self.client.get("/authorities/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([t["template_type"] for t in response.context["attestable"]],
                         ["LocationCredential", "EthicsApprovalCredential", "ProjectOwnershipCredential"])
        kinds = {a["contract_id"]: (a["kind"], a["fact_names"]) for a in response.context["authorities"]}
        self.assertEqual(kinds, {OFFICE: ("hand-signing", ["Location"]), EKA: ("system", ["Session key"])})

    def test_a_hand_signing_authority_is_listed_in_the_directory(self):
        refused = self.client.post("/authorities/", {
            "name": "Ethics office", "kind": "hand-signing", "facts": ["LocationCredential"], "checks": "",
        })
        self.assertEqual(refused.status_code, 302)
        self.assertEqual(self.registries.registered, [], "an authority must say what it checks")

        response = self.client.post("/authorities/", {
            "name": "Ethics office", "kind": "hand-signing", "facts": ["LocationCredential"],
            "checks": "Reviews each protocol.",
        })
        self.assertEqual(response.status_code, 302)
        record = self.registries.registered[0]
        self.assertEqual((record["did"], record["kind"], record["facts"]),
                         ("did:pdo:office02#poc", "hand-signing", ["LocationCredential"]))

    def test_signing_checks_the_claims_and_delivers_to_the_chosen_wallet(self):
        url = f"/api/authorities/{encode_cid(OFFICE)}/sign-credential/"
        payload = {"template_type": "LocationCredential", "subject_did": "did:pdo:pi000001",
                   "holder_did": "did:pdo:member01"}
        bad = self.post(url, {**payload, "claims": {"locatedAt": {}}})
        self.assertEqual(bad.status_code, 400)
        self.assertIn("country", bad.json()["error"])

        good = self.post(url, {**payload, "claims": {"locatedAt": {"country": "US"}}})
        self.assertEqual(good.status_code, 200, good.content)
        credential = self.runner["sign_credential"].call_args.args[2]
        self.assertEqual(credential["issuer"]["id"], f"did:pdo:{OFFICE}#poc")
        self.assertEqual(credential["credentialSubject"]["subject"]["id"], "did:pdo:pi000001")
        self.runner["wallet_add_vc"].assert_called_once_with("member01", {"signed": True}, OWNER)

    def test_a_fact_about_a_third_party_is_delivered_to_a_wallet(self):
        url = f"/api/authorities/{encode_cid(OFFICE)}/sign-credential/"
        payload = {"template_type": "LocationCredential", "subject_did": "did:example:pi",
                   "claims": {"locatedAt": {"country": "US"}}}
        self.assertEqual(self.post(url, payload).status_code, 400)
        response = self.post(url, {**payload, "holder_did": "did:pdo:member01"})
        self.assertEqual(response.status_code, 200, response.content)
        credential = self.runner["sign_credential"].call_args.args[2]
        self.assertEqual(credential["credentialSubject"]["subject"]["id"], "did:example:pi")
        self.runner["wallet_add_vc"].assert_called_once_with("member01", {"signed": True}, OWNER)

    def test_an_authority_signs_only_the_facts_it_attests(self):
        response = self.post(f"/api/authorities/{encode_cid(OFFICE)}/sign-credential/", {
            "template_type": "publicKeyCredential", "subject_did": "did:pdo:pi000001", "claims": {},
        })
        self.assertEqual(response.status_code, 400)


class Wallets(ViewTestCase):
    def test_a_wallet_signs_only_self_asserted_claims(self):
        url = f"/api/wallets/{encode_cid(WALLET)}/sign-credential/"
        refused = self.post(url, {"template_type": "LocationCredential", "subject_did": "did:pdo:script01",
                                  "claims": {"locatedAt": {"country": "US"}}})
        self.assertEqual(refused.status_code, 400)
        signed = self.post(url, {"template_type": "ScriptOwnershipCredential", "subject_did": "did:pdo:script01",
                                 "claims": {"ownedBy": WALLET_DID}})
        self.assertEqual(signed.status_code, 200, signed.content)
        self.runner["sign_credential_with_contract_key"].assert_called_once()
        self.runner["wallet_add_vc"].assert_called_once_with("script01", {"signed": True}, OWNER)

    def test_the_wallet_page_decodes_what_it_holds(self):
        location = vc("LocationCredential", WALLET_DID, {"locatedAt": {"country": "US"}}, signer=OFFICE)
        self.runner["wallet_credentials"].return_value = held(location)
        response = self.client.get(f"/wallets/{encode_cid(WALLET)}/")
        self.assertEqual(response.status_code, 200)
        [row] = response.context["credentials"]
        self.assertEqual((row["name"], row["about"], row["issuer"]),
                         ("Location", "this wallet", "University registry"))
