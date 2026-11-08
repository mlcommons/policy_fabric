package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

agreement(document) := testlib.credential(
	"AgreementCredential",
	testlib.requester,
	{"agreementInfo": {"documentID": document, "documentVersion": "1"}},
)

environment(secure) := testlib.credential(
	"ComputeEnvironmentCredential",
	testlib.requester,
	{"hasComputeProfile": {"profile": {"SecureHandlingOfResults": secure}}},
)

data_ := {"requiredDocumentID": "did:example:terms-1"}

test_requirements if {
	subpolicy.requirements == {"User": ["AgreementCredential", "ComputeEnvironmentCredential"]}
}

test_allows_terms_and_a_secure_environment if {
	held := [agreement("did:example:terms-1"), environment(true)]
	r := subpolicy.result with input as testlib.requester_input(held, data_, {})
	r.decision
	r.verification_tasks == [{"index": 0}, {"index": 1}]
}

test_denies_an_insecure_environment if {
	held := [agreement("did:example:terms-1"), environment(false)]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {})
}

test_denies_other_terms if {
	held := [agreement("did:example:terms-2"), environment(true)]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {})
}

test_denies_an_environment_of_someone_else if {
	held := [agreement("did:example:terms-1"), testlib.about_someone_else(environment(true))]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {})
}

test_ignores_an_untrusted_environment if {
	held := [agreement("did:example:terms-1"), testlib.untrusted(environment(true))]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {})
}
