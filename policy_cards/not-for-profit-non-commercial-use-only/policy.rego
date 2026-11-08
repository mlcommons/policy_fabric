# DUO_0000018 NPUNCU -- Not-for-profit, non-commercial use only
# The requester acts for a not-for-profit organisation, and the research of the
# project the request names has none of the prohibited (commercial) purposes.

package subpolicy

import rego.v1

requirements := {"User": ["LegalDesignationCredential", "ResearchPurposeCredential"]}

designations := [c |
	some c in input.presentations.User
	c.type == "LegalDesignationCredential"
	c.trusted
	c.subject == input.holders.User
	c.claims.hasLegalForm in input.policy_data.nonprofitLegalForms
]

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

decision if {
	count(designations) > 0
	count(research) > 0
}

relied_on := array.concat(designations, research)

verification_tasks := [{"index": c.index} | some c in relied_on]

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
}
