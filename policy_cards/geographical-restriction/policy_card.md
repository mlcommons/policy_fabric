# Policy Card — DUO_0000022 GS (Geographical Restriction)

Authored against the Policy Fabric Policy Card template: the numbered sections below.

---

## 1  Identification

- **id:** `card.duo.0000022-gs`
- **version:** 3.0.0
- **status:** released
- **title:** Geographical restriction (DUO_0000022 GS)
- **description:** Grant access only to a requester located in a country the
  data owner allows.
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
| 1.0.0   | 2026-07-10 | MLCommons | released | Initial policy card authored from the GS policy.       |
| 2.0.0   | 2026-10-02 | MLCommons | released | One Rego file reading one credential per holder; rule-based authorities joined the chains, and a delivery module issued the capability. |
| 3.0.0   | 2026-11-10 | MLCommons | released | A graph of policy components. |

## 4  Summary & Intent

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester is located in a country you allow.

The requester's organisation is located in a country the owner allows. Outputs the DownloadGrantCredential that Grant download takes.

The card is a graph of policy components: each takes credentials, presented or produced by the
components before it, and outputs one of its own, until Grant download issues the capability.

- **Governance objective:** restrict use of the asset to requesters located in
  an approved country.

## 5  Declarative Representation

```text
Permission: use the target dataset through its guardian
  Assignee:  the requester
  Conditions (all must hold), as the graph's components check them:
    - GeographicalRestriction: The requester's organisation is located in a country the owner allows.
    - Grant download: every card granted the holder of the session key
    - each presented credential is from an authority the owner accepts for its type
  On grant:  do_download, encrypted to the requester's session key (the key in their publicKeyCredential)
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`credentials/`](../../credentials/).

| Role | Credential | About | Claims read |
|---|---|---|---|
| User | Location (`LocationCredential`) | the requester | `locatedAt.country` |
| User | Session key (`publicKeyCredential`) | the requester | `key` |

## 7  Reference Values Schema

- **GeographicalRestriction · `allowedCountries`** (array of strings): Country values the owner allows. A LocationCredential qualifies if claims.locatedAt.country is in this list (exact string match).

## 8  Capability Granted

`do_download`, encrypted to the requester's session key (the key in their `publicKeyCredential`), issued by Grant download. With several cards on one
asset, their graphs compose into one under that component, which issues the capability only when
every card granted it.

## 9  Codified Representation

The card is [`graph.json`](graph.json), a graph of the components in
[`policy_components/`](../../policy_components/), each a Rego component with
its own unit tests and `component.json`:

| Policy Component | What it checks |
|---|---|
| GeographicalRestriction | The requester's organisation is located in a country the owner allows. Outputs the DownloadGrantCredential that Grant download takes. |
| Grant download | The end of every download card. Issues do_download to the holder of the key when the card granted that same person: the publicKeyCredential and the DownloadGrantCredential must be about the same subject. The channel key is the key in the publicKeyCredential. |

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
