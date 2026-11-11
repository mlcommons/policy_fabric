"""Policy graphs on the owner's side: the graph of the cards an owner puts on one asset, and
what requesters will have to present to it.

A card's graph is its ``graph.json``; the catalog (the template registry's ``/api/catalog/``)
describes the components, whose ``component.json`` mirrors each Rego interface. No Rego runs
here: the contract validates the graph when it is set.
"""

from pdo.rego.graph.requirements import alternatives

# the input of a grant that takes the cards' grants
GRANT_INPUT = "grant"


def interfaces(graph, catalog):
    """The interfaces of the graph's components, as set_policy_graph evaluates them."""
    out = {}
    for node in graph["nodes"].values():
        c = catalog["components"][node["component"]]
        inputs = {}
        for name, spec in c["inputs"].items():
            inputs[name] = {"type": spec["type"], "role": spec["role"]}
            if "supplied_key" in spec:
                inputs[name]["supplied_key"] = True
        out[node["component"]] = {
            "output": "Capability" if c["group"] == "grant" else c["output"]["type"],
            "inputs": inputs,
            "policy_data_schema": c["policy_data_schema"],
        }
    return out


def compose(card_graphs):
    """One graph from the graphs of the cards on one asset: every card's nodes, a node shared
    by several cards once (node ids are component ids), under one grant whose grant input
    takes every card's grant. Raises ValueError when the cards cannot share a graph."""
    if not card_graphs:
        raise ValueError("Select at least one policy.")
    roots = {g["root"] for g in card_graphs}
    if len(roots) != 1:
        raise ValueError("The policies end in different grants: " + ", ".join(sorted(roots)))
    root = roots.pop()

    nodes, grants, trusted = {}, [], set()
    for g in card_graphs:
        for node_id, node in g["nodes"].items():
            if node_id == root:
                continue
            if node_id in nodes and nodes[node_id] != node:
                raise ValueError(f"The policies use {node_id} differently.")
            nodes[node_id] = node
        grants.append(g["nodes"][root]["inputs"][GRANT_INPUT])
        trusted.update(g["trusted_issuers"])

    root_node = dict(card_graphs[0]["nodes"][root])
    root_node["inputs"] = {
        **root_node["inputs"],
        GRANT_INPUT: grants[0] if len(grants) == 1 else grants,
    }
    return {
        "version": 2,
        "name": " + ".join(g["name"] for g in card_graphs),
        "root": root,
        "nodes": {**nodes, root: root_node},
        "trusted_issuers": {t: [] for t in sorted(trusted)},
    }


def requirement_alternatives(graph, catalog):
    """The bundles of credential types, by role, of which requesters present one, smallest
    first, as the contract will list them."""
    return alternatives(graph, interfaces(graph, catalog))


def satisfiable(bundles, accepted, self_asserted):
    """The bundles every type of which is either accepted from some authority or asserted by
    the requester themselves: those a requester can present."""
    return [
        bundle for bundle in bundles
        if all(t in self_asserted or accepted[t] for types in bundle.values() for t in types)
    ]
