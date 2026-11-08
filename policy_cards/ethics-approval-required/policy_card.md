# Policy Card — DUO_0000021 IRB (Ethics Approval Required)

Authored against the Policy Fabric Policy Card template (`duos/policy_schema.txt`).

---

## 1  Identification

- **id:** `card.duo.0000021-irb`
- **version:** 2.0.0
- **status:** released
- **title:** Ethics approval required (DUO_0000021 IRB)
- **description:** Grant access only when the requester's research has ethics
  approval.
- **author:** MLCommons
- **contact:** —

## 2  Scope & Target

- **target.asset:** the dataset the data owner exposes for controlled access.
- **target.guardians:** `download`, `inference`.
- **Out of scope:** any control over the asset after it is delivered
  (redistribution, retention).

## 3  Version History

| Version | Date       | Author    | Status   | Summary of change                                      |
|---------|------------|-----------|----------|--------------------------------------------------------|
| 1.0.0   | 2026-07-15 | MLCommons | released | Initial policy card authored from the IRB policy.      |
| 2.0.0   | 2026-10-02 | MLCommons | released | Reads one fact per holder; evidence chains and delivery moved out. |

## 4  Summary & Intent

The requester holds an `EthicsApprovalCredential` about themselves, from an
authority this asset accepts for that fact. The fact must be about the project
the request names, which keeps this card consistent with every other
project-bound card on the same asset.

How the approval was established is the authority's business, not this card's:
an IRB office can hand-sign it after its own review, and the
*accredited-committee check* authority card issues it from the project's
approval by a committee accredited for the PI's institution. The owner picks
which of them to accept; this card reads the fact the same way whoever issued
it.

- **Governance objective:** restrict use of the asset to ethically approved
  research.

## 5  Declarative Representation

```text
Permission: use the target dataset through its guardian
  Assignee:  the requester (the holder of each role's presentation)
  Conditions (all must hold):
    - an EthicsApprovalCredential about the requester
    - the approval is for the project the request names
    - each credential is from an authority the owner accepts for its type
  On grant:  the operation the guardian's delivery module names
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`../../credentials/`](../../credentials/).

| Role | Credential type | About | Claims consumed |
|------|-----------------|-------|-----------------|
| User | `EthicsApprovalCredential` | the requester | `project` |

Each credential must be about the holder of its role: facts about third parties
-- a PI, a project, a committee -- are inputs to authorities, never to this
card.

## 7  Reference Values Schema

This card needs no owner-configured values; the decision is structural.

## 8  Capability Granted

None of its own. A card decides; it does not deliver. The asset's guardian type
picks one delivery module, which describes the policy decision: `do_download`
with the requester's channel key for a download guardian, `do_inference` with
the approved script's digest for an inference guardian. The policy agent issues
the decision only if every card on the asset allows, and the asset's token turns
it into the capability.

## 9  Codified Representation

The rule is codified in Rego as [`policy.rego`](policy.rego), with unit tests in
[`policy_test.rego`](policy_test.rego). It reads `input.presentations`,
`input.holders`, `input.request` and this card's own `input.policy_data`, and
returns the decision and the credentials to verify.

## 10  Legal & Disclaimers

Reference-implementation status: this card and its Rego policy are a reference
implementation provided as-is. You are responsible for verifying its accuracy and
fitness for your use case before relying on it — it is not a certified or legally
reviewed compliance control. Do not use this card or policy to protect sensitive
data (e.g., health, medical, genetic, or other legally regulated personal data)
without independent legal and security review.
