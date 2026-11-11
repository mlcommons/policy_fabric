# DUO_0000045 — NPU (Not-for-Profit Organisation Use Only)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester acts for a not-for-profit organisation.

It reads LegalDesignationCredential, compares them with its policy data, and outputs the DownloadGrantCredential that Grant download takes.

The card is a graph of policy components. Each takes credentials, from the requester's presentation or
from the components before it, and outputs a credential of its own; the last, Grant download, issues
`do_download`, encrypted to the requester's session key (the key in their `publicKeyCredential`).

| Policy Component | What it checks |
|---|---|
| NotForProfitOrganisationUseOnly | It reads LegalDesignationCredential, compares them with its policy data, and outputs the DownloadGrantCredential that Grant download takes. |
| Grant download | The end of every download card. Issues do_download to the holder of the key when the card granted that same person: the publicKeyCredential and the DownloadGrantCredential must be about the same subject. The channel key is the key in the publicKeyCredential. |

**Presented credentials**, each from an authority the asset's owner accepts for its type:

| Role | Credential | About | Claims read |
|---|---|---|---|
| User | Legal designation (`LegalDesignationCredential`) | the requester | `hasLegalForm` |
| User | Session key (`publicKeyCredential`) | the requester | `key` |

**Parameters:**

- **NotForProfitOrganisationUseOnly · `nonprofitLegalForms`** (array of strings): ISO 20275 ELF codes the data owner treats as not-for-profit; a LegalDesignationCredential qualifies if its hasLegalForm is in this list. If the key is missing, nothing qualifies and access is denied.

> The card is [`graph.json`](graph.json), decided as [`graph_vectors.json`](graph_vectors.json) says; its
> components are in [`policy_components/`](../../policy_components/), and [`card.json`](card.json) names it.
