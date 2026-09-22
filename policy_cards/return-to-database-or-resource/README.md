# DUO_0000029 — RTN (Return to Database or Resource)

**Rule type:** Obligation (duty) · **Outcomes:** allow / deny

Access carries a duty to return derived or enriched data to a designated resource.
The requester presents an **AgreementCredential** (claim
`agreementInfo.documentID`) accepting the required terms document and a
**publicKeyCredential** (claim `key`) issued to the same subject, and the work must
run on a compute environment attested by a **ComputeEnvironmentCredential** (claim
`hasComputeProfile.profile.SecureHandlingOfResults`) to handle results securely,
which is what lets the return obligation be honoured. The data owner configures the
`requiredDocumentID` in `policy_data`. Access is **allowed** when the accepted
document matches, a channel key is present, and a secure compute environment is
attested; otherwise it is **denied**. The credentials the decision relies on are
emitted as `verification_tasks` so the contract verifies their signatures before
the result is trusted.

**Requirements** (`data.subpolicy.requirements`): `{ "User": ["AgreementCredential", "ComputeEnvironmentCredential", "publicKeyCredential"] }`
**Policy data:** `requiredDocumentID: <did>`
**Context returned:** `{ "channel_key": "<requester public key>" }`

> Source of truth for the executable logic is [`policy.rego`](policy.rego); this
> file is the human-readable companion. The two are maintained in parallel.
