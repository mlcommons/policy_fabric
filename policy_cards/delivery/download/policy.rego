# Delivery for a download guardian: the data is released encrypted to the session
# key the request names, bound to the requester, who holds its private half.

package subpolicy

import rego.v1

requirements := {"User": ["publicKeyCredential"]}

issues := "policy_decision"

session_keys := [c |
	some c in input.presentations.User
	c.type == "publicKeyCredential"
	c.trusted
	c.subject == input.holders.User
	c.claims.key == input.request.channel_key
]

default decision := false

decision if count(session_keys) > 0

verification_tasks := [{"index": c.index} | some c in session_keys]

result := {
	"decision": true,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
	"credential": {
		"subject": input.holders.User,
		"claims": {"name": "do_download", "parameters": {"channel_key": input.request.channel_key}},
	},
} if decision

result := {"decision": false, "verification_tasks": [], "vc_supplied_verification_tasks": []} if not decision
