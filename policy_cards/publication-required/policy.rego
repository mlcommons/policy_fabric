# DUO_0000019 PUB -- Publication required
# The requester's institution accepted the Publication obligation for this
# dataset, in the project the request names.

package subpolicy

import rego.v1

requirements := {"User": ["ObligationAcceptanceCredential"]}

obligations := [c |
	some c in input.presentations.User
	c.type == "ObligationAcceptanceCredential"
	c.trusted
	c.subject == input.holders.User
	c.claims.project == input.request.project
	some scope in c.claims.scopes
	scope.obligation == "Publication"
	scope.dataset == input.policy_data.datasetID
]

default decision := false

decision if count(obligations) > 0

verification_tasks := [{"index": c.index} | some c in obligations]

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
}
