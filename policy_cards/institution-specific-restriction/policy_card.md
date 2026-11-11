# Policy Card — DUO_0000028 IS (Institution-Specific Restriction)

Authored against the Policy Fabric Policy Card template (`duos/policy_schema.txt`).

---

## 1  Identification

- **id:** `card.duo.0000028-is`
- **version:** 3.0.0
- **status:** released
- **title:** Institution-specific restriction (DUO_0000028 IS)
- **description:** Grant access only to a requester who is a member of an
  institution the data owner allows.
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
| 1.0.0   | 2026-07-10 | MLCommons | released | Initial policy card authored from the IS policy.       |
| 2.0.0   | 2026-10-02 | MLCommons | released | Reads one fact per holder; evidence chains and delivery moved out. |
| 3.0.0   | 2026-11-10 | MLCommons | released | A graph of policy components: the chain is joined in the policy, and a joined credential an owner accepts may be presented instead. |

## 4  Summary & Intent

It reads AffiliationCredential, compares them with its policy data, and outputs the DownloadGrantCredential that Grant download takes.

The card is a graph of policy components: each takes credentials, presented or produced by the
components before it, and outputs one of its own, until Grant download issues the capability.

- **Governance objective:** restrict use of the asset to members of approved
  institutions.

## 5  Declarative Representation

```text
Permission: use the target dataset through its guardian
  Assignee:  the requester
  Conditions (all must hold), as the graph's components check them:
    - InstitutionSpecificRestriction: It reads AffiliationCredential, compares them with its policy data, and outputs the DownloadGrantCredential that Grant download takes.
    - Grant download: every card granted the holder of the session key
    - each presented credential is from an authority the owner accepts for its type
  On grant:  do_download, encrypted to the requester's session key (the key in their publicKeyCredential)
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`credentials/`](../../credentials/).

| Role | Credential | About | Claims read |
|---|---|---|---|
| User | Affiliation (`AffiliationCredential`) | the requester | `isMemberOf` |
| User | Session key (`publicKeyCredential`) | the requester | `key` |

## 7  Reference Values Schema

- **InstitutionSpecificRestriction · `allowedInstitutions`** (array of strings): Institution DIDs the owner allows. An AffiliationCredential qualifies if claims.isMemberOf is in this list.

## 8  Capability Granted

`do_download`, encrypted to the requester's session key (the key in their `publicKeyCredential`), issued by Grant download. With several cards on one
asset, their graphs compose into one under that component, which issues the capability only when
every card granted it.

## 9  Codified Representation

The card is [`graph.json`](graph.json), a graph of the components in
[`policy_components/`](../../policy_components/), each a Rego module with its
own unit tests. [`graph_vectors.json`](graph_vectors.json) states the decisions the graph must reach; the
contract, the reference implementation in pdo-contracts (`pdo.rego.graph`) and the card tests run them.

## 10  Legal & Disclaimers

Reference-implementation status: this card and its Rego policy are a reference
implementation provided as-is. You are responsible for verifying its accuracy and
fitness for your use case before relying on it — it is not a certified or legally
reviewed compliance control. Do not use this card or policy to protect sensitive
data (e.g., health, medical, genetic, or other legally regulated personal data)
without independent legal and security review.
