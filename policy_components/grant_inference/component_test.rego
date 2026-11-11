package pf.components.grant_inference_test

import rego.v1

import data.pf.components.grant_inference

grant := {"type": "InferenceGrantCredential", "subject": "did:example:script",
	"claims": {"script_digest": "sha256:abc"}, "evidence": [0, 1]}

infer(grants, request) := out if {
	out := grant_inference.output with input as {"inputs": {"grant": grants}, "policy_data": {}, "request": request}
}

test_the_requested_digest_of_the_granted_script if {
	infer([grant], {"script_digest": "sha256:abc"}) == [{
		"type": "Capability", "subject": "did:example:script",
		"claims": {"operation": {"name": "do_inference", "parameters": {"script_digest": "sha256:abc"}}},
		"evidence": [0, 1],
	}]
}

test_another_digest if {
	infer([grant], {"script_digest": "sha256:other"}) == []
	infer([grant], {}) == []
}

test_every_card_granted_the_script if {
	second := object.union(grant, {"evidence": [2, 3]})
	[c.evidence | some c in infer([grant, second], {"script_digest": "sha256:abc"})] == [[0, 1, 2, 3]]
	other := object.union(grant, {"subject": "did:example:other-script"})
	infer([grant, other], {"script_digest": "sha256:abc"}) == []
	infer([], {"script_digest": "sha256:abc"}) == []
}
