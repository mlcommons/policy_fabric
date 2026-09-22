# DUO_0000021 — IRB (Ethics Approval Required)
#
# Allow when the project has ethics approval from a committee responsible for the
# requester's institution. The requester is tied to a project and institution
# through a chain: a TeamCredential places them on a PI's team, a
# ProjectOwnershipCredential shows that PI owns a project, and an
# AffiliationCredential shows that PI belongs to an institution. An
# IRBApprovalCredential shows the project is approved by an ethics committee, and an
# EthicsCommitteeAccreditationCredential shows that committee is responsible for the
# PI's institution. The project's IntendedDataUseCredential declares its intended
# use. The requester also presents a publicKeyCredential whose claim is their
# channel public key. That key is returned as the parameters of a "do_download"
# operation so the token can build the guardian capability. The decision is
# structural and needs no owner-configured reference values. Signature verification
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
#   input.policy_data         : { }       (no reference values needed)

package subpolicy

import rego.v1

# ---- requirements ---------------------------------------------------------
# The roles/credential-types this subpolicy needs. Evaluated by set_rego_policy
# with NO input, so it must be static.
requirements := {"User": [
	"IntendedDataUseCredential",
	"IRBApprovalCredential",
	"ProjectOwnershipCredential",
	"EthicsCommitteeAccreditationCredential",
	"AffiliationCredential",
	"TeamCredential",
	"publicKeyCredential",
]}

# ---- standardized credential views ----------------------------------------
idu_creds := [c |
	some c in input.presentations.User
	c.type == "IntendedDataUseCredential"
]

irb_creds := [c |
	some c in input.presentations.User
	c.type == "IRBApprovalCredential"
]

ownership_creds := [c |
	some c in input.presentations.User
	c.type == "ProjectOwnershipCredential"
]

accreditation_creds := [c |
	some c in input.presentations.User
	c.type == "EthicsCommitteeAccreditationCredential"
]

affiliation_creds := [c |
	some c in input.presentations.User
	c.type == "AffiliationCredential"
]

team_creds := [c |
	some c in input.presentations.User
	c.type == "TeamCredential"
]

public_key_creds := [c |
	some c in input.presentations.User
	c.type == "publicKeyCredential"
]

# ---- credential chain ------------------------------------------------------
# A qualifying chain binds a requester to a project whose ethics approval comes
# from a committee responsible for the requester's institution:
#   TeamCredential           requester   -> PI          (claims.MemberOfTeamOf)
#   ProjectOwnershipCred     PI          -> project     (claims.Owns)
#   AffiliationCredential    PI          -> institution (claims.isMemberOf)
#   IRBApprovalCredential    project     -> committee   (claims.isApprovedByEthicsCommittee)
#   EthicsCommitteeAccredit. committee   -> institution (claims.ResponsibleFor)
#   IntendedDataUseCred      project     -> declared intended use
# together with the requester's own publicKeyCredential.
qualified_chains := {chain |
	some team in team_creds
	some ownership in ownership_creds
	ownership.subject == team.claims.MemberOfTeamOf
	some affiliation in affiliation_creds
	affiliation.subject == team.claims.MemberOfTeamOf
	some irb in irb_creds
	irb.subject == ownership.claims.Owns
	some accreditation in accreditation_creds
	accreditation.subject == irb.claims.isApprovedByEthicsCommittee
	accreditation.claims.ResponsibleFor == affiliation.claims.isMemberOf
	some idu in idu_creds
	idu.subject == ownership.claims.Owns
	some pubkey in public_key_creds
	pubkey.subject == team.subject
	chain := {
		"subject": team.subject,
		"indices": [
			team.index, ownership.index, affiliation.index,
			irb.index, accreditation.index, idu.index, pubkey.index,
		],
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
