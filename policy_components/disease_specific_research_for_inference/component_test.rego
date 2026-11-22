package pf.components.disease_specific_research_for_inference_test

import rego.v1

import data.pf.components.disease_specific_research_for_inference

use := {"type": "IntendedDataUseCredential", "issuer": "did:example:dac", "subject": "did:example:script",
	"claims": {"useOnlyFor": {"purposes": ["DS"], "diseases": ["MONDO:0005015"]}}, "evidence": [0]}

condition(uses) := out if {
	out := disease_specific_research_for_inference.output with input as {
		"inputs": {"intendedDataUse": uses},
		"policy_data": {"allowedDiseases": ["MONDO:0005015"]}, "request": {},
	}
}

# the component's decision when its condition holds for one subject, and when it holds for none
allowed(subject) := {"allow": true, "parameters": {"subject": [subject]}}

denied := {"allow": false, "parameters": {"subject": []}}

test_the_script_declares_an_allowed_disease if {
	condition([use]) == allowed("did:example:script")
}

test_a_disease_the_owner_does_not_allow if {
	condition([object.union(use, {"claims": {"useOnlyFor": {"diseases": ["MONDO:9999999"]}}})]) == denied
}
