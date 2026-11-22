# Policy Card — DUO_0000024 MOR (Publication Moratorium)

Authored against the Policy Fabric Policy Card template: the numbered sections below.

---

## 1  Identification

- **id:** `card.duo.0000024-mor`
- **version:** 3.0.0
- **status:** released
- **title:** Publication moratorium (DUO_0000024 MOR)
- **description:** Grant access only to a requester who accepted the moratorium
  terms and handles results securely.
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
| 1.0.0   | 2026-07-15 | MLCommons | released | Initial policy card authored from the MOR policy.      |
| 2.0.0   | 2026-10-02 | MLCommons | released | One Rego file reading one credential per holder; rule-based authorities joined the chains, and a delivery module issued the capability. |
| 3.0.0   | 2026-11-10 | MLCommons | released | A graph of policy components. |

## 4  Summary & Intent

**Rule type:** Obligation (duty) · **Outcomes:** allow / deny

**Rule:** The requester accepted your moratorium terms and handles results securely.

The requester accepted the terms document the owner requires, and a compute environment attests that it handles results securely. Decides about the requester.

The card is a graph of policy components: each takes credentials, presented or produced by the
components before it, and outputs one of its own or a decision. AllowIfAll joins the card
component's decision with ChannelKey's, and the graph's capability makes it into `do_download`.

- **Governance objective:** hold publications back until the moratorium ends.

## 5  Declarative Representation

```text
Permission: use the target dataset through its guardian
  Assignee:  the requester
  Conditions (all must hold), as the graph checks them:
    - PublicationMoratorium: The requester accepted the terms document the owner requires, and a compute environment attests that it handles results securely.
    - the requester holds the session key the request names: a publicKeyCredential about them carries it
    - each presented credential is from an authority the owner accepts for its type
  On grant:  do_download, encrypted to the requester's session key (the key in their publicKeyCredential)
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`credentials/`](../../credentials/).

| Role | Credential | About | Claims read |
|---|---|---|---|
| User | Accepted terms (`AgreementCredential`) | the requester | `agreementInfo.documentID` |
| User | Compute environment (`ComputeEnvironmentCredential`) | the compute node | `hasComputeProfile.profile.SecureHandlingOfResults` |
| User | Session key (`publicKeyCredential`) | the requester | `key` |

## 7  Reference Values Schema

- **PublicationMoratorium · `requiredDocumentID`** (string): Identifier of the terms document the requester must have accepted; compared for equality with AgreementCredential.agreementInfo.documentID. If the key is missing, nothing qualifies and access is denied.

## 8  Capability Granted

`do_download`, encrypted to the requester's session key (the key in their `publicKeyCredential`), made by the graph's capability from AllowIfAll's decision. With several cards on one
asset, their graphs compose into one whose AllowIfAll takes every card's decision, so it issues
`do_download` only when every card holds for the same requester.

## 9  Codified Representation

The card is [`graph.json`](graph.json), a graph of the components in
[`policy_components/`](../../policy_components/), each a Rego component with
its own unit tests and `component.json`:

| Policy Component | What it checks |
|---|---|
| PublicationMoratorium | The requester accepted the terms document the owner requires, and a compute environment attests that it handles results securely. Decides about the requester. |
| ChannelKey | The requester holds the channel key the request names, the key the download is encrypted to. Decides about the requester and admits that channel_key, which do_download takes. |
| AllowIfAll | Allows when every decision it takes allows and, for each parameter they name, they admit a value in common. Its parameters are the values all of them admit; a parameter a decision leaves out, it does not restrict. |

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
