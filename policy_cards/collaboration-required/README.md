# DUO_0000020 — COL (Collaboration Required)

**Rule type:** Obligation (duty) · **Outcomes:** allow / deny

Access requires an executed collaboration agreement that binds the requester's
institution to the governed dataset. The requester presents the chain that ties
them to a project and institution — a **TeamCredential** (claim `MemberOfTeamOf`)
placing them on a PI's team, a **ProjectOwnershipCredential** (claim `Owns`)
showing that PI owns a project, and an **AffiliationCredential** (claim
`isMemberOf`) showing that PI belongs to an institution — together with a
**ScopedAgreementCredential** (claim `agreementInfo.scope`) naming a terms
document scoped to that project with the `Collaboration` obligation for the
governed dataset, and an **AgreementCredential** (claim
`agreementInfo.documentID`) showing the institution agreed to that document. A
**publicKeyCredential** (claim `key`) carries the requester's channel public key.
The data owner configures the governed `datasetID` in `policy_data`. Access is
**allowed** when the chain resolves to a single requester; otherwise it is
**denied**. The credentials the decision relies on are emitted as
`verification_tasks` so the contract verifies their signatures before the result
is trusted.

**Requirements** (`data.subpolicy.requirements`): `{ "User": ["ProjectOwnershipCredential", "AffiliationCredential", "TeamCredential", "ScopedAgreementCredential", "AgreementCredential", "publicKeyCredential"] }`
**Policy data:** `datasetID: <did>`
**Context returned:** `{ "channel_key": "<requester public key>" }`

> Source of truth for the executable logic is [`policy.rego`](policy.rego); this
> file is the human-readable companion. The two are maintained in parallel.
