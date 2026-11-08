package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

declared := {"project": "did:example:p1"}

approval(project) := testlib.credential(
	"EthicsApprovalCredential",
	testlib.requester,
	{"project": project, "approvedBy": "did:example:irb-office"},
)

test_requirements if {
	subpolicy.requirements == {"User": ["EthicsApprovalCredential"]}
}

test_allows_an_approval if {
	r := subpolicy.result with input as testlib.requester_input([approval("did:example:p1")], {}, declared)
	r.decision
	r.verification_tasks == [{"index": 0}]
	not "credential" in object.keys(r)
}

test_requires_the_requested_project if {
	held := [approval("did:example:p1")]
	subpolicy.result.decision with input as testlib.requester_input(held, {}, {"project": "did:example:p1"})
	not subpolicy.result.decision with input as testlib.requester_input(held, {}, {"project": "did:example:p2"})
	not subpolicy.result.decision with input as testlib.requester_input(held, {}, {})
}

test_flags_only_the_approval_for_the_requested_project if {
	held := [approval("did:example:p1"), approval("did:example:p2")]
	r := subpolicy.result with input as testlib.requester_input(held, {}, {"project": "did:example:p2"})
	r.verification_tasks == [{"index": 1}]
}

test_denies_an_approval_of_someone_else if {
	c := testlib.about_someone_else(approval("did:example:p1"))
	not subpolicy.result.decision with input as testlib.requester_input([c], {}, declared)
}

test_ignores_an_untrusted_approval if {
	c := testlib.untrusted(approval("did:example:p1"))
	not subpolicy.result.decision with input as testlib.requester_input([c], {}, declared)
}

test_denies_without_an_approval if {
	not subpolicy.result.decision with input as testlib.requester_input([], {}, declared)
}
