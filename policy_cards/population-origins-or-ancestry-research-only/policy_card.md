# Policy Card — DUO_0000011 POA (Population Origins or Ancestry Research Only)

Authored against the Policy Fabric Policy Card template (`duos/policy_schema.txt`).

---

## 1  Identification

- **id:** `card.duo.0000011-poa`
- **version:** 2.0.0
- **status:** released
- **title:** Population origins or ancestry research only (DUO_0000011 POA)
- **description:** Grant access only for population-origins or ancestry
  research.
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
| 1.0.0   | 2026-07-15 | MLCommons | released | Initial policy card authored from the POA policy.      |
| 2.0.0   | 2026-10-02 | MLCommons | released | Reads one fact per holder; evidence chains and delivery moved out. |

## 4  Summary & Intent

The requester holds a `ResearchPurposeCredential` about themselves whose
`purposes` include one of the owner's `allowedPurposes`, which this card presets
to the population-origins/ancestry term. The fact must be about the project the
request names, which keeps this card consistent with every other project-bound
card on the same asset.

- **Governance objective:** restrict use of the asset to population-origins and
  ancestry research.

## 5  Declarative Representation

```text
Permission: use the target dataset through its guardian
  Assignee:  the requester (the holder of each role's presentation)
  Conditions (all must hold):
    - a ResearchPurposeCredential about the requester lists a purpose ∈ allowedPurposes
    - the credential is about the project the request names
    - each credential is from an authority the owner accepts for its type
  On grant:  the operation the guardian's delivery module names
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`../../credentials/`](../../credentials/).

| Role | Credential type | About | Claims consumed |
|------|-----------------|-------|-----------------|
| User | `ResearchPurposeCredential` | the requester | `purposes`, `project` |

Each credential must be about the holder of its role: facts about third parties
-- a PI, a project, a committee -- are inputs to authorities, never to this
card.

## 7  Reference Values Schema

The values the data owner configures, as a JSON Schema in
[`card.json`](card.json) (`parameters`), which also generates the owner's form:

```json
{
  "allowedPurposes": ["string"]
}
```

- `allowedPurposes` — Research purposes that qualify; the research must have at
  least one. Preset: `["POA"]`.

## 8  Capability Granted

None of its own. A card decides; it does not deliver. The asset's guardian type
picks one delivery module, which describes the policy decision: `do_download`
with the requester's channel key for a download guardian, `do_inference` with
the approved script's digest for an inference guardian. The policy agent issues
the decision only if every card on the asset allows, and the asset's token turns
it into the capability.

## 9  Codified Representation

The rule is codified in Rego as the
[`purpose-allowed`](../templates/purpose-allowed/policy.rego) rule template,
with unit tests in [its tests](../templates/purpose-allowed/policy_test.rego).
It reads `input.presentations`, `input.holders`, `input.request` and this card's
own `input.policy_data`, and returns the decision and the credentials to verify.

## 10  Legal & Disclaimers

Reference-implementation status: this card and its Rego policy are a reference
implementation provided as-is. You are responsible for verifying its accuracy and
fitness for your use case before relying on it — it is not a certified or legally
reviewed compliance control. Do not use this card or policy to protect sensitive
data (e.g., health, medical, genetic, or other legally regulated personal data)
without independent legal and security review.
