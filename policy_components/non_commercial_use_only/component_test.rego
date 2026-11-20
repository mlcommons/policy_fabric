package pf.components.non_commercial_use_only_test

import rego.v1

import data.pf.components.non_commercial_use_only

membership := {"type": "ProjectMembershipCredential", "subject": "did:example:user",
	"claims": {"project": "did:example:project"}, "evidence": [0, 1]}

use := {"type": "IntendedDataUseCredential", "issuer": "did:example:dac", "subject": "did:example:project",
	"claims": {"useOnlyFor": {"purposes": ["HMB"], "diseases": []}}, "evidence": [2]}

agreement := {"type": "AgreementCredential", "issuer": "did:example:platform", "subject": "did:example:user",
	"claims": {"agreementInfo": {"documentID": "did:example:terms", "documentVersion": "1.0"}}, "evidence": [3]}

condition(uses, agreements) := out if {
	out := non_commercial_use_only.output with input as {
		"inputs": {"projectMembership": [membership], "intendedDataUse": uses, "agreement": agreements},
		"policy_data": {"prohibitedPurposes": ["commercial"]}, "request": {},
	}
}

test_no_purpose_the_owner_prohibits if {
	condition([use], [agreement]) == [{"type": "DataUseConditionCredential", "subject": "did:example:user", "claims": {}, "evidence": [0, 1, 2, 3]}]
}

test_a_purpose_the_owner_prohibits if {
	condition([object.union(use, {"claims": {"useOnlyFor": {"purposes": ["HMB", "commercial"]}}})], [agreement]) == []
}

test_policy_data_without_the_prohibited_purposes if {
	non_commercial_use_only.output == [] with input as {
		"inputs": {"projectMembership": [membership], "intendedDataUse": [use], "agreement": [agreement]},
		"policy_data": {}, "request": {},
	}
}

test_the_use_of_another_project if {
	condition([object.union(use, {"subject": "did:example:other-project"})], [agreement]) == []
}

test_the_agreement_of_someone_else if {
	condition([use], [object.union(agreement, {"subject": "did:example:other"})]) == []
}
