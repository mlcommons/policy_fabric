# DUO_0000045 NPU -- Not-for-profit organisation use only
# The requester acts for an organisation whose legal form is not-for-profit.

package subpolicy

import rego.v1

requirements := {"User": ["LegalDesignationCredential"]}

designations := [c |
	some c in input.presentations.User
	c.type == "LegalDesignationCredential"
	c.trusted
	c.subject == input.holders.User
	c.claims.hasLegalForm in input.policy_data.nonprofitLegalForms
]

default decision := false

decision if count(designations) > 0

verification_tasks := [{"index": c.index} | some c in designations]

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
}
