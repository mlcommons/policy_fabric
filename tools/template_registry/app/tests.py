import io
import json
import os
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from .models import AuthorityTemplate, CredentialTemplate, PolicyTemplate

FABRIC = Path(__file__).resolve().parents[3]
CARD_FOLDERS = {
    "CREDENTIALS_DIR": FABRIC / "credentials",
    "POLICY_CARDS_DIR": FABRIC / "policy_cards",
    "AUTHORITY_CARDS_DIR": FABRIC / "authority_cards",
}
for variable, folder in CARD_FOLDERS.items():
    os.environ.setdefault(variable, str(folder))


class SeededFromTheRepository(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_templates", stdout=io.StringIO())

    def test_every_card_and_credential_is_seeded(self):
        policy_cards = list((FABRIC / "policy_cards").rglob("card.json"))
        authority_cards = list((FABRIC / "authority_cards").rglob("card.json"))
        schemas = list((FABRIC / "credentials").glob("*.schema.json"))
        self.assertEqual(PolicyTemplate.objects.count(), len(policy_cards))
        self.assertEqual(AuthorityTemplate.objects.count(), len(authority_cards))
        self.assertEqual(CredentialTemplate.objects.count(), len(schemas))

    def test_a_card_on_a_template_runs_the_templates_rule(self):
        gso = PolicyTemplate.objects.get(name="GENETIC-STUDIES-ONLY")
        template = FABRIC / "policy_cards" / "templates" / "purpose-allowed" / "policy.rego"
        self.assertEqual(gso.rego_source, template.read_text())
        self.assertEqual(gso.defaults, {"allowedPurposes": ["GSO"]})

    def test_a_card_carries_its_manifest(self):
        irb = PolicyTemplate.objects.get(name="ETHICS-APPROVAL-REQUIRED")
        self.assertEqual(irb.kind, "policy")
        self.assertEqual(irb.code, "IRB")
        self.assertEqual(irb.requirements, {"User": ["EthicsApprovalCredential"]})
        self.assertEqual(irb.guardian_types, ["download", "inference"])
        self.assertTrue(irb.rule)
        self.assertIn("EthicsApprovalCredential", irb.readme)

    def test_delivery_modules_name_their_operation(self):
        download = PolicyTemplate.objects.get(name="DELIVERY-DOWNLOAD")
        self.assertEqual((download.kind, download.operation), ("delivery", "do_download"))

    def test_credentials_carry_their_fact_metadata(self):
        approval = CredentialTemplate.objects.get(template_type="EthicsApprovalCredential")
        self.assertEqual(approval.display_name, "Ethics approval")
        self.assertEqual(approval.subject_kinds, ["wallet"])
        self.assertEqual(approval.json_schema["required"], ["project", "approvedBy"])
        self.assertEqual(approval.claims_schema["project"], "string")
        self.assertFalse(approval.self_asserted)
        self.assertTrue(CredentialTemplate.objects.get(template_type="ScriptOwnershipCredential").self_asserted)

    def test_policies_are_listed_by_guardian_type_and_kind(self):
        inference = self.client.get("/api/policies/", {"guardian_type": "inference", "kind": "policy"}).json()
        codes = {t["code"] for t in inference}
        self.assertIn("FL-DS", codes)
        self.assertIn("IRB", codes)
        download = self.client.get("/api/policies/", {"guardian_type": "download"}).json()
        self.assertNotIn("FL-DS", {t["code"] for t in download})
        self.assertEqual(
            [t["operation"] for t in download if t["kind"] == "delivery"], ["do_download"]
        )

    def test_authorities_are_listed_with_the_fact_they_issue(self):
        listed = {a["name"]: a for a in self.client.get("/api/authorities/").json()}
        check = listed["ACCREDITED-COMMITTEE-CHECK"]
        self.assertEqual(check["issues"], "EthicsApprovalCredential")
        self.assertIn("IRBApprovalCredential", check["requirements"]["User"])
        detail = self.client.get(f"/api/authorities/{check['id']}/").json()
        self.assertTrue(detail["rego_source"].startswith("# Accredited-committee check"))

    def test_reseeding_changes_nothing(self):
        before = json.dumps(self.client.get("/api/policies/").json(), sort_keys=True)
        call_command("seed_templates", stdout=io.StringIO())
        after = json.dumps(self.client.get("/api/policies/").json(), sort_keys=True)
        self.assertEqual(before, after)
