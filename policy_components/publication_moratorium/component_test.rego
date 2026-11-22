package pf.components.publication_moratorium_test

import rego.v1

import data.pf.components.publication_moratorium

agreement := {"type": "AgreementCredential", "issuer": "did:example:platform", "subject": "did:example:user",
	"claims": {"agreementInfo": {"documentID": "did:example:terms", "documentVersion": "1.0"}}, "evidence": [0]}

compute := {"type": "ComputeEnvironmentCredential", "issuer": "did:example:compute-provider", "subject": "did:example:node",
	"claims": {"hasComputeProfile": {"profile": {"SecureHandlingOfResults": true, "shutsDownAt": "2027-06-01T00:00:00Z"}}}, "evidence": [1]}

condition(agreements, computes) := out if {
	out := publication_moratorium.output with input as {
		"inputs": {"agreement": agreements, "computeEnvironment": computes},
		"policy_data": {"requiredDocumentID": "did:example:terms"}, "request": {},
	}
}

# the component's decision when its condition holds for one subject, and when it holds for none
allowed(subject) := {"allow": true, "parameters": {"subject": [subject]}}

denied := {"allow": false, "parameters": {"subject": []}}

test_the_required_terms_on_a_compute_environment_that_handles_results_securely if {
	condition([agreement], [compute]) == allowed("did:example:user")
}

test_an_agreement_to_other_terms if {
	condition([object.union(agreement, {"claims": {"agreementInfo": {"documentID": "did:example:other-terms"}}})], [compute]) == denied
}

test_a_compute_environment_that_does_not_handle_results_securely if {
	insecure := object.union(compute, {"claims": {"hasComputeProfile": {"profile": {"SecureHandlingOfResults": false}}}})
	condition([agreement], [insecure]) == denied
}
