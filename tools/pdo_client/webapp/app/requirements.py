"""The requirement alternatives of a policy graph, as the rego_policy_agent's set_rego_policy
expands them (compute_alternatives, in pdo-contracts' rego-contract/src/common/policy_graph.cpp).
Needs no Rego engine, so the webapp lists them, from the components' interfaces alone, before
an asset's policy is set; the card tests check every card's against the same limit."""

MAX_ALTERNATIVES = 64


class GraphError(Exception):
    pass


def _minimal(bundles):
    unique = set(bundles)
    return [b for b in unique if not any(other < b for other in unique)]


def _product(left, right):
    out = _minimal([a | b for a in left for b in right])
    if len(out) > MAX_ALTERNATIVES:
        raise GraphError(f"the graph has more than {MAX_ALTERNATIVES} requirement alternatives")
    return out


def _bundle_key(bundle):
    return (len(bundle), sorted(f"{role}\0{type}" for role, type in bundle))


def alternatives(graph, interfaces):
    """The requirement alternatives: each a minimal set of presented credential types, by role,
    smallest first. A node input needs its producer's requirements; accept_presented adds the
    alternative of presenting that credential instead."""
    memo = {}

    def node_alternatives(n):
        if n not in memo:
            node = graph["nodes"][n]
            alts = [frozenset()]
            for name in sorted(node["inputs"]):
                alts = _product(alts, input_alternatives(node, name))
            memo[n] = alts
        return memo[n]

    def input_alternatives(node, name):
        spec = interfaces[node["component"]]["inputs"][name]
        own = [frozenset([(spec["role"], spec["type"])])]
        raw = node["inputs"][name]
        alts = [frozenset()]
        for source in raw if isinstance(raw, list) else [raw]:
            if source["from"] == "presented":
                options = own
            elif source["accept_presented"]:
                options = _minimal(own + node_alternatives(source["node"]))
            else:
                options = node_alternatives(source["node"])
            alts = _product(alts, options)
        return alts

    out = []
    for bundle in sorted(node_alternatives(graph["root"]), key=_bundle_key):
        by_role = {}
        for role, type in bundle:
            by_role.setdefault(role, []).append(type)
        out.append({role: sorted(types) for role, types in sorted(by_role.items())})
    return out


def roles(graph, interfaces):
    """Every role some alternative presents from."""
    return sorted({role for bundle in alternatives(graph, interfaces) for role in bundle})
