package pf.components.return_to_database_or_resource_test

import rego.v1

import data.pf.components.return_to_database_or_resource

agreement := {"type": "AgreementCredential", "issuer": "did:example:platform", "subject": "did:example:user",
	"claims": {"agreementInfo": {"documentID": "did:example:terms", "documentVersion": "1.0"}}, "evidence": [0]}

compute := {"type": "ComputeEnvironmentCredential", "issuer": "did:example:compute-provider", "subject": "did:example:node",
	"claims": {"hasComputeProfile": {"profile": {"SecureHandlingOfResults": true, "shutsDownAt": "2027-06-01T00:00:00Z"}}}, "evidence": [1]}

condition(agreements, computes) := out if {
	out := return_to_database_or_resource.output with input as {
		"inputs": {"agreement": agreements, "computeEnvironment": computes},
		"policy_data": {"requiredDocumentID": "did:example:terms"}, "request": {},
	}
}

test_the_terms_accepted_and_results_handled_securely if {
	condition([agreement], [compute]) == [{"type": "DataUseConditionCredential", "subject": "did:example:user", "claims": {}, "evidence": [0, 1]}]
}

test_an_agreement_to_another_document if {
	condition([object.union(agreement, {"claims": {"agreementInfo": {"documentID": "did:example:other-terms"}}})], [compute]) == []
}

test_a_compute_environment_that_does_not_handle_results_securely if {
	insecure := object.union(compute, {"claims": {"hasComputeProfile": {"profile": {"SecureHandlingOfResults": false}}}})
	condition([agreement], [insecure]) == []
}
