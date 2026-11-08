import unittest

from app import trust

from .fixtures import authority, trusting

DIRECTORY = [
    authority("did:pdo:irb#poc", "IRB office", "hand-signing", ["EthicsApprovalCredential"]),
    authority("did:pdo:committee", "Committee check", "rule-based", ["EthicsApprovalCredential"]),
    authority("did:pdo:eka", "Session keys", "system", ["publicKeyCredential"]),
]
NAMES = {"EthicsApprovalCredential": "Ethics approval", "publicKeyCredential": "Session key",
         "LocationCredential": "Location"}


class Trust(unittest.TestCase):
    def test_a_row_per_fact_with_accepted_and_offered_authorities(self):
        rows = trust.panel(
            ["EthicsApprovalCredential", "publicKeyCredential"],
            trusting("irb", ["EthicsApprovalCredential"]),
            DIRECTORY,
            NAMES,
        )
        ethics = rows[0]
        self.assertEqual(ethics["name"], "Ethics approval")
        self.assertEqual([a["name"] for a in ethics["accepted"]], ["IRB office"])
        self.assertEqual(ethics["accepted"][0]["kind_label"], "Hand-signing")
        self.assertEqual([o["name"] for o in ethics["options"]], ["Committee check"])
        self.assertEqual(rows[1]["accepted"], [])

    def test_an_accepted_issuer_missing_from_the_directory_is_still_shown(self):
        rows = trust.panel(["LocationCredential"], trusting("unlisted", ["LocationCredential"]), DIRECTORY, NAMES)
        self.assertEqual(rows[0]["accepted"][0]["kind_label"], "unlisted")

    def test_a_lone_system_authority_is_preselected(self):
        self.assertEqual(trust.preselected("publicKeyCredential", DIRECTORY), ["did:pdo:eka"])
        self.assertEqual(trust.preselected("EthicsApprovalCredential", DIRECTORY), [])

    def test_choices_become_one_registration_per_authority_and_context(self):
        self.assertEqual(
            trust.registrations({
                "LocationCredential": ["did:pdo:irb#poc"],
                "AffiliationCredential": ["did:pdo:irb#poc"],
                "publicKeyCredential": ["did:pdo:eka"],
            }),
            [("eka", [], ["publicKeyCredential"]), ("irb", ["poc"], ["AffiliationCredential", "LocationCredential"])],
        )
