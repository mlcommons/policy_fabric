package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

designation(form) := testlib.credential("LegalDesignationCredential", testlib.requester, {"hasLegalForm": form})

data_ := {"nonprofitLegalForms": ["V2VJ", "8ES1"]}

test_requirements if {
	subpolicy.requirements == {"User": ["LegalDesignationCredential"]}
}

test_allows_a_nonprofit_form if {
	r := subpolicy.result with input as testlib.requester_input([designation("V2VJ")], data_, {})
	r.decision
	r.verification_tasks == [{"index": 0}]
}

test_denies_another_form if {
	not subpolicy.result.decision with input as testlib.requester_input([designation("XTIQ")], data_, {})
}

test_denies_a_designation_of_someone_else if {
	c := testlib.about_someone_else(designation("V2VJ"))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, {})
}

test_ignores_an_untrusted_designation if {
	c := testlib.untrusted(designation("V2VJ"))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, {})
}
