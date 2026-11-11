# DUO_0000022 — GS (Geographical Restriction)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester is located in a country you allow.

It reads LocationCredential, compares them with its policy data, and outputs the DownloadGrantCredential that Grant download takes.

The card is a graph of policy components. Each takes credentials, from the requester's presentation or
from the components before it, and outputs a credential of its own; the last, Grant download, issues
`do_download`, encrypted to the requester's session key (the key in their `publicKeyCredential`).

| Policy Component | What it checks |
|---|---|
| GeographicalRestriction | It reads LocationCredential, compares them with its policy data, and outputs the DownloadGrantCredential that Grant download takes. |
| Grant download | The end of every download card. Issues do_download to the holder of the key when the card granted that same person: the publicKeyCredential and the DownloadGrantCredential must be about the same subject. The channel key is the key in the publicKeyCredential. |

**Presented credentials**, each from an authority the asset's owner accepts for its type:

| Role | Credential | About | Claims read |
|---|---|---|---|
| User | Location (`LocationCredential`) | the requester | `locatedAt.country` |
| User | Session key (`publicKeyCredential`) | the requester | `key` |

**Parameters:**

- **GeographicalRestriction · `allowedCountries`** (array of strings): Country values the owner allows. A LocationCredential qualifies if claims.locatedAt.country is in this list (exact string match).

> The card is [`graph.json`](graph.json), decided as [`graph_vectors.json`](graph_vectors.json) says; its
> components are in [`policy_components/`](../../policy_components/), and [`card.json`](card.json) names it.
