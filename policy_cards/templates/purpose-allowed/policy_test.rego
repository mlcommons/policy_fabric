package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

declared := {"project": "did:example:p1"}

research(project, purposes) := testlib.credential(
	"ResearchPurposeCredential",
	testlib.requester,
	{"project": project, "purposes": purposes, "diseases": []},
)

data_ := {"allowedPurposes": ["GSO"]}

test_requirements if {
	subpolicy.requirements == {"User": ["ResearchPurposeCredential"]}
}

test_allows_an_allowed_purpose if {
	r := subpolicy.result with input as testlib.requester_input([research("did:example:p1", ["HMB", "GSO"])], data_, declared)
	r.decision
	r.verification_tasks == [{"index": 0}]
}

test_denies_without_an_allowed_purpose if {
	held := [research("did:example:p1", ["HMB"])]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, declared)
}

test_requires_the_requested_project if {
	held := [research("did:example:p1", ["GSO"])]
	subpolicy.result.decision with input as testlib.requester_input(held, data_, {"project": "did:example:p1"})
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {"project": "did:example:p2"})
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {})
}

test_denies_research_of_someone_else if {
	c := testlib.about_someone_else(research("did:example:p1", ["GSO"]))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, declared)
}

test_ignores_untrusted_research if {
	c := testlib.untrusted(research("did:example:p1", ["GSO"]))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, declared)
}

test_denies_without_allowed_purposes if {
	held := [research("did:example:p1", ["GSO"])]
	not subpolicy.result.decision with input as testlib.requester_input(held, {}, declared)
}
