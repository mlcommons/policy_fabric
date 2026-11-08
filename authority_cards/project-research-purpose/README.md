# Project research purpose

**Rule-based authority** · issues **ResearchPurposeCredential**

**Rule:** The member works on their PI's project, and carries the use that project declared.

The member presents the whole chain from their own wallet: their TeamCredential,
and copies of the credentials about their PI, project that the issuing offices
delivered to it. The research purpose lands in the member's wallet.

| Role | Input |
|------|-------|
| User | `TeamCredential` |
| User | `ProjectOwnershipCredential` |
| User | `IntendedDataUseCredential` |

Every input must come from an issuer the authority's operator trusts for its
type. The issued credential is about the member (`holders.User`) and carries
`project`, and the `purposes` and `diseases` the project declared. Only the
chain of the project the request names counts.

> The executable rule is [`policy.rego`](policy.rego); [`card.json`](card.json) is
> its manifest.
