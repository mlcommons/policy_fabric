package pf.components.project_membership

import rego.v1

# ProjectMembership: the requester is on the team of a PI who owns a project.
#   team      TeamCredential              about the requester, MemberOfTeamOf = the PI
#   ownership ProjectOwnershipCredential  about the PI, Owns = the project
# -> ProjectMembershipCredential about the requester, {project}.
# Shared by every card that asks for the requester's project.
interface := {
	"output": "ProjectMembershipCredential",
	"inputs": {
		"team": {"type": "TeamCredential", "role": "User"},
		"ownership": {"type": "ProjectOwnershipCredential", "role": "User"},
	},
	"policy_data_schema": {},
}

output := [cred |
	some team in input.inputs.team
	some ownership in input.inputs.ownership
	ownership.subject == team.claims.MemberOfTeamOf
	cred := {
		"type": "ProjectMembershipCredential",
		"subject": team.subject,
		"claims": {"project": ownership.claims.Owns},
		"evidence": evidence([team, ownership]),
	}
]

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
