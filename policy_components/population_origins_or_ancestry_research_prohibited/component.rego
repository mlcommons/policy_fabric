package pf.components.population_origins_or_ancestry_research_prohibited

import rego.v1

# PopulationOriginsOrAncestryResearchProhibited, the card component of Population Origins or
# Ancestry Research Prohibited (DUO_0000044): the requester's project intends to use the data
# for no purpose the owner prohibits, such as population origins or ancestry research, and the
# requester accepted the terms.
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
		"properties": {"prohibitedPurposes": {
			"type": "array",
			"items": {"type": "string"},
			"description": "Purpose terms the owner prohibits, such as population origins or ancestry research.",
		}},
		"required": ["prohibitedPurposes"],
	},
}

output := [condition |
	some membership in input.inputs.projectMembership
	some use in input.inputs.intendedDataUse
	use.subject == membership.claims.project
	no_prohibited_purpose(use)
	some agreement in input.inputs.agreement
	agreement.subject == membership.subject
	condition := {
		"type": "DataUseConditionCredential",
		"subject": membership.subject,
		"claims": {},
		"evidence": evidence([membership, use, agreement]),
	}
]

# The list is bound outside the "not", so that policy data without it fails the check
# instead of prohibiting nothing.
no_prohibited_purpose(use) if {
	prohibited := input.policy_data.prohibitedPurposes
	every purpose in use.claims.useOnlyFor.purposes {
		not purpose in prohibited
	}
}

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
