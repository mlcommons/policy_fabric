# DUO_0000028 — IS (Institution Specific Restriction)
#
# Allow when an AffiliationCredential shows the subject is a member of an allowed
# institution. The allowed-institution list is configured by the data owner in
# policy_data and handed to Rego as input.policy_data. The request must also carry
# a publicKeyCredential whose claim is the requester's channel public key. Both
# credentials must be issued to the SAME subject, so the requester proves the
# affiliation and owns the channel key. That key is returned as the parameters of a
# "do_download" operation so the token can build the guardian capability. Signature
# verification of the credentials the decision relies on is delegated to the
# rego_policy_agent contract via `verification_tasks` (referenced by index).
#
# Written for the rego_policy_agent contract: package `subpolicy`, with the two
# rules the contract evaluates -- `data.subpolicy.requirements` (static, no input)
# and `data.subpolicy.result` (over the standardized input below).
#
# Input shape (built by the contract):
#   input.presentations[role] : [ { type, issuer, subject, claims, index } ]
#   input.trusted_issuers     : { ... }   (the contract verifies trust itself)
#   input.policy_data         : { allowedInstitutions: [..] }

package subpolicy

import rego.v1

# ---- requirements ---------------------------------------------------------
# The roles/credential-types this subpolicy needs. Evaluated by set_rego_policy
# with NO input, so it must be static.
requirements := {"User": ["AffiliationCredential", "publicKeyCredential"]}

# ---- standardized credential views ----------------------------------------
affiliation_creds := [c |
	some c in input.presentations.User
	c.type == "AffiliationCredential"
]

public_key_creds := [c |
	some c in input.presentations.User
	c.type == "publicKeyCredential"
]

# affiliation credentials naming an allowed institution
matching_affiliation := [c |
	some c in affiliation_creds
	c.claims.isMemberOf in input.policy_data.allowedInstitutions
]

# subjects that presented a public key credential
public_key_subjects := {p.subject | some p in public_key_creds}

# subjects satisfying the policy with the SAME subject across both credentials:
# an approved affiliation AND a public key credential issued to that subject
qualified_subjects := {c.subject |
	some c in matching_affiliation
	c.subject in public_key_subjects
}

# ---- decision -------------------------------------------------------------
default decision := false

decision if count(qualified_subjects) > 0

# ---- verification tasks ---------------------------------------------------
# Flag the same-subject credentials the decision relies on (the matching
# affiliation and the public key) for the contract to verify by global index.
flagged_creds := array.concat(
	[c | some c in matching_affiliation; c.subject in qualified_subjects],
	[p | some p in public_key_creds; p.subject in qualified_subjects],
)

verification_tasks := [{"index": c.index} | some c in flagged_creds]

# ---- operation ------------------------------------------------------------
# Name the "do_download" guardian operation and carry the channel key (the public
# key of the same subject's publicKeyCredential) as its parameters. Defaults keep
# the result well-formed on deny.
channel_keys := [p.claims.key |
	some p in public_key_creds
	p.subject in qualified_subjects
]

default channel_key := ""

channel_key := channel_keys[0] if count(channel_keys) > 0

operation := {"name": "do_download", "parameters": {"channel_key": channel_key}}

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
	"operation": operation,
}
