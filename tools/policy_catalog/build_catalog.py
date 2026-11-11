#!/usr/bin/env python3
"""Read the repo's credentials, policy components and policy cards into one catalog JSON.

The docs composer and the webapp's policy views draw from this catalog, so both show what the
repo holds. It also checks the files against each other and exits 1 on any mismatch.

    python3 tools/policy_catalog/build_catalog.py --repo . --out catalog.json

It reads, under the repo:
  credentials/<Type>.schema.json             presented and produced credential types (JSON Schema)
  policy_components/<id>/component.json      what the views show: name, group, inputs, output, policy data
  policy_components/<id>/component.rego      package pf.components.<id>
  policy_cards/**/graph.json                 a card, as a graph (version 2)
  policy_cards/**/card.json                  its code, name and one-line rule

A type no component outputs is presented by wallets. A produced type may also be presented only
when its schema says "x-presentable": true (a registry may issue it directly).

The interfaces in the Rego are not evaluated here; policy_components/tests checks them against
component.json on OPA and regorus. Standard library only: the docs build and the template
registry run it.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# who a credential is about: the word after "subject:" and the legend text, in legend order
SUBJECTS = {
    "requester": {"word": "requester", "legend": "the requester"},
    "project": {"word": "project", "legend": "the project"},
    "pi": {"word": "PI", "legend": "the PI"},
    "institution": {"word": "institution", "legend": "an institution"},
    "committee": {"word": "ethics committee", "legend": "the ethics committee"},
    "script": {"word": "script", "legend": "the script"},
    "compute": {"word": "compute node", "legend": "a compute node"},
    "document": {"word": "terms document", "legend": "a terms document"},
}
GROUPS = ("shared", "card", "grant")
COMPONENT_KEYS = {"name", "group", "summary", "inputs", "output", "policy_data", "changes_from_today"}
CARD_KEYS = COMPONENT_KEYS | {"card", "duo"}
# a card folder's card.json: how the card is named to the asset owner
CARD_MANIFEST_KEYS = {"code", "name", "rule"}
# an input may also list claims the plan adds to its type, and mark a credential its
# component checks against a key it supplies rather than against an issuer
INPUT_KEYS = {"type", "about", "role", "claims"}
INPUT_EXTRA_KEYS = {"new_claims", "supplied_key"}
# the type labels component.json gives policy data, and the JSON Schema each stands for
POLICY_DATA_TYPES = {
    "string": {"type": "string"},
    "string (ISO-8601 datetime)": {"type": "string"},
    "array of strings": {"type": "array", "items": {"type": "string"}},
}


def template_name(folder):
    """The template registry's name for a card folder, as seed_templates names it."""
    return "-".join(Path(folder).parts).upper()


def build(credentials_dir, components_dir, cards_dir):
    """The catalog and the problems found, from the three folders."""
    problems = []
    credentials, flagged = read_credentials(Path(credentials_dir))
    folders = sorted(p.parent.relative_to(cards_dir).as_posix() for p in Path(cards_dir).rglob("graph.json"))
    components = {}
    for d in sorted(p.parent for p in Path(components_dir).glob("*/component.json")):
        component, found = read_component(d, credentials, folders)
        components[d.name] = component
        problems += found
    for t, c in credentials.items():
        c["presentable"] = not c["produced_by"] or t in flagged
    for t in sorted(flagged):
        if not credentials[t]["produced_by"]:
            problems.append(f"credentials/{t}: x-presentable is only for produced types; no component outputs {t}")

    cards = {}
    for folder in folders:
        graph = json.loads((Path(cards_dir) / folder / "graph.json").read_text())
        problems += check_graph(folder, graph, components, credentials)
        manifest = json.loads((Path(cards_dir) / folder / "card.json").read_text())
        if set(manifest) != CARD_MANIFEST_KEYS:
            problems.append(f"policy_cards/{folder}/card.json: has {sorted(manifest)}, needs {sorted(CARD_MANIFEST_KEYS)}")
        owners = [c for c in components.values() if c["group"] == "card" and c["card"] == folder]
        if len(owners) != 1:
            problems.append(f"policy_cards/{folder}: {len(owners)} card components name this card, not one")
            continue
        cards[folder] = {
            "name": graph["name"],
            "duo": owners[0]["duo"],
            "component": owners[0]["id"],
            "template": template_name(folder),
            "graph": graph,
        }
    catalog = {"version": 1, "subjects": SUBJECTS, "credentials": credentials, "components": components, "cards": cards}
    return catalog, problems


def read_credentials(credentials_dir):
    credentials, flagged = {}, set()
    for p in sorted(credentials_dir.glob("*.schema.json")):
        s = json.loads(p.read_text())
        credentials[s["$id"]] = {
            "title": s["title"],
            "description": s["description"],
            "claims": {k: {"type": v["type"], "description": v["description"]} for k, v in s["properties"].items()},
            "required": s["required"],
            "produced_by": [],
            "presentable": True,
        }
        if "x-presentable" in s:
            flagged.add(s["$id"])
    return credentials, flagged


def policy_data_schema(policy_data):
    """The JSON Schema of a component's policy data, for the forms that edit it; every key is
    required. The component's Rego interface declares the same schema."""
    if not policy_data:
        return {}
    return {
        "type": "object",
        "properties": {k: {**POLICY_DATA_TYPES[v["type"]], "description": v["description"]} for k, v in policy_data.items()},
        "required": sorted(policy_data),
    }


def read_component(d, credentials, folders):
    cid, problems = d.name, []
    m = json.loads((d / "component.json").read_text())
    keys = CARD_KEYS if m["group"] == "card" else COMPONENT_KEYS
    if set(m) != keys:
        problems.append(f"policy_components/{cid}/component.json: has {sorted(m)}, needs {sorted(keys)}")
    if m["group"] not in GROUPS:
        problems.append(f"{cid}: group must be one of {GROUPS}")
    for name, spec in m["inputs"].items():
        if not INPUT_KEYS <= set(spec) <= INPUT_KEYS | INPUT_EXTRA_KEYS:
            problems.append(f"{cid}.{name}: an input has {sorted(INPUT_KEYS)}, and may have {sorted(INPUT_EXTRA_KEYS)}")
            continue
        if spec["type"] not in credentials:
            problems.append(f"{cid}.{name}: unknown credential type {spec['type']}")
        if spec["about"] not in SUBJECTS:
            problems.append(f"{cid}.{name}: about must be one of {list(SUBJECTS)}")
    output = m["output"]
    if m["group"] == "grant":
        if set(output) != {"capability", "parameters"}:
            problems.append(f"{cid}: a grant outputs {{capability, parameters}}")
    elif set(output) != {"type", "about", "claims"} or output["type"] not in credentials:
        problems.append(f"{cid}: output must be {{type, about, claims}} of a known credential type")
    else:
        credentials[output["type"]]["produced_by"].append(cid)
        if output["about"] not in SUBJECTS:
            problems.append(f"{cid}: output about must be one of {list(SUBJECTS)}")
    if m["group"] == "card" and m["card"] not in folders:
        problems.append(f"{cid}: card folder policy_cards/{m['card']} has no graph.json")
    for key, spec in m["policy_data"].items():
        if set(spec) != {"type", "description"} or spec["type"] not in POLICY_DATA_TYPES:
            problems.append(f"{cid}: policy data {key} is {{type, description}}, type one of {list(POLICY_DATA_TYPES)}")
            return {**m, "id": cid, "rego": None, "package": f"pf.components.{cid}", "policy_data_schema": {}}, problems

    rego_path = d / "component.rego"
    rego = rego_path.read_text() if rego_path.exists() else None
    if rego is None:
        problems.append(f"policy_components/{cid}: no component.rego")
    elif not re.search(rf"^package pf\.components\.{re.escape(cid)}$", rego, re.M):
        problems.append(f"{cid}: component.rego is not package pf.components.{cid}")
    return {**m, "id": cid, "rego": rego, "package": f"pf.components.{cid}",
            "policy_data_schema": policy_data_schema(m["policy_data"])}, problems


def check_graph(folder, g, components, credentials):
    out, where = [], f"policy_cards/{folder}/graph.json"
    if set(g) != {"version", "name", "root", "nodes", "trusted_issuers"} or g["version"] != 2:
        return [f"{where}: a version 2 graph has exactly version, name, root, nodes and trusted_issuers"]
    nodes = g["nodes"]
    root = g["root"]
    if root not in nodes or nodes[root]["component"] not in components or components[nodes[root]["component"]]["group"] != "grant":
        out.append(f"{where}: root must be a grant node")
    deps, registry_types = {}, set()
    for nid, n in nodes.items():
        if set(n) != {"component", "inputs", "policy_data"} or n["policy_data"] != {}:
            out.append(f"{where}: {nid} has component, inputs and policy_data {{}}; values are the asset owner's")
        if n["component"] not in components:
            out.append(f"{where}: {nid} uses unknown component {n['component']}")
            continue
        c = components[n["component"]]
        if set(n["inputs"]) != set(c["inputs"]):
            out.append(f"{where}: {nid} binds {sorted(n['inputs'])}, component has {sorted(c['inputs'])}")
        deps[nid] = set()
        for name, raw in n["inputs"].items():
            if name not in c["inputs"]:
                continue
            spec = c["inputs"][name]
            want = spec["type"]
            if want not in credentials:
                out.append(f"{where}: {nid}.{name} takes {want}, which credentials/ does not define")
                continue
            presentable = credentials[want]["presentable"]
            sources = raw if isinstance(raw, list) else [raw]
            if isinstance(raw, list) and (len(raw) < 2 or any(
                    set(s) != {"from", "node", "accept_presented"} or s["from"] != "node" or s["accept_presented"] is not False
                    for s in raw)):
                out.append(f"{where}: {nid}.{name}: a list of sources reads two or more nodes, none accepting presented")
            for src in sources:
                if src == {"from": "presented"}:
                    if not presentable:
                        out.append(f"{where}: {nid}.{name} takes {want} presented, but only components produce it; wire one")
                    if "supplied_key" not in spec:
                        registry_types.add(want)
                    continue
                if set(src) != {"from", "node", "accept_presented"} or src["from"] != "node":
                    out.append(f"{where}: {nid}.{name}: a source is {{from: presented}} or {{from: node, node, accept_presented}}")
                    continue
                if "supplied_key" in spec:
                    out.append(f"{where}: {nid}.{name}: a credential its component checks by key is presented, not wired")
                if src["node"] not in nodes:
                    out.append(f"{where}: {nid}.{name} reads unknown node {src['node']}")
                    continue
                producer = nodes[src["node"]]["component"]
                got = components[producer]["output"]["type"] if producer in components and "type" in components[producer]["output"] else None
                if got != want:
                    out.append(f"{where}: {nid}.{name} wants {want}, {src['node']} outputs {got}")
                if not isinstance(src["accept_presented"], bool):
                    out.append(f"{where}: {nid}.{name} needs accept_presented true or false")
                elif src["accept_presented"]:
                    if not presentable:
                        out.append(f"{where}: {nid}.{name} accepts a presented {want}, but its schema does not allow one (x-presentable)")
                    registry_types.add(want)
                deps[nid].add(src["node"])

    seen, stack = set(), set()

    def visit(n):
        if n in stack:
            out.append(f"{where}: cycle through {n}")
            return
        if n in seen:
            return
        stack.add(n)
        for m in sorted(deps[n] if n in deps else ()):
            visit(m)
        stack.discard(n)
        seen.add(n)

    if root in nodes:
        visit(root)
    for nid in nodes:
        if nid not in seen:
            out.append(f"{where}: {nid} does not lead to the root")
    if set(g["trusted_issuers"]) != registry_types:
        out.append(f"{where}: trusted_issuers lists {sorted(g['trusted_issuers'])}, the graph takes {sorted(registry_types)} presented")
    for t, dids in g["trusted_issuers"].items():
        if dids != []:
            out.append(f"{where}: trusted_issuers of {t} must be []; the asset owner chooses issuers")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True, type=Path, help="the policy_fabric checkout")
    ap.add_argument("--out", required=True, type=Path, help="where to write the catalog")
    a = ap.parse_args()
    catalog, problems = build(a.repo / "credentials", a.repo / "policy_components", a.repo / "policy_cards")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        sys.exit(1)
    a.out.write_text(json.dumps(catalog, indent=1, ensure_ascii=False) + "\n")
    c = catalog
    print(f"catalog: {len(c['credentials'])} credential types, {len(c['components'])} components, "
          f"{len(c['cards'])} cards", file=sys.stderr)


if __name__ == "__main__":
    main()
