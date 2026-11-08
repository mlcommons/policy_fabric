package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

pi := "did:pdo:pi"

chain := [
	testlib.credential("TeamCredential", testlib.requester, {"MemberOfTeamOf": pi}),
	testlib.credential("ProjectOwnershipCredential", pi, {"Owns": "did:example:p1"}),
	testlib.credential("IntendedDataUseCredential", "did:example:p1", {"useOnlyFor": {"purposes": ["HMB"], "diseases": ["MONDO:0005148"]}}),
]

p1 := {"project": "did:example:p1"}

test_requirements_name_the_chain if {
	subpolicy.requirements == {"User": ["TeamCredential", "ProjectOwnershipCredential", "IntendedDataUseCredential"]}
}

test_issues_the_projects_purpose_to_the_member if {
	r := subpolicy.result with input as testlib.requester_input(chain, {}, p1)
	r.decision
	r.credential == {
		"subject": testlib.requester,
		"claims": {"project": "did:example:p1", "purposes": ["HMB"], "diseases": ["MONDO:0005148"]},
	}
	r.verification_tasks == [{"index": 0}, {"index": 1}, {"index": 2}]
}

test_issues_for_the_requested_project_only if {
	not subpolicy.result.decision with input as testlib.requester_input(chain, {}, {"project": "did:example:p2"})
	not subpolicy.result.decision with input as testlib.requester_input(chain, {}, {})
}

test_denies_a_use_declared_for_another_project if {
	other := testlib.credential("IntendedDataUseCredential", "did:example:p2", {"useOnlyFor": {"purposes": ["HMB"], "diseases": []}})
	not subpolicy.result.decision with input as testlib.requester_input([chain[0], chain[1], other], {}, p1)
}

test_denies_a_member_of_another_team if {
	other := testlib.credential("TeamCredential", testlib.requester, {"MemberOfTeamOf": "did:pdo:another-pi"})
	not subpolicy.result.decision with input as testlib.requester_input([other, chain[1], chain[2]], {}, p1)
}

test_ignores_an_untrusted_link if {
	not subpolicy.result.decision with input as testlib.requester_input([chain[0], testlib.untrusted(chain[1]), chain[2]], {}, p1)
}
