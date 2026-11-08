# Rule template: the requester accepted the terms document the owner requires,
# and computes in an environment that handles results securely.
# Presets: MOR, RTN.

package subpolicy

import rego.v1

requirements := {"User": ["AgreementCredential", "ComputeEnvironmentCredential"]}

agreements := [c |
	some c in input.presentations.User
	c.type == "AgreementCredential"
	c.trusted
	c.subject == input.holders.User
	c.claims.agreementInfo.documentID == input.policy_data.requiredDocumentID
]

environments := [c |
	some c in input.presentations.User
	c.type == "ComputeEnvironmentCredential"
	c.trusted
	c.subject == input.holders.User
	c.claims.hasComputeProfile.profile.SecureHandlingOfResults == true
]

default decision := false

decision if {
	count(agreements) > 0
	count(environments) > 0
}

relied_on := array.concat(agreements, environments)

verification_tasks := [{"index": c.index} | some c in relied_on]

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
}
