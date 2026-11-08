# DUO_0000027 — PS (Project-Specific Restriction)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester works on a project you approved.

The requester holds a `ResearchPurposeCredential` about themselves naming a
`project` on the owner's `approvedProjects` list. The fact must be about the
project the request names, which keeps this card consistent with every other
project-bound card on the same asset.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| User | `ResearchPurposeCredential` | the requester | `project` |

**Parameters**

- `approvedProjects` — DIDs of the projects the data may be used for.

Each fact must be about the holder of its role, and from an authority this asset
accepts for that type. The card names no operation: the delivery module of the
asset's guardian does.

> The executable rule is [`policy.rego`](policy.rego); this file is its
> human-readable companion, and [`card.json`](card.json) is its manifest.
