package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

declared := {"project": "did:example:p1"}

research(purposes) := testlib.credential(
	"ResearchPurposeCredential",
	testlib.requester,
	{"project": "did:example:p1", "purposes": purposes, "diseases": []},
)

data_ := {"allowedPurposes": ["HMB"], "prohibitedPurposes": ["POA"]}

test_requirements if {
	subpolicy.requirements == {"User": ["ResearchPurposeCredential"]}
}

test_allows_a_health_purpose if {
	r := subpolicy.result with input as testlib.requester_input([research(["HMB"])], data_, declared)
	r.decision
	r.verification_tasks == [{"index": 0}]
}

test_denies_without_a_health_purpose if {
	not subpolicy.result.decision with input as testlib.requester_input([research(["GSO"])], data_, declared)
}

test_denies_a_prohibited_purpose_alongside_a_health_one if {
	not subpolicy.result.decision with input as testlib.requester_input([research(["HMB", "POA"])], data_, declared)
}

test_requires_the_requested_project if {
	held := [research(["HMB"])]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {"project": "did:example:p2"})
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {})
}

test_ignores_untrusted_research if {
	c := testlib.untrusted(research(["HMB"]))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, declared)
}
