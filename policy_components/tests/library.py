"""The component library and the card graphs, as the tests read them.

The graph reference implementation (pdo.rego.graph) comes from a pdo-contracts checkout:
run_tests.sh puts $PDO_CONTRACTS_ROOT/rego-contract on the path.
"""

import json
import subprocess
from pathlib import Path

FABRIC = Path(__file__).resolve().parents[2]
COMPONENTS = FABRIC / "policy_components"
CARDS = FABRIC / "policy_cards"
CREDENTIALS = FABRIC / "credentials"


def component_ids():
    return sorted(p.parent.name for p in COMPONENTS.glob("*/component.json"))


def component_json(component_id):
    return json.loads((COMPONENTS / component_id / "component.json").read_text())


def card_folders():
    """Every card that is a graph, by folder under policy_cards/ (FL cards are under FL/)."""
    return sorted(p.parent.relative_to(CARDS).as_posix() for p in CARDS.rglob("graph.json"))


def graph(card):
    return json.loads((CARDS / card / "graph.json").read_text())


def vectors(card):
    return json.loads((CARDS / card / "graph_vectors.json").read_text())


def opa_eval(sources, query, input_doc):
    """The value of query over input_doc, on OPA."""
    args = ["opa", "eval", "--format", "json", "--stdin-input", query]
    for source in sources:
        args += ["--data", str(source)]
    out = subprocess.run(args, input=json.dumps(input_doc), capture_output=True, text=True, check=True)
    result = json.loads(out.stdout)["result"]
    if not result:
        raise KeyError(f"{query} is undefined")
    return result[0]["expressions"][0]["value"]
