# DUO_0000022 — GS (Geographical Restriction)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester is located in a country you allow.

Access depends on where the requester (or their institution) is located. The
requester holds a `LocationCredential` about themselves, from an authority this
asset accepts for that fact, and its `locatedAt.country` must be one of the
`allowedCountries` the owner sets.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| User | `LocationCredential` | the requester | `locatedAt.country` |

**Parameters**

- `allowedCountries` — Countries the requester may be located in, as
  LocationCredential names them.

Each fact must be about the holder of its role, and from an authority this asset
accepts for that type. The card names no operation: the delivery module of the
asset's guardian does.

> The executable rule is [`policy.rego`](policy.rego); this file is its
> human-readable companion, and [`card.json`](card.json) is its manifest.
