# Accredited-committee check

**Rule-based authority** · issues **EthicsApprovalCredential**

**Rule:** The member's project is approved by an ethics committee accredited for their PI's institution.

The member presents the whole chain from their own wallet: their TeamCredential,
and copies of the credentials about their PI, project and the approving
committee that the issuing offices delivered to it. The ethics approval lands in
the member's wallet.

| Role | Input |
|------|-------|
| User | `TeamCredential` |
| User | `ProjectOwnershipCredential` |
| User | `AffiliationCredential` |
| User | `IRBApprovalCredential` |
| User | `EthicsCommitteeAccreditationCredential` |

Every input must come from an issuer the authority's operator trusts for its
type. The issued credential is about the member (`holders.User`) and carries
`project` (the PI's project), `approvedBy` (the approving committee). Only the
chain of the project the request names counts.

> The executable rule is [`policy.rego`](policy.rego); [`card.json`](card.json) is
> its manifest.
