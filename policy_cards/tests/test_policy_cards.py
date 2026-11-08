"""Checks on every policy and delivery card, beyond its own Rego unit tests.

    python3 -m unittest discover -s policy_cards/tests -p "test_policy_cards.py"

Needs `opa` (or $OPA), `regorus` (or $REGORUS) -- the engine the policy agent
actually runs, which must agree with opa on every module -- and the jsonschema
package.
"""

import json
import unittest

import jsonschema

from cards import (
    HOLDER_KINDS,
    POLICY_CARDS,
    TEMPLATES,
    Engine,
    PolicyAgent,
    cards,
    credential_schemas,
    guardian_types,
)

OPA = Engine.find("opa", "OPA")
REGORUS = Engine.find("regorus", "REGORUS")
ENGINES = [OPA, REGORUS]

CARDS = cards(POLICY_CARDS)
BY_CODE = {card.manifest["code"]: card for card in CARDS if card.manifest["kind"] == "policy"}
CARD_SCHEMA = json.loads((POLICY_CARDS / "card.schema.json").read_text())
CREDENTIALS = credential_schemas()

REQUESTER = "did:pdo:requester"
SCRIPT = "did:pdo:script"
CHANNEL = {"channel_key": "CHANNEL-KEY"}
EMPTY_INPUT = {
    "presentations": {"User": [], "Script": []},
    "holders": {"User": REQUESTER, "Script": SCRIPT},
    "request": {},
    "trusted_issuers": {},
    "policy_data": {},
}


def by_role(card):
    return {role: sorted(types) for role, types in card.manifest["facts"].items()}


def delivery(guardian_type):
    return next(
        c for c in CARDS if c.manifest["kind"] == "delivery" and guardian_type in c.manifest["guardianTypes"]
    )


def credential(type_, subject, claims, index, trusted=True):
    return {
        "type": type_,
        "issuer": "did:pdo:registry",
        "signer": "did:pdo:registry",
        "trusted": trusted,
        "subject": subject,
        "claims": claims,
        "index": index,
    }


# An input each delivery module allows, by the operation it names.
DELIVERED = {
    "do_download": dict(
        EMPTY_INPUT,
        presentations={"User": [credential("publicKeyCredential", REQUESTER, {"key": "KEY"}, 0)], "Script": []},
        request={"channel_key": "KEY"},
    ),
    "do_inference": dict(
        EMPTY_INPUT,
        presentations={"User": [], "Script": [credential("ScriptHashCredential", SCRIPT, {"scriptHash": "sha256:abc"}, 0)]},
        request={"script_digest": "sha256:abc"},
    ),
}


class Manifests(unittest.TestCase):
    def test_every_rule_folder_is_a_card(self):
        folders = {c.folder for c in CARDS}
        for rule in POLICY_CARDS.rglob("policy.rego"):
            if TEMPLATES in rule.parents:
                continue
            self.assertIn(rule.parent, folders, f"{rule.parent} has a rule but no card.json")

    def test_manifests_follow_the_schema(self):
        for card in CARDS:
            with self.subTest(card=card.relative):
                jsonschema.validate(card.manifest, CARD_SCHEMA)
                self.assertIn(card.manifest["kind"], ("policy", "delivery"))

    def test_every_card_has_a_tested_rule(self):
        for card in CARDS:
            with self.subTest(card=card.relative):
                self.assertTrue(card.rule_path.is_file(), f"no rule at {card.rule_path}")
                self.assertTrue((card.rule_path.parent / "policy_test.rego").is_file())

    def test_every_template_is_used(self):
        used = {c.manifest["template"] for c in CARDS if "template" in c.manifest}
        for template in TEMPLATES.iterdir():
            if template.is_dir():
                self.assertIn(template.name, used, f"template {template.name} is not used by any card")

    def test_facts_are_the_rules_requirements(self):
        for card in CARDS:
            with self.subTest(card=card.relative):
                requirements = OPA.eval(card.source, "data.subpolicy.requirements")
                self.assertEqual(
                    {role: sorted(types) for role, types in requirements.items()},
                    by_role(card),
                )

    def test_facts_are_about_the_roles_holder(self):
        for card in CARDS:
            for role, types in card.manifest["facts"].items():
                for type_ in types:
                    with self.subTest(card=card.relative, role=role, type=type_):
                        self.assertIn(role, HOLDER_KINDS)
                        self.assertIn(type_, CREDENTIALS, f"{type_} has no schema in credentials/")
                        self.assertIn(HOLDER_KINDS[role], CREDENTIALS[type_]["subjectKinds"])

    def test_a_card_reads_the_requested_project_when_a_fact_is_about_one(self):
        """The webapp asks the requester for a project exactly when a fact the
        asset needs carries one."""
        for card in CARDS:
            with self.subTest(card=card.relative):
                about_a_project = any(
                    "project" in CREDENTIALS[t]["properties"] for types in card.manifest["facts"].values() for t in types
                )
                self.assertEqual("input.request.project" in card.source, about_a_project)

    def test_parameters_generate_a_form(self):
        for card in CARDS:
            with self.subTest(card=card.relative):
                parameters = card.manifest["parameters"]
                jsonschema.Draft202012Validator.check_schema(parameters)
                self.assertEqual(parameters["type"], "object")
                for name, spec in parameters["properties"].items():
                    self.assertTrue(spec["title"], f"{name} has no title for the form")
                if "defaults" in card.manifest:
                    jsonschema.validate(card.manifest["defaults"], parameters)

    def test_only_delivery_describes_the_decision(self):
        for card in CARDS:
            with self.subTest(card=card.relative):
                denied = OPA.eval(card.source, "data.subpolicy.result", EMPTY_INPUT)
                self.assertFalse(denied["decision"])
                self.assertNotIn("credential", denied)
                if card.manifest["kind"] == "delivery":
                    allowed = OPA.eval(card.source, "data.subpolicy.result", DELIVERED[card.manifest["operation"]])
                    self.assertTrue(allowed["decision"])
                    self.assertEqual(allowed["credential"]["claims"]["name"], card.manifest["operation"])

    def test_only_delivery_declares_what_the_policy_issues(self):
        for card in CARDS:
            with self.subTest(card=card.relative):
                expected = ["policy_decision"] if card.manifest["kind"] == "delivery" else []
                self.assertEqual(OPA.issues(card.source), expected)

    def test_one_delivery_module_per_guardian_type(self):
        types = guardian_types()
        for guardian_type in types:
            with self.subTest(guardian=guardian_type):
                modules = [
                    c for c in CARDS
                    if c.manifest["kind"] == "delivery" and guardian_type in c.manifest["guardianTypes"]
                ]
                self.assertEqual(len(modules), 1)
        for card in CARDS:
            self.assertLessEqual(set(card.manifest["guardianTypes"]), types, card.relative)


class Engines(unittest.TestCase):
    """The policy agent runs regorus; every module must mean the same thing there."""

    def test_regorus_agrees_with_opa(self):
        for card in CARDS:
            with self.subTest(card=card.relative):
                queries = [("data.subpolicy.requirements", None), ("data.subpolicy.result", EMPTY_INPUT)]
                if card.manifest["kind"] == "delivery":
                    queries.append(("data.subpolicy.result", DELIVERED[card.manifest["operation"]]))
                for query, value in queries:
                    self.assertEqual(REGORUS.eval(card.source, query, value), OPA.eval(card.source, query, value))
                self.assertEqual(REGORUS.issues(card.source), OPA.issues(card.source))


class Combination(unittest.TestCase):
    """Several cards on one asset, merged the way the policy agent merges them."""

    def agent(self, engine, guardian_type, policy_data):
        """Cards by code, each with its policy data, and the guardian's delivery
        module, which has none."""
        module = delivery(guardian_type)
        modules = [(BY_CODE[code].name, BY_CODE[code].source) for code in policy_data]
        modules.append((module.name, module.source))
        data = {BY_CODE[code].name: values for code, values in policy_data.items()}
        data[module.name] = {}
        return PolicyAgent(engine, modules, data)

    def each_engine(self):
        for engine in ENGINES:
            with self.subTest(engine=engine.name):
                yield engine

    def download_agent(self, engine):
        return self.agent(engine, "download", {
            "GS": {"allowedCountries": ["US"]},
            "IS": {"allowedInstitutions": ["did:example:university"]},
        })

    def requester(self, location_subject=REQUESTER):
        return {
            "User": [
                credential("LocationCredential", location_subject, {"locatedAt": {"country": "US"}}, 0),
                credential("AffiliationCredential", REQUESTER, {"isMemberOf": "did:example:university"}, 1),
                credential("publicKeyCredential", REQUESTER, {"key": "CHANNEL-KEY"}, 2),
            ]
        }

    def test_download_asset_asks_for_the_union_of_its_cards(self):
        for engine in self.each_engine():
            merged = self.download_agent(engine).requirements()
            self.assertEqual(
                sorted(merged["requirements"]["User"]),
                ["AffiliationCredential", "LocationCredential", "publicKeyCredential"],
            )

    def test_download_asset_allows_one_requester_holding_every_fact(self):
        for engine in self.each_engine():
            result = self.download_agent(engine).judge(self.requester(), {"User": REQUESTER}, CHANNEL)
            self.assertTrue(result["decision"], result)
            self.assertEqual(result["credential"], {
                "subject": REQUESTER,
                "claims": {"name": "do_download", "parameters": {"channel_key": "CHANNEL-KEY"}},
            })
            self.assertEqual(sorted(t["index"] for t in result["verification_tasks"]), [0, 1, 2])

    def test_a_fact_about_someone_else_denies_the_request(self):
        for engine in self.each_engine():
            result = self.download_agent(engine).judge(self.requester("did:pdo:someone-else"), {"User": REQUESTER}, CHANNEL)
            self.assertEqual(result, {"decision": False, "reason": "a module denied the request"})

    def test_every_module_needs_its_own_policy_data(self):
        modules = [(BY_CODE["GS"].name, BY_CODE["GS"].source), (delivery("download").name, delivery("download").source)]
        agent = PolicyAgent(OPA, modules, {BY_CODE["GS"].name: {"allowedCountries": ["US"]}})
        with self.assertRaisesRegex(ValueError, "no policy data"):
            agent.judge(self.requester(), {"User": REQUESTER}, CHANNEL)

    def test_project_bound_cards_agree_on_the_requested_project(self):
        held = {
            "User": [
                credential("EthicsApprovalCredential", REQUESTER, {"project": "did:example:p1", "approvedBy": "did:example:irb"}, 0),
                credential("ResearchPurposeCredential", REQUESTER, {"project": "did:example:p2", "purposes": ["HMB"], "diseases": []}, 1),
                credential("publicKeyCredential", REQUESTER, {"key": "CHANNEL-KEY"}, 2),
            ]
        }
        for engine in self.each_engine():
            agent = self.agent(engine, "download", {
                "IRB": {},
                "PS": {"approvedProjects": ["did:example:p1", "did:example:p2"]},
            })
            # each fact is about an approved project, but not about the same one
            for project in ("did:example:p1", "did:example:p2"):
                result = agent.judge(held, {"User": REQUESTER}, dict(CHANNEL, project=project))
                self.assertFalse(result["decision"], project)

            consistent = json.loads(json.dumps(held))
            consistent["User"][1]["claims"]["project"] = "did:example:p1"
            result = agent.judge(consistent, {"User": REQUESTER}, dict(CHANNEL, project="did:example:p1"))
            self.assertTrue(result["decision"], result)

            undeclared = agent.judge(consistent, {"User": REQUESTER}, CHANNEL)
            self.assertFalse(undeclared["decision"], "a project-bound card needs the project declared")

    def inference_presentations(self):
        return {
            "User": [
                credential("AffiliationCredential", REQUESTER, {"isMemberOf": "did:example:university"}, 0),
                credential("WalletVerifyingKeyCredential", REQUESTER, {"verifying_key": "WALLET-PEM"}, 1),
            ],
            "Script": [
                dict(credential("ScriptOwnershipCredential", SCRIPT, {"ownedBy": REQUESTER}, 2, trusted=False),
                     issuer=REQUESTER, signer=REQUESTER),
                credential("ScriptHashCredential", SCRIPT, {"scriptHash": "sha256:abc"}, 3),
                credential("IntendedDataUseCredential", SCRIPT, {"useOnlyFor": {"purposes": ["research"], "diseases": ["MONDO:0005148"]}}, 4),
            ],
        }

    def test_requester_agnostic_inference_site_asks_only_about_the_script(self):
        for engine in self.each_engine():
            agent = self.agent(engine, "inference", {"FL-DS": {"allowedDiseases": ["MONDO:0005148"]}})
            self.assertEqual(agent.requirements()["roles"], ["Script"])
            result = agent.judge(
                {"Script": self.inference_presentations()["Script"]}, {"Script": SCRIPT}, {"script_digest": "sha256:abc"}
            )
            self.assertTrue(result["decision"], result)
            self.assertEqual(result["credential"], {
                "subject": SCRIPT,
                "claims": {"name": "do_inference", "parameters": {"script_digest": "sha256:abc"}},
            })

    def test_inference_site_with_both_fl_cards(self):
        for engine in self.each_engine():
            agent = self.agent(engine, "inference", {
                "FL-DS": {"allowedDiseases": ["MONDO:0005148"]},
                "FL-IS": {"allowedInstitutions": ["did:example:university"]},
            })
            self.assertEqual(sorted(agent.requirements()["roles"]), ["Script", "User"])
            holders = {"User": REQUESTER, "Script": SCRIPT}
            result = agent.judge(self.inference_presentations(), holders, {"script_digest": "sha256:abc"})
            self.assertTrue(result["decision"], result)
            self.assertEqual(result["vc_supplied_verification_tasks"], [{"index": 2, "key": "WALLET-PEM", "key_type": "ec"}])
            checked = [t["index"] for t in result["verification_tasks"]] + [2]
            self.assertEqual(sorted(checked), [0, 1, 2, 3, 4], "every credential relied on is verified once")

            tampered = agent.judge(self.inference_presentations(), holders, {"script_digest": "sha256:tampered"})
            self.assertFalse(tampered["decision"])


if __name__ == "__main__":
    unittest.main()
