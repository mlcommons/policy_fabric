# FL-IS — Institution Specific Restriction (inference)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

The inference counterpart of [DUO_0000028 IS](../../institution-specific-restriction/).
It keeps that rule — the requester must belong to an allowed institution — and adds
the question inference raises that download does not: *whose code is about to run on
the data?*

The requester presents an **AffiliationCredential** (claim `isMemberOf`), a
**publicKeyCredential** (claim `key`) carrying their channel public key, and a
**WalletVerifyingKeyCredential** (claim `verifying_key`) binding their wallet to the
key it is registered with. The script presents a **ScriptHashCredential** (claim
`scriptHash`) stating its content digest and a **ScriptOwnershipCredential** (claim
`ownedBy`) in which a wallet claims the script as its own.

The ownership credential is issued by the requester's own wallet, not by a
registered authority. It is therefore checked against the verifying key the
WalletVerifyingKeyCredential carries — which is what makes a self-issued claim
mean something, and what ties the script to the same person the affiliation is
about.

Access is **allowed** when everything lines up on one wallet and one script: the
affiliation names an approved institution, the channel key and the wallet key are
about that same wallet, that wallet is the one claiming the script, and the hash
credential describes that same script. Otherwise it is **denied**.

The policy says nothing about what the script is *for* — only who stands behind it.

**Requirements** (`data.subpolicy.requirements`):

```json
{
  "User": ["AffiliationCredential", "publicKeyCredential", "WalletVerifyingKeyCredential"],
  "Script": ["ScriptOwnershipCredential", "ScriptHashCredential"]
}
```

**Policy data:** `allowedInstitutions: [..]`
**Context returned:** `{ "channel_key": "<requester public key>", "script_digest": "<approved script digest>" }`

> Source of truth for the executable logic is [`policy.rego`](policy.rego); this
> file is the human-readable companion. The two are maintained in parallel.
