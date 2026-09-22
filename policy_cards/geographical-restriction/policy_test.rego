# Unit tests for DUO_0000022 (GS).  Run with:  opa test gs/ -v
package subpolicy_test

import data.subpolicy

base_input := {
	"policy_data": {"allowedCountries": ["US", "CA"]},
	"presentations": {"User": [
		{
			"type": "LocationCredential",
			"issuer": "did:example:loc-authority",
			"subject": "did:example:user-1",
			"claims": {"locatedAt": {"street": "1 Main", "zipCode": "00000", "state": "MA", "country": "US"}},
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
	subpolicy.requirements == {"User": ["LocationCredential", "publicKeyCredential"]}
}

test_allow_when_in_allowed_country if {
	subpolicy.result.decision == true with input as base_input
}

test_operation_carries_name_and_channel_key if {
	subpolicy.result.operation == {"name": "do_download", "parameters": {"channel_key": "PUBKEY"}} with input as base_input
}

test_tasks_flag_location_and_public_key if {
	tasks := subpolicy.result.verification_tasks with input as base_input
	count(tasks) == 2
}

test_deny_when_country_not_allowed if {
	moved := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/0/claims/locatedAt/country",
		"value": "FR",
	}])
	subpolicy.result.decision == false with input as moved
}

test_deny_when_no_public_key_credential if {
	nokey := json.patch(base_input, [{"op": "remove", "path": "/presentations/User/1"}])
	subpolicy.result.decision == false with input as nokey
}

test_deny_when_subjects_differ if {
	# the public key credential is for a different subject than the location credential
	mismatched := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/1/subject",
		"value": "did:example:someone-else",
	}])
	subpolicy.result.decision == false with input as mismatched
}
