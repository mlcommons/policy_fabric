# DUO_0000024 — MOR (Publication Moratorium)

**Rule type:** Obligation (duty) · **Outcomes:** allow / deny

**Rule:** The requester accepted your moratorium terms and handles results securely.

It reads AgreementCredential and ComputeEnvironmentCredential, compares them with its policy data, and outputs the DownloadGrantCredential that Grant download takes.

The card is a graph of policy components. Each takes credentials, from the requester's presentation or
from the components before it, and outputs a credential of its own; the last, Grant download, issues
`do_download`, encrypted to the requester's session key (the key in their `publicKeyCredential`).

| Policy Component | What it checks |
|---|---|
| PublicationMoratorium | It reads AgreementCredential and ComputeEnvironmentCredential, compares them with its policy data, and outputs the DownloadGrantCredential that Grant download takes. |
| Grant download | The end of every download card. Issues do_download to the holder of the key when the card granted that same person: the publicKeyCredential and the DownloadGrantCredential must be about the same subject. The channel key is the key in the publicKeyCredential. |

**Presented credentials**, each from an authority the asset's owner accepts for its type:

| Role | Credential | About | Claims read |
|---|---|---|---|
| User | Accepted terms (`AgreementCredential`) | the requester | `agreementInfo.documentID` |
| User | Compute environment (`ComputeEnvironmentCredential`) | the compute node | `hasComputeProfile.profile.SecureHandlingOfResults` |
| User | Session key (`publicKeyCredential`) | the requester | `key` |

**Parameters:**

- **PublicationMoratorium · `requiredDocumentID`** (string): Identifier of the terms document the requester must have accepted; compared for equality with AgreementCredential.agreementInfo.documentID. If the key is missing, nothing qualifies and access is denied.

> The card is [`graph.json`](graph.json), decided as [`graph_vectors.json`](graph_vectors.json) says; its
> components are in [`policy_components/`](../../policy_components/), and [`card.json`](card.json) names it.
