# DUO_0000026 — US (User-Specific Restriction)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester's platform account is approved by id, account type or profile status.

The requester holds a `UserPlatformCredential` about themselves, from an
authority this asset accepts for that fact. The account qualifies through any
one of three routes the owner configures: its `userId` is approved by name, its
`accountType` is allowed as a group, or its `profileStatus` is accepted.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| User | `UserPlatformCredential` | the requester | `userId`, `accountType`, `profileStatus` |

**Parameters**

- `approvedUsers` — Platform account ids approved by name.
- `allowedAccountTypes` — Account types approved as a group.
- `requiredProfileStatuses` — Profile statuses approved as a group.

Each fact must be about the holder of its role, and from an authority this asset
accepts for that type. The card names no operation: the delivery module of the
asset's guardian does.

> The executable rule is [`policy.rego`](policy.rego); this file is its
> human-readable companion, and [`card.json`](card.json) is its manifest.
