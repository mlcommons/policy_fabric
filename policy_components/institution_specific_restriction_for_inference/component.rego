package pf.components.institution_specific_restriction_for_inference

import rego.v1

# InstitutionSpecificRestrictionForInference, the card component of Institution Specific
# Restriction for inference (DUO_0000028): a member of an allowed institution owns the script.
# The ownership is signed by the member's own wallet, so it is checked against the key the
# wallet's verifying key credential attests, not against an issuer.
#   affiliation         AffiliationCredential         about the requester, isMemberOf
#   walletVerifyingKey  WalletVerifyingKeyCredential  about the requester, verifying_key
#   scriptOwnership     ScriptOwnershipCredential     about the script, ownedBy, signed by the requester
# -> Decision about the script.
interface := {
	"output": "Decision",
	"inputs": {
		"affiliation": {"type": "AffiliationCredential", "role": "User"},
		"walletVerifyingKey": {"type": "WalletVerifyingKeyCredential", "role": "User"},
		"scriptOwnership": {"type": "ScriptOwnershipCredential", "role": "Script", "supplied_key": true},
	},
	"policy_data_schema": {
		"type": "object",
		"properties": {"allowedInstitutions": {
			"type": "array",
			"items": {"type": "string"},
			"description": "Institutions whose members may run their scripts.",
		}},
		"required": ["allowedInstitutions"],
	},
}

# for whom the condition holds, and the key check of each script ownership that makes it hold
holds contains {"subject": ownership.subject, "check": {"index": ownership.evidence[0], "key": wallet_key.claims.verifying_key, "key_type": "ec"}} if {
	some affiliation in input.inputs.affiliation
	affiliation.claims.isMemberOf in input.policy_data.allowedInstitutions
	some wallet_key in input.inputs.walletVerifyingKey
	wallet_key.subject == affiliation.subject
	some ownership in input.inputs.scriptOwnership
	ownership.issuer == affiliation.subject
	ownership.claims.ownedBy == affiliation.subject
}

subjects := {h.subject | some h in holds}

output := {
	"allow": count(subjects) > 0,
	"parameters": {"subject": sort(subjects)},
	"key_checks": sort({h.check | some h in holds}),
}
