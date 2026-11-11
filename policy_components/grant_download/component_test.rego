package pf.components.grant_download_test

import rego.v1

import data.pf.components.grant_download

key := {"type": "publicKeyCredential", "issuer": "did:example:platform", "subject": "did:example:user",
	"claims": {"key": "KEY-1"}, "evidence": [6]}

grant := {"type": "DownloadGrantCredential", "subject": "did:example:user", "claims": {}, "evidence": [0, 5]}

download(keys, grants, request) := out if {
	out := grant_download.output with input as {
		"inputs": {"key": keys, "grant": grants}, "policy_data": {}, "request": request,
	}
}

test_the_requested_key_of_the_granted_requester if {
	download([key], [grant], {"channel_key": "KEY-1"}) == [{
		"type": "Capability", "subject": "did:example:user",
		"claims": {"operation": {"name": "do_download", "parameters": {"channel_key": "KEY-1"}}},
		"evidence": [0, 5, 6],
	}]
}

test_the_key_of_someone_else if {
	download([object.union(key, {"subject": "did:example:other"})], [grant], {"channel_key": "KEY-1"}) == []
}

test_only_the_key_the_request_names if {
	other := object.union(key, {"claims": {"key": "KEY-2"}, "evidence": [7]})
	[c.claims.operation.parameters.channel_key | some c in download([other, key], [grant], {"channel_key": "KEY-1"})] == ["KEY-1"]
	download([key], [grant], {}) == []
}

test_every_card_granted_the_key_holder if {
	second := object.union(grant, {"evidence": [8]})
	count(download([key], [grant, second], {"channel_key": "KEY-1"})) == 1
	someone_else := object.union(grant, {"subject": "did:example:other"})
	download([key], [grant, someone_else], {"channel_key": "KEY-1"}) == []
	download([key], [], {"channel_key": "KEY-1"}) == []
}
