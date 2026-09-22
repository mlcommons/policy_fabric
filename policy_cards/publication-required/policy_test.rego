# Unit tests for DUO_0000019 (PUB).  Run with:  opa test pub/ -v
package subpolicy_test

import data.subpolicy

base_input := {
	"policy_data": {"datasetID": "did:example:dataset-1"},
	"presentations": {"User": [
		{
			"type": "ProjectOwnershipCredential",
			"issuer": "did:example:registry",
			"subject": "did:example:pi-1",
			"claims": {"Owns": "did:example:project-1"},
			"index": 0,
		},
		{
			"type": "AffiliationCredential",
			"issuer": "did:example:registry",
			"subject": "did:example:pi-1",
			"claims": {"isMemberOf": "did:example:institution-1", "typeOfMembership": "faculty"},
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
			"type": "ScopedAgreementCredential",
			"issuer": "did:example:notary",
			"subject": "did:example:terms-1",
			"claims": {"agreementInfo": {
				"counterParty": "did:example:owner-1",
				"scope": {"obligation": "Publication", "project": "did:example:project-1", "dataset": "did:example:dataset-1"},
			}},
			"index": 3,
		},
		{
			"type": "AgreementCredential",
			"issuer": "did:example:notary",
			"subject": "did:example:institution-1",
			"claims": {"agreementInfo": {"documentID": "did:example:terms-1", "documentVersion": "1.0"}},
			"index": 4,
		},
		{
			"type": "publicKeyCredential",
			"issuer": "did:example:platform",
			"subject": "did:example:user-1",
			"claims": {"key": "PUBKEY"},
			"index": 5,
		},
	]},
}

test_requirements_list_the_chain_credentials if {
	subpolicy.requirements == {"User": [
		"ProjectOwnershipCredential",
		"AffiliationCredential",
		"TeamCredential",
		"ScopedAgreementCredential",
		"AgreementCredential",
		"publicKeyCredential",
	]}
}

test_allow_when_publication_agreement_in_place if {
	subpolicy.result.decision == true with input as base_input
}

test_operation_carries_name_and_channel_key if {
	subpolicy.result.operation == {"name": "do_download", "parameters": {"channel_key": "PUBKEY"}} with input as base_input
}

test_tasks_flag_the_whole_chain if {
	tasks := subpolicy.result.verification_tasks with input as base_input
	count(tasks) == 6
}

test_deny_when_obligation_is_not_publication if {
	other := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/3/claims/agreementInfo/scope/obligation",
		"value": "Collaboration",
	}])
	subpolicy.result.decision == false with input as other
}

test_deny_when_agreement_is_for_a_different_dataset if {
	other := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/3/claims/agreementInfo/scope/dataset",
		"value": "did:example:dataset-other",
	}])
	subpolicy.result.decision == false with input as other
}

test_deny_when_institution_has_not_agreed if {
	# the institution's agreement points at a different terms document
	other := json.patch(base_input, [{
		"op": "replace",
		"path": "/presentations/User/4/claims/agreementInfo/documentID",
		"value": "did:example:terms-other",
	}])
	subpolicy.result.decision == false with input as other
}

test_deny_when_no_public_key_credential if {
	nokey := json.patch(base_input, [{"op": "remove", "path": "/presentations/User/5"}])
	subpolicy.result.decision == false with input as nokey
}
