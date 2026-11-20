# Policy Card — DUO_0000026 US (User-Specific Restriction)

Authored against the Policy Fabric Policy Card template: the numbered sections below.

---

## 1  Identification

- **id:** `card.duo.0000026-us`
- **version:** 3.0.0
- **status:** released
- **title:** User-specific restriction (DUO_0000026 US)
- **description:** Grant access only to requesters whose platform account the
  data owner approved.
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
| 1.0.0   | 2026-07-15 | MLCommons | released | Initial policy card authored from the US policy.       |
| 2.0.0   | 2026-10-02 | MLCommons | released | One Rego file reading one credential per holder; rule-based authorities joined the chains, and a delivery module issued the capability. |
| 3.0.0   | 2026-11-10 | MLCommons | released | A graph of policy components. |

## 4  Summary & Intent

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester's platform account is approved by id, account type or profile status.

The requester's platform account belongs to an approved user, is of an allowed account type, or has a profile status the owner accepts. Outputs the DownloadGrantCredential that Grant download takes.

The card is a graph of policy components: each takes credentials, presented or produced by the
components before it, and outputs one of its own, until Grant download issues the capability.

- **Governance objective:** restrict use of the asset to approved platform
  users.

## 5  Declarative Representation

```text
Permission: use the target dataset through its guardian
  Assignee:  the requester
  Conditions (all must hold), as the graph's components check them:
    - UserSpecificRestriction: The requester's platform account belongs to an approved user, is of an allowed account type, or has a profile status the owner accepts.
    - Grant download: every card granted the holder of the session key
    - each presented credential is from an authority the owner accepts for its type
  On grant:  do_download, encrypted to the requester's session key (the key in their publicKeyCredential)
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`credentials/`](../../credentials/).

| Role | Credential | About | Claims read |
|---|---|---|---|
| User | Platform account (`UserPlatformCredential`) | the requester | `userId`, `accountType`, `profileStatus` |
| User | Session key (`publicKeyCredential`) | the requester | `key` |

## 7  Reference Values Schema

- **UserSpecificRestriction · `approvedUsers`** (array of strings): Route 1: approved user identifiers, matched against UserPlatformCredential claims.userId.
- **UserSpecificRestriction · `allowedAccountTypes`** (array of strings): Route 2: allowed account types, matched against claims.accountType.
- **UserSpecificRestriction · `requiredProfileStatuses`** (array of strings): Route 3: accepted profile statuses, matched against claims.profileStatus. An alternative route, not an extra requirement.

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
| UserSpecificRestriction | The requester's platform account belongs to an approved user, is of an allowed account type, or has a profile status the owner accepts. Outputs the DownloadGrantCredential that Grant download takes. |
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
