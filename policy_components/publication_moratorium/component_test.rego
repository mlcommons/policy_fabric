package pf.components.publication_moratorium_test

import rego.v1

import data.pf.components.publication_moratorium

agreement := {"type": "AgreementCredential", "issuer": "did:example:platform", "subject": "did:example:user",
	"claims": {"agreementInfo": {"documentID": "did:example:terms", "documentVersion": "1.0"}}, "evidence": [0]}

compute := {"type": "ComputeEnvironmentCredential", "issuer": "did:example:compute-provider", "subject": "did:example:node",
	"claims": {"hasComputeProfile": {"profile": {"SecureHandlingOfResults": true, "shutsDownAt": "2027-06-01T00:00:00Z"}}}, "evidence": [1]}

grant(agreements, computes) := out if {
	out := publication_moratorium.output with input as {
		"inputs": {"agreement": agreements, "computeEnvironment": computes},
		"policy_data": {"requiredDocumentID": "did:example:terms"}, "request": {},
	}
}

test_the_required_terms_on_a_compute_environment_that_handles_results_securely if {
	grant([agreement], [compute]) == [{"type": "DownloadGrantCredential", "subject": "did:example:user", "claims": {}, "evidence": [0, 1]}]
}

test_an_agreement_to_other_terms if {
	grant([object.union(agreement, {"claims": {"agreementInfo": {"documentID": "did:example:other-terms"}}})], [compute]) == []
}

test_a_compute_environment_that_does_not_handle_results_securely if {
	insecure := object.union(compute, {"claims": {"hasComputeProfile": {"profile": {"SecureHandlingOfResults": false}}}})
	grant([agreement], [insecure]) == []
}
