# FL-IS — Institution-Specific Restriction, for inference

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester is a member of an institution you allow, and owns the script they bring.

The requester holds an `AffiliationCredential` about themselves naming one of
the owner's `allowedInstitutions`, and a `WalletVerifyingKeyCredential` binding
their wallet to the key it is registered with on the ledger. The script holds a
`ScriptOwnershipCredential` in which the requester's wallet claims it.

That ownership claim is self-issued, so no trusted issuer stands behind it. The
card checks its signature against the wallet key an authority attested instead,
through `vc_supplied_verification_tasks`: the claim counts because the
requester's own wallet signed it.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| User | `AffiliationCredential` | the requester | `isMemberOf` |
| User | `WalletVerifyingKeyCredential` | the requester | `verifying_key` |
| Script | `ScriptOwnershipCredential` | the script | `ownedBy` |

**Parameters**

- `allowedInstitutions` — DIDs of the institutions the requester may be a member
  of.

Each fact must be about the holder of its role, and from an authority this asset
accepts for that type. The card names no operation: the delivery module of the
asset's guardian does.

> The executable rule is [`policy.rego`](policy.rego); this file is its
> human-readable companion, and [`card.json`](card.json) is its manifest.
