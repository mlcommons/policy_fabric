# FL-IS — Institution Specific Restriction, for inference
#
# The inference counterpart of DUO_0000028 (IS). It keeps that rule -- the
# requester must be a member of an allowed institution -- and adds the question an
# inference request raises that a download does not: *whose code is about to run on
# the data?*
#
# The requester presents an AffiliationCredential naming an allowed institution, a
# publicKeyCredential carrying their channel public key, and a
# WalletVerifyingKeyCredential binding their wallet to the verifying key it is
# registered with. The script presents a ScriptHashCredential stating its content
# digest and a ScriptOwnershipCredential in which a wallet claims the script as its
# own. That ownership credential is signed by the requester's own wallet, so it is
# checked against the verifying key carried by the WalletVerifyingKeyCredential
# rather than against a registered issuer -- which is what ties the script to the
# same person the affiliation is about.
#
# Everything must line up on one wallet and one script: the affiliation, the channel
# key and the wallet key are about the same wallet; that wallet is the one claiming
# the script; and the hash credential is about that same script. The digest travels
# to the guardian in the "do_inference" operation so the code that actually runs can
# be measured against the code that was approved, and the channel key travels with it
# so results reach the requester who was checked.
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
# with NO input, so it must be static. Evidence about the requester and evidence
# about the code are separate roles because they are about different subjects and
# come from different wallets.
requirements := {
	"User": [
		"AffiliationCredential",
		"publicKeyCredential",
		"WalletVerifyingKeyCredential",
	],
	"Script": [
		"ScriptOwnershipCredential",
		"ScriptHashCredential",
	],
}

# ---- standardized credential views ----------------------------------------
affiliation_creds := [c |
	some c in input.presentations.User
	c.type == "AffiliationCredential"
]

public_key_creds := [c |
	some c in input.presentations.User
	c.type == "publicKeyCredential"
]

wallet_key_creds := [c |
	some c in input.presentations.User
	c.type == "WalletVerifyingKeyCredential"
]

ownership_creds := [c |
	some c in input.presentations.Script
	c.type == "ScriptOwnershipCredential"
]

script_hash_creds := [c |
	some c in input.presentations.Script
	c.type == "ScriptHashCredential"
]

# affiliation credentials naming an allowed institution
matching_affiliation := [c |
	some c in affiliation_creds
	c.claims.isMemberOf in input.policy_data.allowedInstitutions
]

# ---- credential chain ------------------------------------------------------
# A qualifying chain binds one wallet to one script:
#   AffiliationCredential         wallet -> institution   (claims.isMemberOf)
#   publicKeyCredential           wallet -> channel key   (claims.key)
#   WalletVerifyingKeyCredential  wallet -> verifying key (claims.verifying_key)
#   ScriptOwnershipCredential     script -> owning wallet (claims.ownedBy, self-issued)
#   ScriptHashCredential          script -> digest        (claims.scriptHash)
#
# The ownership credential is required to be issued by the very wallet it names as
# owner, and that wallet must be the one the other three credentials are about; on
# its own a self-issued claim carries no weight, which is why its signature is
# checked against the wallet's attested verifying key below.
qualified_chains := {chain |
	some affiliation in matching_affiliation
	some pubkey in public_key_creds
	pubkey.subject == affiliation.subject
	some wallet_key in wallet_key_creds
	wallet_key.subject == affiliation.subject
	some ownership in ownership_creds
	ownership.issuer == affiliation.subject
	ownership.claims.ownedBy == affiliation.subject
	some script_hash in script_hash_creds
	script_hash.subject == ownership.subject
	chain := {
		"subject": affiliation.subject,
		"script": ownership.subject,
		"channel_key": pubkey.claims.key,
		"script_hash": script_hash.claims.scriptHash,
		"verifying_key": wallet_key.claims.verifying_key,
		"indices": [
			affiliation.index, pubkey.index,
			wallet_key.index, script_hash.index,
		],
		"ownership_index": ownership.index,
	}
}

qualified_subjects := {chain.subject | some chain in qualified_chains}

# ---- decision -------------------------------------------------------------
default decision := false

decision if count(qualified_chains) > 0

# ---- verification tasks ---------------------------------------------------
# Credentials that come from a registered issuer are flagged by index for the
# contract to verify against that issuer.
flagged_indices := {idx |
	some chain in qualified_chains
	some idx in chain.indices
}

verification_tasks := [{"index": idx} | some idx in flagged_indices]

# The ownership credential has no registered issuer -- it was signed by the
# requester's wallet -- so it is flagged for verification against the verifying key
# the WalletVerifyingKeyCredential carries. PDO credentials are signed with ECDSA,
# hence "ec".
supplied_task_set := {task |
	some chain in qualified_chains
	task := {
		"index": chain.ownership_index,
		"key": chain.verifying_key,
		"key_type": "ec",
	}
}

vc_supplied_verification_tasks := [task | some task in supplied_task_set]

# ---- operation ------------------------------------------------------------
# Name the "do_inference" guardian operation and carry both the channel key and the
# approved script digest as its parameters. Defaults keep the result well-formed on
# deny.
channel_keys := [chain.channel_key | some chain in qualified_chains]

default channel_key := ""

channel_key := channel_keys[0] if count(channel_keys) > 0

script_digests := [chain.script_hash | some chain in qualified_chains]

default script_digest := ""

script_digest := script_digests[0] if count(script_digests) > 0

operation := {"name": "do_inference", "parameters": {
	"channel_key": channel_key,
	"script_digest": script_digest,
}}

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": vc_supplied_verification_tasks,
	"operation": operation,
}
