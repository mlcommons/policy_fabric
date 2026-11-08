# DUO_0000028 — IS (Institution-Specific Restriction)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester is a member of an institution you allow.

The requester holds an `AffiliationCredential` about themselves, from an
authority this asset accepts for that fact, and its `isMemberOf` must be one of
the `allowedInstitutions` the owner sets. A requester with several affiliations
qualifies through any one of them.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| User | `AffiliationCredential` | the requester | `isMemberOf` |

**Parameters**

- `allowedInstitutions` — DIDs of the institutions the requester may be a member
  of.

Each fact must be about the holder of its role, and from an authority this asset
accepts for that type. The card names no operation: the delivery module of the
asset's guardian does.

> The executable rule is [`policy.rego`](policy.rego); this file is its
> human-readable companion, and [`card.json`](card.json) is its manifest.
