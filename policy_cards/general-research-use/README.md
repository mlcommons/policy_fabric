# DUO_0000042 — GRU (General Research Use)

**Rule type:** Permission · **Outcomes:** allow / deny

**Rule:** The requester accepted your terms.

The requester holds an `AgreementCredential` about themselves showing they
accepted the terms document the owner requires (`requiredDocumentID`).

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| User | `AgreementCredential` | the requester | `agreementInfo.documentID` |

**Parameters**

- `requiredDocumentID` — DID of the terms document the requester must have
  accepted.

Each fact must be about the holder of its role, and from an authority this asset
accepts for that type. The card names no operation: the delivery module of the
asset's guardian does.

> The executable rule is [`policy.rego`](policy.rego); this file is its
> human-readable companion, and [`card.json`](card.json) is its manifest.
