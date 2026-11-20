package pf.components.population_origins_or_ancestry_research_only

import rego.v1

# PopulationOriginsOrAncestryResearchOnly, the card component of Population Origins or
# Ancestry Research Only (DUO_0000011): the requester's project intends to use the data for a
# population origins or ancestry purpose the owner allows, and the requester accepted the terms.
#   projectMembership  ProjectMembershipCredential  about the requester, project
#   intendedDataUse    IntendedDataUseCredential    about the project, useOnlyFor.purposes
#   agreement          AgreementCredential          about the requester
# -> DataUseConditionCredential about the requester.
interface := {
	"output": "DataUseConditionCredential",
	"inputs": {
		"projectMembership": {"type": "ProjectMembershipCredential", "role": "User"},
		"intendedDataUse": {"type": "IntendedDataUseCredential", "role": "User"},
		"agreement": {"type": "AgreementCredential", "role": "User"},
	},
	"policy_data_schema": {
		"type": "object",
		"properties": {"allowedPurposes": {
			"type": "array",
			"items": {"type": "string"},
			"description": "Population origins or ancestry purpose terms the owner allows.",
		}},
		"required": ["allowedPurposes"],
	},
}

output := [condition |
	some membership in input.inputs.projectMembership
	some use in input.inputs.intendedDataUse
	use.subject == membership.claims.project
	allowed_purpose(use)
	some agreement in input.inputs.agreement
	agreement.subject == membership.subject
	condition := {
		"type": "DataUseConditionCredential",
		"subject": membership.subject,
		"claims": {},
		"evidence": evidence([membership, use, agreement]),
	}
]

allowed_purpose(use) if {
	some purpose in use.claims.useOnlyFor.purposes
	purpose in input.policy_data.allowedPurposes
}

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
