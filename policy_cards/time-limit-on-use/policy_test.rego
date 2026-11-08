package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

agreement := testlib.credential(
	"AgreementCredential",
	testlib.requester,
	{"agreementInfo": {"documentID": "did:example:terms-1", "documentVersion": "1"}},
)

environment(shuts_down_at) := testlib.credential(
	"ComputeEnvironmentCredential",
	testlib.requester,
	{"hasComputeProfile": {"profile": {"SecureHandlingOfResults": true, "shutsDownAt": shuts_down_at}}},
)

data_ := {"requiredDocumentID": "did:example:terms-1", "notAfter": "2027-12-31T23:59:59Z"}

test_requirements if {
	subpolicy.requirements == {"User": ["AgreementCredential", "ComputeEnvironmentCredential"]}
}

test_allows_an_environment_that_shuts_down_in_time if {
	held := [agreement, environment("2027-06-01T00:00:00Z")]
	r := subpolicy.result with input as testlib.requester_input(held, data_, {})
	r.decision
	r.verification_tasks == [{"index": 0}, {"index": 1}]
}

test_denies_an_environment_that_runs_past_the_deadline if {
	held := [agreement, environment("2028-06-01T00:00:00Z")]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {})
}

test_denies_without_the_terms if {
	held := [environment("2027-06-01T00:00:00Z")]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {})
}

test_denies_an_environment_of_someone_else if {
	held := [agreement, testlib.about_someone_else(environment("2027-06-01T00:00:00Z"))]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {})
}
