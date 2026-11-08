# DUO_0000042 GRU -- General research use
# The requester accepted the terms document the owner requires.

package subpolicy

import rego.v1

requirements := {"User": ["AgreementCredential"]}

agreements := [c |
	some c in input.presentations.User
	c.type == "AgreementCredential"
	c.trusted
	c.subject == input.holders.User
	c.claims.agreementInfo.documentID == input.policy_data.requiredDocumentID
]

default decision := false

decision if count(agreements) > 0

verification_tasks := [{"index": c.index} | some c in agreements]

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
}
