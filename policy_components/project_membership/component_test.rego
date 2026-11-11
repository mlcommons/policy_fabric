package pf.components.project_membership_test

import rego.v1

import data.pf.components.project_membership

team := {"type": "TeamCredential", "issuer": "did:example:registry", "subject": "did:example:user",
	"claims": {"MemberOfTeamOf": "did:example:pi"}, "evidence": [0]}

ownership := {"type": "ProjectOwnershipCredential", "issuer": "did:example:registry", "subject": "did:example:pi",
	"claims": {"Owns": "did:example:project"}, "evidence": [1]}

test_the_requester_works_on_the_project_their_pi_owns if {
	project_membership.output == [{
		"type": "ProjectMembershipCredential", "subject": "did:example:user",
		"claims": {"project": "did:example:project"}, "evidence": [0, 1],
	}] with input as {"inputs": {"team": [team], "ownership": [ownership]}, "policy_data": {}, "request": {}}
}

test_the_team_of_another_pi if {
	other := object.union(team, {"claims": {"MemberOfTeamOf": "did:example:other-pi"}})
	project_membership.output == [] with input as {"inputs": {"team": [other], "ownership": [ownership]}, "policy_data": {}, "request": {}}
}

test_one_membership_per_owned_project if {
	second := object.union(ownership, {"claims": {"Owns": "did:example:second"}, "evidence": [2]})
	memberships := project_membership.output with input as {"inputs": {"team": [team], "ownership": [ownership, second]}, "policy_data": {}, "request": {}}
	{m.claims.project | some m in memberships} == {"did:example:project", "did:example:second"}
}
