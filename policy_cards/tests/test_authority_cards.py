"""Checks on every rule-based authority card, beyond its own Rego unit tests.

    python3 -m unittest discover -s policy_cards/tests -p "test_authority_cards.py"

An authority is a policy agent whose output is a fact other policy agents accept.
What it issues must be a standard fact about a holder, declared by its rule, and
the claims its rule produces must satisfy that fact's schema -- the contract does
not check them.
"""

import json
import unittest

import jsonschema

from cards import AUTHORITY_CARDS, POLICY_CARDS, Engine, cards, credential_schemas

OPA = Engine.find("opa", "OPA")
REGORUS = Engine.find("regorus", "REGORUS")

CARDS = cards(AUTHORITY_CARDS)
BY_ISSUED = {card.manifest["issues"]: card for card in CARDS}
CARD_SCHEMA = json.loads((POLICY_CARDS / "card.schema.json").read_text())
CREDENTIALS = credential_schemas()

MEMBER = "did:pdo:member"
PI = "did:pdo:pi"
PROJECT = "did:example:p1"


def credential(type_, subject, claims, index):
    return {
        "type": type_,
        "issuer": "did:pdo:registry",
        "signer": "did:pdo:registry",
        "trusted": True,
        "subject": subject,
        "claims": claims,
        "index": index,
    }


def presented(*credentials):
    return {
        "presentations": {"User": [credential(*c, index=i) for i, c in enumerate(credentials)]},
        "holders": {"User": MEMBER},
        "request": {"project": PROJECT},
        "trusted_issuers": {},
        "policy_data": {},
    }


TEAM = ("TeamCredential", MEMBER, {"MemberOfTeamOf": PI})
OWNERSHIP = ("ProjectOwnershipCredential", PI, {"Owns": PROJECT})
AFFILIATION = ("AffiliationCredential", PI, {"isMemberOf": "did:example:university", "typeOfMembership": "faculty"})

# For each issued fact, a member presenting a complete chain.
CHAINS = {
    "EthicsApprovalCredential": presented(
        TEAM, OWNERSHIP, AFFILIATION,
        ("IRBApprovalCredential", PROJECT, {"isApprovedByEthicsCommittee": "did:example:committee"}),
        ("EthicsCommitteeAccreditationCredential", "did:example:committee", {"ResponsibleFor": "did:example:university"}),
    ),
    "ResearchPurposeCredential": presented(
        TEAM, OWNERSHIP,
        ("IntendedDataUseCredential", PROJECT, {"useOnlyFor": {"purposes": ["HMB"], "diseases": ["MONDO:0005148"]}}),
    ),
    "ObligationAcceptanceCredential": presented(
        TEAM, OWNERSHIP, AFFILIATION,
        ("ScopedAgreementCredential", "did:example:agreement", {"agreementInfo": {
            "counterParty": "did:example:owner",
            "scope": {"obligation": "Collaboration", "project": PROJECT, "dataset": "did:example:dataset"},
        }}),
        ("AgreementCredential", "did:example:university", {"agreementInfo": {"documentID": "did:example:agreement", "documentVersion": "1"}}),
    ),
}


class AuthorityCards(unittest.TestCase):
    def test_manifests_follow_the_schema(self):
        for card in CARDS:
            with self.subTest(card=card.relative):
                jsonschema.validate(card.manifest, CARD_SCHEMA)
                self.assertEqual(card.manifest["kind"], "authority")
                self.assertTrue((card.folder / "policy_test.rego").is_file())

    def test_facts_are_the_rules_requirements(self):
        for card in CARDS:
            with self.subTest(card=card.relative):
                requirements = OPA.eval(card.source, "data.subpolicy.requirements")
                self.assertEqual(requirements, card.manifest["facts"])
                for types in requirements.values():
                    for type_ in types:
                        self.assertIn(type_, CREDENTIALS)

    def test_the_rule_declares_what_the_card_issues(self):
        for card in CARDS:
            with self.subTest(card=card.relative):
                self.assertEqual(OPA.issues(card.source), [card.manifest["issues"]])

    def test_an_authority_reads_the_requested_project_when_its_fact_is_about_one(self):
        for card in CARDS:
            with self.subTest(card=card.relative):
                about_a_project = "project" in CREDENTIALS[card.manifest["issues"]]["properties"]
                self.assertEqual("input.request.project" in card.source, about_a_project)

    def test_each_issues_a_standard_fact_about_a_holder(self):
        for card in CARDS:
            with self.subTest(card=card.relative):
                issued = CREDENTIALS[card.manifest["issues"]]
                self.assertIn("wallet", issued["subjectKinds"])

    def test_issued_claims_satisfy_the_facts_schema(self):
        self.assertEqual(set(CHAINS), set(BY_ISSUED), "every authority needs a complete chain here")
        for issued, chain in CHAINS.items():
            with self.subTest(issues=issued):
                result = OPA.eval(BY_ISSUED[issued].source, "data.subpolicy.result", chain)
                self.assertTrue(result["decision"])
                self.assertEqual(result["credential"]["subject"], MEMBER)
                schema = {k: v for k, v in CREDENTIALS[issued].items() if k != "$id"}
                jsonschema.validate(result["credential"]["claims"], schema)
                self.assertEqual(result["credential"]["claims"]["project"], PROJECT)

    def test_issues_nothing_for_another_project_or_none(self):
        for issued, chain in CHAINS.items():
            for request in ({"project": "did:example:p2"}, {}):
                with self.subTest(issues=issued, request=request):
                    result = OPA.eval(BY_ISSUED[issued].source, "data.subpolicy.result", dict(chain, request=request))
                    self.assertEqual(result, {"decision": False, "verification_tasks": [], "vc_supplied_verification_tasks": []})

    def test_regorus_agrees_with_opa(self):
        for issued, chain in CHAINS.items():
            source = BY_ISSUED[issued].source
            with self.subTest(issues=issued):
                self.assertEqual(
                    REGORUS.eval(source, "data.subpolicy.requirements"),
                    OPA.eval(source, "data.subpolicy.requirements"),
                )
                self.assertEqual(REGORUS.issues(source), OPA.issues(source))
                for value in (chain, dict(chain, request={})):
                    self.assertEqual(
                        REGORUS.eval(source, "data.subpolicy.result", value),
                        OPA.eval(source, "data.subpolicy.result", value),
                    )


if __name__ == "__main__":
    unittest.main()
