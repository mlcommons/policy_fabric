# Unit tests for DUO_0000028 (IS).  Run with:  opa test is/ -v
package subpolicy_test

import data.subpolicy

base_input := {
	"policy_data": {"allowedInstitutions": ["did:example:university", "did:example:hospital"]},
	"presentations": {"User": [
		{
			"type": "AffiliationCredential",
			"issuer": "did:example:university",
			"subject": "did:example:user-1",
			"claims": {"isMemberOf": "did:example:university", "typeOfMembership": "student"},
			"index": 0,
		},
		{
			"type": "publicKeyCredential",
			"issuer": "did:example:key-authority",
			"subject": "did:example:user-1",
			"claims": {"key": "PUBKEY"},
			"index": 1,
		},
	]},
}

test_requirements_are_user_role_with_credential_types if {
	subpolicy.requirements == {"User": ["AffiliationCredential", "publicKeyCredential"]}
}

test_allow_when_member_of_approved_institution if {
	subpolicy.result.decision == true with input as base_input
}

test_operation_carries_name_and_channel_key if {
	subpolicy.result.operation == {"name": "do_download", "parameters": {"channel_key": "PUBKEY"}} with input as base_input
}

test_tasks_flag_affiliation_and_public_key if {
	tasks := subpolicy.result.verification_tasks with input as base_input
	count(tasks) == 2
}

test_deny_when_institution_not_approved if {
	other := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/0/claims/isMemberOf",
		"value": "did:example:unknown",
	}])
	subpolicy.result.decision == false with input as other
}

test_deny_when_no_public_key_credential if {
	nokey := json.patch(base_input, [{"op": "remove", "path": "/presentations/User/1"}])
	subpolicy.result.decision == false with input as nokey
}

test_deny_when_subjects_differ if {
	# the public key credential is for a different subject than the affiliation credential
	mismatched := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/1/subject",
		"value": "did:example:someone-else",
	}])
	subpolicy.result.decision == false with input as mismatched
}
