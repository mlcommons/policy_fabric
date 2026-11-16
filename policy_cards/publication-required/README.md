# DUO_0000019 — PUB (Publication Required)

**Rule type:** Obligation (duty) · **Outcomes:** allow / deny

**Rule:** The requester's institution accepted to publish results from this dataset.

The requester's institution agreed to terms with the Publication obligation, scoped to the owner's dataset and the requester's project. Outputs the DownloadGrantCredential that Grant download takes.

The card is a graph of policy components. Each takes credentials, from the requester's presentation or
from the components before it, and outputs a credential of its own; the last, Grant download, issues
`do_download`, encrypted to the requester's session key (the key in their `publicKeyCredential`).

| Policy Component | What it checks |
|---|---|
| ProjectMembership | The requester is on the team of a PI who owns a project. Checks that the ProjectOwnershipCredential is about the PI the TeamCredential names (MemberOfTeamOf); outputs the project, for the requester. |
| PublicationRequired | The requester's institution agreed to terms with the Publication obligation, scoped to the owner's dataset and the requester's project. Outputs the DownloadGrantCredential that Grant download takes. |
| Grant download | The end of every download card. Issues do_download to the holder of the key when the card granted that same person: the publicKeyCredential and the DownloadGrantCredential must be about the same subject. The channel key is the key in the publicKeyCredential. |

**Presented credentials**, each from an authority the asset's owner accepts for its type:

| Role | Credential | About | Claims read |
|---|---|---|---|
| User | Project ownership (`ProjectOwnershipCredential`) | the PI | `Owns` |
| User | Team membership (`TeamCredential`) | the requester | `MemberOfTeamOf` |
| User | Affiliation (`AffiliationCredential`) | the requester | `isMemberOf` |
| User | Accepted terms (`AgreementCredential`) | the institution | `agreementInfo.documentID` |
| User | Scoped agreement (`ScopedAgreementCredential`) | the terms document | `agreementInfo.scope.obligation`, `agreementInfo.scope.dataset`, `agreementInfo.scope.project` |
| User | Session key (`publicKeyCredential`) | the requester | `key` |

A credential the graph also accepts presented, from an authority the owner accepts for it, stands in for the components that would produce it:

- Project membership (`ProjectMembershipCredential`) about the requester, in place of ProjectMembership's.

**Parameters:**

- **PublicationRequired · `datasetID`** (string): DID of the governed dataset. Only ScopedAgreementCredentials whose agreementInfo.scope.dataset equals it are kept.

> The card is [`graph.json`](graph.json), decided as [`graph_vectors.json`](graph_vectors.json) says; its
> components are in [`policy_components/`](../../policy_components/), and [`card.json`](card.json) names it.
