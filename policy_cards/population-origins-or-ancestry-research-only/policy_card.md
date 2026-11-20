# Policy Card — DUO_0000011 POA (Population Origins or Ancestry Research Only)

Authored against the Policy Fabric Policy Card template: the numbered sections below.

---

## 1  Identification

- **id:** `card.duo.0000011-poa`
- **version:** 3.0.0
- **status:** released
- **title:** Population origins or ancestry research only (DUO_0000011 POA)
- **description:** Grant access only for population-origins or ancestry
  research.
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
| 1.0.0   | 2026-07-15 | MLCommons | released | Initial policy card authored from the POA policy.      |
| 2.0.0   | 2026-10-02 | MLCommons | released | One Rego file reading one credential per holder; rule-based authorities joined the chains, and a delivery module issued the capability. |
| 3.0.0   | 2026-11-10 | MLCommons | released | A graph of policy components: the chain is joined in the policy, and a joined credential an owner accepts may be presented instead. |

## 4  Summary & Intent

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester's research studies population origins or ancestry.

The requester's project intends to use the data for a population origins or ancestry purpose the owner allows, and the requester accepted the terms. Outputs the DownloadGrantCredential that Grant download takes.

The card is a graph of policy components: each takes credentials, presented or produced by the
components before it, and outputs one of its own, until Grant download issues the capability.

- **Governance objective:** restrict use of the asset to population-origins and
  ancestry research.

## 5  Declarative Representation

```text
Permission: use the target dataset through its guardian
  Assignee:  the requester
  Conditions (all must hold), as the graph's components check them:
    - ProjectMembership: The requester is on the team of a PI who owns a project.
    - PopulationOriginsOrAncestryResearchOnly: The requester's project intends to use the data for a population origins or ancestry purpose the owner allows, and the requester accepted the terms.
    - Grant download: every card granted the holder of the session key
    - each presented credential is from an authority the owner accepts for its type
  On grant:  do_download, encrypted to the requester's session key (the key in their publicKeyCredential)
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`credentials/`](../../credentials/).

| Role | Credential | About | Claims read |
|---|---|---|---|
| User | Project ownership (`ProjectOwnershipCredential`) | the PI | `Owns` |
| User | Team membership (`TeamCredential`) | the requester | `MemberOfTeamOf` |
| User | Accepted terms (`AgreementCredential`) | the requester | none |
| User | Intended data use (`IntendedDataUseCredential`) | the project | `useOnlyFor.purposes` |
| User | Session key (`publicKeyCredential`) | the requester | `key` |

A credential the graph also accepts presented, from an authority the owner accepts for it, stands in for the components that would produce it:

- Project membership (`ProjectMembershipCredential`) about the requester, in place of ProjectMembership's.

## 7  Reference Values Schema

- **PopulationOriginsOrAncestryResearchOnly · `allowedPurposes`** (array of strings): Purpose terms, as they appear in IntendedDataUseCredential.useOnlyFor.purposes, that make an IDU usable: at least one of its purposes must be in this list. If the key is missing, no IDU qualifies and access is denied.

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
| ProjectMembership | The requester is on the team of a PI who owns a project. Checks that the ProjectOwnershipCredential is about the PI the TeamCredential names (MemberOfTeamOf); outputs the project, for the requester. |
| PopulationOriginsOrAncestryResearchOnly | The requester's project intends to use the data for a population origins or ancestry purpose the owner allows, and the requester accepted the terms. Outputs the DownloadGrantCredential that Grant download takes. |
| Grant download | The end of every download card. Issues do_download to the holder of the key when the card granted that same person: the publicKeyCredential and the DownloadGrantCredential must be about the same subject. The channel key is the key in the publicKeyCredential. |

[`graph_vectors.json`](graph_vectors.json) states the decisions the
graph must reach; the contract and the card tests (`policy_components/run_tests.sh`) run
them.

## 10  Legal & Disclaimers

Reference-implementation status: this card, its graph and its components are a reference
implementation provided as-is. You are responsible for verifying its accuracy and
fitness for your use case before relying on it — it is not a certified or legally
reviewed compliance control. Do not use this card or policy to protect sensitive
data (e.g., health, medical, genetic, or other legally regulated personal data)
without independent legal and security review.
