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
     "subject_kinds": ["wallet"], "self_asserted": False, "presentable": True, "json_schema": LOCATION_SCHEMA},
    {"id": 2, "template_type": "publicKeyCredential", "display_name": "Session key", "meaning": "A key.",
     "subject_kinds": ["wallet"], "self_asserted": False, "presentable": True,
     "json_schema": {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]}},
    {"id": 3, "template_type": "ScriptOwnershipCredential", "display_name": "Script ownership",
     "meaning": "Owned.", "subject_kinds": ["script"], "self_asserted": True, "presentable": True,
     "json_schema": {"type": "object", "properties": {"ownedBy": {"type": "string"}}, "required": ["ownedBy"]}},
    {"id": 4, "template_type": "IRBClearanceCredential", "display_name": "IRB clearance",
     "meaning": "Cleared.", "subject_kinds": ["wallet"], "self_asserted": False, "presentable": True,
     "json_schema": {"type": "object", "properties": {"project": {"type": "string"}}, "required": ["project"]}},
    {"id": 5, "template_type": "ProjectOwnershipCredential", "display_name": "Project ownership",
     "meaning": "Owns.", "subject_kinds": ["wallet"], "self_asserted": False, "presentable": True,
     "json_schema": {"type": "object", "properties": {"Owns": {"type": "string"}}, "required": ["Owns"]}},
    {"id": 6, "template_type": "AffiliationCredential", "display_name": "Affiliation",
     "meaning": "A member.", "subject_kinds": ["wallet"], "self_asserted": False, "presentable": True,
     "json_schema": {"type": "object", "properties": {"isMemberOf": {"type": "string"}}, "required": ["isMemberOf"]}},
    {"id": 7, "template_type": "DataUseConditionCredential", "display_name": "Data use condition",
     "meaning": "Met.", "subject_kinds": ["wallet"], "self_asserted": False, "presentable": False,
     "json_schema": {"type": "object", "properties": {}, "required": []}},
]

# two download cards and an inference one as graphs of components, and the catalog that
# describes the components
COUNTRIES = {
    "type": "object",
    "properties": {"allowedCountries": {"type": "array", "items": {"type": "string"}, "description": "Countries."}},
    "required": ["allowedCountries"],
}


DOWNLOAD_PARAMETERS = {"channel_key": {"type": "publicKeyCredential", "role": "User", "claim": "key"}}


def card_graph(name, node, input_name, input_type):
    return {
        "version": 3, "name": name,
        "nodes": {node: {"component": node, "inputs": {input_name: {"from": "presented"}}, "policy_data": {}}},
        "capability": {"operation": "do_download", "requires": [node], "parameters": DOWNLOAD_PARAMETERS},
        "trusted_issuers": {input_type: [], "publicKeyCredential": []},
    }


GS_GRAPH = card_graph("Geographical Restriction", "geographical_restriction", "location", "LocationCredential")
IS_GRAPH = card_graph("Institution Specific Restriction", "institution_specific_restriction", "affiliation",
                      "AffiliationCredential")
FL_GRAPH = {
    "version": 3, "name": "Inference",
    "nodes": {"declared_use": {"component": "declared_use", "inputs": {"use": {"from": "presented"}}, "policy_data": {}}},
    "capability": {"operation": "do_inference", "requires": ["declared_use"],
                   "parameters": {"script_digest": {"type": "ScriptHashCredential", "role": "Script", "claim": "scriptHash"}}},
    "trusted_issuers": {"IntendedDataUseCredential": [], "ScriptHashCredential": []},
}


def card_component(component_id, name, input_name, input_type, schema):
    return {
        "name": name, "group": "card", "policy_data_schema": schema, "rego": f"package pf.components.{component_id}",
        "inputs": {input_name: {"type": input_type, "about": "requester", "role": "User", "claims": []}},
        "output": {"type": "DataUseConditionCredential", "about": "requester", "claims": []},
    }


def catalog_card(name, component, template, graph):
    return {"name": name, "duo": "DUO_0000000", "component": component, "template": template, "graph": graph}


CATALOG = {
    "subjects": {"requester": {"word": "requester", "legend": "the requester"}},
    "credentials": {},
    "components": {
        "geographical_restriction": card_component(
            "geographical_restriction", "GeographicalRestriction", "location", "LocationCredential", COUNTRIES),
        "institution_specific_restriction": card_component(
            "institution_specific_restriction", "InstitutionSpecificRestriction", "affiliation", "AffiliationCredential", {}),
    },
    "cards": {
        "geographical-restriction": catalog_card(
            "Geographical Restriction", "geographical_restriction", "GEOGRAPHICAL-RESTRICTION", GS_GRAPH),
        "institution-specific-restriction": catalog_card(
            "Institution Specific Restriction", "institution_specific_restriction", "INSTITUTION-SPECIFIC-RESTRICTION",
            IS_GRAPH),
    },
}
COMPONENTS = [
    {"component_id": cid, "package": f"pf.components.{cid}", "rego_source": f"package pf.components.{cid}",
     "metadata": {}, "policy_data_schema": {}}
    for cid in CATALOG["components"]
]
GS = {
    "id": 1, "name": "GEOGRAPHICAL-RESTRICTION", "code": "GS", "title": "Geographical restriction",
    "rule": "The requester is located in an allowed country.", "guardian_types": ["download"],
    "policy_card": "# GS", "graph": GS_GRAPH,
}
IS = {
    "id": 2, "name": "INSTITUTION-SPECIFIC-RESTRICTION", "code": "IS", "title": "Institution specific restriction",
    "rule": "The requester belongs to an allowed institution.", "guardian_types": ["download"],
    "policy_card": "# IS", "graph": IS_GRAPH,
}
FL = {
    "id": 3, "name": "FL-INFERENCE", "code": "FL", "title": "Inference", "rule": "For inference.",
    "guardian_types": ["inference"], "policy_card": "# FL", "graph": FL_GRAPH,
}
REGISTRY_OFFICE = {
    "id": 1, "did": f"did:pdo:{OFFICE}#poc", "name": "University registry", "kind": "hand-signing",
    "operator": "vc_issuer", "facts": ["LocationCredential"], "checks": "Checks records.",
}
SESSION_KEYS = {
    "id": 2, "did": f"did:pdo:{EKA}", "name": "Session keys", "kind": "system", "operator": "vc_issuer",
    "facts": ["publicKeyCredential"], "checks": "",
}


class FakeRegistries:
    """The asset registry's assets and directory, and the template registry."""

    def __init__(self, metadata):
        self.asset = {"id": 7, "name": "data1", "did": ASSET_DID, "metadata": dict(metadata)}
        self.directory = [REGISTRY_OFFICE, SESSION_KEYS]
        self.registered = []

    def patches(self):
        policies = [GS, IS, FL]

        def policy_templates_for(guardian_type):
            return [p for p in policies if guardian_type in p["guardian_types"]]

        def update(did, changes):
            self.asset["metadata"].update(changes)

        return mock.patch.multiple(
            "app.registry_client",
            get_asset_by_did=mock.Mock(side_effect=lambda did: self.asset),
            list_assets=mock.Mock(side_effect=lambda: [self.asset]),
            update_asset_metadata_by_did=mock.Mock(side_effect=update),
            policy_templates_for=mock.Mock(side_effect=policy_templates_for),
            get_policy_template=mock.Mock(side_effect=lambda pk: {p["id"]: p for p in policies}[int(pk)]),
            list_credential_templates=mock.Mock(return_value=CREDENTIALS),
            list_authorities=mock.Mock(side_effect=lambda: self.directory),
            list_trust_lists=mock.Mock(return_value=[]),
            register_authority=mock.Mock(side_effect=self.registered.append),
            get_authority_by_did=mock.Mock(side_effect=self.authority_by_did),
            get_catalog=mock.Mock(return_value=CATALOG),
            list_policy_components=mock.Mock(return_value=COMPONENTS),
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
                list_external_key_authority_ids=mock.Mock(return_value=[EKA]),
                list_wallet_key_authority_ids=mock.Mock(return_value=[]),
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.runner = {
            "create_asset_policy": mock.Mock(
                return_value={"policy_contract_id": POLICY, "token_contract_id": TOKEN, "graph_hash": "hash="}
            ),
            "get_policy_graph": mock.Mock(return_value={"policy_graph": GS_GRAPH, "components": [], "sha256": "hash="}),
            "get_policy_data": mock.Mock(
                return_value={"geographical_restriction": {"allowedCountries": ["US"]}}
            ),
            "register_trusted_issuer": mock.Mock(),
            "unregister_trusted_issuer": mock.Mock(),
            "resolve_policy_id": mock.Mock(return_value=POLICY),
            "get_requirement_alternatives": mock.Mock(
                return_value=[{"User": ["LocationCredential", "publicKeyCredential"]}]
            ),
            "set_node_policy_data": mock.Mock(),
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
    parameters = {
        "geographical_restriction": {"allowedCountries": ["US"]},
        "institution_specific_restriction": {},
    }
    authorities = {
        "LocationCredential": [REGISTRY_OFFICE["did"]],
        "AffiliationCredential": [REGISTRY_OFFICE["did"]],
        "publicKeyCredential": [SESSION_KEYS["did"]],
    }

    def compose(self, cards):
        return self.post(f"/api/assets/{encode_cid(ASSET)}/compose/", {"cards": cards})

    def expose(self, payload):
        return ndjson(self.post(f"/assets/{encode_cid(ASSET)}/expose/stream/", payload))

    def test_the_panel_offers_the_cards_for_the_guardian_and_the_directory(self):
        response = self.client.get(f"/assets/{encode_cid(ASSET)}/")
        self.assertEqual(response.status_code, 200)
        expose = response.context["expose"]
        self.assertEqual([c["name"] for c in expose["cards"]], ["GEOGRAPHICAL-RESTRICTION", "INSTITUTION-SPECIFIC-RESTRICTION"])
        self.assertEqual(expose["cards"][0]["graph"], GS_GRAPH)
        self.assertEqual(expose["cards"][0]["rego_source"], "package pf.components.geographical_restriction")
        self.assertEqual([a["name"] for a in expose["authorities"]], ["University registry", "Session keys"])
        self.assertContains(response, 'id="expose-data"')
        self.assertContains(response, 'id="policy-catalog"')

    def test_two_cards_compose_under_one_capability(self):
        body = self.compose([GS["id"], IS["id"]]).json()
        graph = body["graph"]
        self.assertEqual(list(graph["nodes"]), ["geographical_restriction", "institution_specific_restriction"])
        self.assertEqual(graph["capability"], {"operation": "do_download", "parameters": DOWNLOAD_PARAMETERS,
                                               "requires": ["geographical_restriction", "institution_specific_restriction"]})
        self.assertEqual(list(graph["trusted_issuers"]), ["AffiliationCredential", "LocationCredential", "publicKeyCredential"])
        self.assertEqual(body["alternatives"], [{"User": ["AffiliationCredential", "LocationCredential", "publicKeyCredential"]}])
        self.assertEqual([n["node"] for n in body["nodes"] if n["schema"]], ["geographical_restriction"])

    def test_one_card_keeps_its_own_graph(self):
        graph = self.compose([GS["id"]]).json()["graph"]
        self.assertEqual(graph["nodes"], GS_GRAPH["nodes"])

    def test_a_card_for_another_guardian_cannot_be_composed(self):
        response = self.compose([FL["id"]])
        self.assertEqual(response.status_code, 400)
        self.assertIn("FL", response.json()["error"])

    def test_exposing_sets_the_composed_graph_with_each_nodes_parameters(self):
        events = self.expose({"cards": [GS["id"], IS["id"]], "parameters": self.parameters, "authorities": self.authorities})
        self.assertEqual(events[-1]["status"], "done", events)
        _, _, _, graph, components = self.runner["create_asset_policy"].call_args.args
        self.assertEqual(graph["nodes"]["geographical_restriction"]["policy_data"], {"allowedCountries": ["US"]})
        self.assertEqual(sorted(components), sorted(CATALOG["components"]))
        registrations = sorted(
            (c.args[1], tuple(c.kwargs["path"]), tuple(c.kwargs["credential_types"]))
            for c in self.runner["register_trusted_issuer"].call_args_list
        )
        self.assertEqual(registrations, [(EKA, (), ("publicKeyCredential",)),
                                         (OFFICE, ("poc",), ("AffiliationCredential", "LocationCredential"))])
        metadata = self.registries.asset["metadata"]
        self.assertEqual((metadata["policy_contract"], metadata["graph_hash"]), (f"did:pdo:{TOKEN}", "hash="))
        self.assertEqual([c["code"] for c in metadata["cards"]], ["GS", "IS"])

    def test_every_node_needs_parameters_that_fit_it(self):
        with self.assertLogs("app.views._streaming", "ERROR"):
            missing = self.expose({"cards": [GS["id"], IS["id"]], "parameters": {"geographical_restriction": {"allowedCountries": ["US"]}},
                                   "authorities": self.authorities})
        self.assertIn("every node", missing[1]["detail"])
        with self.assertLogs("app.views._streaming", "ERROR"):
            unfit = self.expose({"cards": [GS["id"]], "parameters": {"geographical_restriction": {"allowedCountries": "US"}},
                                 "authorities": {"LocationCredential": [REGISTRY_OFFICE["did"]], "publicKeyCredential": [SESSION_KEYS["did"]]}})
        self.assertIn("GeographicalRestriction", unfit[1]["detail"])
        self.runner["create_asset_policy"].assert_not_called()

    def test_some_way_to_meet_the_graph_must_be_accepted(self):
        with self.assertLogs("app.views._streaming", "ERROR"):
            events = self.expose({"cards": [GS["id"], IS["id"]], "parameters": self.parameters,
                                  "authorities": {**self.authorities, "publicKeyCredential": []}})
        self.assertIn("at least one way to meet the policy", events[1]["detail"])
        self.runner["create_asset_policy"].assert_not_called()

    def test_the_payload_must_name_cards_parameters_and_authorities(self):
        response = self.post(f"/assets/{encode_cid(ASSET)}/expose/stream/", {"cards": [GS["id"]], "parameters": {}})
        self.assertEqual(response.status_code, 400)
        self.runner["create_asset_policy"].assert_not_called()


class ExposedDashboard(ViewTestCase):
    metadata = {
        **ViewTestCase.metadata,
        "policy_contract": f"did:pdo:{TOKEN}",
        "graph_hash": "hash=",
        "cards": [{"name": "GEOGRAPHICAL-RESTRICTION", "code": "GS", "title": "Geographical restriction", "rule": "Allowed countries."}],
        "policy_data": {"geographical_restriction": {"allowedCountries": ["US"]}},
    }

    def test_the_dashboard_draws_the_graph_with_each_nodes_parameters(self):
        response = self.client.get(f"/assets/{encode_cid(ASSET)}/")
        self.assertEqual(response.status_code, 200)
        policy = response.context["graph_policy"]
        self.assertEqual(policy["graph"], GS_GRAPH)
        self.assertEqual([(n["node"], n["values"]) for n in policy["nodes"]],
                         [("geographical_restriction", {"allowedCountries": ["US"]})])
        self.assertEqual(response.context["alternatives"], [["Location", "Session key"]])
        self.assertContains(response, 'id="asset-policy-graph"')

    def test_trust_is_shown_by_name_and_kind(self):
        response = self.client.get(f"/assets/{encode_cid(ASSET)}/")
        rows = {r["type"]: r for r in response.context["trust_rows"]}
        self.assertEqual(set(rows), {"LocationCredential", "publicKeyCredential"})
        self.assertEqual([a["name"] for a in rows["LocationCredential"]["accepted"]], ["University registry"])
        self.assertEqual(rows["publicKeyCredential"]["accepted"][0]["kind_label"], "System")
        self.assertContains(response, 'data-action="withdraw"')

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

    def test_a_nodes_policy_data_is_set_on_its_own(self):
        url = f"/api/assets/{encode_cid(ASSET)}/update-policy-data/"
        good = self.post(url, {"node": "geographical_restriction", "policy_data": {"allowedCountries": ["CA"]}})
        self.assertEqual(good.status_code, 200, good.content)
        self.runner["set_node_policy_data"].assert_called_once_with(POLICY, "geographical_restriction", {"allowedCountries": ["CA"]}, OWNER)
        self.assertEqual(self.registries.asset["metadata"]["policy_data"]["geographical_restriction"], {"allowedCountries": ["CA"]})
        self.assertEqual(self.post(url, {"node": "nope", "policy_data": {}}).status_code, 400)
        self.assertEqual(self.post(url, {"node": "geographical_restriction", "policy_data": {"allowedCountries": "CA"}}).status_code, 400)
        # a node whose component takes no policy data
        self.runner["get_policy_graph"].return_value = {"policy_graph": IS_GRAPH, "components": [], "sha256": "hash="}
        self.assertEqual(self.post(url, {"node": "institution_specific_restriction", "policy_data": {}}).status_code, 400)

    def test_the_checklist_reports_each_credential(self):
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

    def test_the_checklist_is_of_a_way_the_requester_can_meet_the_graph(self):
        self.runner["get_requirement_alternatives"].return_value = [
            {"User": ["IRBClearanceCredential", "publicKeyCredential"]},
            {"User": ["LocationCredential", "publicKeyCredential"]},
        ]
        location = vc("LocationCredential", WALLET_DID, {"locatedAt": {"country": "US"}}, signer=OFFICE)
        self.runner["wallet_credentials"].return_value = held(location)
        body = self.post("/api/assets/checklist/", {"asset_did": ASSET_DID, "wallets": {"User": WALLET}}).json()
        self.assertEqual([r["type"] for r in body["rows"]], ["LocationCredential", "publicKeyCredential"])
        self.assertTrue(body["ready"])

    def test_the_use_form_names_every_credential_some_way_needs(self):
        self.runner["get_requirement_alternatives"].return_value = [
            {"User": ["IRBClearanceCredential", "publicKeyCredential"]},
            {"User": ["LocationCredential", "publicKeyCredential"]},
        ]
        body = self.post("/api/assets/use-form/", {"asset_did": ASSET_DID}).json()
        self.assertEqual(body["roles"][0]["credential_types"],
                         ["IRBClearanceCredential", "LocationCredential", "publicKeyCredential"])


class Policies(ViewTestCase):
    def test_every_card_of_the_catalog_is_drawn(self):
        response = self.client.get("/policies/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([c["folder"] for c in response.context["cards"]],
                         ["geographical-restriction", "institution-specific-restriction"])
        self.assertContains(response, 'data-graph-of="geographical-restriction"')
        self.assertContains(response, 'id="policy-catalog"')


class Authorities(ViewTestCase):
    def test_the_list_offers_only_credentials_a_person_signs(self):
        response = self.client.get("/authorities/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([t["template_type"] for t in response.context["attestable"]],
                         ["LocationCredential", "IRBClearanceCredential", "ProjectOwnershipCredential",
                          "AffiliationCredential"])
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
