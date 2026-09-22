# DUO_0000018 — NPUNCU (Not-for-Profit, Non-Commercial Use Only)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

Access is limited to not-for-profit organizations pursuing a non-commercial use.
The requester presents a **LegalDesignationCredential** (claim `hasLegalForm`, an
ISO 20275 ELF code) and a **publicKeyCredential** (claim `key`) carrying their
channel public key, both issued to the same subject, together with the project's
**IntendedDataUseCredential** (claim `useOnlyFor.purposes`). The data owner
configures the accepted `nonprofitLegalForms` and the `prohibitedPurposes` in
`policy_data`. Access is **allowed** when the legal form is not-for-profit, the
intended use declares no prohibited (commercial) purpose, and a channel key is
present; otherwise it is **denied**. The credentials the decision relies on are
emitted as `verification_tasks` so the contract verifies their signatures before
the result is trusted.

**Requirements** (`data.subpolicy.requirements`): `{ "User": ["LegalDesignationCredential", "IntendedDataUseCredential", "publicKeyCredential"] }`
**Policy data:** `nonprofitLegalForms: [..]`, `prohibitedPurposes: [..]`
**Context returned:** `{ "channel_key": "<requester public key>" }`

> Source of truth for the executable logic is [`policy.rego`](policy.rego); this
> file is the human-readable companion. The two are maintained in parallel.
