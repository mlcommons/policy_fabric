# DUO_0000027 — PS (Project Specific Restriction)
#
# Allow when a project's IntendedDataUseCredential is for a project on the data
# owner's approved list, and the requester is bound to that project through the
# team/ownership chain: a TeamCredential places the requester on a PI's team, and a
# ProjectOwnershipCredential shows that PI owns the project the IDU is about. The
# requester must also present an AgreementCredential (accepted terms) and a
# publicKeyCredential whose claim is the requester's channel public key. The approved
# project identifiers are configured by the data owner in policy_data. That key is
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
#   input.policy_data         : { approvedProjects: [..] }

package subpolicy

import rego.v1

# ---- requirements ---------------------------------------------------------
# The roles/credential-types this subpolicy needs. Evaluated by set_rego_policy
# with NO input, so it must be static.
requirements := {"User": [
	"IntendedDataUseCredential",
	"ProjectOwnershipCredential",
	"TeamCredential",
	"AgreementCredential",
	"publicKeyCredential",
]}

# ---- standardized credential views ----------------------------------------
idu_creds := [c |
	some c in input.presentations.User
	c.type == "IntendedDataUseCredential"
]

ownership_creds := [c |
	some c in input.presentations.User
	c.type == "ProjectOwnershipCredential"
]

team_creds := [c |
	some c in input.presentations.User
	c.type == "TeamCredential"
]

agreement_creds := [c |
	some c in input.presentations.User
	c.type == "AgreementCredential"
]

public_key_creds := [c |
	some c in input.presentations.User
	c.type == "publicKeyCredential"
]

# intended-data-use credentials for a project on the data owner's approved list
matching_idu := [c |
	some c in idu_creds
	c.subject in input.policy_data.approvedProjects
]

# ---- credential chain ------------------------------------------------------
# A qualifying chain binds a requester to an in-scope project:
#   TeamCredential        requester -> PI            (claims.MemberOfTeamOf)
#   ProjectOwnershipCred  PI        -> project       (claims.Owns)
#   IntendedDataUseCred   project   -> disease scope (claims.useOnlyFor.diseases)
# together with the requester's own AgreementCredential and publicKeyCredential.
qualified_chains := {chain |
	some team in team_creds
	some ownership in ownership_creds
	ownership.subject == team.claims.MemberOfTeamOf
	some idu in matching_idu
	idu.subject == ownership.claims.Owns
	some agreement in agreement_creds
	agreement.subject == team.subject
	some pubkey in public_key_creds
	pubkey.subject == team.subject
	chain := {
		"subject": team.subject,
		"indices": [team.index, ownership.index, idu.index, agreement.index, pubkey.index],
	}
}

qualified_subjects := {chain.subject | some chain in qualified_chains}

# ---- decision -------------------------------------------------------------
default decision := false

decision if count(qualified_subjects) > 0

# ---- verification tasks ---------------------------------------------------
# Flag every credential a qualifying chain relies on for the contract to verify
# by global index (the team, ownership, IDU, agreement and public key).
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
