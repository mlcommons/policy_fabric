package pf.components.script_digest_test

import rego.v1

import data.pf.components.script_digest

hash := {"type": "ScriptHashCredential", "issuer": "did:example:registry", "subject": "did:example:script",
	"claims": {"scriptHash": "sha256:abc"}, "evidence": [0]}

decide(hashes, request) := out if {
	out := script_digest.output with input as {"inputs": {"scriptHash": hashes}, "policy_data": {}, "request": request}
}

test_the_script_has_the_requested_digest if {
	decide([hash], {"script_digest": "sha256:abc"}) == {"allow": true, "parameters": {"subject": ["did:example:script"], "script_digest": ["sha256:abc"]}}
}

test_another_digest if {
	decide([hash], {"script_digest": "sha256:def"}) == {"allow": false, "parameters": {"subject": [], "script_digest": ["sha256:def"]}}
}

test_a_request_that_names_no_digest if {
	decide([hash], {}) == {"allow": false, "parameters": {}}
}
