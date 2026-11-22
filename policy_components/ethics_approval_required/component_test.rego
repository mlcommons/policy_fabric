package pf.components.ethics_approval_required_test

import rego.v1

import data.pf.components.ethics_approval_required

clearance := {"type": "IRBClearanceCredential", "subject": "did:example:user",
	"claims": {"project": "did:example:project", "purposes": ["HMB", "DS"]}, "evidence": [0, 1]}

use := {"type": "IntendedDataUseCredential", "issuer": "did:example:dac", "subject": "did:example:project",
	"claims": {"useOnlyFor": {"purposes": ["HMB"], "diseases": ["MONDO:0005015"]}}, "evidence": [2]}

condition(uses) := out if {
	out := ethics_approval_required.output with input as {
		"inputs": {"clearance": [clearance], "use": uses}, "policy_data": {}, "request": {},
	}
}

# the component's decision when its condition holds for one subject, and when it holds for none
allowed(subject) := {"allow": true, "parameters": {"subject": [subject]}}

denied := {"allow": false, "parameters": {"subject": []}}

test_the_use_is_within_what_the_irb_approved if {
	condition([use]) == allowed("did:example:user")
}

test_the_use_of_another_project if {
	condition([object.union(use, {"subject": "did:example:other-project"})]) == denied
}

test_a_purpose_the_irb_did_not_approve if {
	condition([object.union(use, {"claims": {"useOnlyFor": {"purposes": ["HMB", "POA"]}}})]) == denied
}

test_a_use_that_names_no_purpose if {
	condition([object.union(use, {"claims": {"useOnlyFor": {"purposes": []}}})]) == denied
}
