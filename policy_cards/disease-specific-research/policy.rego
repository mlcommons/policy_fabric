# DUO_0000007 DS -- Disease-specific research
# The research of the project the request names studies a disease within the
# owner's MONDO scope.

package subpolicy

import rego.v1

requirements := {"User": ["ResearchPurposeCredential"]}

research := [c |
	some c in input.presentations.User
	c.type == "ResearchPurposeCredential"
	c.trusted
	c.subject == input.holders.User
	c.claims.project == input.request.project
	studies_allowed_disease(c)
]

studies_allowed_disease(c) if {
	some disease in c.claims.diseases
	disease in input.policy_data.allowedDiseases
}

default decision := false

decision if count(research) > 0

verification_tasks := [{"index": c.index} | some c in research]

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
}
