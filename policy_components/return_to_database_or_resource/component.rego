package pf.components.return_to_database_or_resource

import rego.v1

# ReturnToDatabaseOrResource, the card component of Return to Database or Resource
# (DUO_0000029): the requester accepted the owner's terms document, and a compute node is
# attested to handle results securely.
#   agreement           AgreementCredential           about the requester, agreementInfo.documentID
#   computeEnvironment  ComputeEnvironmentCredential  about a compute node, hasComputeProfile.profile.SecureHandlingOfResults
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
