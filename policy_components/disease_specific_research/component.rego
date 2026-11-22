package pf.components.disease_specific_research

import rego.v1

# DiseaseSpecificResearch, the card component of Disease Specific Research (DUO_0000007):
# the requester's project intends to use the data for a disease the owner allows, and the
# requester accepted the terms.
#   projectMembership  ProjectMembershipCredential  about the requester, project
#   intendedDataUse    IntendedDataUseCredential    about the project, useOnlyFor.diseases
#   agreement          AgreementCredential          about the requester
# -> Decision about the requester.
interface := {
	"output": "Decision",
	"inputs": {
		"projectMembership": {"type": "ProjectMembershipCredential", "role": "User"},
		"intendedDataUse": {"type": "IntendedDataUseCredential", "role": "User"},
		"agreement": {"type": "AgreementCredential", "role": "User"},
	},
	"policy_data_schema": {
		"type": "object",
		"properties": {"allowedDiseases": {
			"type": "array",
			"items": {"type": "string"},
			"description": "MONDO disease codes the owner allows.",
		}},
		"required": ["allowedDiseases"],
	},
}

# for whom the condition holds
subjects contains membership.subject if {
	some membership in input.inputs.projectMembership
	some use in input.inputs.intendedDataUse
	use.subject == membership.claims.project
	allowed_disease(use)
	some agreement in input.inputs.agreement
	agreement.subject == membership.subject
}

output := {"allow": count(subjects) > 0, "parameters": {"subject": sort(subjects)}}

allowed_disease(use) if {
	some disease in use.claims.useOnlyFor.diseases
	disease in input.policy_data.allowedDiseases
}
