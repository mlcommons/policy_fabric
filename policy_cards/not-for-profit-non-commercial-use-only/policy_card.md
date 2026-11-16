# Policy Card — DUO_0000018 NPUNCU (Not-for-Profit, Non-Commercial Use Only)

Authored against the Policy Fabric Policy Card template: the numbered sections below.

---

## 1  Identification

- **id:** `card.duo.0000018-npuncu`
- **version:** 3.0.0
- **status:** released
- **title:** Not-for-profit, non-commercial use only (DUO_0000018 NPUNCU)
- **description:** Grant access only to a not-for-profit requester whose
  research has no commercial purpose.
- **author:** MLCommons
- **contact:** —

## 2  Scope & Target

- **target.asset:** the dataset the data owner exposes for controlled access.
- **target.guardians:** `download`.
- **Out of scope:** any control over the asset after it is delivered
  (redistribution, retention).

## 3  Version History

| Version | Date       | Author    | Status   | Summary of change                                      |
|---------|------------|-----------|----------|--------------------------------------------------------|
| 1.0.0   | 2026-07-15 | MLCommons | released | Initial policy card authored from the NPUNCU policy.   |
| 2.0.0   | 2026-10-02 | MLCommons | released | One Rego file reading one credential per holder; rule-based authorities joined the chains, and a delivery module issued the capability. |
| 3.0.0   | 2026-11-10 | MLCommons | released | A graph of policy components. |

## 4  Summary & Intent

The requester's legal form is one the owner treats as not-for-profit, and an intended use names no purpose the owner treats as commercial. Outputs the DownloadGrantCredential that Grant download takes.

The card is a graph of policy components: each takes credentials, presented or produced by the
components before it, and outputs one of its own, until Grant download issues the capability.

- **Governance objective:** restrict use of the asset to not-for-profit,
  non-commercial research.

## 5  Declarative Representation

```text
Permission: use the target dataset through its guardian
  Assignee:  the requester
  Conditions (all must hold), as the graph's components check them:
    - NotForProfitNonCommercialUseOnly: The requester's legal form is one the owner treats as not-for-profit, and an intended use names no purpose the owner treats as commercial.
    - Grant download: every card granted the holder of the session key
    - each presented credential is from an authority the owner accepts for its type
  On grant:  do_download, encrypted to the requester's session key (the key in their publicKeyCredential)
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`credentials/`](../../credentials/).

| Role | Credential | About | Claims read |
|---|---|---|---|
| User | Intended data use (`IntendedDataUseCredential`) | the project | `useOnlyFor.purposes` |
| User | Legal designation (`LegalDesignationCredential`) | the requester | `hasLegalForm` |
| User | Session key (`publicKeyCredential`) | the requester | `key` |

## 7  Reference Values Schema

- **NotForProfitNonCommercialUseOnly · `nonprofitLegalForms`** (array of strings): ISO 20275 ELF codes the data owner treats as not-for-profit; a LegalDesignationCredential qualifies if its hasLegalForm is in this list. If the key is missing, nothing qualifies and access is denied.
- **NotForProfitNonCommercialUseOnly · `prohibitedPurposes`** (array of strings): Purpose terms, as they appear in IntendedDataUseCredential.useOnlyFor.purposes, that make a use commercial; at least one presented IDU must contain none of them. If the key is missing, nothing qualifies and access is denied.

## 8  Capability Granted

`do_download`, encrypted to the requester's session key (the key in their `publicKeyCredential`), issued by Grant download. With several cards on one
asset, their graphs compose into one under that component, which issues the capability only when
every card granted it.

## 9  Codified Representation

The card is [`graph.json`](graph.json), a graph of the components in
[`policy_components/`](../../policy_components/), each a Rego component with
its own unit tests and `component.json`. [`graph_vectors.json`](graph_vectors.json) states the decisions the
graph must reach; the contract, the reference implementation in pdo-contracts (`pdo.rego.graph`) and the card
tests run them.

## 10  Legal & Disclaimers

Reference-implementation status: this card, its graph and its components are a reference
implementation provided as-is. You are responsible for verifying its accuracy and
fitness for your use case before relying on it — it is not a certified or legally
reviewed compliance control. Do not use this card or policy to protect sensitive
data (e.g., health, medical, genetic, or other legally regulated personal data)
without independent legal and security review.
