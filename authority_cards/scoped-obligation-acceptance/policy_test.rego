package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

pi := "did:pdo:pi"

p1 := {"project": "did:example:p1"}

scoped(document, obligation, project, dataset) := testlib.credential("ScopedAgreementCredential", document, {"agreementInfo": {
	"counterParty": "did:example:owner",
	"scope": {"obligation": obligation, "project": project, "dataset": dataset},
}})

agreement(document, institution) := testlib.credential("AgreementCredential", institution, {"agreementInfo": {"documentID": document, "documentVersion": "1"}})

chain := [
	testlib.credential("TeamCredential", testlib.requester, {"MemberOfTeamOf": pi}),
	testlib.credential("ProjectOwnershipCredential", pi, {"Owns": "did:example:p1"}),
	testlib.credential("AffiliationCredential", pi, {"isMemberOf": "did:example:university", "typeOfMembership": "faculty"}),
	scoped("did:example:agreement", "Collaboration", "did:example:p1", "did:example:dataset-1"),
	agreement("did:example:agreement", "did:example:university"),
]

test_issues_the_accepted_obligation_to_the_member if {
	r := subpolicy.result with input as testlib.requester_input(chain, {}, p1)
	r.decision
	r.credential == {"subject": testlib.requester, "claims": {
		"project": "did:example:p1",
		"scopes": [{"obligation": "Collaboration", "dataset": "did:example:dataset-1", "agreement": "did:example:agreement"}],
	}}
	count(r.verification_tasks) == 5
}

test_lists_every_obligation_accepted_for_the_project if {
	held := array.concat(chain, [
		scoped("did:example:agreement-2", "Publication", "did:example:p1", "did:example:dataset-2"),
		agreement("did:example:agreement-2", "did:example:university"),
	])
	r := subpolicy.result with input as testlib.requester_input(held, {}, p1)
	{s.obligation | some s in r.credential.claims.scopes} == {"Collaboration", "Publication"}
	count(r.verification_tasks) == 7
}

test_issues_for_the_requested_project_only if {
	not subpolicy.result.decision with input as testlib.requester_input(chain, {}, {"project": "did:example:p2"})
	not subpolicy.result.decision with input as testlib.requester_input(chain, {}, {})
}

test_denies_an_agreement_accepted_by_another_institution if {
	held := [chain[0], chain[1], chain[2], chain[3], agreement("did:example:agreement", "did:example:elsewhere")]
	r := subpolicy.result with input as testlib.requester_input(held, {}, p1)
	not r.decision
	not r.credential
}

test_denies_an_agreement_scoped_to_another_project if {
	other := scoped("did:example:agreement", "Collaboration", "did:example:p2", "did:example:dataset-1")
	held := [chain[0], chain[1], chain[2], other, chain[4]]
	not subpolicy.result.decision with input as testlib.requester_input(held, {}, p1)
}

test_ignores_an_untrusted_link if {
	held := [chain[0], chain[1], chain[2], testlib.untrusted(chain[3]), chain[4]]
	not subpolicy.result.decision with input as testlib.requester_input(held, {}, p1)
}
