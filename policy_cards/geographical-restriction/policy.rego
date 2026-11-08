# DUO_0000022 GS -- Geographical restriction
# The requester is located in a country the owner allows.

package subpolicy

import rego.v1

requirements := {"User": ["LocationCredential"]}

locations := [c |
	some c in input.presentations.User
	c.type == "LocationCredential"
	c.trusted
	c.subject == input.holders.User
	c.claims.locatedAt.country in input.policy_data.allowedCountries
]

default decision := false

decision if count(locations) > 0

verification_tasks := [{"index": c.index} | some c in locations]

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
}
