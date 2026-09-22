# DUO_0000025 — TS (Time Limit on Use)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

Access is bounded in time. The requester presents an **AgreementCredential** (claim
`agreementInfo.documentID`) accepting the required terms document and a
**publicKeyCredential** (claim `key`) issued to the same subject, and the work must
run on a compute environment attested by a **ComputeEnvironmentCredential** (claim
`hasComputeProfile.profile.shutsDownAt`) to shut down no later than the policy
deadline. The data owner configures the `requiredDocumentID` and the `notAfter`
deadline in `policy_data`. Access is **allowed** when the accepted document
matches, a channel key is present, and the attested shutdown time is no later than
`notAfter`; otherwise it is **denied**. The credentials the decision relies on are
emitted as `verification_tasks` so the contract verifies their signatures before
the result is trusted.

**Requirements** (`data.subpolicy.requirements`): `{ "User": ["AgreementCredential", "ComputeEnvironmentCredential", "publicKeyCredential"] }`
**Policy data:** `requiredDocumentID: <did>`, `notAfter: <ISO-8601 datetime>`
**Context returned:** `{ "channel_key": "<requester public key>" }`

> Source of truth for the executable logic is [`policy.rego`](policy.rego); this
> file is the human-readable companion. The two are maintained in parallel.
