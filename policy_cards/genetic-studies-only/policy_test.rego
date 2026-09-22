# Unit tests for DUO_0000016 (GSO).  Run with:  opa test gso/ -v
package subpolicy_test

import data.subpolicy

base_input := {
	"policy_data": {"allowedPurposes": ["GSO"]},
	"presentations": {"User": [
		{
			"type": "IntendedDataUseCredential",
			"issuer": "did:example:dac",
			"subject": "did:example:project-1",
			"claims": {"useOnlyFor": {"purposes": ["GSO"]}},
			"index": 0,
		},
		{
			"type": "ProjectOwnershipCredential",
			"issuer": "did:example:registry",
			"subject": "did:example:pi-1",
			"claims": {"Owns": "did:example:project-1"},
			"index": 1,
		},
		{
			"type": "TeamCredential",
			"issuer": "did:example:registry",
			"subject": "did:example:user-1",
			"claims": {"MemberOfTeamOf": "did:example:pi-1"},
			"index": 2,
		},
		{
			"type": "AgreementCredential",
			"issuer": "did:example:platform",
			"subject": "did:example:user-1",
			"claims": {"agreementInfo": {"documentID": "did:example:terms", "documentVersion": "1.0"}},
			"index": 3,
		},
		{
			"type": "publicKeyCredential",
			"issuer": "did:example:platform",
			"subject": "did:example:user-1",
			"claims": {"key": "PUBKEY"},
			"index": 4,
		},
	]},
}

test_requirements_list_the_chain_credentials if {
	subpolicy.requirements == {"User": [
		"IntendedDataUseCredential",
		"ProjectOwnershipCredential",
		"TeamCredential",
		"AgreementCredential",
		"publicKeyCredential",
	]}
}

test_allow_when_purpose_in_scope if {
	subpolicy.result.decision == true with input as base_input
}

test_operation_carries_name_and_channel_key if {
	subpolicy.result.operation == {"name": "do_download", "parameters": {"channel_key": "PUBKEY"}} with input as base_input
}

test_tasks_flag_the_whole_chain if {
	tasks := subpolicy.result.verification_tasks with input as base_input
	count(tasks) == 5
}

test_deny_when_purpose_not_in_scope if {
	other := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/0/claims/useOnlyFor/purposes",
		"value": ["SomethingElse"],
	}])
	subpolicy.result.decision == false with input as other
}

test_deny_when_no_public_key_credential if {
	nokey := json.patch(base_input, [{"op": "remove", "path": "/presentations/User/4"}])
	subpolicy.result.decision == false with input as nokey
}

test_deny_when_requester_not_on_owning_pis_team if {
	# the team credential names a PI who does not own the project
	mismatched := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/2/claims/MemberOfTeamOf",
		"value": "did:example:pi-other",
	}])
	subpolicy.result.decision == false with input as mismatched
}

test_deny_when_owned_project_is_not_the_idu_project if {
	# the PI owns a different project than the one the IDU is about
	mismatched := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/1/claims/Owns",
		"value": "did:example:project-other",
	}])
	subpolicy.result.decision == false with input as mismatched
}
