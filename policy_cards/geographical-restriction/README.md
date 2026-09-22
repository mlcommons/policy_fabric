# DUO_0000022 — GS (Geographical Restriction)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

Access depends on where the requester (or their institution) is located. The
requester must present a **LocationCredential** (claim `locatedAt` with at least
a `country`) issued by an authority the policy agent trusts for that credential
type, and a **publicKeyCredential** (claim `key`) carrying their channel public
key. The data owner configures the list of `allowedCountries` in `policy_data`.
Access is **allowed** when the credential's country is in `allowedCountries` and
a channel key is present; otherwise it is **denied**. The matching location and
the public key credential are emitted as `verification_tasks` so the contract
verifies their signatures before the result is trusted.

**Requirements** (`data.subpolicy.requirements`): `{ "User": ["LocationCredential", "publicKeyCredential"] }`
**Policy data:** `allowedCountries: [..]`
**Context returned:** `{ "channel_key": "<requester public key>" }`

> Source of truth for the executable logic is [`policy.rego`](policy.rego); this
> file is the human-readable companion. The two are maintained in parallel.
