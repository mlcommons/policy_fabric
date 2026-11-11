package pf.components.grant_inference

import rego.v1

# Grant inference, the root of every federated learning card: the do_inference capability
# for the script digest the request names, when every grant the cards produced is about one
# script, with that digest.
#   grant  InferenceGrantCredential  about the script, script_digest, from each card on the asset
# -> Capability do_inference {script_digest}.
interface := {
	"output": "Capability",
	"inputs": {"grant": {"type": "InferenceGrantCredential", "role": "Script"}},
	"policy_data_schema": {},
}

output := [capability |
	some script in scripts
	granted(script)
	capability := {
		"type": "Capability",
		"subject": script,
		"claims": {"operation": {"name": "do_inference", "parameters": {"script_digest": input.request.script_digest}}},
		"evidence": evidence(input.inputs.grant),
	}
]

scripts contains script if {
	some grant in input.inputs.grant
	script := grant.subject
}

# With several cards on the asset the grant input holds every card's grants, and is empty
# unless each card granted some script; all of them must be about this one, for the digest
# the request names.
granted(script) if {
	every grant in input.inputs.grant {
		grant.subject == script
		grant.claims.script_digest == input.request.script_digest
	}
}

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
