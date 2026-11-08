# FL-DS -- Disease-specific inference
# The script declares a use within the owner's MONDO disease scope.

package subpolicy

import rego.v1

requirements := {"Script": ["IntendedDataUseCredential"]}

declared_uses := [c |
	some c in input.presentations.Script
	c.type == "IntendedDataUseCredential"
	c.trusted
	c.subject == input.holders.Script
	studies_allowed_disease(c)
]

studies_allowed_disease(c) if {
	some disease in c.claims.useOnlyFor.diseases
	disease in input.policy_data.allowedDiseases
}

default decision := false

decision if count(declared_uses) > 0

verification_tasks := [{"index": c.index} | some c in declared_uses]

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
}
