# Rule template: the research purpose of the project the request names includes
# none of the purposes the owner prohibits. Presets: NMDS, NCU, NPOA.

package subpolicy

import rego.v1

requirements := {"User": ["ResearchPurposeCredential"]}

research := [c |
	some c in input.presentations.User
	c.type == "ResearchPurposeCredential"
	c.trusted
	c.subject == input.holders.User
	c.claims.project == input.request.project
	not has_prohibited_purpose(c)
]

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
