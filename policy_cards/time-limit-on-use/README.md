# DUO_0000025 — TS (Time Limit on Use)

**Rule type:** Obligation (duty) · **Outcomes:** allow / deny

**Rule:** The requester accepted your terms and computes in an environment that shuts down by your deadline.

The requester holds an `AgreementCredential` about themselves for the owner's
terms (`requiredDocumentID`), and a `ComputeEnvironmentCredential` about
themselves whose profile shuts down no later than `notAfter`.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| User | `AgreementCredential` | the requester | `agreementInfo.documentID` |
| User | `ComputeEnvironmentCredential` | the requester | `hasComputeProfile.profile.shutsDownAt` |

**Parameters**

- `requiredDocumentID` — DID of the terms document the requester must have
  accepted.
- `notAfter` — ISO-8601 time after which use is no longer permitted.

Each fact must be about the holder of its role, and from an authority this asset
accepts for that type. The card names no operation: the delivery module of the
asset's guardian does.

> The executable rule is [`policy.rego`](policy.rego); this file is its
> human-readable companion, and [`card.json`](card.json) is its manifest.
