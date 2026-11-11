# DUO_0000021 — IRB (Ethics Approval Required)

**Rule type:** Obligation (duty) · **Outcomes:** allow / deny

**Rule:** The requester's research has ethics approval.

The requester holds an IRBClearanceCredential for a project, and that project's IntendedDataUseCredential names at least one purpose and only purposes the IRB approved. Outputs the DownloadGrantCredential that Grant download takes. No policy data.

The card is a graph of policy components. Each takes credentials, from the requester's presentation or
from the components before it, and outputs a credential of its own; the last, Grant download, issues
`do_download`, encrypted to the requester's session key (the key in their `publicKeyCredential`).

| Policy Component | What it checks |
|---|---|
| InstitutionalIRBApproval | The project was approved by an IRB that is accredited for an institution. Checks that the EthicsCommitteeAccreditationCredential is about the committee that approved the project (isApprovedByEthicsCommittee); outputs, for the project, that institution (ResponsibleFor) and the purposes the IRB approved. |
| ProjectMembership | The requester is on the team of a PI who owns a project. Checks that the ProjectOwnershipCredential is about the PI the TeamCredential names (MemberOfTeamOf); outputs the project, for the requester. |
| IRBClearance | The requester belongs to the institution whose accredited IRB approved the requester's project. Checks that the AffiliationCredential is the requester's, that its isMemberOf is the approval's institution, and that the approved project is the requester's project; outputs, for the requester, the project and the approved purposes. |
| EthicsApprovalRequired | The requester holds an IRBClearanceCredential for a project, and that project's IntendedDataUseCredential names at least one purpose and only purposes the IRB approved. Outputs the DownloadGrantCredential that Grant download takes. No policy data. |
| Grant download | The end of every download card. Issues do_download to the holder of the key when the card granted that same person: the publicKeyCredential and the DownloadGrantCredential must be about the same subject. The channel key is the key in the publicKeyCredential. |

**Presented credentials**, each from an authority the asset's owner accepts for its type:

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

**Parameters:**

None: the decision is structural.

> The card is [`graph.json`](graph.json), decided as [`graph_vectors.json`](graph_vectors.json) says; its
> components are in [`policy_components/`](../../policy_components/), and [`card.json`](card.json) names it.
