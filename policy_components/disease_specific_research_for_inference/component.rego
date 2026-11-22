package pf.components.disease_specific_research_for_inference

import rego.v1

# DiseaseSpecificResearchForInference, the card component of Disease Specific Research for
# inference (DUO_0000007): the script declares a use for a disease the owner allows.
#   intendedDataUse  IntendedDataUseCredential  about the script, useOnlyFor.diseases
# -> Decision about the script.
interface := {
	"output": "Decision",
	"inputs": {"intendedDataUse": {"type": "IntendedDataUseCredential", "role": "Script"}},
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
subjects contains use.subject if {
	some use in input.inputs.intendedDataUse
	allowed_disease(use)
}

output := {"allow": count(subjects) > 0, "parameters": {"subject": sort(subjects)}}

allowed_disease(use) if {
	some disease in use.claims.useOnlyFor.diseases
	disease in input.policy_data.allowedDiseases
}
