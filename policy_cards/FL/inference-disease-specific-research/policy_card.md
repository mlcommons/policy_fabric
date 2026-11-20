# Policy Card — FL-DS Disease-Specific Research, for inference

Authored against the Policy Fabric Policy Card template: the numbered sections below.

---

## 1  Identification

- **id:** `card.fl.inference-0000007-ds`
- **version:** 3.0.0
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
| 2.0.0   | 2026-10-02 | MLCommons | draft    | One Rego file reading one credential per holder; rule-based authorities joined the chains, and a delivery module issued the capability. |
| 3.0.0   | 2026-11-10 | MLCommons | draft | A graph of policy components. |

## 4  Summary & Intent

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The script declares a use within your disease scope.

The script declares a use for a disease the owner allows. Outputs the InferenceGrantCredential that Grant inference takes.

The card is a graph of policy components: each takes credentials, presented or produced by the
components before it, and outputs one of its own, until Grant inference issues the capability.

- **Governance objective:** restrict inference to code declared for the diseases
  the data is consented for.

## 5  Declarative Representation

```text
Permission: use the target dataset through its guardian
  Assignee:  the requester
  Conditions (all must hold), as the graph's components check them:
    - DiseaseSpecificResearchForInference: The script declares a use for a disease the owner allows.
    - Grant inference: every card granted the script the request names, with that digest
    - each presented credential is from an authority the owner accepts for its type
  On grant:  do_inference for the digest of the script the request names
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`credentials/`](../../../credentials/).

| Role | Credential | About | Claims read |
|---|---|---|---|
| Script | Intended data use (`IntendedDataUseCredential`) | the script | `useOnlyFor.diseases` |
| Script | Script digest (`ScriptHashCredential`) | the script | `scriptHash` |

## 7  Reference Values Schema

- **DiseaseSpecificResearchForInference · `allowedDiseases`** (array of strings): Allowed MONDO disease codes. An IntendedDataUseCredential qualifies if any entry of claims.useOnlyFor.diseases is in this list.

## 8  Capability Granted

`do_inference` for the digest of the script the request names, issued by Grant inference. With several cards on one
asset, their graphs compose into one under that component, which issues the capability only when
every card granted it.

## 9  Codified Representation

The card is [`graph.json`](graph.json), a graph of the components in
[`policy_components/`](../../../policy_components/), each a Rego component with
its own unit tests and `component.json`:

| Policy Component | What it checks |
|---|---|
| DiseaseSpecificResearchForInference | The script declares a use for a disease the owner allows. Outputs the InferenceGrantCredential that Grant inference takes. |
| Grant inference | The end of every federated learning card. Issues do_inference for the script digest the request names, when every card on the asset granted that script, with that digest. |

[`graph_tests.json`](graph_tests.json) states the decisions the
graph must reach; the contract and the card tests (`policy_components/run_tests.sh`) run
them.

## 10  Legal & Disclaimers

Reference-implementation status: this card, its graph and its components are a reference
implementation provided as-is. You are responsible for verifying its accuracy and
fitness for your use case before relying on it — it is not a certified or legally
reviewed compliance control. Do not use this card or policy to protect sensitive
data (e.g., health, medical, genetic, or other legally regulated personal data)
without independent legal and security review.
