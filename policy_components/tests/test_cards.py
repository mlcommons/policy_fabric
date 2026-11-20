"""Every card's graph passes its graph tests through policy_graph.py, which runs the contract's
validator and planner, as the contract would; and, unless the card changes meaning on purpose or was added since, as the card
did when it was one Rego module.

The comparison with the old Rego file (at commit 760742d, read through git) allows
for what the graph does differently everywhere: the operation may carry fewer parameters (an
inference capability no longer carries a channel key), and only credentials of the types the
graph reads are compared with what the old module flagged. A test that presents a type a
component produces (a registry's shortcut) has no counterpart in the old module, and is not
compared.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from library import CARDS, FABRIC, card_folders, component_json, graph, graph_tests, opa_eval
from policy_graph import load_components, validate
from graph_tests import GraphTestVerifier, resolve, run

LEGACY_COMMIT = "760742d"
CHANGED_ON_PURPOSE = {
    "ethics-approval-required": "reads the requester's affiliation, not the PI's, and checks the IRB approved every intended purpose",
    "collaboration-required": "reads the requester's affiliation, not the PI's",
    "publication-required": "reads the requester's affiliation, not the PI's",
}


def checked_graph(card):
    g = graph(card)
    components = load_components(g, FABRIC / "policy_components")
    interfaces, problems = validate(g, components)
    if problems:
        raise AssertionError(f"{card}: " + "; ".join(problems))
    return g, components, interfaces


def legacy_cards():
    """The cards that had a Rego file at LEGACY_COMMIT; a card added since has no old decisions."""
    listing = subprocess.run(
        ["git", "-C", str(FABRIC), "ls-tree", "-r", "--name-only", LEGACY_COMMIT, "policy_cards"],
        capture_output=True, text=True, check=True,
    ).stdout
    return {path.split("/", 1)[1].rsplit("/", 1)[0] for path in listing.splitlines() if path.endswith("/policy.rego")}


def legacy_source(card):
    return subprocess.run(
        ["git", "-C", str(FABRIC), "show", f"{LEGACY_COMMIT}:policy_cards/{card}/policy.rego"],
        capture_output=True, text=True, check=True,
    ).stdout


def legacy_outcome(path, suite, graph_test, card_node):
    """The old module's decision, operation and flagged credentials, as the contract that ran
    it would decide: it denied unless every flagged credential verified."""
    presented, names, credentials = resolve(suite, graph_test)
    views = {view["index"]: view for creds in presented.values() for view in creds}
    legacy_input = {
        "presentations": {
            role: [{key: view[key] for key in ("type", "issuer", "subject", "claims", "index")} for view in creds]
            for role, creds in presented.items()
        },
        "trusted_issuers": {},
        "policy_data": suite["policy_data"][card_node],
    }
    result = opa_eval([path], "data.subpolicy.result", legacy_input)
    verifier = GraphTestVerifier(credentials, names)
    flagged = [task["index"] for task in result["verification_tasks"]]
    supplied = result["vc_supplied_verification_tasks"]
    verified = all(verifier.registry(views[i]) for i in flagged) and all(
        verifier.key(views[task["index"]], task["key"], task["key_type"]) for task in supplied
    )
    relied_on = flagged + [task["index"] for task in supplied]
    return result["decision"] and verified, result["operation"], {names[i]: views[i]["type"] for i in relied_on}


def name_of(text):
    return text.replace("/", "_").replace("-", "_")


class Cards(unittest.TestCase):
    """Two tests per card, test_<card>_graph_tests and test_<card>_as_before, so that -k selects
    one card."""

    def test_every_card_is_a_graph_with_tests(self):
        folders = sorted(p.parent.relative_to(CARDS).as_posix() for p in CARDS.rglob("policy_card.md"))
        self.assertEqual(folders, card_folders())
        for card in folders:
            self.assertTrue((CARDS / card / "graph_tests.json").exists(), card)


def graph_tests_test(card):
    def test(self):
        g, components, interfaces = checked_graph(card)
        for graph_test, expected, got, _ in run(g, components, interfaces, graph_tests(card)):
            with self.subTest(test=graph_test["name"]):
                self.assertEqual(got, expected)

    return test


def as_before_test(card):
    def test(self):
        g, components, interfaces = checked_graph(card)
        suite = graph_tests(card)
        card_node = next(n for n, node in g["nodes"].items() if component_json(node["component"])["group"] == "card")
        read_types = {spec["type"] for iface in interfaces.values() for spec in iface["inputs"].values()}
        produced = {iface["output"] for iface in interfaces.values()}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.rego"
            path.write_text(legacy_source(card))
            for graph_test, _, got, result in run(g, components, interfaces, suite):
                presented_types = {suite["credentials"][name]["type"] for names in graph_test["present"].values() for name in names}
                if presented_types & produced:
                    continue
                with self.subTest(test=graph_test["name"]):
                    decision, operation, relied_on = legacy_outcome(path, suite, graph_test, card_node)
                    self.assertEqual(got["decision"], decision)
                    if not decision:
                        continue
                    self.assertEqual(result["operation"]["name"], operation["name"])
                    for key, value in result["operation"]["parameters"].items():
                        self.assertEqual(operation["parameters"][key], value)
                    self.assertEqual(
                        sorted(got["evidence"]),
                        sorted(name for name, t in relied_on.items() if t in read_types),
                    )

    return test


LEGACY_CARDS = legacy_cards()
for card_folder in card_folders():
    setattr(Cards, f"test_{name_of(card_folder)}_graph_tests", graph_tests_test(card_folder))
    if card_folder in LEGACY_CARDS and card_folder not in CHANGED_ON_PURPOSE:
        setattr(Cards, f"test_{name_of(card_folder)}_as_before", as_before_test(card_folder))


if __name__ == "__main__":
    unittest.main()
