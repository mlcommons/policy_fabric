package pf.components.disease_specific_research_for_inference

import rego.v1

# DiseaseSpecificResearchForInference, the card component of Disease Specific Research for
# inference (DUO_0000007): the script declares a use for a disease the owner allows.
#   intendedDataUse  IntendedDataUseCredential  about the script, useOnlyFor.diseases
# -> DataUseConditionCredential about the script.
interface := {
	"output": "DataUseConditionCredential",
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

output := [condition |
	some use in input.inputs.intendedDataUse
	allowed_disease(use)
	condition := {
		"type": "DataUseConditionCredential",
		"subject": use.subject,
		"claims": {},
		"evidence": evidence([use]),
	}
]

allowed_disease(use) if {
	some disease in use.claims.useOnlyFor.diseases
	disease in input.policy_data.allowedDiseases
}

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
