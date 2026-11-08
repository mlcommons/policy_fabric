# Delivery for an inference guardian: the approved script the request names by its
# digest -- the one of the script actually being sent -- may run.

package subpolicy

import rego.v1

requirements := {"Script": ["ScriptHashCredential"]}

issues := "policy_decision"

digests := [c |
	some c in input.presentations.Script
	c.type == "ScriptHashCredential"
	c.trusted
	c.subject == input.holders.Script
	c.claims.scriptHash == input.request.script_digest
]

default decision := false

decision if count(digests) > 0

verification_tasks := [{"index": c.index} | some c in digests]

result := {
	"decision": true,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
	"credential": {
		"subject": input.holders.Script,
		"claims": {"name": "do_inference", "parameters": {"script_digest": input.request.script_digest}},
	},
} if decision

result := {"decision": false, "verification_tasks": [], "vc_supplied_verification_tasks": []} if not decision
