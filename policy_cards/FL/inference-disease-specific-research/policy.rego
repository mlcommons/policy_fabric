# FL-DS — Disease Specific Research, for inference
#
# The inference counterpart of DUO_0000007 (DS). When the data never moves, the
# thing that must declare its purpose is the code that will run against it, so both
# credentials this policy reads are about the script.
#
# The script presents an IntendedDataUseCredential whose disease scope intersects
# the owner's allowed MONDO codes, and a ScriptHashCredential stating its content
# digest. Both must name the SAME script as their subject: a declared use attached
# to one script says nothing about another, and without that tie a requester could
# pair an in-scope declaration with an unrelated digest. The digest travels to the
# guardian in the "do_inference" operation so the code that actually runs can be
# measured against the code that was approved.
#
# Written for the rego_policy_agent contract: package `subpolicy`, with the two
# rules the contract evaluates -- `data.subpolicy.requirements` (static, no input)
# and `data.subpolicy.result` (over the standardized input below).
#
# Input shape (built by the contract):
#   input.presentations[role] : [ { type, issuer, subject, claims, index } ]
#   input.trusted_issuers     : { ... }   (the contract verifies trust itself)
#   input.policy_data         : { allowedDiseases: [..] }

package subpolicy

import rego.v1

# ---- requirements ---------------------------------------------------------
# The roles/credential-types this subpolicy needs. Evaluated by set_rego_policy
# with NO input, so it must be static. Both credentials describe the script, so
# both belong to the Script role.
requirements := {"Script": [
	"IntendedDataUseCredential",
	"ScriptHashCredential",
]}

# ---- standardized credential views ----------------------------------------
idu_creds := [c |
	some c in input.presentations.Script
	c.type == "IntendedDataUseCredential"
]

script_hash_creds := [c |
	some c in input.presentations.Script
	c.type == "ScriptHashCredential"
]

# intended-data-use credentials whose disease scope intersects the allowed MONDO codes
matching_idu := [c |
	some c in idu_creds
	some d in c.claims.useOnlyFor.diseases
	d in input.policy_data.allowedDiseases
]

# ---- qualifying evidence ---------------------------------------------------
# One script, declaring an in-scope use and stating its digest:
#   IntendedDataUseCredential  script -> disease scope (claims.useOnlyFor.diseases)
#   ScriptHashCredential       script -> digest        (claims.scriptHash)
# Both credentials must have the same subject, so the declared use belongs to the
# very script whose digest is approved.
qualified_runs := {run |
	some idu in matching_idu
	some script_hash in script_hash_creds
	idu.subject == script_hash.subject
	run := {
		"script": script_hash.subject,
		"script_hash": script_hash.claims.scriptHash,
		"indices": [idu.index, script_hash.index],
	}
}

# ---- decision -------------------------------------------------------------
default decision := false

decision if count(qualified_runs) > 0

# ---- verification tasks ---------------------------------------------------
# Flag the credentials the decision relies on for the contract to verify by global
# index (the intended-data-use credential and the script's hash).
flagged_indices := {idx |
	some run in qualified_runs
	some idx in run.indices
}

verification_tasks := [{"index": idx} | some idx in flagged_indices]

# ---- operation ------------------------------------------------------------
# Name the "do_inference" guardian operation and carry the approved script digest.
# The default keeps the result well-formed on deny.
script_digests := [run.script_hash | some run in qualified_runs]

default script_digest := ""

script_digest := script_digests[0] if count(script_digests) > 0

operation := {"name": "do_inference", "parameters": {"script_digest": script_digest}}

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
	"operation": operation,
}
