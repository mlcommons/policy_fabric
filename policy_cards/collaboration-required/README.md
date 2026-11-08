# DUO_0000020 — COL (Collaboration Required)

**Rule type:** Obligation (duty) · **Outcomes:** allow / deny

**Rule:** The requester's institution accepted to collaborate with you on this dataset.

The requester holds an `ObligationAcceptanceCredential` about themselves: their
institution accepted the `Collaboration` obligation for their project and for
this dataset (`datasetID`). The fact must be about the project the request
names, which keeps this card consistent with every other project-bound card on
the same asset.

Establishing that acceptance -- the requester's PI, the PI's institution and
project, and an agreement scoped to the obligation the institution signed -- is
the job of an authority such as the *scoped obligation acceptance* authority
card.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| User | `ObligationAcceptanceCredential` | the requester | `project`, `scopes` (`obligation`, `dataset`) |

**Parameters**

- `datasetID` — DID of this dataset, as the obligation names it.

Each fact must be about the holder of its role, and from an authority this asset
accepts for that type. The card names no operation: the delivery module of the
asset's guardian does.

> The executable rule is [`policy.rego`](policy.rego); this file is its
> human-readable companion, and [`card.json`](card.json) is its manifest.
