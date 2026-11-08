# DUO_0000006 HMB -- Health or medical or biomedical research
# The research of the project the request names has an allowed health, medical
# or biomedical purpose and none of the prohibited ones.

package subpolicy

import rego.v1

requirements := {"User": ["ResearchPurposeCredential"]}

research := [c |
	some c in input.presentations.User
	c.type == "ResearchPurposeCredential"
	c.trusted
	c.subject == input.holders.User
	c.claims.project == input.request.project
	has_allowed_purpose(c)
	not has_prohibited_purpose(c)
]

has_allowed_purpose(c) if {
	some purpose in c.claims.purposes
	purpose in input.policy_data.allowedPurposes
}

has_prohibited_purpose(c) if {
	some purpose in c.claims.purposes
	purpose in input.policy_data.prohibitedPurposes
}

default decision := false

decision if count(research) > 0

verification_tasks := [{"index": c.index} | some c in research]

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
}
