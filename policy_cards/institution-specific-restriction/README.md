# DUO_0000028 — IS (Institution Specific Restriction)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

Access is limited to requesters affiliated with an allowed institution. The
requester must present an **AffiliationCredential** (claim `isMemberOf` naming
the institution) issued by an authority the policy agent trusts for that
credential type, and a **publicKeyCredential** (claim `key`) carrying their
channel public key. The data owner configures the set of `allowedInstitutions`
in `policy_data`. Access is **allowed** when a trusted affiliation names an
institution in that set and a channel key is present; otherwise it is **denied**.
The matching affiliation and the public key credential are emitted as
`verification_tasks` so the contract verifies their signatures before the result
is trusted.

**Requirements** (`data.subpolicy.requirements`): `{ "User": ["AffiliationCredential", "publicKeyCredential"] }`
**Policy data:** `allowedInstitutions: [..]`
**Context returned:** `{ "channel_key": "<requester public key>" }`

> Source of truth for the executable logic is [`policy.rego`](policy.rego); this
> file is the human-readable companion. The two are maintained in parallel.
