# Unit tests for DUO_0000021 (IRB).  Run with:  opa test irb/ -v
package subpolicy_test

import data.subpolicy

base_input := {
	"policy_data": {},
	"presentations": {"User": [
		{
			"type": "IntendedDataUseCredential",
			"issuer": "did:example:dac",
			"subject": "did:example:project-1",
			"claims": {"useOnlyFor": {"purposes": ["HMB"], "diseases": []}},
			"index": 0,
		},
		{
			"type": "IRBApprovalCredential",
			"issuer": "did:example:dac",
			"subject": "did:example:project-1",
			"claims": {"isApprovedByEthicsCommittee": "did:example:committee-1"},
			"index": 1,
		},
		{
			"type": "ProjectOwnershipCredential",
			"issuer": "did:example:registry",
			"subject": "did:example:pi-1",
			"claims": {"Owns": "did:example:project-1"},
			"index": 2,
		},
		{
			"type": "EthicsCommitteeAccreditationCredential",
			"issuer": "did:example:registry",
			"subject": "did:example:committee-1",
			"claims": {"ResponsibleFor": "did:example:institution-1"},
			"index": 3,
		},
		{
			"type": "AffiliationCredential",
			"issuer": "did:example:registry",
			"subject": "did:example:pi-1",
			"claims": {"isMemberOf": "did:example:institution-1", "typeOfMembership": "faculty"},
			"index": 4,
		},
		{
			"type": "TeamCredential",
			"issuer": "did:example:registry",
			"subject": "did:example:user-1",
			"claims": {"MemberOfTeamOf": "did:example:pi-1"},
			"index": 5,
		},
		{
			"type": "publicKeyCredential",
			"issuer": "did:example:platform",
			"subject": "did:example:user-1",
			"claims": {"key": "PUBKEY"},
			"index": 6,
		},
	]},
}

test_requirements_list_the_chain_credentials if {
	subpolicy.requirements == {"User": [
		"IntendedDataUseCredential",
		"IRBApprovalCredential",
		"ProjectOwnershipCredential",
		"EthicsCommitteeAccreditationCredential",
		"AffiliationCredential",
		"TeamCredential",
		"publicKeyCredential",
	]}
}

test_allow_when_ethics_approval_matches_institution if {
	subpolicy.result.decision == true with input as base_input
}

test_operation_carries_name_and_channel_key if {
	subpolicy.result.operation == {"name": "do_download", "parameters": {"channel_key": "PUBKEY"}} with input as base_input
}

test_tasks_flag_the_whole_chain if {
	tasks := subpolicy.result.verification_tasks with input as base_input
	count(tasks) == 7
}

test_deny_when_committee_not_responsible_for_pis_institution if {
	other := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/3/claims/ResponsibleFor",
		"value": "did:example:institution-other",
	}])
	subpolicy.result.decision == false with input as other
}

test_deny_when_project_not_approved if {
	# the IRB approval is about a different project than the one the PI owns
	other := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/1/subject",
		"value": "did:example:project-other",
	}])
	subpolicy.result.decision == false with input as other
}

test_deny_when_requester_not_on_owning_pis_team if {
	mismatched := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/5/claims/MemberOfTeamOf",
		"value": "did:example:pi-other",
	}])
	subpolicy.result.decision == false with input as mismatched
}

test_deny_when_no_public_key_credential if {
	nokey := json.patch(base_input, [{"op": "remove", "path": "/presentations/User/6"}])
	subpolicy.result.decision == false with input as nokey
}
