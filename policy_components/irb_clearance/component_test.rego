package pf.components.irb_clearance_test

import rego.v1

import data.pf.components.irb_clearance

approval := {"type": "InstitutionalIRBApprovalCredential", "subject": "did:example:project",
	"claims": {"institution": "did:example:institution", "purposes": ["HMB"]}, "evidence": [2, 3]}

affiliation := {"type": "AffiliationCredential", "issuer": "did:example:registry", "subject": "did:example:user",
	"claims": {"isMemberOf": "did:example:institution", "typeOfMembership": "staff"}, "evidence": [4]}

membership := {"type": "ProjectMembershipCredential", "subject": "did:example:user",
	"claims": {"project": "did:example:project"}, "evidence": [0, 1]}

clear(approvals, affiliations, memberships) := out if {
	out := irb_clearance.output with input as {
		"inputs": {"approval": approvals, "affiliation": affiliations, "membership": memberships},
		"policy_data": {}, "request": {},
	}
}

test_the_requester_is_cleared_for_their_project if {
	clear([approval], [affiliation], [membership]) == [{
		"type": "IRBClearanceCredential", "subject": "did:example:user",
		"claims": {"project": "did:example:project", "purposes": ["HMB"]}, "evidence": [0, 1, 2, 3, 4],
	}]
}

test_the_affiliation_of_someone_else if {
	pi := object.union(affiliation, {"subject": "did:example:pi"})
	clear([approval], [pi], [membership]) == []
}

test_another_institution if {
	elsewhere := object.union(affiliation, {"claims": {"isMemberOf": "did:example:other-institution"}})
	clear([approval], [elsewhere], [membership]) == []
}

test_an_approval_of_another_project if {
	other := object.union(approval, {"subject": "did:example:other-project"})
	clear([other], [affiliation], [membership]) == []
}
