package pf.components.not_for_profit_non_commercial_use_only_test

import rego.v1

import data.pf.components.not_for_profit_non_commercial_use_only

designation := {"type": "LegalDesignationCredential", "issuer": "did:example:registry", "subject": "did:example:org",
	"claims": {"hasLegalForm": "V2VJ"}, "evidence": [0]}

use := {"type": "IntendedDataUseCredential", "issuer": "did:example:dac", "subject": "did:example:project",
	"claims": {"useOnlyFor": {"purposes": ["HMB"], "diseases": []}}, "evidence": [1]}

grant(designations, uses) := out if {
	out := not_for_profit_non_commercial_use_only.output with input as {
		"inputs": {"legalDesignation": designations, "intendedDataUse": uses},
		"policy_data": {"nonprofitLegalForms": ["V2VJ", "8ES1"], "prohibitedPurposes": ["commercial"]}, "request": {},
	}
}

test_a_not_for_profit_requester_and_a_non_commercial_use if {
	grant([designation], [use]) == [{"type": "DownloadGrantCredential", "subject": "did:example:org", "claims": {}, "evidence": [0, 1]}]
}

test_a_legal_form_the_owner_does_not_treat_as_not_for_profit if {
	grant([object.union(designation, {"claims": {"hasLegalForm": "XTIQ"}})], [use]) == []
}

test_a_commercial_purpose_among_others if {
	grant([designation], [object.union(use, {"claims": {"useOnlyFor": {"purposes": ["HMB", "commercial"]}}})]) == []
}

test_a_use_that_declares_no_purposes if {
	grant([designation], [json.remove(use, ["claims/useOnlyFor/purposes"])]) == []
}
