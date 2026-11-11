package pf.components.institutional_irb_approval_test

import rego.v1

import data.pf.components.institutional_irb_approval

accreditation := {"type": "EthicsCommitteeAccreditationCredential", "issuer": "did:example:registry",
	"subject": "did:example:committee", "claims": {"ResponsibleFor": "did:example:institution"}, "evidence": [0]}

irb := {"type": "IRBApprovalCredential", "issuer": "did:example:dac", "subject": "did:example:project",
	"claims": {"isApprovedByEthicsCommittee": "did:example:committee", "purposes": ["HMB", "DS"]}, "evidence": [1]}

approve(accreditations, irbs) := out if {
	out := institutional_irb_approval.output with input as {
		"inputs": {"accreditation": accreditations, "irb": irbs}, "policy_data": {}, "request": {},
	}
}

test_an_accredited_committee_approved_the_project if {
	approve([accreditation], [irb]) == [{
		"type": "InstitutionalIRBApprovalCredential", "subject": "did:example:project",
		"claims": {"institution": "did:example:institution", "purposes": ["HMB", "DS"]}, "evidence": [0, 1],
	}]
}

test_an_unaccredited_committee if {
	other := object.union(irb, {"claims": {"isApprovedByEthicsCommittee": "did:example:other-committee"}})
	approve([accreditation], [other]) == []
}
