# Project research purpose
# Issues a ResearchPurposeCredential to a project member, carrying the intended
# use the project declared: member -> PI -> project -> intended use, for the
# project the request names.

package subpolicy

import rego.v1

requirements := {"User": ["TeamCredential", "ProjectOwnershipCredential", "IntendedDataUseCredential"]}

issues := "ResearchPurposeCredential"

teams := [c | some c in input.presentations.User; c.type == "TeamCredential"; c.trusted]

ownerships := [c | some c in input.presentations.User; c.type == "ProjectOwnershipCredential"; c.trusted]

uses := [c | some c in input.presentations.User; c.type == "IntendedDataUseCredential"; c.trusted]

chains := [chain |
	some team in teams
	team.subject == input.holders.User
	some ownership in ownerships
	ownership.subject == team.claims.MemberOfTeamOf
	ownership.claims.Owns == input.request.project
	some use in uses
	use.subject == input.request.project
	chain := {"use": use.claims.useOnlyFor, "links": [team, ownership, use]}
]

default decision := false

decision if count(chains) > 0

verification_tasks := [{"index": c.index} | some c in chains[0].links]

credential := {
	"subject": input.holders.User,
	"claims": {
		"project": input.request.project,
		"purposes": chains[0].use.purposes,
		"diseases": chains[0].use.diseases,
	},
}

result := {
	"decision": true,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
	"credential": credential,
} if decision

result := {"decision": false, "verification_tasks": [], "vc_supplied_verification_tasks": []} if not decision
