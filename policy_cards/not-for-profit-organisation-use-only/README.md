# DUO_0000045 — NPU (Not-for-Profit Organisation Use Only)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

Access is limited to not-for-profit organizations. The requester presents a
**LegalDesignationCredential** (claim `hasLegalForm`, an ISO 20275 ELF code) and a
**publicKeyCredential** (claim `key`) carrying their channel public key, both
issued to the same subject. The data owner configures the set of
`nonprofitLegalForms` in `policy_data`. Access is **allowed** when the credential's
legal form is in that set and a channel key is present; otherwise it is **denied**.
The matching legal designation and the public key credential are emitted as
`verification_tasks` so the contract verifies their signatures before the result is
trusted.

**Requirements** (`data.subpolicy.requirements`): `{ "User": ["LegalDesignationCredential", "publicKeyCredential"] }`
**Policy data:** `nonprofitLegalForms: [..]`
**Context returned:** `{ "channel_key": "<requester public key>" }`

> Source of truth for the executable logic is [`policy.rego`](policy.rego); this
> file is the human-readable companion. The two are maintained in parallel.
