# Policy Card — FL-DS Disease-Specific Research, for inference

Authored against the Policy Fabric Policy Card template (`duos/policy_schema.txt`).

---

## 1  Identification

- **id:** `card.fl.inference-0000007-ds`
- **version:** 2.0.0
- **status:** draft
- **title:** Disease-specific inference (FL-DS)
- **description:** Permit an inference run only for a script that declares a use
  within the data owner's disease scope.
- **author:** MLCommons
- **contact:** —

## 2  Scope & Target

- **target.asset:** the dataset the data owner exposes for controlled access.
- **target.guardians:** `inference`.
- **Out of scope:** any control over the asset after it is delivered
  (redistribution, retention).

## 3  Version History

| Version | Date       | Author    | Status   | Summary of change                                      |
|---------|------------|-----------|----------|--------------------------------------------------------|
| 1.0.0   | 2026-08-20 | MLCommons | draft    | Initial card, adapting DUO_0000007 DS to inference runs. |
| 2.0.0   | 2026-10-02 | MLCommons | draft    | Reads one fact per holder; evidence chains and delivery moved out. |

## 4  Summary & Intent

The data stays put and a script runs against it, so this card asks what the code
is for rather than who is asking. The script asset holds an
`IntendedDataUseCredential` about itself, from an authority this site accepts,
and at least one of its `useOnlyFor.diseases` must be in the owner's
`allowedDiseases`.

Which script runs is fixed by the inference delivery module, which authorizes
the digest of the same script asset; both read facts about the one `Script`
holder.

- **Governance objective:** restrict inference to code declared for the diseases
  the data is consented for.

## 5  Declarative Representation

```text
Permission: use the target dataset through its guardian
  Assignee:  the requester (the holder of each role's presentation)
  Conditions (all must hold):
    - an IntendedDataUseCredential about the script lists a disease ∈ allowedDiseases
    - each credential is from an authority the owner accepts for its type
  On grant:  the operation the guardian's delivery module names
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`../../../credentials/`](../../../credentials/).

| Role | Credential type | About | Claims consumed |
|------|-----------------|-------|-----------------|
| Script | `IntendedDataUseCredential` | the script | `useOnlyFor.diseases` |

Each credential must be about the holder of its role: facts about third parties
-- a PI, a project, a committee -- are inputs to authorities, never to this
card.

## 7  Reference Values Schema

The values the data owner configures, as a JSON Schema in
[`card.json`](card.json) (`parameters`), which also generates the owner's form:

```json
{
  "allowedDiseases": ["string"]
}
```

- `allowedDiseases` — MONDO codes of the diseases research may study.

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
