package pf.components.institution_specific_restriction

import rego.v1

# InstitutionSpecificRestriction, the card component of Institution Specific Restriction
# (DUO_0000028): the requester is a member of an institution the owner allows.
#   affiliation  AffiliationCredential  about the requester, isMemberOf
# -> Decision about the requester.
interface := {
	"output": "Decision",
	"inputs": {"affiliation": {"type": "AffiliationCredential", "role": "User"}},
	"policy_data_schema": {
		"type": "object",
		"properties": {"allowedInstitutions": {
			"type": "array",
			"items": {"type": "string"},
			"description": "Institution DIDs the owner allows.",
		}},
		"required": ["allowedInstitutions"],
	},
}

# for whom the condition holds
subjects contains affiliation.subject if {
	some affiliation in input.inputs.affiliation
	affiliation.claims.isMemberOf in input.policy_data.allowedInstitutions
}

output := {"allow": count(subjects) > 0, "parameters": {"subject": sort(subjects)}}
