package pf.components.institution_specific_restriction_test

import rego.v1

import data.pf.components.institution_specific_restriction

affiliation := {"type": "AffiliationCredential", "issuer": "did:example:university", "subject": "did:example:user",
	"claims": {"isMemberOf": "did:example:university", "typeOfMembership": "student"}, "evidence": [0]}

condition(affiliations) := out if {
	out := institution_specific_restriction.output with input as {
		"inputs": {"affiliation": affiliations},
		"policy_data": {"allowedInstitutions": ["did:example:university", "did:example:hospital"]}, "request": {},
	}
}

test_an_institution_the_owner_allows if {
	condition([affiliation]) == [{"type": "DataUseConditionCredential", "subject": "did:example:user", "claims": {}, "evidence": [0]}]
}

test_an_institution_the_owner_does_not_allow if {
	condition([object.union(affiliation, {"claims": {"isMemberOf": "did:example:unknown"}})]) == []
}
