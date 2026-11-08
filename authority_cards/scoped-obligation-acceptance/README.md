# Scoped obligation acceptance

**Rule-based authority** · issues **ObligationAcceptanceCredential**

**Rule:** The member's institution accepted obligations for their project, each scoped to a dataset.

The member presents the whole chain from their own wallet: their TeamCredential,
and copies of the credentials about their PI, project, the institution and the
agreement that the issuing offices delivered to it. The obligation acceptance
lands in the member's wallet.

| Role | Input |
|------|-------|
| User | `TeamCredential` |
| User | `ProjectOwnershipCredential` |
| User | `AffiliationCredential` |
| User | `ScopedAgreementCredential` |
| User | `AgreementCredential` |

Every input must come from an issuer the authority's operator trusts for its
type. The issued credential is about the member (`holders.User`) and carries the
`project` the request names and its `scopes`: every `obligation` the
institution accepted for that project, each with its `dataset` and the
`agreement` that carries it.

> The executable rule is [`policy.rego`](policy.rego); [`card.json`](card.json) is
> its manifest.
