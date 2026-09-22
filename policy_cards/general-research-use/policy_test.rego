# Unit tests for DUO_0000042 (GRU).  Run with:  opa test gru/ -v
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
			"type": "publicKeyCredential",
			"issuer": "did:example:platform",
			"subject": "did:example:user-1",
			"claims": {"key": "PUBKEY"},
			"index": 1,
		},
	]},
}

test_requirements_are_user_role_with_credential_types if {
	subpolicy.requirements == {"User": ["AgreementCredential", "publicKeyCredential"]}
}

test_allow_when_required_terms_accepted if {
	subpolicy.result.decision == true with input as base_input
}

test_operation_carries_name_and_channel_key if {
	subpolicy.result.operation == {"name": "do_download", "parameters": {"channel_key": "PUBKEY"}} with input as base_input
}

test_tasks_flag_agreement_and_public_key if {
	tasks := subpolicy.result.verification_tasks with input as base_input
	count(tasks) == 2
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
	nokey := json.patch(base_input, [{"op": "remove", "path": "/presentations/User/1"}])
	subpolicy.result.decision == false with input as nokey
}

test_deny_when_subjects_differ if {
	# the public key credential is for a different subject than the agreement
	mismatched := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/1/subject",
		"value": "did:example:someone-else",
	}])
	subpolicy.result.decision == false with input as mismatched
}
