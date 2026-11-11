package pf.components.disease_specific_research_for_inference_test

import rego.v1

import data.pf.components.disease_specific_research_for_inference

use := {"type": "IntendedDataUseCredential", "issuer": "did:example:dac", "subject": "did:example:script",
	"claims": {"useOnlyFor": {"purposes": ["DS"], "diseases": ["MONDO:0005015"]}}, "evidence": [0]}

hash := {"type": "ScriptHashCredential", "issuer": "did:example:script-authority", "subject": "did:example:script",
	"claims": {"scriptHash": "sha256:abc"}, "evidence": [1]}

grant(uses, hashes) := out if {
	out := disease_specific_research_for_inference.output with input as {
		"inputs": {"intendedDataUse": uses, "scriptHash": hashes},
		"policy_data": {"allowedDiseases": ["MONDO:0005015"]}, "request": {},
	}
}

test_the_script_declares_an_allowed_disease if {
	grant([use], [hash]) == [{
		"type": "InferenceGrantCredential", "subject": "did:example:script",
		"claims": {"script_digest": "sha256:abc"}, "evidence": [0, 1],
	}]
}

test_a_disease_the_owner_does_not_allow if {
	grant([object.union(use, {"claims": {"useOnlyFor": {"diseases": ["MONDO:9999999"]}}})], [hash]) == []
}

test_the_hash_of_another_script if {
	grant([use], [object.union(hash, {"subject": "did:example:other-script"})]) == []
}
