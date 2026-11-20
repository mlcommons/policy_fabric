package pf.components.collaboration_required_test

import rego.v1

import data.pf.components.collaboration_required

membership := {"type": "ProjectMembershipCredential", "subject": "did:example:user",
	"claims": {"project": "did:example:project"}, "evidence": [0, 1]}

affiliation := {"type": "AffiliationCredential", "issuer": "did:example:registry", "subject": "did:example:user",
	"claims": {"isMemberOf": "did:example:institution", "typeOfMembership": "staff"}, "evidence": [2]}

scoped := {"type": "ScopedAgreementCredential", "issuer": "did:example:notary", "subject": "did:example:terms",
	"claims": {"agreementInfo": {"counterParty": "did:example:owner", "scope": {
		"obligation": "Collaboration", "project": "did:example:project", "dataset": "did:example:dataset",
	}}}, "evidence": [3]}

agreement := {"type": "AgreementCredential", "issuer": "did:example:notary", "subject": "did:example:institution",
	"claims": {"agreementInfo": {"documentID": "did:example:terms", "documentVersion": "1.0"}}, "evidence": [4]}

condition(affiliations, scopeds, agreements) := out if {
	out := collaboration_required.output with input as {
		"inputs": {
			"projectMembership": [membership], "affiliation": affiliations,
			"scopedAgreement": scopeds, "agreement": agreements,
		},
		"policy_data": {"datasetID": "did:example:dataset"}, "request": {},
	}
}

scope(change) := object.union(scoped, {"claims": {"agreementInfo": {"scope": change}}})

test_the_requesters_institution_agreed_to_collaborate if {
	condition([affiliation], [scoped], [agreement]) == [{"type": "DataUseConditionCredential", "subject": "did:example:user", "claims": {}, "evidence": [0, 1, 2, 3, 4]}]
}

test_the_affiliation_of_the_pi if {
	condition([object.union(affiliation, {"subject": "did:example:pi"})], [scoped], [agreement]) == []
}

test_another_obligation if {
	condition([affiliation], [scope({"obligation": "Publication"})], [agreement]) == []
}

test_another_dataset if {
	condition([affiliation], [scope({"dataset": "did:example:other-dataset"})], [agreement]) == []
}

test_another_project if {
	condition([affiliation], [scope({"project": "did:example:other-project"})], [agreement]) == []
}

test_an_institution_that_did_not_agree if {
	condition([object.union(affiliation, {"claims": {"isMemberOf": "did:example:other-institution"}})], [scoped], [agreement]) == []
}

test_an_agreement_to_other_terms if {
	condition([affiliation], [scoped], [object.union(agreement, {"claims": {"agreementInfo": {"documentID": "did:example:other-terms"}}})]) == []
}
