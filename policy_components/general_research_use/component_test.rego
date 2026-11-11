package pf.components.general_research_use_test

import rego.v1

import data.pf.components.general_research_use

agreement := {"type": "AgreementCredential", "issuer": "did:example:platform", "subject": "did:example:user",
	"claims": {"agreementInfo": {"documentID": "did:example:terms", "documentVersion": "1.0"}}, "evidence": [0]}

grant(agreements) := out if {
	out := general_research_use.output with input as {
		"inputs": {"agreement": agreements}, "policy_data": {"requiredDocumentID": "did:example:terms"}, "request": {},
	}
}

test_the_requester_accepted_the_required_terms if {
	grant([agreement]) == [{"type": "DownloadGrantCredential", "subject": "did:example:user", "claims": {}, "evidence": [0]}]
}

test_an_agreement_to_other_terms if {
	grant([object.union(agreement, {"claims": {"agreementInfo": {"documentID": "did:example:other-terms"}}})]) == []
}
