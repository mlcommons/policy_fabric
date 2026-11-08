package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

pi := "did:pdo:pi"

chain := [
	testlib.credential("TeamCredential", testlib.requester, {"MemberOfTeamOf": pi}),
	testlib.credential("ProjectOwnershipCredential", pi, {"Owns": "did:example:p1"}),
	testlib.credential("AffiliationCredential", pi, {"isMemberOf": "did:example:university", "typeOfMembership": "faculty"}),
	testlib.credential("IRBApprovalCredential", "did:example:p1", {"isApprovedByEthicsCommittee": "did:example:committee"}),
	testlib.credential("EthicsCommitteeAccreditationCredential", "did:example:committee", {"ResponsibleFor": "did:example:university"}),
]

p1 := {"project": "did:example:p1"}

replaced(i, c) := array.concat(array.concat(array.slice(chain, 0, i), [c]), array.slice(chain, i + 1, count(chain)))

test_requirements_name_the_chain if {
	subpolicy.requirements == {"User": [
		"TeamCredential",
		"ProjectOwnershipCredential",
		"AffiliationCredential",
		"IRBApprovalCredential",
		"EthicsCommitteeAccreditationCredential",
	]}
}

test_issues_an_approval_about_the_member if {
	r := subpolicy.result with input as testlib.requester_input(chain, {}, p1)
	r.decision
	r.credential == {
		"subject": testlib.requester,
		"claims": {"project": "did:example:p1", "approvedBy": "did:example:committee"},
	}
	r.verification_tasks == [{"index": 0}, {"index": 1}, {"index": 2}, {"index": 3}, {"index": 4}]
}

test_issues_for_the_requested_project_only if {
	not subpolicy.result.decision with input as testlib.requester_input(chain, {}, {"project": "did:example:p2"})
	not subpolicy.result.decision with input as testlib.requester_input(chain, {}, {})
}

test_denies_a_committee_not_responsible_for_the_pis_institution if {
	other := testlib.credential("EthicsCommitteeAccreditationCredential", "did:example:committee", {"ResponsibleFor": "did:example:elsewhere"})
	r := subpolicy.result with input as testlib.requester_input(replaced(4, other), {}, p1)
	not r.decision
	not r.credential
}

test_denies_a_member_of_another_team if {
	other := testlib.credential("TeamCredential", testlib.requester, {"MemberOfTeamOf": "did:pdo:another-pi"})
	not subpolicy.result.decision with input as testlib.requester_input(replaced(0, other), {}, p1)
}

test_denies_a_team_credential_of_someone_else if {
	other := testlib.about_someone_else(chain[0])
	not subpolicy.result.decision with input as testlib.requester_input(replaced(0, other), {}, p1)
}

test_denies_an_approval_for_another_project if {
	other := testlib.credential("IRBApprovalCredential", "did:example:p2", {"isApprovedByEthicsCommittee": "did:example:committee"})
	not subpolicy.result.decision with input as testlib.requester_input(replaced(3, other), {}, p1)
}

test_ignores_an_untrusted_link if {
	not subpolicy.result.decision with input as testlib.requester_input(replaced(3, testlib.untrusted(chain[3])), {}, p1)
}
