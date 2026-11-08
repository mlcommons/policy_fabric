# DUO_0000045 — NPU (Not-for-Profit Organisation Use Only)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester acts for a not-for-profit organisation.

The requester holds a `LegalDesignationCredential` about themselves, from an
authority this asset accepts for that fact, whose `hasLegalForm` is one of the
not-for-profit ISO 20275 legal forms the owner lists.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| User | `LegalDesignationCredential` | the requester | `hasLegalForm` |

**Parameters**

- `nonprofitLegalForms` — ISO 20275 ELF codes of the legal forms that count as
  not-for-profit. Preset: `["V2VJ", "8ES1"]`.

Each fact must be about the holder of its role, and from an authority this asset
accepts for that type. The card names no operation: the delivery module of the
asset's guardian does.

> The executable rule is [`policy.rego`](policy.rego); this file is its
> human-readable companion, and [`card.json`](card.json) is its manifest.
