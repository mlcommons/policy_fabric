package pf.components.channel_key

import rego.v1

# ChannelKey: the requester holds the channel key the request names, the key the download is
# encrypted to: a session key credential carries it.
#   key  publicKeyCredential  about the requester, key
# -> Decision about the requester, admitting that channel_key. No policy data.
interface := {
	"output": "Decision",
	"inputs": {"key": {"type": "publicKeyCredential", "role": "User"}},
	"policy_data_schema": {},
}

default output := {"allow": false, "parameters": {}}

output := {"allow": count(holders) > 0, "parameters": {"subject": sort(holders), "channel_key": [key]}} if {
	key := input.request.channel_key
	holders := {c.subject | some c in input.inputs.key; c.claims.key == key}
}
