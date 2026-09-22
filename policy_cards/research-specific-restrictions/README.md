# DUO_0000012 — RS (Research Specific Restrictions)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

Access is limited to projects whose approved intended use falls within the data
owner's allowed research scope. The requester presents the project's
**IntendedDataUseCredential** (claim `useOnlyFor.purposes`) together with the
chain that binds them to that project — a **ProjectOwnershipCredential** (claim
`Owns`) showing a PI owns the project and a **TeamCredential** (claim
`MemberOfTeamOf`) placing the requester on that PI's team — plus an
**AgreementCredential** (accepted terms) and a **publicKeyCredential** (claim
`key`) carrying their channel public key. The data owner configures the set of
`allowedPurposes` in `policy_data`. Access is **allowed** when at least one of the
project's declared purposes is in that set and the chain resolves to a single
requester; otherwise it is **denied**. The credentials the decision relies on are
emitted as `verification_tasks` so the contract verifies their signatures before
the result is trusted.

**Requirements** (`data.subpolicy.requirements`): `{ "User": ["IntendedDataUseCredential", "ProjectOwnershipCredential", "TeamCredential", "AgreementCredential", "publicKeyCredential"] }`
**Policy data:** `allowedPurposes: [..]`
**Context returned:** `{ "channel_key": "<requester public key>" }`

> Source of truth for the executable logic is [`policy.rego`](policy.rego); this
> file is the human-readable companion. The two are maintained in parallel.
