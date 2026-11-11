package pf.components.institution_specific_restriction_for_inference

import rego.v1

# InstitutionSpecificRestrictionForInference, the card component of Institution Specific
# Restriction for inference (DUO_0000028): a member of an allowed institution owns the script.
# The ownership is signed by the member's own wallet, so it is checked against the key the
# wallet's verifying key credential attests, not against an issuer.
#   affiliation         AffiliationCredential         about the requester, isMemberOf
#   walletVerifyingKey  WalletVerifyingKeyCredential  about the requester, verifying_key
#   scriptOwnership     ScriptOwnershipCredential     about the script, ownedBy, signed by the requester
#   scriptHash          ScriptHashCredential          about the script, scriptHash
# -> InferenceGrantCredential about the script, {script_digest}.
interface := {
	"output": "InferenceGrantCredential",
	"inputs": {
		"affiliation": {"type": "AffiliationCredential", "role": "User"},
		"walletVerifyingKey": {"type": "WalletVerifyingKeyCredential", "role": "User"},
		"scriptOwnership": {"type": "ScriptOwnershipCredential", "role": "Script", "supplied_key": true},
		"scriptHash": {"type": "ScriptHashCredential", "role": "Script"},
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

output := [grant |
	some affiliation in input.inputs.affiliation
	affiliation.claims.isMemberOf in input.policy_data.allowedInstitutions
	some wallet_key in input.inputs.walletVerifyingKey
	wallet_key.subject == affiliation.subject
	some ownership in input.inputs.scriptOwnership
	ownership.issuer == affiliation.subject
	ownership.claims.ownedBy == affiliation.subject
	some hash in input.inputs.scriptHash
	hash.subject == ownership.subject
	grant := {
		"type": "InferenceGrantCredential",
		"subject": hash.subject,
		"claims": {"script_digest": hash.claims.scriptHash},
		"evidence": evidence([affiliation, wallet_key, ownership, hash]),
		"key_checks": [{"index": ownership.evidence[0], "key": wallet_key.claims.verifying_key, "key_type": "ec"}],
	}
]

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
