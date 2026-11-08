# DUO_0000018 — NPUNCU (Not-for-Profit, Non-Commercial Use Only)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester acts for a not-for-profit organisation, and their research has no commercial purpose.

The requester holds a `LegalDesignationCredential` about themselves with a
not-for-profit legal form (`nonprofitLegalForms`), and a
`ResearchPurposeCredential` about themselves none of whose purposes is
prohibited (`prohibitedPurposes`, preset to the commercial term). The fact must
be about the project the request names, which keeps this card consistent with
every other project-bound card on the same asset.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| User | `LegalDesignationCredential` | the requester | `hasLegalForm` |
| User | `ResearchPurposeCredential` | the requester | `purposes`, `project` |

**Parameters**

- `nonprofitLegalForms` — ISO 20275 ELF codes of the legal forms that count as
  not-for-profit. Preset: `["V2VJ", "8ES1"]`.
- `prohibitedPurposes` — Research purposes that disqualify; the research must
  have none. Preset: `["commercial"]`.

Each fact must be about the holder of its role, and from an authority this asset
accepts for that type. The card names no operation: the delivery module of the
asset's guardian does.

> The executable rule is [`policy.rego`](policy.rego); this file is its
> human-readable companion, and [`card.json`](card.json) is its manifest.
