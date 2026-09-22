# Unit tests for FL-DS.  Run with:  opa test FL/inference-disease-specific-research/ -v
package subpolicy_test

import data.subpolicy

base_input := {
	"policy_data": {"allowedDiseases": ["MONDO:0005148", "MONDO:0007254"]},
	"presentations": {"Script": [
		{
			"type": "IntendedDataUseCredential",
			"issuer": "did:example:dac",
			"subject": "did:pdo:script-asset",
			"claims": {"useOnlyFor": {
				"purposes": ["research"],
				"diseases": ["MONDO:0005148"],
			}},
			"index": 0,
		},
		{
			"type": "ScriptHashCredential",
			"issuer": "did:example:script-authority",
			"subject": "did:pdo:script-asset",
			"claims": {"scriptHash": "sha256:abc"},
			"index": 1,
		},
	]},
}

test_requirements_are_script_role_with_credential_types if {
	subpolicy.requirements == {"Script": ["IntendedDataUseCredential", "ScriptHashCredential"]}
}

test_allow_when_disease_is_in_scope if {
	subpolicy.result.decision == true with input as base_input
}

test_operation_carries_the_script_digest if {
	subpolicy.result.operation == {
		"name": "do_inference",
		"parameters": {"script_digest": "sha256:abc"},
	} with input as base_input
}

test_tasks_flag_the_intended_use_and_the_script_hash if {
	tasks := subpolicy.result.verification_tasks with input as base_input
	count(tasks) == 2
}

test_no_supplied_key_tasks if {
	subpolicy.result.vc_supplied_verification_tasks == [] with input as base_input
}

test_deny_when_disease_out_of_scope if {
	other := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/Script/0/claims/useOnlyFor/diseases",
		"value": ["MONDO:9999999"],
	}])
	subpolicy.result.decision == false with input as other
}

test_allow_when_any_declared_disease_is_in_scope if {
	several := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/Script/0/claims/useOnlyFor/diseases",
		"value": ["MONDO:9999999", "MONDO:0007254"],
	}])
	subpolicy.result.decision == true with input as several
}

test_deny_when_the_declared_use_is_about_a_different_script if {
	# an in-scope declaration attached to some other script must not license this one
	other_subject := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/Script/0/subject",
		"value": "did:pdo:other-script",
	}])
	subpolicy.result.decision == false with input as other_subject
}

test_deny_when_the_hash_is_about_a_different_script if {
	other_subject := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/Script/1/subject",
		"value": "did:pdo:other-script",
	}])
	subpolicy.result.decision == false with input as other_subject
}

test_only_the_matching_pair_qualifies_when_two_scripts_are_presented if {
	# a second script declares an out-of-scope use; only the in-scope pair counts
	two_scripts := json.patch(base_input, [
		{"op": "add", "path": "/presentations/Script/-", "value": {
			"type": "IntendedDataUseCredential",
			"issuer": "did:example:dac",
			"subject": "did:pdo:other-script",
			"claims": {"useOnlyFor": {"purposes": ["research"], "diseases": ["MONDO:9999999"]}},
			"index": 2,
		}},
		{"op": "add", "path": "/presentations/Script/-", "value": {
			"type": "ScriptHashCredential",
			"issuer": "did:example:script-authority",
			"subject": "did:pdo:other-script",
			"claims": {"scriptHash": "sha256:def"},
			"index": 3,
		}},
	])
	result := subpolicy.result with input as two_scripts
	result.decision == true
	result.operation.parameters.script_digest == "sha256:abc"
	count(result.verification_tasks) == 2
}

test_deny_when_no_script_hash if {
	nohash := json.patch(base_input, [{"op": "remove", "path": "/presentations/Script/1"}])
	subpolicy.result.decision == false with input as nohash
}

test_deny_when_no_intended_use if {
	nouse := json.patch(base_input, [{"op": "remove", "path": "/presentations/Script/0"}])
	subpolicy.result.decision == false with input as nouse
}

test_result_is_well_formed_on_deny if {
	empty := json.patch(base_input, [{"op": "replace", "path": "/presentations/Script", "value": []}])
	result := subpolicy.result with input as empty
	result.operation == {"name": "do_inference", "parameters": {"script_digest": ""}}
	result.verification_tasks == []
}
