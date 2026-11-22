# Policy components

A policy card is a graph of small Rego components that pass credentials and decisions to each
other (its `graph.json`). Each component reads credentials or decisions and outputs credentials
of one type, or one decision; the graph's capability makes one decision into the operation,
with the parameters it admits. The `rego_policy_agent` contract runs a graph
set with `set_rego_policy`: a trusted planner decides per request which components run, and
whether a presented credential stands in for a component's output. pdo-contracts'
`rego-contract/docs/policy_graph.md` is the spec.

| Folder | Holds |
| --- | --- |
| `<id>/component.rego` | `package pf.components.<id>`: the `interface` (inputs by type and role, output type, policy data schema) and the `output` rule |
| `<id>/component.json` | what the views show: name, group, summary, who each credential is about and the claims it reads, the policy data |
| `<id>/component_test.rego` | its unit tests |
| `tests/` | every component against its `component.json` on OPA and regorus, and every card's graph against its `graph_tests.json` and against the card's Rego file before cards became graphs |

A component reads `{inputs: {<input>: [credential or decision]}, policy_data, request}` and
returns a list of `{type, subject, claims, evidence}`, where evidence lists the presented
credentials the output rests on, or one decision, `{allow, parameters}`: whether it allows, and
for each parameter it names the values it admits (`subject`, whom it is about, among them). Only
ChannelKey and ScriptDigest read the request, for the session key (download) or the script
digest (inference) it names.

## The library

**Shared**: used by several cards.

| Component | Reads | Outputs |
| --- | --- | --- |
| `project_membership` | TeamCredential, ProjectOwnershipCredential | ProjectMembershipCredential |
| `institutional_irb_approval` | EthicsCommitteeAccreditationCredential, IRBApprovalCredential | InstitutionalIRBApprovalCredential |
| `irb_clearance` | InstitutionalIRBApprovalCredential, AffiliationCredential, ProjectMembershipCredential | IRBClearanceCredential |
| `channel_key` | publicKeyCredential | a Decision about the requester, admitting the `channel_key` the request names |
| `script_digest` | ScriptHashCredential | a Decision about the script, admitting the `script_digest` the request names |

**Cards**: one per card, named after it, outputting a Decision about whom the card checks:
the requester, or for the FL cards the script. Their `component.json` names the card folder
and the DUO term.

**Decisions**: `allow_if_all` takes one or more decisions and allows when all of them allow
and, for each parameter they name, admit a value in common; its parameters are those common
values. A card's graph joins its card component's decision with ChannelKey's (or
ScriptDigest's) in it, and its capability takes AllowIfAll's decision.

A ProjectMembershipCredential or an IRBClearanceCredential may also be presented, when an
authority the owner accepts issues it directly (their schemas say `"x-presentable": true`): a
graph input that accepts it presented skips the components that would produce it.

## Writing a component

1. **Its output type.** A component outputs one credential type, with a JSON Schema in
   `credentials/` (`displayName`, `meaning`, `subjectKinds`, `selfAsserted` and the claims, like
   the others), or a Decision. Add `"x-presentable": true` only when an authority may also
   issue it directly; a type no component outputs is always presentable.
2. **`<id>/component.rego`**, in `package pf.components.<id>`, `<id>` being the folder name:
   - `interface`, a static rule: `{output: <type or "Decision">, inputs: {<name>: {type, role}}, policy_data_schema}`.
     `role` is the presentation the credential comes from (`User`, or `Script` for the FL
     cards); an input of decisions is `{"type": "Decision"}`. Mark an input
     `"supplied_key": true` when the component checks its credential against a key it
     supplies rather than against an accepted authority (FL-IS's self-signed script
     ownership); such an input must be presented.
   - `output`, over `input.inputs` and `input.policy_data` (and `input.request`, for a
     component that needs what the requester declared). A list of credentials, each exactly
     `{type, subject, claims, evidence}`; or one decision, exactly `{allow, parameters}`, each
     parameter a list of the values it admits, at least one each when it allows. A card
     component's decision admits whom its condition holds for:
     `{"allow": count(subjects) > 0, "parameters": {"subject": sort(subjects)}}`. A component
     with a `supplied_key` input also returns `key_checks: [{index, key, key_type}]` on every
     credential or on its decision, naming the key to check each such credential against.
     Anything else is an error, not a denial. Build outputs; never pass a presented credential
     through (it carries an `issuer`).
   - Keep to what regorus accepts: no comprehension in a rule head that uses body variables, no
     comprehension nested in another, no `time.*`, and no rule head reading a field the value may
     lack.
3. **`<id>/component_test.rego`**, in `package pf.components.<id>_test`, with credentials shaped
   as the component receives them (`{type, issuer, subject, claims, evidence}`).
4. **`<id>/component.json`**, what the views draw, which the tests check against the Rego:

   | Key | Holds |
   | --- | --- |
   | `name` | the name drawn on the Policy Component, such as `GeographicalRestriction` |
   | `group` | `shared`, `card` or `decision` (a component that only combines decisions) |
   | `summary` | what it checks, in a sentence or two; the card's Policy Card repeats it |
   | `inputs` | `{<name>: {type, about, role, claims}}`, the same names, types and roles as the interface, and `supplied_key: true` where it has it; `{type: "Decision"}` for an input of decisions. `about` says who the credential is about: `requester`, `project`, `pi`, `institution`, `committee`, `script`, `compute` or `document`. `claims` lists the claims it reads (dotted paths); `new_claims` lists any the plan adds to the type |
   | `output` | `{type, about, claims}` for a credential; `{type: "Decision", about, parameters}` for a decision, `parameters` listing what it admits besides `subject`; `{type: "Decision"}` for a `decision` component, whose decision is about whom its decisions are about |
   | `policy_data` | `{<key>: {type, description}}`, `type` being `string`, `string (ISO-8601 datetime)` or `array of strings`. The interface's `policy_data_schema` must say the same |
   | `changes_from_today` | how its card's decisions differ from the card's Rego before cards became graphs; `[]` for none |
   | `card`, `duo` | card components only: the card folder under `policy_cards/` and the DUO term |

5. Run the tests below and `python3 tools/policy_catalog/build_catalog.py --repo . --out /tmp/catalog.json`,
   which checks components, cards and credential types against each other.

A new card that uses the component is a graph of it: see
[`../policy_cards/README.md`](../policy_cards/README.md#writing-a-card).

## Tests

```bash
PDO_CONTRACTS_ROOT=~/pdo-contracts ./run_tests.sh
```

It runs `opa test` on every component, then `tests/test_components.py` (every component's
interface on OPA and on regorus, against its `component.json`) and `tests/test_cards.py`
(every card's graph against its `graph_tests.json`, and against the card's Rego file at
commit `760742d`, before cards became graphs). It needs `opa`, python3 with `jsonschema` and
the regorus bindings (built as `tests/engine.py` says), a pdo-contracts checkout, and this
repository's history back to `760742d`.

The cards are decided by `tests/policy_graph.py`, which does in Python what the
`rego_policy_agent` does on-chain: it runs the contract's own validator and planner, read
from `$PDO_CONTRACTS_ROOT/rego-contract/src/rego/common/`, and each component on regorus, the engine
the contract embeds. `tests/graph_tests.py` reads a card's `graph_tests.json` and checks each
decision, and the requirement alternatives come from the webapp's `app/requirements.py`, the
expansion the Expose form shows.

To run one component's or one card's tests:

```bash
cd policy_components/tests
PYTHONPATH=../../tools/pdo_client/webapp:../../tools/policy_catalog python3 -m unittest -v test_cards -k geographical
```

The cards that change meaning on purpose (Ethics Approval Required, Collaboration Required and
Publication Required read the requester's affiliation, not the PI's) are not compared with
their Rego file at `760742d`.
