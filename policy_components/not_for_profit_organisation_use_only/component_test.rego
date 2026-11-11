package pf.components.not_for_profit_organisation_use_only_test

import rego.v1

import data.pf.components.not_for_profit_organisation_use_only

designation := {"type": "LegalDesignationCredential", "issuer": "did:example:registry", "subject": "did:example:org",
	"claims": {"hasLegalForm": "V2VJ"}, "evidence": [0]}

grant(designations) := out if {
	out := not_for_profit_organisation_use_only.output with input as {
		"inputs": {"legalDesignation": designations}, "policy_data": {"nonprofitLegalForms": ["V2VJ", "8ES1"]}, "request": {},
	}
}

test_a_not_for_profit_legal_form if {
	grant([designation]) == [{"type": "DownloadGrantCredential", "subject": "did:example:org", "claims": {}, "evidence": [0]}]
}

test_a_legal_form_the_owner_does_not_accept if {
	grant([object.union(designation, {"claims": {"hasLegalForm": "XTIQ"}})]) == []
}
