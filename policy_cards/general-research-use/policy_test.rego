package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

agreement(document) := testlib.credential(
	"AgreementCredential",
	testlib.requester,
	{"agreementInfo": {"documentID": document, "documentVersion": "1"}},
)

data_ := {"requiredDocumentID": "did:example:terms-1"}

test_requirements if {
	subpolicy.requirements == {"User": ["AgreementCredential"]}
}

test_allows_the_required_terms if {
	r := subpolicy.result with input as testlib.requester_input([agreement("did:example:terms-1")], data_, {})
	r.decision
	r.verification_tasks == [{"index": 0}]
}

test_denies_other_terms if {
	not subpolicy.result.decision with input as testlib.requester_input([agreement("did:example:terms-2")], data_, {})
}

test_denies_terms_accepted_by_someone_else if {
	c := testlib.about_someone_else(agreement("did:example:terms-1"))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, {})
}

test_ignores_an_untrusted_agreement if {
	c := testlib.untrusted(agreement("did:example:terms-1"))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, {})
}
