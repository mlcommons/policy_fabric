# Policy Card — DUO_0000021 IRB (Ethics Approval Required)

Authored against the Policy Fabric Policy Card template: the numbered sections below.

---

## 1  Identification

- **id:** `card.duo.0000021-irb`
- **version:** 3.0.0
- **status:** released
- **title:** Ethics approval required (DUO_0000021 IRB)
- **description:** Grant access only when the requester's research has ethics
  approval.
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
| 1.0.0   | 2026-07-15 | MLCommons | released | Initial policy card authored from the IRB policy.      |
| 2.0.0   | 2026-10-02 | MLCommons | released | One Rego file reading one credential per holder; rule-based authorities joined the chains, and a delivery module issued the capability. |
| 3.0.0   | 2026-11-10 | MLCommons | released | A graph of policy components: the chain is joined in the policy, and a joined credential an owner accepts may be presented instead. |

## 4  Summary & Intent

**Rule type:** Obligation (duty) · **Outcomes:** allow / deny

**Rule:** The requester's research has ethics approval.

The requester holds an IRBClearanceCredential for a project, and that project's IntendedDataUseCredential names at least one purpose and only purposes the IRB approved. Outputs a DataUseConditionCredential about the requester. No policy data.

The card is a graph of policy components: each takes credentials, presented or produced by the
components before it, and outputs one of its own. The graph's capability issues `do_download` when the
card's component holds.

- **Governance objective:** restrict use of the asset to ethically approved
  research.

## 5  Declarative Representation

```text
Permission: use the target dataset through its guardian
  Assignee:  the requester
  Conditions (all must hold), as the graph checks them:
    - InstitutionalIRBApproval: The project was approved by an IRB that is accredited for an institution.
    - ProjectMembership: The requester is on the team of a PI who owns a project.
    - IRBClearance: The requester belongs to the institution whose accredited IRB approved the requester's project.
    - EthicsApprovalRequired: The requester holds an IRBClearanceCredential for a project, and that project's IntendedDataUseCredential names at least one purpose and only purposes the IRB approved.
    - the requester holds the session key the request names: a publicKeyCredential about them carries it
    - each presented credential is from an authority the owner accepts for its type
  On grant:  do_download, encrypted to the requester's session key (the key in their publicKeyCredential)
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`credentials/`](../../credentials/).

| Role | Credential | About | Claims read |
|---|---|---|---|
| User | Ethics committee accreditation (`EthicsCommitteeAccreditationCredential`) | the ethics committee | `ResponsibleFor` |
| User | IRB approval (`IRBApprovalCredential`) | the project | `isApprovedByEthicsCommittee`, `purposes` |
| User | Project ownership (`ProjectOwnershipCredential`) | the PI | `Owns` |
| User | Team membership (`TeamCredential`) | the requester | `MemberOfTeamOf` |
| User | Affiliation (`AffiliationCredential`) | the requester | `isMemberOf` |
| User | Intended data use (`IntendedDataUseCredential`) | the project | `useOnlyFor.purposes` |
| User | Session key (`publicKeyCredential`) | the requester | `key` |

A credential the graph also accepts presented, from an authority the owner accepts for it, stands in for the components that would produce it:

- Project membership (`ProjectMembershipCredential`) about the requester, in place of ProjectMembership's.
- IRB clearance (`IRBClearanceCredential`) about the requester, in place of IRBClearance's.

## 7  Reference Values Schema

This card needs no owner-configured values; the decision is structural.

## 8  Capability Granted

`do_download`, encrypted to the requester's session key (the key in their `publicKeyCredential`), issued by the graph's capability. With several cards on one
asset, their graphs compose into one whose capability requires every card's component, so it issues
`do_download` only when every card holds for the same requester.

## 9  Codified Representation

The card is [`graph.json`](graph.json), a graph of the components in
[`policy_components/`](../../policy_components/), each a Rego component with
its own unit tests and `component.json`:

| Policy Component | What it checks |
|---|---|
| InstitutionalIRBApproval | The project was approved by an IRB that is accredited for an institution. Checks that the EthicsCommitteeAccreditationCredential is about the committee that approved the project (isApprovedByEthicsCommittee); outputs, for the project, that institution (ResponsibleFor) and the purposes the IRB approved. |
| ProjectMembership | The requester is on the team of a PI who owns a project. Checks that the ProjectOwnershipCredential is about the PI the TeamCredential names (MemberOfTeamOf); outputs the project, for the requester. |
| IRBClearance | The requester belongs to the institution whose accredited IRB approved the requester's project. Checks that the AffiliationCredential is the requester's, that its isMemberOf is the approval's institution, and that the approved project is the requester's project; outputs, for the requester, the project and the approved purposes. |
| EthicsApprovalRequired | The requester holds an IRBClearanceCredential for a project, and that project's IntendedDataUseCredential names at least one purpose and only purposes the IRB approved. Outputs a DataUseConditionCredential about the requester. No policy data. |

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
