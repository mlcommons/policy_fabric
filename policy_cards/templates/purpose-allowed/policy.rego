# Rule template: the research purpose of the project the request names includes
# a purpose the owner allows. Presets: GSO, RS, POA.

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
]

has_allowed_purpose(c) if {
	some purpose in c.claims.purposes
	purpose in input.policy_data.allowedPurposes
}

default decision := false

decision if count(research) > 0

verification_tasks := [{"index": c.index} | some c in research]

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
}
