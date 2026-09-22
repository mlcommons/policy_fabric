# Unit tests for DUO_0000026 (US).  Run with:  opa test us/ -v
package subpolicy_test

import data.subpolicy

base_input := {
	"policy_data": {
		"approvedUsers": ["did:example:user-1"],
		"allowedAccountTypes": ["institutional"],
		"requiredProfileStatuses": ["verified"],
	},
	"presentations": {"User": [
		{
			"type": "UserPlatformCredential",
			"issuer": "did:example:platform",
			"subject": "did:example:user-1",
			"claims": {"userId": "did:example:user-1", "accountType": "individual", "profileStatus": "pending", "isUser": true},
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
	subpolicy.requirements == {"User": ["UserPlatformCredential", "publicKeyCredential"]}
}

test_allow_when_user_is_approved if {
	subpolicy.result.decision == true with input as base_input
}

test_allow_via_required_profile_status if {
	# not an approved user and not an allowed account type, but a required profile status
	other := json.patch(base_input, [
		{"op": "replace", "path": "/presentations/User/0/claims/userId", "value": "did:example:user-unknown"},
		{"op": "replace", "path": "/presentations/User/0/claims/profileStatus", "value": "verified"},
	])
	subpolicy.result.decision == true with input as other
}

test_operation_carries_name_and_channel_key if {
	subpolicy.result.operation == {"name": "do_download", "parameters": {"channel_key": "PUBKEY"}} with input as base_input
}

test_tasks_flag_platform_account_and_public_key if {
	tasks := subpolicy.result.verification_tasks with input as base_input
	count(tasks) == 2
}

test_deny_when_no_access_route_matches if {
	none := json.patch(base_input, [
		{"op": "replace", "path": "/presentations/User/0/claims/userId", "value": "did:example:user-unknown"},
		{"op": "replace", "path": "/presentations/User/0/claims/accountType", "value": "individual"},
		{"op": "replace", "path": "/presentations/User/0/claims/profileStatus", "value": "pending"},
	])
	subpolicy.result.decision == false with input as none
}

test_deny_when_no_public_key_credential if {
	nokey := json.patch(base_input, [{"op": "remove", "path": "/presentations/User/1"}])
	subpolicy.result.decision == false with input as nokey
}

test_deny_when_subjects_differ if {
	# the public key credential is for a different subject than the platform account
	mismatched := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/1/subject",
		"value": "did:example:someone-else",
	}])
	subpolicy.result.decision == false with input as mismatched
}
