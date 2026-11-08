# DUO_0000015 — NMDS (No General Methods Research)

**Rule type:** Prohibition · **Outcomes:** allow / deny

**Rule:** The requester's research does not develop general methods.

The requester holds a `ResearchPurposeCredential` about themselves none of whose
`purposes` is among the owner's `prohibitedPurposes`, which this card presets to
methods-development terms. The fact must be about the project the request names,
which keeps this card consistent with every other project-bound card on the same
asset.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| User | `ResearchPurposeCredential` | the requester | `purposes`, `project` |

**Parameters**

- `prohibitedPurposes` — Research purposes that disqualify; the research must
  have none. Preset: `["MDS", "AI_Development", "Software_Development",
  "TrainModel"]`.

Each fact must be about the holder of its role, and from an authority this asset
accepts for that type. The card names no operation: the delivery module of the
asset's guardian does.

> The executable rule is the
> [`purpose-prohibited`](../templates/purpose-prohibited/policy.rego) rule
> template; this file is its human-readable companion, and
> [`card.json`](card.json) is its manifest.
