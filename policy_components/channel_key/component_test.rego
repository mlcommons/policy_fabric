package pf.components.channel_key_test

import rego.v1

import data.pf.components.channel_key

key := {"type": "publicKeyCredential", "issuer": "did:example:platform", "subject": "did:example:user",
	"claims": {"key": "PUBKEY-1"}, "evidence": [0]}

decide(keys, request) := out if {
	out := channel_key.output with input as {"inputs": {"key": keys}, "policy_data": {}, "request": request}
}

test_the_requester_holds_the_requested_key if {
	decide([key], {"channel_key": "PUBKEY-1"}) == {"allow": true, "parameters": {"subject": ["did:example:user"], "channel_key": ["PUBKEY-1"]}}
}

test_only_the_holders_of_the_requested_key if {
	other := object.union(key, {"subject": "did:example:other", "claims": {"key": "PUBKEY-2"}})
	decide([key, other], {"channel_key": "PUBKEY-2"}).parameters.subject == ["did:example:other"]
}

test_a_key_the_requester_does_not_hold if {
	decide([key], {"channel_key": "PUBKEY-2"}) == {"allow": false, "parameters": {"subject": [], "channel_key": ["PUBKEY-2"]}}
}

test_a_request_that_names_no_key if {
	decide([key], {}) == {"allow": false, "parameters": {}}
}
