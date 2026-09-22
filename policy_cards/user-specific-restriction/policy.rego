# DUO_0000026 — US (User Specific Restriction)
#
# Allow when the requester's UserPlatformCredential satisfies at least one of the
# data owner's approved-access routes: the account is an approved user, holds an
# allowed account type, or holds a required profile status. That credential and a
# publicKeyCredential (whose claim is the requester's channel public key) must be
# issued to the SAME subject, so the requester proves eligibility and owns the
# channel key. The approved users, account types, and profile statuses are
# configured by the data owner in policy_data. That key is returned as the
# parameters of a "do_download" operation so the token can build the guardian
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
#   input.policy_data         : { approvedUsers: [..], allowedAccountTypes: [..], requiredProfileStatuses: [..] }

package subpolicy

import rego.v1

# ---- requirements ---------------------------------------------------------
# The roles/credential-types this subpolicy needs. Evaluated by set_rego_policy
# with NO input, so it must be static.
requirements := {"User": ["UserPlatformCredential", "publicKeyCredential"]}

# ---- standardized credential views ----------------------------------------
user_creds := [c |
	some c in input.presentations.User
	c.type == "UserPlatformCredential"
]

public_key_creds := [c |
	some c in input.presentations.User
	c.type == "publicKeyCredential"
]

# a platform account satisfies the policy through any one approved-access route
user_qualifies(c) if c.claims.userId in input.policy_data.approvedUsers

user_qualifies(c) if c.claims.accountType in input.policy_data.allowedAccountTypes

user_qualifies(c) if c.claims.profileStatus in input.policy_data.requiredProfileStatuses

# platform credentials meeting at least one approved-access route
matching_user := [c |
	some c in user_creds
	user_qualifies(c)
]

# subjects that presented a public key credential
public_key_subjects := {p.subject | some p in public_key_creds}

# subjects satisfying the policy with the SAME subject across both credentials:
# an eligible platform account AND a public key credential issued to that subject
qualified_subjects := {c.subject |
	some c in matching_user
	c.subject in public_key_subjects
}

# ---- decision -------------------------------------------------------------
default decision := false

decision if count(qualified_subjects) > 0

# ---- verification tasks ---------------------------------------------------
# Flag the same-subject credentials the decision relies on (the eligible platform
# account and the public key) for the contract to verify by global index.
flagged_creds := array.concat(
	[c | some c in matching_user; c.subject in qualified_subjects],
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
