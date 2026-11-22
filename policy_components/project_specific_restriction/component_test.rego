package pf.components.project_specific_restriction_test

import rego.v1

import data.pf.components.project_specific_restriction

membership := {"type": "ProjectMembershipCredential", "subject": "did:example:user",
	"claims": {"project": "did:example:project"}, "evidence": [0, 1]}

use := {"type": "IntendedDataUseCredential", "issuer": "did:example:dac", "subject": "did:example:project",
	"claims": {"useOnlyFor": {"purposes": ["HMB"]}}, "evidence": [2]}

agreement := {"type": "AgreementCredential", "issuer": "did:example:platform", "subject": "did:example:user",
	"claims": {"agreementInfo": {"documentID": "did:example:terms", "documentVersion": "1.0"}}, "evidence": [3]}

condition(memberships, uses, agreements) := out if {
	out := project_specific_restriction.output with input as {
		"inputs": {"projectMembership": memberships, "intendedDataUse": uses, "agreement": agreements},
		"policy_data": {"approvedProjects": ["did:example:project", "did:example:other-project"]}, "request": {},
	}
}

# the component's decision when its condition holds for one subject, and when it holds for none
allowed(subject) := {"allow": true, "parameters": {"subject": [subject]}}

denied := {"allow": false, "parameters": {"subject": []}}

test_a_project_the_owner_approved if {
	condition([membership], [use], [agreement]) == allowed("did:example:user")
}

test_a_project_the_owner_did_not_approve if {
	other := object.union(membership, {"claims": {"project": "did:example:unapproved-project"}})
	condition([other], [object.union(use, {"subject": "did:example:unapproved-project"})], [agreement]) == denied
}

test_the_use_of_another_project if {
	condition([membership], [object.union(use, {"subject": "did:example:other-project"})], [agreement]) == denied
}

test_the_agreement_of_someone_else if {
	condition([membership], [use], [object.union(agreement, {"subject": "did:example:other"})]) == denied
}
