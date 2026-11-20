package pf.components.time_limit_on_use_test

import rego.v1

import data.pf.components.time_limit_on_use

agreement := {"type": "AgreementCredential", "issuer": "did:example:platform", "subject": "did:example:user",
	"claims": {"agreementInfo": {"documentID": "did:example:terms", "documentVersion": "1.0"}}, "evidence": [0]}

compute := {"type": "ComputeEnvironmentCredential", "issuer": "did:example:compute-provider", "subject": "did:example:node",
	"claims": {"hasComputeProfile": {"profile": {"SecureHandlingOfResults": true, "shutsDownAt": "2027-06-01T00:00:00Z"}}}, "evidence": [1]}

condition(agreements, computes) := out if {
	out := time_limit_on_use.output with input as {
		"inputs": {"agreement": agreements, "computeEnvironment": computes},
		"policy_data": {"requiredDocumentID": "did:example:terms", "notAfter": "2027-12-31T23:59:59Z"}, "request": {},
	}
}

test_the_terms_accepted_and_shut_down_before_the_deadline if {
	condition([agreement], [compute]) == [{"type": "DataUseConditionCredential", "subject": "did:example:user", "claims": {}, "evidence": [0, 1]}]
}

test_a_shutdown_at_the_deadline if {
	on_time := object.union(compute, {"claims": {"hasComputeProfile": {"profile": {"shutsDownAt": "2027-12-31T23:59:59Z"}}}})
	count(condition([agreement], [on_time])) == 1
}

test_a_shutdown_after_the_deadline if {
	late := object.union(compute, {"claims": {"hasComputeProfile": {"profile": {"shutsDownAt": "2028-06-01T00:00:00Z"}}}})
	condition([agreement], [late]) == []
}

test_an_agreement_to_another_document if {
	condition([object.union(agreement, {"claims": {"agreementInfo": {"documentID": "did:example:other-terms"}}})], [compute]) == []
}
