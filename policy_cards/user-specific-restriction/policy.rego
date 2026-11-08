# DUO_0000026 US -- User-specific restriction
# The requester's platform account is approved by id, by account type, or by
# profile status.

package subpolicy

import rego.v1

requirements := {"User": ["UserPlatformCredential"]}

accounts := [c |
	some c in input.presentations.User
	c.type == "UserPlatformCredential"
	c.trusted
	c.subject == input.holders.User
	eligible(c)
]

eligible(c) if c.claims.userId in input.policy_data.approvedUsers

eligible(c) if c.claims.accountType in input.policy_data.allowedAccountTypes

eligible(c) if c.claims.profileStatus in input.policy_data.requiredProfileStatuses

default decision := false

decision if count(accounts) > 0

verification_tasks := [{"index": c.index} | some c in accounts]

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
}
