package pf.components.ethics_approval_required_test

import rego.v1

import data.pf.components.ethics_approval_required

clearance := {"type": "IRBClearanceCredential", "subject": "did:example:user",
	"claims": {"project": "did:example:project", "purposes": ["HMB", "DS"]}, "evidence": [0, 1]}

use := {"type": "IntendedDataUseCredential", "issuer": "did:example:dac", "subject": "did:example:project",
	"claims": {"useOnlyFor": {"purposes": ["HMB"], "diseases": ["MONDO:0005015"]}}, "evidence": [2]}

grant(uses) := out if {
	out := ethics_approval_required.output with input as {
		"inputs": {"clearance": [clearance], "use": uses}, "policy_data": {}, "request": {},
	}
}

test_the_use_is_within_what_the_irb_approved if {
	grant([use]) == [{"type": "DownloadGrantCredential", "subject": "did:example:user", "claims": {}, "evidence": [0, 1, 2]}]
}

test_the_use_of_another_project if {
	grant([object.union(use, {"subject": "did:example:other-project"})]) == []
}

test_a_purpose_the_irb_did_not_approve if {
	grant([object.union(use, {"claims": {"useOnlyFor": {"purposes": ["HMB", "POA"]}}})]) == []
}

test_a_use_that_names_no_purpose if {
	grant([object.union(use, {"claims": {"useOnlyFor": {"purposes": []}}})]) == []
}
