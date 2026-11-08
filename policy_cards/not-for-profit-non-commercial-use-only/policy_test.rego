package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

declared := {"project": "did:example:p1"}

designation(form) := testlib.credential("LegalDesignationCredential", testlib.requester, {"hasLegalForm": form})

research(purposes) := testlib.credential(
	"ResearchPurposeCredential",
	testlib.requester,
	{"project": "did:example:p1", "purposes": purposes, "diseases": []},
)

data_ := {"nonprofitLegalForms": ["V2VJ", "8ES1"], "prohibitedPurposes": ["commercial"]}

test_requirements if {
	subpolicy.requirements == {"User": ["LegalDesignationCredential", "ResearchPurposeCredential"]}
}

test_allows_nonprofit_noncommercial_research if {
	held := [designation("V2VJ"), research(["HMB"])]
	r := subpolicy.result with input as testlib.requester_input(held, data_, declared)
	r.decision
	r.verification_tasks == [{"index": 0}, {"index": 1}]
}

test_denies_a_for_profit_form if {
	held := [designation("XTIQ"), research(["HMB"])]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, declared)
}

test_denies_commercial_research if {
	held := [designation("V2VJ"), research(["HMB", "commercial"])]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, declared)
}

test_denies_research_of_someone_else if {
	held := [designation("V2VJ"), testlib.about_someone_else(research(["HMB"]))]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, declared)
}

test_requires_the_requested_project if {
	held := [designation("V2VJ"), research(["HMB"])]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {"project": "did:example:p2"})
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {})
}
