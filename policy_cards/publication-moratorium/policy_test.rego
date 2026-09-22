# Unit tests for DUO_0000024 (MOR).  Run with:  opa test mor/ -v
package subpolicy_test

import data.subpolicy

base_input := {
	"policy_data": {"requiredDocumentID": "did:example:terms-1"},
	"presentations": {"User": [
		{
			"type": "AgreementCredential",
			"issuer": "did:example:platform",
			"subject": "did:example:user-1",
			"claims": {"agreementInfo": {"documentID": "did:example:terms-1", "documentVersion": "1.0"}},
			"index": 0,
		},
		{
			"type": "ComputeEnvironmentCredential",
			"issuer": "did:example:compute-provider",
			"subject": "did:example:node-1",
			"claims": {"hasComputeProfile": {"profile": {"SecureHandlingOfResults": true, "shutsDownAt": "2027-06-01T00:00:00Z"}}},
			"index": 1,
		},
		{
			"type": "publicKeyCredential",
			"issuer": "did:example:platform",
			"subject": "did:example:user-1",
			"claims": {"key": "PUBKEY"},
			"index": 2,
		},
	]},
}

test_requirements_are_user_role_with_credential_types if {
	subpolicy.requirements == {"User": ["AgreementCredential", "ComputeEnvironmentCredential", "publicKeyCredential"]}
}

test_allow_when_terms_accepted_and_results_handled_securely if {
	subpolicy.result.decision == true with input as base_input
}

test_operation_carries_name_and_channel_key if {
	subpolicy.result.operation == {"name": "do_download", "parameters": {"channel_key": "PUBKEY"}} with input as base_input
}

test_tasks_flag_agreement_compute_and_public_key if {
	tasks := subpolicy.result.verification_tasks with input as base_input
	count(tasks) == 3
}

test_deny_when_results_not_handled_securely if {
	insecure := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/1/claims/hasComputeProfile/profile/SecureHandlingOfResults",
		"value": false,
	}])
	subpolicy.result.decision == false with input as insecure
}

test_deny_when_no_compute_credential if {
	nocompute := json.patch(base_input, [{"op": "remove", "path": "/presentations/User/1"}])
	subpolicy.result.decision == false with input as nocompute
}

test_deny_when_required_terms_not_accepted if {
	other := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/0/claims/agreementInfo/documentID",
		"value": "did:example:terms-other",
	}])
	subpolicy.result.decision == false with input as other
}

test_deny_when_no_public_key_credential if {
	nokey := json.patch(base_input, [{"op": "remove", "path": "/presentations/User/2"}])
	subpolicy.result.decision == false with input as nokey
}
