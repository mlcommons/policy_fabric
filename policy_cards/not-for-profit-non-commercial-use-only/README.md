# DUO_0000018 — NPUNCU (Not-for-Profit, Non-Commercial Use Only)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester acts for a not-for-profit organisation, and their research has no commercial purpose.

The requester's legal form is one the owner treats as not-for-profit, and an intended use names no purpose the owner treats as commercial. Outputs the DownloadGrantCredential that Grant download takes.

The card is a graph of policy components. Each takes credentials, from the requester's presentation or
from the components before it, and outputs a credential of its own; the last, Grant download, issues
`do_download`, encrypted to the requester's session key (the key in their `publicKeyCredential`).

| Policy Component | What it checks |
|---|---|
| NotForProfitNonCommercialUseOnly | The requester's legal form is one the owner treats as not-for-profit, and an intended use names no purpose the owner treats as commercial. Outputs the DownloadGrantCredential that Grant download takes. |
| Grant download | The end of every download card. Issues do_download to the holder of the key when the card granted that same person: the publicKeyCredential and the DownloadGrantCredential must be about the same subject. The channel key is the key in the publicKeyCredential. |

**Presented credentials**, each from an authority the asset's owner accepts for its type:

| Role | Credential | About | Claims read |
|---|---|---|---|
| User | Intended data use (`IntendedDataUseCredential`) | the project | `useOnlyFor.purposes` |
| User | Legal designation (`LegalDesignationCredential`) | the requester | `hasLegalForm` |
| User | Session key (`publicKeyCredential`) | the requester | `key` |

**Parameters:**

- **NotForProfitNonCommercialUseOnly · `nonprofitLegalForms`** (array of strings): ISO 20275 ELF codes the data owner treats as not-for-profit; a LegalDesignationCredential qualifies if its hasLegalForm is in this list. If the key is missing, nothing qualifies and access is denied.
- **NotForProfitNonCommercialUseOnly · `prohibitedPurposes`** (array of strings): Purpose terms, as they appear in IntendedDataUseCredential.useOnlyFor.purposes, that make a use commercial; at least one presented IDU must contain none of them. If the key is missing, nothing qualifies and access is denied.

> The card is [`graph.json`](graph.json), decided as [`graph_vectors.json`](graph_vectors.json) says; its
> components are in [`policy_components/`](../../policy_components/), and [`card.json`](card.json) names it.
