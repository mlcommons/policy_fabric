# DUO_0000018 — NPUNCU (Not-for-Profit, Non-Commercial Use Only)
#
# Allow when the requester's organization has a not-for-profit legal form AND the
# project's intended use is non-commercial. A LegalDesignationCredential whose legal
# form is a data-owner-accepted non-profit form and a publicKeyCredential (whose
# claim is the requester's channel public key) must be issued to the SAME subject,
# and an IntendedDataUseCredential must declare no prohibited (commercial) purpose.
# The accepted legal forms and prohibited purposes are configured by the data owner
# in policy_data. That key is returned as the parameters of a "do_download"
# operation so the token can build the guardian capability. Signature verification
# of the credentials the decision relies on is delegated to the rego_policy_agent
# contract via `verification_tasks` (referenced by global index).
#
# Written for the rego_policy_agent contract: package `subpolicy`, with the two
# rules the contract evaluates -- `data.subpolicy.requirements` (static, no input)
# and `data.subpolicy.result` (over the standardized input below).
#
# Input shape (built by the contract):
#   input.presentations[role] : [ { type, issuer, subject, claims, index } ]
#   input.trusted_issuers     : { ... }   (the contract verifies trust itself)
#   input.policy_data         : { nonprofitLegalForms: [..], prohibitedPurposes: [..] }

package subpolicy

import rego.v1

# ---- requirements ---------------------------------------------------------
# The roles/credential-types this subpolicy needs. Evaluated by set_rego_policy
# with NO input, so it must be static.
requirements := {"User": ["LegalDesignationCredential", "IntendedDataUseCredential", "publicKeyCredential"]}

# ---- standardized credential views ----------------------------------------
legal_creds := [c |
	some c in input.presentations.User
	c.type == "LegalDesignationCredential"
]

idu_creds := [c |
	some c in input.presentations.User
	c.type == "IntendedDataUseCredential"
]

public_key_creds := [c |
	some c in input.presentations.User
	c.type == "publicKeyCredential"
]

# legal-designation credentials whose legal form is a data-owner-accepted non-profit form
matching_legal := [c |
	some c in legal_creds
	c.claims.hasLegalForm in input.policy_data.nonprofitLegalForms
]

idu_declares_prohibited(c) if {
	some p in c.claims.useOnlyFor.purposes
	p in input.policy_data.prohibitedPurposes
}

# intended-data-use credentials that do not declare a commercial purpose
non_commercial_idus := [c |
	some c in idu_creds
	not idu_declares_prohibited(c)
]

# subjects that presented a public key credential
public_key_subjects := {p.subject | some p in public_key_creds}

# a non-commercial intended use must be declared for any requester to qualify
non_commercial_use if count(non_commercial_idus) > 0

# subjects satisfying the policy with the SAME subject across the legal designation
# and the public key, provided a non-commercial intended use is declared
qualified_subjects := {c.subject |
	some c in matching_legal
	c.subject in public_key_subjects
	non_commercial_use
}

# ---- decision -------------------------------------------------------------
default decision := false

decision if count(qualified_subjects) > 0

# ---- verification tasks ---------------------------------------------------
# Flag the credentials the decision relies on (the non-profit legal designation,
# the public key, and the non-commercial intended use) for the contract to verify
# by global index.
flagged_creds := array.concat(
	array.concat(
		[c | some c in matching_legal; c.subject in qualified_subjects],
		[p | some p in public_key_creds; p.subject in qualified_subjects],
	),
	[c | some c in non_commercial_idus; count(qualified_subjects) > 0],
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
