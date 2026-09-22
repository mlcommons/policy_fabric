# DUO_0000021 — IRB (Ethics Approval Required)

**Rule type:** Obligation (duty) · **Outcomes:** allow / deny

Access requires the project to hold ethics approval from a committee responsible
for the requester's institution. The requester presents the chain that ties them
to a project and institution — a **TeamCredential** (claim `MemberOfTeamOf`)
placing them on a PI's team, a **ProjectOwnershipCredential** (claim `Owns`)
showing that PI owns a project, and an **AffiliationCredential** (claim
`isMemberOf`) showing that PI belongs to an institution — together with an
**IRBApprovalCredential** (claim `isApprovedByEthicsCommittee`) showing the project
is approved by an ethics committee, an **EthicsCommitteeAccreditationCredential**
(claim `ResponsibleFor`) showing that committee is responsible for the PI's
institution, and the project's **IntendedDataUseCredential** declaring its intended
use. A **publicKeyCredential** (claim `key`) carries the requester's channel public
key. Access is **allowed** when the chain resolves to a single requester;
otherwise it is **denied**. The decision is structural and needs no `policy_data`.
The credentials the decision relies on are emitted as `verification_tasks` so the
contract verifies their signatures before the result is trusted.

**Requirements** (`data.subpolicy.requirements`): `{ "User": ["IntendedDataUseCredential", "IRBApprovalCredential", "ProjectOwnershipCredential", "EthicsCommitteeAccreditationCredential", "AffiliationCredential", "TeamCredential", "publicKeyCredential"] }`
**Policy data:** none (structural decision)
**Context returned:** `{ "channel_key": "<requester public key>" }`

> Source of truth for the executable logic is [`policy.rego`](policy.rego); this
> file is the human-readable companion. The two are maintained in parallel.
