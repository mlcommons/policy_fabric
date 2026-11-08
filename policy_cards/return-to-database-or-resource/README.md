# DUO_0000029 — RTN (Return to Database or Resource)

**Rule type:** Obligation (duty) · **Outcomes:** allow / deny

**Rule:** The requester accepted to return derived data and handles results securely.

The requester holds an `AgreementCredential` about themselves for the owner's
return terms (`requiredDocumentID`), and a `ComputeEnvironmentCredential` about
themselves whose profile handles results securely.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| User | `AgreementCredential` | the requester | `agreementInfo.documentID` |
| User | `ComputeEnvironmentCredential` | the requester | `hasComputeProfile.profile.SecureHandlingOfResults` |

**Parameters**

- `requiredDocumentID` — DID of the terms document the requester must have
  accepted.

Each fact must be about the holder of its role, and from an authority this asset
accepts for that type. The card names no operation: the delivery module of the
asset's guardian does.

> The executable rule is the
> [`secure-results`](../templates/secure-results/policy.rego) rule template;
> this file is its human-readable companion, and [`card.json`](card.json) is its
> manifest.
