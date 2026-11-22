"""The tests of a policy graph, a card's graph_tests.json, run by test_cards.py.

A graph tests file names its credentials once and builds each test from them:

    {
      "registry":    {<type>: [<signer DID>, ...]},      whom the contract trusts, per type
      "request":     {...},                               what the requester declares
      "policy_data": {<node>: {...}},                     every node's policy data
      "credentials": {<name>: {"type", "issuer", "signer", "subject", "claims"}},
      "tests": [
        {"name": "...",
         "present": {<role>: [<credential name>, ...]},
         "change":  {<credential name>: <JSON merge patch>},       {} for none
         "expect":  {"decision": true, "subject", "operation", "verified": [<name>]}
                 or {"decision": false, "missing": [{"node", "input"}]}
                 or {"decision": false, "reason": "<why>"}}
      ]
    }

A credential is trusted, as the contract computes it, when its issuer is its signer and the
registry lists that signer for its type; every type a credential has must be a key of
"registry" (``[]`` when no signer is trusted for it). A credential a component checks against
a key it supplies also has "signing_key", a name standing for the key wherever a claim or the
policy data carries it: the key check passes when the key is ``"ec"``, the credential's issuer
is its signer, and the supplied key is that name. (pdo-contracts' on-chain test,
``rego-contract/test/python/policy_graph_test.py``, signs such a credential with a real key and
puts its PEM wherever the name appears.)

An allow compares the decision's subject and operation, and its "verified" (every presented
credential bound to a node that ran), as a set of names. A denial compares "missing" as a
set, or "reason" exactly. Indices are given in presentation order, roles sorted.
"""

import copy
import json

from policy_graph import evaluate


def merge_patch(target, patch):
    """RFC 7386."""
    if not isinstance(patch, dict):
        return copy.deepcopy(patch)
    out = copy.deepcopy(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        if value is None:
            out.pop(key, None)
        else:
            out[key] = merge_patch(out.get(key), value)
    return out


def resolve(suite, graph_test):
    """The test's presentation as the contract would view it, ``{role: [view]}``, and the
    credential names by index."""
    credentials = {
        name: merge_patch(cred, graph_test["change"][name]) if name in graph_test["change"] else cred
        for name, cred in suite["credentials"].items()
    }
    unknown = set(graph_test["change"]) - set(credentials)
    if unknown:
        raise KeyError(f"{graph_test['name']}: change names unknown credentials {sorted(unknown)}")
    presented, names = {}, []
    for role in sorted(graph_test["present"]):
        presented[role] = []
        for name in graph_test["present"][role]:
            cred = credentials[name]
            presented[role].append({
                "type": cred["type"],
                "issuer": cred["issuer"],
                "signer": cred["signer"],
                "trusted": cred["issuer"] == cred["signer"] and cred["signer"] in suite["registry"][cred["type"]],
                "subject": cred["subject"],
                "claims": cred["claims"],
                "index": len(names),
                "proof_value": "",
            })
            names.append(name)
    return presented, names, credentials


class GraphTestVerifier:
    """Signature checks for graph tests: a registry check passes for a trusted credential; a key
    check passes when the supplied key is the credential's signing key."""

    def __init__(self, credentials, names):
        self.credentials = credentials
        self.names = names

    def registry(self, view):
        return view["trusted"]

    def key(self, view, key, key_type):
        cred = self.credentials[self.names[view["index"]]]
        return view["issuer"] == view["signer"] and key_type == "ec" and key == cred["signing_key"]


def missing(entry):
    """A missing input, as a test names it."""
    return {"node": entry["node"], "input": entry["input"]}


def outcome(result, names):
    """What a test's expect compares with."""
    if not result["decision"]:
        if "missing" in result:
            return {"decision": False, "missing": [missing(m) for m in result["missing"]]}
        return {"decision": False, "reason": result["reason"]}
    return {
        "decision": True,
        "subject": result["subject"],
        "operation": result["operation"],
        "verified": [names[i] for i in result["verified"]],
    }


def normalized(expect):
    out = copy.deepcopy(expect)
    if "verified" in out:
        out["verified"] = sorted(out["verified"])
    if "missing" in out:
        out["missing"] = sorted(out["missing"], key=json.dumps)
    return out


def run(graph, components, interfaces, suite):
    """Yield ``(graph_test, expected, got, result)`` for each test of the suite."""
    for graph_test in suite["tests"]:
        presented, names, credentials = resolve(suite, graph_test)
        result = evaluate(
            graph, components, interfaces, presented, suite["request"], suite["policy_data"],
            GraphTestVerifier(credentials, names),
        )
        yield graph_test, normalized(graph_test["expect"]), normalized(outcome(result, names)), result
