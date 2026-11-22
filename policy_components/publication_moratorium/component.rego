package pf.components.publication_moratorium

import rego.v1

# PublicationMoratorium, the card component of Publication Moratorium (DUO_0000024): the
# requester accepted the terms document the owner requires, and a compute environment
# attests that it handles results securely.
#   agreement           AgreementCredential           about the requester, agreementInfo.documentID
#   computeEnvironment  ComputeEnvironmentCredential  about the compute node, hasComputeProfile.profile.SecureHandlingOfResults
# -> Decision about the requester.
interface := {
	"output": "Decision",
	"inputs": {
		"agreement": {"type": "AgreementCredential", "role": "User"},
		"computeEnvironment": {"type": "ComputeEnvironmentCredential", "role": "User"},
	},
	"policy_data_schema": {
		"type": "object",
		"properties": {"requiredDocumentID": {
			"type": "string",
			"description": "DID of the terms document the requester must accept.",
		}},
		"required": ["requiredDocumentID"],
	},
}

# for whom the condition holds
subjects contains agreement.subject if {
	some agreement in input.inputs.agreement
	agreement.claims.agreementInfo.documentID == input.policy_data.requiredDocumentID
	some compute in input.inputs.computeEnvironment
	compute.claims.hasComputeProfile.profile.SecureHandlingOfResults == true
}

output := {"allow": count(subjects) > 0, "parameters": {"subject": sort(subjects)}}
