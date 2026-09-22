# Unit tests for DUO_0000045 (NPU).  Run with:  opa test npu/ -v
package subpolicy_test

import data.subpolicy

base_input := {
	"policy_data": {"nonprofitLegalForms": ["V2VJ", "8ES1"]},
	"presentations": {"User": [
		{
			"type": "LegalDesignationCredential",
			"issuer": "did:example:registry",
			"subject": "did:example:org-1",
			"claims": {"hasLegalForm": "V2VJ"},
			"index": 0,
		},
		{
			"type": "publicKeyCredential",
			"issuer": "did:example:platform",
			"subject": "did:example:org-1",
			"claims": {"key": "PUBKEY"},
			"index": 1,
		},
	]},
}

test_requirements_are_user_role_with_credential_types if {
	subpolicy.requirements == {"User": ["LegalDesignationCredential", "publicKeyCredential"]}
}

test_allow_when_legal_form_is_nonprofit if {
	subpolicy.result.decision == true with input as base_input
}

test_operation_carries_name_and_channel_key if {
	subpolicy.result.operation == {"name": "do_download", "parameters": {"channel_key": "PUBKEY"}} with input as base_input
}

test_tasks_flag_legal_designation_and_public_key if {
	tasks := subpolicy.result.verification_tasks with input as base_input
	count(tasks) == 2
}

test_deny_when_legal_form_not_nonprofit if {
	forprofit := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/0/claims/hasLegalForm",
		"value": "XTIQ",
	}])
	subpolicy.result.decision == false with input as forprofit
}

test_deny_when_no_public_key_credential if {
	nokey := json.patch(base_input, [{"op": "remove", "path": "/presentations/User/1"}])
	subpolicy.result.decision == false with input as nokey
}

test_deny_when_subjects_differ if {
	# the public key credential is for a different subject than the legal designation
	mismatched := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/1/subject",
		"value": "did:example:someone-else",
	}])
	subpolicy.result.decision == false with input as mismatched
}
