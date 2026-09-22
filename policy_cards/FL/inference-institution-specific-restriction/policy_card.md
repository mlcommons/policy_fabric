# Policy Card — FL-IS (Institution Specific Restriction, inference)

Authored against the Policy Fabric Policy Card template (`duos/policy_schema.txt`).

---

## 1  Identification

- **id:** `card.fl.inference-0000028-is`
- **version:** 1.0.0
- **status:** draft
- **title:** Institution Specific Restriction for inference (FL-IS)
- **description:** Permit an inference run over the dataset when the requester
  belongs to an approved institution and the code to be run is one the requester
  has claimed as their own.
- **author:** MLCommons
- **contact:** —

## 2  Scope & Target

- **target.asset:** the dataset the data owner exposes for federated inference.
- **target.operations:** `inference`.
- **Out of scope:** what the requester does with the metrics an inference run
  returns; the substance or purpose of the script beyond its identity and its owner.

## 3  Version History

| Version | Date       | Author    | Status | Summary of change                                        |
|---------|------------|-----------|--------|----------------------------------------------------------|
| 1.0.0   | 2026-08-20 | MLCommons | draft  | Initial card, adapting DUO_0000028 IS to inference runs.  |

## 4  Summary & Intent

The dataset stays where it is and a script is run against it in place, so the
governing question is not only who is asking but also what will run. The requester
presents an `AffiliationCredential` naming an approved institution, a
`publicKeyCredential` carrying the public key results are returned to, and a
`WalletVerifyingKeyCredential` binding their wallet to the key it is registered
with. The script presents a `ScriptHashCredential` giving its content digest and a
`ScriptOwnershipCredential` in which a wallet claims the script.

All five must line up on one wallet and one script: the affiliation, the channel key
and the wallet key describe the same wallet; that wallet is the one claiming the
script; and the digest describes that same script. The requester therefore stands
behind the code as well as the request.

- **Governance objective:** restrict inference over the asset to requesters
  affiliated with an approved institution, running code they have claimed as
  their own.

## 5  Declarative Representation

```text
Permission: run inference over the target dataset
  Assignee:  the requester (subject of the presented requester credentials)
  Conditions (all must hold):
    - an AffiliationCredential states isMemberOf ∈ allowedInstitutions
    - a publicKeyCredential supplies the requester's channel public key
    - a WalletVerifyingKeyCredential supplies the requester's wallet verifying key
    - a ScriptOwnershipCredential names that same wallet as the script's owner
    - a ScriptHashCredential gives the digest of that same script
    - the requester credentials share one subject; the script credentials share one subject
  On grant:  a capability naming the channel key and the approved script digest
  Otherwise: denied
```

## 6  Associated Credentials

| Credential type                | Claims consumed | Required |
|--------------------------------|-----------------|----------|
| `AffiliationCredential`        | `isMemberOf`    | yes      |
| `publicKeyCredential`          | `key`           | yes      |
| `WalletVerifyingKeyCredential` | `verifying_key` | yes      |
| `ScriptOwnershipCredential`    | `ownedBy`       | yes      |
| `ScriptHashCredential`         | `scriptHash`    | yes      |

The three requester credentials must share one subject, and the two script
credentials must share one subject. The `ownedBy` claim must name the requester's
wallet, and the ownership credential must come from that same wallet.

## 7  Reference Values Schema

```json
{
  "allowedInstitutions": ["list of strings"]
}
```

- `allowedInstitutions` — the institutions whose members may run inference over
  this asset, each named by its identifier.

## 8  Capability Granted

```json
{
  "name": "do_inference",
  "parameters": {
    "channel_key": "<requester public key>",
    "script_digest": "<approved script digest>"
  }
}
```

- `channel_key` — the public key the requester receives results on, taken from the
  `publicKeyCredential`.
- `script_digest` — the digest of the approved script, taken from the
  `ScriptHashCredential`. The Asset Guardian compares it against the code actually
  presented for execution, so a capability granted for one script cannot be used to
  run another.

## 9  Codified Representation

The executable rules are in [`policy.rego`](policy.rego), with unit tests in
[`policy_test.rego`](policy_test.rego). The module allows only when a single wallet
is affiliated with an approved institution, owns the script, and supplies a channel
key, and the script's digest is stated for that same script.

## 10  Legal & Disclaimers

- **Reference implementation.** This card is part of a demonstration of the
  Policy Fabric decoupling architecture and ships without warranty.
- **Scope.** The card governs the access decision only. It makes no claim about
  what happens to results after an inference run, and adopting it does not by
  itself establish conformance with any external requirement.
