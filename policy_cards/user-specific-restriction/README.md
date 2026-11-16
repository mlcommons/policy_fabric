# DUO_0000026 — US (User-Specific Restriction)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester's platform account is approved by id, account type or profile status.

The requester's platform account belongs to an approved user, is of an allowed account type, or has a profile status the owner accepts. Outputs the DownloadGrantCredential that Grant download takes.

The card is a graph of policy components. Each takes credentials, from the requester's presentation or
from the components before it, and outputs a credential of its own; the last, Grant download, issues
`do_download`, encrypted to the requester's session key (the key in their `publicKeyCredential`).

| Policy Component | What it checks |
|---|---|
| UserSpecificRestriction | The requester's platform account belongs to an approved user, is of an allowed account type, or has a profile status the owner accepts. Outputs the DownloadGrantCredential that Grant download takes. |
| Grant download | The end of every download card. Issues do_download to the holder of the key when the card granted that same person: the publicKeyCredential and the DownloadGrantCredential must be about the same subject. The channel key is the key in the publicKeyCredential. |

**Presented credentials**, each from an authority the asset's owner accepts for its type:

| Role | Credential | About | Claims read |
|---|---|---|---|
| User | Platform account (`UserPlatformCredential`) | the requester | `userId`, `accountType`, `profileStatus` |
| User | Session key (`publicKeyCredential`) | the requester | `key` |

**Parameters:**

- **UserSpecificRestriction · `approvedUsers`** (array of strings): Route 1: approved user identifiers, matched against UserPlatformCredential claims.userId.
- **UserSpecificRestriction · `allowedAccountTypes`** (array of strings): Route 2: allowed account types, matched against claims.accountType.
- **UserSpecificRestriction · `requiredProfileStatuses`** (array of strings): Route 3: accepted profile statuses, matched against claims.profileStatus. An alternative route, not an extra requirement.

> The card is [`graph.json`](graph.json), decided as [`graph_vectors.json`](graph_vectors.json) says; its
> components are in [`policy_components/`](../../policy_components/), and [`card.json`](card.json) names it.
