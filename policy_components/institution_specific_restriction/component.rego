package pf.components.institution_specific_restriction

import rego.v1

# InstitutionSpecificRestriction, the card component of Institution Specific Restriction
# (DUO_0000028): the requester is a member of an institution the owner allows.
#   affiliation  AffiliationCredential  about the requester, isMemberOf
# -> DataUseConditionCredential about the requester.
interface := {
	"output": "DataUseConditionCredential",
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

output := [condition |
	some affiliation in input.inputs.affiliation
	affiliation.claims.isMemberOf in input.policy_data.allowedInstitutions
	condition := {
		"type": "DataUseConditionCredential",
		"subject": affiliation.subject,
		"claims": {},
		"evidence": evidence([affiliation]),
	}
]

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
