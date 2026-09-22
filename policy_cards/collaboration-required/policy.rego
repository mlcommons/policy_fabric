# DUO_0000020 — COL (Collaboration Required)
#
# Allow when an executed collaboration agreement binds the requester's institution
# to the governed dataset. The requester is tied to a project and institution
# through a chain: a TeamCredential places them on a PI's team, a
# ProjectOwnershipCredential shows that PI owns a project, and an
# AffiliationCredential shows that PI belongs to an institution. A
# ScopedAgreementCredential names a terms document scoped to that project with the
# "Collaboration" obligation for the governed dataset, and an AgreementCredential
# shows the institution has agreed to that terms document. The requester also
# presents a publicKeyCredential whose claim is their channel public key. The
# governed dataset is configured by the data owner in policy_data. That key is
# returned as the parameters of a "do_download" operation so the token can build the
# guardian capability. Signature verification of the credentials the decision relies
# on is delegated to the rego_policy_agent contract via `verification_tasks`
# (referenced by global index).
#
# Written for the rego_policy_agent contract: package `subpolicy`, with the two
# rules the contract evaluates -- `data.subpolicy.requirements` (static, no input)
# and `data.subpolicy.result` (over the standardized input below).
#
# Input shape (built by the contract):
#   input.presentations[role] : [ { type, issuer, subject, claims, index } ]
#   input.trusted_issuers     : { ... }   (the contract verifies trust itself)
#   input.policy_data         : { datasetID: <did> }

package subpolicy

import rego.v1

# ---- requirements ---------------------------------------------------------
# The roles/credential-types this subpolicy needs. Evaluated by set_rego_policy
# with NO input, so it must be static.
requirements := {"User": [
	"ProjectOwnershipCredential",
	"AffiliationCredential",
	"TeamCredential",
	"ScopedAgreementCredential",
	"AgreementCredential",
	"publicKeyCredential",
]}

# ---- standardized credential views ----------------------------------------
ownership_creds := [c |
	some c in input.presentations.User
	c.type == "ProjectOwnershipCredential"
]

affiliation_creds := [c |
	some c in input.presentations.User
	c.type == "AffiliationCredential"
]

team_creds := [c |
	some c in input.presentations.User
	c.type == "TeamCredential"
]

scoped_agreement_creds := [c |
	some c in input.presentations.User
	c.type == "ScopedAgreementCredential"
]

agreement_creds := [c |
	some c in input.presentations.User
	c.type == "AgreementCredential"
]

public_key_creds := [c |
	some c in input.presentations.User
	c.type == "publicKeyCredential"
]

# scoped-agreement documents carrying the collaboration obligation for the governed dataset
scoped_for_collaboration := [c |
	some c in scoped_agreement_creds
	c.claims.agreementInfo.scope.obligation == "Collaboration"
	c.claims.agreementInfo.scope.dataset == input.policy_data.datasetID
]

# ---- credential chain ------------------------------------------------------
# A qualifying chain binds a requester to an institution that has executed the
# collaboration agreement for the governed dataset:
#   TeamCredential           requester   -> PI          (claims.MemberOfTeamOf)
#   ProjectOwnershipCred     PI          -> project     (claims.Owns)
#   AffiliationCredential    PI          -> institution (claims.isMemberOf)
#   ScopedAgreementCred      terms doc   -> project + collaboration obligation
#   AgreementCredential      institution -> terms doc   (claims.agreementInfo.documentID)
# together with the requester's own publicKeyCredential.
qualified_chains := {chain |
	some team in team_creds
	some ownership in ownership_creds
	ownership.subject == team.claims.MemberOfTeamOf
	some affiliation in affiliation_creds
	affiliation.subject == team.claims.MemberOfTeamOf
	some scoped in scoped_for_collaboration
	scoped.claims.agreementInfo.scope.project == ownership.claims.Owns
	some agreement in agreement_creds
	agreement.subject == affiliation.claims.isMemberOf
	agreement.claims.agreementInfo.documentID == scoped.subject
	some pubkey in public_key_creds
	pubkey.subject == team.subject
	chain := {
		"subject": team.subject,
		"indices": [team.index, ownership.index, affiliation.index, scoped.index, agreement.index, pubkey.index],
	}
}

qualified_subjects := {chain.subject | some chain in qualified_chains}

# ---- decision -------------------------------------------------------------
default decision := false

decision if count(qualified_subjects) > 0

# ---- verification tasks ---------------------------------------------------
# Flag every credential a qualifying chain relies on for the contract to verify
# by global index.
flagged_indices := {idx |
	some chain in qualified_chains
	some idx in chain.indices
}

verification_tasks := [{"index": idx} | some idx in flagged_indices]

# ---- operation ------------------------------------------------------------
# Name the "do_download" guardian operation and carry the channel key (the public
# key of the qualified requester's publicKeyCredential) as its parameters. Defaults
# keep the result well-formed on deny.
channel_keys := [pubkey.claims.key |
	some pubkey in public_key_creds
	pubkey.subject in qualified_subjects
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
