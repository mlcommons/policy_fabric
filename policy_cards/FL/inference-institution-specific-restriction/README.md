# FL-IS — Institution-Specific Restriction, for inference

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The requester is a member of an institution you allow, and owns the script they bring.

The requester is a member of an allowed institution and owns the script: the ScriptOwnershipCredential is signed by the requester's own wallet, and checked against the key its WalletVerifyingKeyCredential attests. Outputs, for the script, the InferenceGrantCredential that Grant inference takes.

The card is a graph of policy components. Each takes credentials, from the requester's presentation or
from the components before it, and outputs a credential of its own; the last, Grant inference, issues
`do_inference` for the digest of the script the request names.

| Policy Component | What it checks |
|---|---|
| InstitutionSpecificRestrictionForInference | The requester is a member of an allowed institution and owns the script: the ScriptOwnershipCredential is signed by the requester's own wallet, and checked against the key its WalletVerifyingKeyCredential attests. Outputs, for the script, the InferenceGrantCredential that Grant inference takes. |
| Grant inference | The end of every federated learning card. Issues do_inference for the script digest the request names, when every card on the asset granted that script, with that digest. |

**Presented credentials**, each from an authority the asset's owner accepts for its type, except the one the requester's own wallet signs:

| Role | Credential | About | Claims read |
|---|---|---|---|
| User | Affiliation (`AffiliationCredential`) | the requester | `isMemberOf` |
| Script | Script digest (`ScriptHashCredential`) | the script | `scriptHash` |
| Script | Script ownership (`ScriptOwnershipCredential`) | the script | `issuer`, `ownedBy`; signed by the requester's own wallet, checked against its attested key |
| User | Wallet key (`WalletVerifyingKeyCredential`) | the requester | `verifying_key` |

**Parameters:**

- **InstitutionSpecificRestrictionForInference · `allowedInstitutions`** (array of strings): Allowed institution identifiers. An AffiliationCredential qualifies if claims.isMemberOf is in this list.

> The card is [`graph.json`](graph.json), decided as [`graph_vectors.json`](graph_vectors.json) says; its
> components are in [`policy_components/`](../../../policy_components/), and [`card.json`](card.json) names it.
