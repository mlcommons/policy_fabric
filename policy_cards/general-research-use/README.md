# DUO_0000042 — GRU (General Research Use)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

Access is available for general research once the requester accepts the data
owner's terms. The requester presents an **AgreementCredential** (claim
`agreementInfo.documentID`) accepting the required terms document, together with a
**publicKeyCredential** (claim `key`) carrying their channel public key. Both
credentials must be issued to the same subject. The data owner configures the
`requiredDocumentID` in `policy_data`. Access is **allowed** when the accepted
document matches and a channel key is present; otherwise it is **denied**. The
matching agreement and the public key credential are emitted as
`verification_tasks` so the contract verifies their signatures before the result
is trusted.

**Requirements** (`data.subpolicy.requirements`): `{ "User": ["AgreementCredential", "publicKeyCredential"] }`
**Policy data:** `requiredDocumentID: <did>`
**Context returned:** `{ "channel_key": "<requester public key>" }`

> Source of truth for the executable logic is [`policy.rego`](policy.rego); this
> file is the human-readable companion. The two are maintained in parallel.
