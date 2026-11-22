package pf.components.disease_specific_research_test

import rego.v1

import data.pf.components.disease_specific_research

membership := {"type": "ProjectMembershipCredential", "subject": "did:example:user",
	"claims": {"project": "did:example:project"}, "evidence": [0, 1]}

use := {"type": "IntendedDataUseCredential", "issuer": "did:example:dac", "subject": "did:example:project",
	"claims": {"useOnlyFor": {"purposes": ["HMB"], "diseases": ["MONDO:0005148"]}}, "evidence": [2]}

agreement := {"type": "AgreementCredential", "issuer": "did:example:platform", "subject": "did:example:user",
	"claims": {"agreementInfo": {"documentID": "did:example:terms", "documentVersion": "1.0"}}, "evidence": [3]}

condition(uses, agreements) := out if {
	out := disease_specific_research.output with input as {
		"inputs": {"projectMembership": [membership], "intendedDataUse": uses, "agreement": agreements},
		"policy_data": {"allowedDiseases": ["MONDO:0005148", "MONDO:0005015"]}, "request": {},
	}
}

# the component's decision when its condition holds for one subject, and when it holds for none
allowed(subject) := {"allow": true, "parameters": {"subject": [subject]}}

denied := {"allow": false, "parameters": {"subject": []}}

test_a_disease_the_owner_allows if {
	condition([use], [agreement]) == allowed("did:example:user")
}

test_one_condition_for_several_allowed_diseases if {
	both := object.union(use, {"claims": {"useOnlyFor": {"diseases": ["MONDO:0005148", "MONDO:0005015"]}}})
	count(condition([both], [agreement]).parameters.subject) == 1
}

test_a_disease_the_owner_does_not_allow if {
	condition([object.union(use, {"claims": {"useOnlyFor": {"diseases": ["MONDO:9999999"]}}})], [agreement]) == denied
}

test_the_use_of_another_project if {
	condition([object.union(use, {"subject": "did:example:other-project"})], [agreement]) == denied
}

test_the_agreement_of_someone_else if {
	condition([use], [object.union(agreement, {"subject": "did:example:other"})]) == denied
}
