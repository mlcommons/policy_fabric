# DUO_0000012 — RS (Research-Specific Restrictions)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester's research has a purpose within the scope you set.

The requester holds a `ResearchPurposeCredential` about themselves whose
`purposes` include one of the owner's `allowedPurposes`. The fact must be about
the project the request names, which keeps this card consistent with every other
project-bound card on the same asset.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| User | `ResearchPurposeCredential` | the requester | `purposes`, `project` |

**Parameters**

- `allowedPurposes` — Research purposes that qualify; the research must have at
  least one.

Each fact must be about the holder of its role, and from an authority this asset
accepts for that type. The card names no operation: the delivery module of the
asset's guardian does.

> The executable rule is the
> [`purpose-allowed`](../templates/purpose-allowed/policy.rego) rule template;
> this file is its human-readable companion, and [`card.json`](card.json) is its
> manifest.
