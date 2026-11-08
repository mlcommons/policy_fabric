# DUO_0000021 IRB -- Ethics approval required
# The research of the project the request names has ethics approval.

package subpolicy

import rego.v1

requirements := {"User": ["EthicsApprovalCredential"]}

approvals := [c |
	some c in input.presentations.User
	c.type == "EthicsApprovalCredential"
	c.trusted
	c.subject == input.holders.User
	c.claims.project == input.request.project
]

default decision := false

decision if count(approvals) > 0

verification_tasks := [{"index": c.index} | some c in approvals]

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
}
