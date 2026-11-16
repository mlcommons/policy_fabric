# DUO_0000006 — HMB (Health or Medical or Biomedical Research)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester's research has a health, medical or biomedical purpose, and none you prohibit.

The requester's project intends to use the data for a health, medical or biomedical purpose the owner allows and for no purpose the owner prohibits, and the requester accepted the terms. Outputs the DownloadGrantCredential that Grant download takes.

The card is a graph of policy components. Each takes credentials, from the requester's presentation or
from the components before it, and outputs a credential of its own; the last, Grant download, issues
`do_download`, encrypted to the requester's session key (the key in their `publicKeyCredential`).

| Policy Component | What it checks |
|---|---|
| ProjectMembership | The requester is on the team of a PI who owns a project. Checks that the ProjectOwnershipCredential is about the PI the TeamCredential names (MemberOfTeamOf); outputs the project, for the requester. |
| HealthOrMedicalOrBiomedicalResearch | The requester's project intends to use the data for a health, medical or biomedical purpose the owner allows and for no purpose the owner prohibits, and the requester accepted the terms. Outputs the DownloadGrantCredential that Grant download takes. |
| Grant download | The end of every download card. Issues do_download to the holder of the key when the card granted that same person: the publicKeyCredential and the DownloadGrantCredential must be about the same subject. The channel key is the key in the publicKeyCredential. |

**Presented credentials**, each from an authority the asset's owner accepts for its type:

| Role | Credential | About | Claims read |
|---|---|---|---|
| User | Project ownership (`ProjectOwnershipCredential`) | the PI | `Owns` |
| User | Team membership (`TeamCredential`) | the requester | `MemberOfTeamOf` |
| User | Accepted terms (`AgreementCredential`) | the requester | none |
| User | Intended data use (`IntendedDataUseCredential`) | the project | `useOnlyFor.purposes` |
| User | Session key (`publicKeyCredential`) | the requester | `key` |

A credential the graph also accepts presented, from an authority the owner accepts for it, stands in for the components that would produce it:

- Project membership (`ProjectMembershipCredential`) about the requester, in place of ProjectMembership's.

**Parameters:**

- **HealthOrMedicalOrBiomedicalResearch · `allowedPurposes`** (array of strings): Purpose terms the owner allows (meant to be health/medical/biomedical purposes). An IntendedDataUseCredential needs at least one useOnlyFor.purposes entry in this list.
- **HealthOrMedicalOrBiomedicalResearch · `prohibitedPurposes`** (array of strings): Purpose terms that disqualify an IntendedDataUseCredential (meant to be population-origins/ancestry purposes). An IDU with any useOnlyFor.purposes entry in this list is dropped.

> The card is [`graph.json`](graph.json), decided as [`graph_vectors.json`](graph_vectors.json) says; its
> components are in [`policy_components/`](../../policy_components/), and [`card.json`](card.json) names it.
