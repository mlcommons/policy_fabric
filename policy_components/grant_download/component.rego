package pf.components.grant_download

import rego.v1

# Grant download, the root of every download card: the do_download capability for the key
# the request names, when every grant the cards produced is about that key's holder.
#   key    publicKeyCredential      about the requester, key
#   grant  DownloadGrantCredential  about the requester, from each card on the asset
# -> Capability do_download {channel_key}.
interface := {
	"output": "Capability",
	"inputs": {
		"key": {"type": "publicKeyCredential", "role": "User"},
		"grant": {"type": "DownloadGrantCredential", "role": "User"},
	},
	"policy_data_schema": {},
}

output := [capability |
	some key in input.inputs.key
	key.claims.key == input.request.channel_key
	granted(key.subject)
	capability := {
		"type": "Capability",
		"subject": key.subject,
		"claims": {"operation": {"name": "do_download", "parameters": {"channel_key": key.claims.key}}},
		"evidence": evidence(array.concat([key], input.inputs.grant)),
	}
]

# With several cards on the asset the grant input holds every card's grants, and is empty
# unless each card granted someone; all of them must be about the key's holder.
granted(subject) if {
	count(input.inputs.grant) > 0
	every grant in input.inputs.grant {
		grant.subject == subject
	}
}

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
