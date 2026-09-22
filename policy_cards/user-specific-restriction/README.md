# DUO_0000026 — US (User Specific Restriction)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

Access is limited to requesters whose platform account meets the data owner's
eligibility criteria. The requester presents a **UserPlatformCredential** (claims
`userId`, `accountType`, `profileStatus`) and a **publicKeyCredential** (claim
`key`) carrying their channel public key, both issued to the same subject. The data
owner configures any of `approvedUsers`, `allowedAccountTypes`, and
`requiredProfileStatuses` in `policy_data`. Access is **allowed** when the account
satisfies at least one of those routes and a channel key is present; otherwise it
is **denied**. The matching platform account and the public key credential are
emitted as `verification_tasks` so the contract verifies their signatures before
the result is trusted.

**Requirements** (`data.subpolicy.requirements`): `{ "User": ["UserPlatformCredential", "publicKeyCredential"] }`
**Policy data:** `approvedUsers: [..]`, `allowedAccountTypes: [..]`, `requiredProfileStatuses: [..]`
**Context returned:** `{ "channel_key": "<requester public key>" }`

> Source of truth for the executable logic is [`policy.rego`](policy.rego); this
> file is the human-readable companion. The two are maintained in parallel.
