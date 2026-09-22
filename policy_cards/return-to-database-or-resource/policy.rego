# DUO_0000029 — RTN (Return to Database or Resource)
#
# Allow when the requester has accepted the data owner's required terms document,
# presents a channel public key, and the work runs on a compute environment that
# attests it handles results securely -- the attestation that lets the
# return-to-resource obligation be honoured. An AgreementCredential whose claim
# `agreementInfo.documentID` matches the required terms document (configured by the
# data owner in policy_data) and a publicKeyCredential must be issued to the SAME
# subject, and a ComputeEnvironmentCredential must attest
# `hasComputeProfile.profile.SecureHandlingOfResults`. The channel key is returned
# as the parameters of a "do_download" operation so the token can build the guardian
# capability. Signature verification of the credentials the decision relies on is
# delegated to the rego_policy_agent contract via `verification_tasks` (referenced
# by global index).
#
# Written for the rego_policy_agent contract: package `subpolicy`, with the two
# rules the contract evaluates -- `data.subpolicy.requirements` (static, no input)
# and `data.subpolicy.result` (over the standardized input below).
#
# Input shape (built by the contract):
#   input.presentations[role] : [ { type, issuer, subject, claims, index } ]
#   input.trusted_issuers     : { ... }   (the contract verifies trust itself)
#   input.policy_data         : { requiredDocumentID: <did> }

package subpolicy

import rego.v1

# ---- requirements ---------------------------------------------------------
# The roles/credential-types this subpolicy needs. Evaluated by set_rego_policy
# with NO input, so it must be static.
requirements := {"User": ["AgreementCredential", "ComputeEnvironmentCredential", "publicKeyCredential"]}

# ---- standardized credential views ----------------------------------------
agreement_creds := [c |
	some c in input.presentations.User
	c.type == "AgreementCredential"
]

compute_creds := [c |
	some c in input.presentations.User
	c.type == "ComputeEnvironmentCredential"
]

public_key_creds := [c |
	some c in input.presentations.User
	c.type == "publicKeyCredential"
]

# agreements accepting the data owner's required terms document
matching_agreements := [c |
	some c in agreement_creds
	c.claims.agreementInfo.documentID == input.policy_data.requiredDocumentID
]

# compute environments attesting they handle results securely
secure_compute_creds := [c |
	some c in compute_creds
	c.claims.hasComputeProfile.profile.SecureHandlingOfResults == true
]

# subjects that presented a public key credential
public_key_subjects := {p.subject | some p in public_key_creds}

# a secure compute environment must be attested for the return obligation to be enforceable
secure_environment if count(secure_compute_creds) > 0

# subjects satisfying the policy with the SAME subject across the agreement and the
# public key, provided a secure compute environment is attested
qualified_subjects := {c.subject |
	some c in matching_agreements
	c.subject in public_key_subjects
	secure_environment
}

# ---- decision -------------------------------------------------------------
default decision := false

decision if count(qualified_subjects) > 0

# ---- verification tasks ---------------------------------------------------
# Flag the credentials the decision relies on (the matching agreement, the public
# key, and the secure compute environment) for the contract to verify by index.
flagged_creds := array.concat(
	array.concat(
		[c | some c in matching_agreements; c.subject in qualified_subjects],
		[p | some p in public_key_creds; p.subject in qualified_subjects],
	),
	[c | some c in secure_compute_creds; count(qualified_subjects) > 0],
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
