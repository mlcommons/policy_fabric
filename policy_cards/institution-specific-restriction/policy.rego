# DUO_0000028 IS -- Institution-specific restriction
# The requester is a member of an institution the owner allows.

package subpolicy

import rego.v1

requirements := {"User": ["AffiliationCredential"]}

affiliations := [c |
	some c in input.presentations.User
	c.type == "AffiliationCredential"
	c.trusted
	c.subject == input.holders.User
	c.claims.isMemberOf in input.policy_data.allowedInstitutions
]

default decision := false

decision if count(affiliations) > 0

verification_tasks := [{"index": c.index} | some c in affiliations]

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
}
