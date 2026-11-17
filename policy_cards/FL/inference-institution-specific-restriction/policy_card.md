# Policy Card — FL-IS Institution-Specific Restriction, for inference

Authored against the Policy Fabric Policy Card template: the numbered sections below.

---

## 1  Identification

- **id:** `card.fl.inference-0000028-is`
- **version:** 3.0.0
- **status:** draft
- **title:** Institution-specific inference (FL-IS)
- **description:** Permit an inference run only for a member of an allowed
  institution who owns the script they bring.
- **author:** MLCommons
- **contact:** —

## 2  Scope & Target

- **target.asset:** the dataset the data owner exposes for controlled access.
- **target.guardians:** `inference`.
- **Out of scope:** what the requester does with the metrics a run returns.

## 3  Version History

| Version | Date       | Author    | Status   | Summary of change                                      |
|---------|------------|-----------|----------|--------------------------------------------------------|
| 1.0.0   | 2026-08-20 | MLCommons | draft    | Initial card, adapting DUO_0000028 IS to inference runs. |
| 2.0.0   | 2026-10-02 | MLCommons | draft    | One Rego file reading one credential per holder; rule-based authorities joined the chains, and a delivery module issued the capability. |
| 3.0.0   | 2026-11-10 | MLCommons | draft | A graph of policy components. |

## 4  Summary & Intent

The requester is a member of an allowed institution and owns the script: the ScriptOwnershipCredential is signed by the requester's own wallet, and checked against the key its WalletVerifyingKeyCredential attests. Outputs, for the script, the InferenceGrantCredential that Grant inference takes.

The card is a graph of policy components: each takes credentials, presented or produced by the
components before it, and outputs one of its own, until Grant inference issues the capability.

- **Governance objective:** restrict inference to code its requester stands
  behind, from approved institutions.

## 5  Declarative Representation

```text
Permission: use the target dataset through its guardian
  Assignee:  the requester
  Conditions (all must hold), as the graph's components check them:
    - InstitutionSpecificRestrictionForInference: The requester is a member of an allowed institution and owns the script: the ScriptOwnershipCredential is signed by the requester's own wallet, and checked against the key its WalletVerifyingKeyCredential attests.
    - Grant inference: every card granted the script the request names, with that digest
    - each presented credential is from an authority the owner accepts for its type, except the one the requester's own wallet signs, checked against its attested key
  On grant:  do_inference for the digest of the script the request names
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`credentials/`](../../../credentials/).

| Role | Credential | About | Claims read |
|---|---|---|---|
| User | Affiliation (`AffiliationCredential`) | the requester | `isMemberOf` |
| Script | Script digest (`ScriptHashCredential`) | the script | `scriptHash` |
| Script | Script ownership (`ScriptOwnershipCredential`) | the script | `issuer`, `ownedBy`; signed by the requester's own wallet, checked against its attested key |
| User | Wallet key (`WalletVerifyingKeyCredential`) | the requester | `verifying_key` |

## 7  Reference Values Schema

- **InstitutionSpecificRestrictionForInference · `allowedInstitutions`** (array of strings): Allowed institution identifiers. An AffiliationCredential qualifies if claims.isMemberOf is in this list.

## 8  Capability Granted

`do_inference` for the digest of the script the request names, issued by Grant inference. With several cards on one
asset, their graphs compose into one under that component, which issues the capability only when
every card granted it.

## 9  Codified Representation

The card is [`graph.json`](graph.json), a graph of the components in
[`policy_components/`](../../../policy_components/), each a Rego component with
its own unit tests and `component.json`. [`graph_vectors.json`](graph_vectors.json) states the decisions the
graph must reach; the contract and the card tests (`policy_components/run_tests.sh`) run
them.

## 10  Legal & Disclaimers

Reference-implementation status: this card, its graph and its components are a reference
implementation provided as-is. You are responsible for verifying its accuracy and
fitness for your use case before relying on it — it is not a certified or legally
reviewed compliance control. Do not use this card or policy to protect sensitive
data (e.g., health, medical, genetic, or other legally regulated personal data)
without independent legal and security review.
