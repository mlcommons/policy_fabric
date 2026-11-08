# DUO_0000027 PS -- Project-specific restriction
# The requester works on the project the request names, and the owner approved it.

package subpolicy

import rego.v1

requirements := {"User": ["ResearchPurposeCredential"]}

research := [c |
	some c in input.presentations.User
	c.type == "ResearchPurposeCredential"
	c.trusted
	c.subject == input.holders.User
	c.claims.project == input.request.project
	c.claims.project in input.policy_data.approvedProjects
]

default decision := false

decision if count(research) > 0

verification_tasks := [{"index": c.index} | some c in research]

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
}
