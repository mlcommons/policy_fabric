# DUO_0000021 — IRB (Ethics Approval Required)

**Rule type:** Obligation (duty) · **Outcomes:** allow / deny

**Rule:** The requester's research has ethics approval.

The requester holds an `EthicsApprovalCredential` about themselves, from an
authority this asset accepts for that fact. The fact must be about the project
the request names, which keeps this card consistent with every other
project-bound card on the same asset.

How the approval was established is the authority's business, not this card's:
an IRB office can hand-sign it after its own review, and the
*accredited-committee check* authority card issues it from the project's
approval by a committee accredited for the PI's institution. The owner picks
which of them to accept; this card reads the fact the same way whoever issued
it.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| User | `EthicsApprovalCredential` | the requester | `project` |

**Parameters:** none; the rule is structural.

Each fact must be about the holder of its role, and from an authority this asset
accepts for that type. The card names no operation: the delivery module of the
asset's guardian does.

> The executable rule is [`policy.rego`](policy.rego); this file is its
> human-readable companion, and [`card.json`](card.json) is its manifest.
