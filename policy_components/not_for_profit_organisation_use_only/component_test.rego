package pf.components.not_for_profit_organisation_use_only_test

import rego.v1

import data.pf.components.not_for_profit_organisation_use_only

designation := {"type": "LegalDesignationCredential", "issuer": "did:example:registry", "subject": "did:example:org",
	"claims": {"hasLegalForm": "V2VJ"}, "evidence": [0]}

condition(designations) := out if {
	out := not_for_profit_organisation_use_only.output with input as {
		"inputs": {"legalDesignation": designations}, "policy_data": {"nonprofitLegalForms": ["V2VJ", "8ES1"]}, "request": {},
	}
}

# the component's decision when its condition holds for one subject, and when it holds for none
allowed(subject) := {"allow": true, "parameters": {"subject": [subject]}}

denied := {"allow": false, "parameters": {"subject": []}}

test_a_not_for_profit_legal_form if {
	condition([designation]) == allowed("did:example:org")
}

test_a_legal_form_the_owner_does_not_accept if {
	condition([object.union(designation, {"claims": {"hasLegalForm": "XTIQ"}})]) == denied
}
