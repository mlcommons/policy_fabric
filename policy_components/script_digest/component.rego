package pf.components.script_digest

import rego.v1

# ScriptDigest: the script has the digest the request names: a script digest credential
# carries it.
#   scriptHash  ScriptHashCredential  about the script, scriptHash
# -> Decision about the script, admitting that script_digest. No policy data.
interface := {
	"output": "Decision",
	"inputs": {"scriptHash": {"type": "ScriptHashCredential", "role": "Script"}},
	"policy_data_schema": {},
}

default output := {"allow": false, "parameters": {}}

output := {"allow": count(scripts) > 0, "parameters": {"subject": sort(scripts), "script_digest": [digest]}} if {
	digest := input.request.script_digest
	scripts := {c.subject | some c in input.inputs.scriptHash; c.claims.scriptHash == digest}
}
