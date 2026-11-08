# DUO_0000007 — DS (Disease-Specific Research)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester's research studies a disease within your scope.

The requester holds a `ResearchPurposeCredential` about themselves: the project
they work on and the purposes and diseases it declared. At least one of its
`diseases` must be in the owner's `allowedDiseases` (MONDO codes). The fact must
be about the project the request names, which keeps this card consistent with
every other project-bound card on the same asset.

Which project the requester works on, and what it declared, is established once
by an authority -- for instance the *project research purpose* authority card,
which checks the requester's team, their PI's project and the project's intended
use -- rather than on every request.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| User | `ResearchPurposeCredential` | the requester | `diseases`, `project` |

**Parameters**

- `allowedDiseases` — MONDO codes of the diseases research may study.

Each fact must be about the holder of its role, and from an authority this asset
accepts for that type. The card names no operation: the delivery module of the
asset's guardian does.

> The executable rule is [`policy.rego`](policy.rego); this file is its
> human-readable companion, and [`card.json`](card.json) is its manifest.
