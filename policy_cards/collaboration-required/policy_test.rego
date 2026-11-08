package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

scope(obligation, dataset) := {"obligation": obligation, "dataset": dataset, "agreement": "did:example:agreement"}

accepted(scopes) := testlib.credential(
	"ObligationAcceptanceCredential",
	testlib.requester,
	{"project": "did:example:p1", "scopes": scopes},
)

data_ := {"datasetID": "did:example:dataset-1"}

p1 := {"project": "did:example:p1"}

test_requirements if {
	subpolicy.requirements == {"User": ["ObligationAcceptanceCredential"]}
}

test_allows_the_accepted_obligation_for_this_dataset if {
	r := subpolicy.result with input as testlib.requester_input([accepted([scope("Collaboration", "did:example:dataset-1")])], data_, p1)
	r.decision
	r.verification_tasks == [{"index": 0}]
}

test_finds_the_obligation_among_the_accepted_scopes if {
	held := [accepted([scope("Publication", "did:example:dataset-1"), scope("Collaboration", "did:example:dataset-1")])]
	subpolicy.result.decision with input as testlib.requester_input(held, data_, p1)
}

test_denies_another_obligation if {
	held := [accepted([scope("Publication", "did:example:dataset-1")])]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, p1)
}

test_denies_an_obligation_for_another_dataset if {
	held := [accepted([scope("Collaboration", "did:example:dataset-2")])]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, p1)
}

test_requires_the_requested_project if {
	held := [accepted([scope("Collaboration", "did:example:dataset-1")])]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {"project": "did:example:p2"})
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {})
}

test_ignores_an_untrusted_acceptance if {
	c := testlib.untrusted(accepted([scope("Collaboration", "did:example:dataset-1")]))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, p1)
}
