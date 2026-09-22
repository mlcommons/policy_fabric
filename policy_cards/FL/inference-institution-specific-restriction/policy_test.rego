# Unit tests for FL-IS.  Run with:  opa test FL/inference-institution-specific-restriction/ -v
package subpolicy_test

import data.subpolicy

base_input := {
	"policy_data": {"allowedInstitutions": ["did:example:university", "did:example:hospital"]},
	"presentations": {
		"User": [
			{
				"type": "AffiliationCredential",
				"issuer": "did:example:university",
				"subject": "did:pdo:user-wallet",
				"claims": {"isMemberOf": "did:example:university", "typeOfMembership": "student"},
				"index": 0,
			},
			{
				"type": "publicKeyCredential",
				"issuer": "did:example:key-authority",
				"subject": "did:pdo:user-wallet",
				"claims": {"key": "CHANNELKEY"},
				"index": 1,
			},
			{
				"type": "WalletVerifyingKeyCredential",
				"issuer": "did:example:wallet-key-authority",
				"subject": "did:pdo:user-wallet",
				"claims": {"verifying_key": "WALLETPEM"},
				"index": 2,
			},
		],
		"Script": [
			{
				"type": "ScriptOwnershipCredential",
				"issuer": "did:pdo:user-wallet",
				"subject": "did:pdo:script-asset",
				"claims": {"ownedBy": "did:pdo:user-wallet"},
				"index": 3,
			},
			{
				"type": "ScriptHashCredential",
				"issuer": "did:example:script-authority",
				"subject": "did:pdo:script-asset",
				"claims": {"scriptHash": "sha256:abc"},
				"index": 4,
			},
		],
	},
}

test_requirements_split_user_and_script_roles if {
	subpolicy.requirements == {
		"User": ["AffiliationCredential", "publicKeyCredential", "WalletVerifyingKeyCredential"],
		"Script": ["ScriptOwnershipCredential", "ScriptHashCredential"],
	}
}

test_allow_when_affiliated_and_script_owned if {
	subpolicy.result.decision == true with input as base_input
}

test_operation_carries_channel_key_and_script_digest if {
	subpolicy.result.operation == {"name": "do_inference", "parameters": {
		"channel_key": "CHANNELKEY",
		"script_digest": "sha256:abc",
	}} with input as base_input
}

test_issuer_tasks_flag_the_four_issued_credentials if {
	tasks := subpolicy.result.verification_tasks with input as base_input
	count(tasks) == 4
}

test_ownership_is_verified_against_the_wallet_key if {
	tasks := subpolicy.result.vc_supplied_verification_tasks with input as base_input
	tasks == [{"index": 3, "key": "WALLETPEM", "key_type": "ec"}]
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

test_deny_when_wallet_key_credential_is_for_another_wallet if {
	# the wallet key credential does not describe the wallet the affiliation is about
	mismatched := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/2/subject",
		"value": "did:pdo:someone-else",
	}])
	subpolicy.result.decision == false with input as mismatched
}

test_deny_when_script_is_owned_by_another_wallet if {
	# the requester is affiliated, but the script belongs to someone else
	other_owner := json.patch(base_input, [
		{"op": "replace", "path": "/presentations/Script/0/issuer", "value": "did:pdo:someone-else"},
		{"op": "replace", "path": "/presentations/Script/0/claims/ownedBy", "value": "did:pdo:someone-else"},
	])
	subpolicy.result.decision == false with input as other_owner
}

test_deny_when_ownership_is_issued_by_someone_other_than_the_named_owner if {
	# a wallet cannot vouch for a claim that names a different wallet as owner
	forged := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/Script/0/issuer",
		"value": "did:pdo:attacker",
	}])
	subpolicy.result.decision == false with input as forged
}

test_deny_when_hash_is_about_a_different_script if {
	other_script := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/Script/1/subject",
		"value": "did:pdo:other-script",
	}])
	subpolicy.result.decision == false with input as other_script
}

test_deny_when_no_script_evidence_at_all if {
	noscript := json.patch(base_input, [{"op": "replace", "path": "/presentations/Script", "value": []}])
	subpolicy.result.decision == false with input as noscript
}

test_result_is_well_formed_on_deny if {
	noscript := json.patch(base_input, [{"op": "replace", "path": "/presentations/Script", "value": []}])
	result := subpolicy.result with input as noscript
	result.operation == {"name": "do_inference", "parameters": {"channel_key": "", "script_digest": ""}}
	result.verification_tasks == []
	result.vc_supplied_verification_tasks == []
}
