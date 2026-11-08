package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

affiliation(institution) := testlib.credential(
	"AffiliationCredential",
	testlib.requester,
	{"isMemberOf": institution, "typeOfMembership": "faculty"},
)

data_ := {"allowedInstitutions": ["did:example:university"]}

test_requirements if {
	subpolicy.requirements == {"User": ["AffiliationCredential"]}
}

test_allows_an_allowed_institution if {
	r := subpolicy.result with input as testlib.requester_input([affiliation("did:example:university")], data_, {})
	r.decision
	r.verification_tasks == [{"index": 0}]
	not "credential" in object.keys(r)
}

test_denies_another_institution if {
	held := [affiliation("did:example:elsewhere")]
	not subpolicy.result.decision with input as testlib.requester_input(held, data_, {})
}

test_allows_when_one_of_several_affiliations_qualifies if {
	held := [affiliation("did:example:elsewhere"), affiliation("did:example:university")]
	r := subpolicy.result with input as testlib.requester_input(held, data_, {})
	r.decision
	r.verification_tasks == [{"index": 1}]
}

test_denies_an_affiliation_of_someone_else if {
	c := testlib.about_someone_else(affiliation("did:example:university"))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, {})
}

test_ignores_an_untrusted_affiliation if {
	c := testlib.untrusted(affiliation("did:example:university"))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, {})
}
