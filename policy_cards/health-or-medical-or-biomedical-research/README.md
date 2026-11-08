# DUO_0000006 — HMB (Health or Medical or Biomedical Research)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester's research has a health, medical or biomedical purpose, and none you prohibit.

The requester holds a `ResearchPurposeCredential` about themselves whose
`purposes` include one of the owner's `allowedPurposes` and none of the
`prohibitedPurposes`. The fact must be about the project the request names,
which keeps this card consistent with every other project-bound card on the same
asset.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| User | `ResearchPurposeCredential` | the requester | `purposes`, `project` |

**Parameters**

- `allowedPurposes` — Research purposes that qualify; the research must have at
  least one. Preset: `["HMB"]`.
- `prohibitedPurposes` — Research purposes that disqualify; the research must
  have none. Preset: `["POA"]`.

Each fact must be about the holder of its role, and from an authority this asset
accepts for that type. The card names no operation: the delivery module of the
asset's guardian does.

> The executable rule is [`policy.rego`](policy.rego); this file is its
> human-readable companion, and [`card.json`](card.json) is its manifest.
