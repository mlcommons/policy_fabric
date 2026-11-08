package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

declared := {"project": "did:example:p1"}

research(project, diseases) := testlib.credential(
	"ResearchPurposeCredential",
	testlib.requester,
	{"project": project, "purposes": ["HMB"], "diseases": diseases},
)

data_ := {"allowedDiseases": ["MONDO:0005148", "MONDO:0005015"]}

test_requirements if {
	subpolicy.requirements == {"User": ["ResearchPurposeCredential"]}
}

test_allows_an_allowed_disease if {
	r := subpolicy.result with input as testlib.requester_input([research("did:example:p1", ["MONDO:0005148"])], data_, declared)
	r.decision
	r.verification_tasks == [{"index": 0}]
}

test_denies_another_disease if {
	held := [research("did:example:p1", ["MONDO:0000001"])]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, declared)
}

test_requires_the_requested_project if {
	held := [research("did:example:p1", ["MONDO:0005148"])]
	subpolicy.result.decision with input as testlib.requester_input(held, data_, {"project": "did:example:p1"})
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {"project": "did:example:p2"})
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {})
}

test_denies_research_of_someone_else if {
	c := testlib.about_someone_else(research("did:example:p1", ["MONDO:0005148"]))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, declared)
}

test_ignores_untrusted_research if {
	c := testlib.untrusted(research("did:example:p1", ["MONDO:0005148"]))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, declared)
}
