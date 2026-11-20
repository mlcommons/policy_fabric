import io
import json
import os
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from .models import CredentialTemplate, PolicyComponent, PolicyTemplate

FABRIC = Path(__file__).resolve().parents[3]
CARD_FOLDERS = {
    "CREDENTIALS_DIR": FABRIC / "credentials",
    "POLICY_CARDS_DIR": FABRIC / "policy_cards",
    "POLICY_COMPONENTS_DIR": FABRIC / "policy_components",
}
for variable, folder in CARD_FOLDERS.items():
    os.environ.setdefault(variable, str(folder))


class SeededFromTheRepository(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_templates", stdout=io.StringIO())

    def test_every_card_and_credential_is_seeded(self):
        cards = list((FABRIC / "policy_cards").rglob("graph.json"))
        schemas = list((FABRIC / "credentials").glob("*.schema.json"))
        self.assertEqual(PolicyTemplate.objects.count(), len(cards))
        self.assertEqual(CredentialTemplate.objects.count(), len(schemas))

    def test_a_card_carries_its_manifest_and_graph(self):
        irb = PolicyTemplate.objects.get(name="ETHICS-APPROVAL-REQUIRED")
        folder = FABRIC / "policy_cards" / "ethics-approval-required"
        self.assertEqual((irb.code, irb.title), ("IRB", "Ethics approval required"))
        self.assertTrue(irb.rule)
        self.assertEqual(irb.guardian_types, ["download"])
        self.assertEqual(irb.graph, json.loads((folder / "graph.json").read_text()))
        self.assertEqual(irb.policy_card, (folder / "policy_card.md").read_text())
        fl = PolicyTemplate.objects.get(name="FL-INFERENCE-DISEASE-SPECIFIC-RESEARCH")
        self.assertEqual((fl.code, fl.guardian_types), ("FL-DS", ["inference"]))

    def test_credentials_carry_their_metadata(self):
        approval = CredentialTemplate.objects.get(template_type="IRBApprovalCredential")
        self.assertEqual(approval.display_name, "IRB approval")
        self.assertEqual(approval.subject_kinds, ["project"])
        self.assertEqual(approval.json_schema["required"], ["isApprovedByEthicsCommittee", "purposes"])
        self.assertEqual(approval.claims_schema["purposes"], ["string"])
        self.assertFalse(approval.self_asserted)
        self.assertTrue(CredentialTemplate.objects.get(template_type="ScriptOwnershipCredential").self_asserted)

    def test_policies_are_listed_by_guardian_type(self):
        inference = {t["code"] for t in self.client.get("/api/policies/", {"guardian_type": "inference"}).json()}
        self.assertEqual(inference, {"FL-DS", "FL-IS"})
        download = {t["code"] for t in self.client.get("/api/policies/", {"guardian_type": "download"}).json()}
        self.assertIn("IRB", download)
        self.assertNotIn("FL-DS", download)

    def test_reseeding_changes_nothing(self):
        before = json.dumps(self.client.get("/api/policies/").json(), sort_keys=True)
        call_command("seed_templates", stdout=io.StringIO())
        after = json.dumps(self.client.get("/api/policies/").json(), sort_keys=True)
        self.assertEqual(before, after)

    def test_components_are_seeded_with_their_rego_and_policy_data_schema(self):
        folders = sorted(p.parent.name for p in (FABRIC / "policy_components").glob("*/component.json"))
        self.assertEqual(sorted(PolicyComponent.objects.values_list("component_id", flat=True)), folders)
        listed = {c["component_id"]: c for c in self.client.get("/api/components/").json()}
        membership = listed["project_membership"]
        self.assertEqual(membership["package"], "pf.components.project_membership")
        self.assertTrue(membership["rego_source"].startswith("package pf.components.project_membership"))
        self.assertEqual(membership["metadata"]["group"], "shared")
        self.assertEqual(membership["policy_data_schema"], {})
        disease = listed["disease_specific_research"]["policy_data_schema"]
        self.assertEqual(disease["required"], ["allowedDiseases"])

    def test_only_presentable_credentials_may_be_issued(self):
        presentable = dict(CredentialTemplate.objects.values_list("template_type", "presentable"))
        self.assertTrue(presentable["TeamCredential"])
        self.assertTrue(presentable["ProjectMembershipCredential"])
        self.assertTrue(presentable["IRBClearanceCredential"])
        self.assertFalse(presentable["DataUseConditionCredential"])
        self.assertFalse(presentable["InstitutionalIRBApprovalCredential"])

    def test_the_catalog_holds_every_card_and_component(self):
        catalog = self.client.get("/api/catalog/").json()
        self.assertEqual(len(catalog["cards"]), PolicyTemplate.objects.count())
        self.assertEqual(set(catalog["components"]), set(PolicyComponent.objects.values_list("component_id", flat=True)))
        self.assertEqual(catalog["cards"]["FL/inference-disease-specific-research"]["template"],
                         "FL-INFERENCE-DISEASE-SPECIFIC-RESEARCH")

    def test_a_posted_template_needs_a_valid_graph(self):
        graph = json.loads((FABRIC / "policy_cards" / "geographical-restriction" / "graph.json").read_text())
        missing = self.client.post("/api/policies/", {"name": "NO-GRAPH"}, content_type="application/json")
        self.assertEqual(missing.status_code, 400)
        broken = json.loads(json.dumps(graph))
        broken["nodes"]["geographical_restriction"]["inputs"].pop("location")
        refused = self.client.post("/api/policies/", {"name": "BROKEN", "graph": broken}, content_type="application/json")
        self.assertEqual(refused.status_code, 400)
        self.assertTrue(any("binds" in p for p in refused.json()["problems"]))
        saved = self.client.post("/api/policies/", {"name": "GEO-COPY", "graph": graph}, content_type="application/json")
        self.assertEqual(saved.status_code, 201)
        self.assertEqual(saved.json()["graph"], graph)
