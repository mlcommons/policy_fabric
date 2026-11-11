# Policy components

A policy card can be a graph of small Rego components that pass credentials to each other
(its `graph.json`). Each component reads one or more credentials and outputs credentials of
one type; the root, a grant, issues the capability. The `rego_policy_agent` contract runs a
graph set with `set_policy_graph`: a trusted planner decides per request which components run,
and whether a presented credential stands in for a component's output. pdo-contracts'
`rego-contract/docs/policy_graph.md` is the spec.

| Folder | Holds |
| --- | --- |
| `<id>/component.rego` | `package pf.components.<id>`: the `interface` (inputs by type and role, output type, policy data schema) and the `output` rule |
| `<id>/component.json` | what the views show: name, group, summary, who each credential is about and the claims it reads, the policy data |
| `<id>/component_test.rego` | its unit tests |
| `tests/` | every component against its `component.json` on OPA and regorus, and every card's graph against its `graph_vectors.json` and against the card's original Rego module |

A component reads `{inputs: {<input>: [credential]}, policy_data, request}` and returns a list
of `{type, subject, claims, evidence}`, where evidence lists the presented credentials the
output rests on. Only the grants read the request: the session key (download) or the script
digest (inference) it names.

## The library

**Shared**: used by several cards.

| Component | Reads | Outputs |
| --- | --- | --- |
| `project_membership` | TeamCredential, ProjectOwnershipCredential | ProjectMembershipCredential |
| `institutional_irb_approval` | EthicsCommitteeAccreditationCredential, IRBApprovalCredential | InstitutionalIRBApprovalCredential |
| `irb_clearance` | InstitutionalIRBApprovalCredential, AffiliationCredential, ProjectMembershipCredential | IRBClearanceCredential |

**Cards**: one per card, named after it, outputting the DownloadGrantCredential (or, for the
FL cards, the InferenceGrantCredential) its grant takes. Their `component.json` names the card
folder and the DUO term.

**Grants**: `grant_download` issues `do_download` for the session key the request names, when
every card on the asset granted that key's holder; `grant_inference` issues `do_inference`
for the script digest the request names, when every card granted that script.

A ProjectMembershipCredential or an IRBClearanceCredential may also be presented, when a
trusted registry issues it directly (their schemas say `"x-presentable": true`): a graph input
that accepts it presented skips the components that would produce it.

## Tests

```bash
PDO_CONTRACTS_ROOT=~/pdo-contracts ./run_tests.sh
```

Needs `opa`, python3 with jsonschema and the regorus bindings (built as
`rego-contract/pdo/rego/graph/engine.py` says), a pdo-contracts checkout with the graph
reference implementation, and this repository's history (the original card modules are read
from its first commit). `-k <card or component>` on the unittest line runs one.

The cards that change meaning on purpose (Ethics Approval Required, Collaboration Required and
Publication Required read the requester's affiliation, not the PI's) are not compared with
their original module.
