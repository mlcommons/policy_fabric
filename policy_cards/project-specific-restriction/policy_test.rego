package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

declared := {"project": "did:example:project-1"}

research(project) := testlib.credential(
	"ResearchPurposeCredential",
	testlib.requester,
	{"project": project, "purposes": ["HMB"], "diseases": []},
)

data_ := {"approvedProjects": ["did:example:project-1"]}

test_requirements if {
	subpolicy.requirements == {"User": ["ResearchPurposeCredential"]}
}

test_allows_an_approved_project if {
	r := subpolicy.result with input as testlib.requester_input([research("did:example:project-1")], data_, declared)
	r.decision
	r.verification_tasks == [{"index": 0}]
}

test_denies_another_project if {
	not subpolicy.result.decision with input as testlib.requester_input([research("did:example:project-2")], data_, {"project": "did:example:project-2"})
}

test_requires_the_requested_project if {
	held := [research("did:example:project-1"), research("did:example:project-2")]
	subpolicy.result.decision with input as testlib.requester_input(held, data_, {"project": "did:example:project-1"})
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {"project": "did:example:project-2"})
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {})
}

test_denies_research_of_someone_else if {
	c := testlib.about_someone_else(research("did:example:project-1"))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, declared)
}

test_ignores_untrusted_research if {
	c := testlib.untrusted(research("did:example:project-1"))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, declared)
}
