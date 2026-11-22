package pf.components.time_limit_on_use

import rego.v1

# TimeLimitOnUse, the card component of Time Limit on Use (DUO_0000025): the requester
# accepted the owner's terms document, and a compute node is attested to shut down no later
# than the owner's deadline.
#   agreement           AgreementCredential           about the requester, agreementInfo.documentID
#   computeEnvironment  ComputeEnvironmentCredential  about a compute node, hasComputeProfile.profile.shutsDownAt
# -> Decision about the requester.
interface := {
	"output": "Decision",
	"inputs": {
		"agreement": {"type": "AgreementCredential", "role": "User"},
		"computeEnvironment": {"type": "ComputeEnvironmentCredential", "role": "User"},
	},
	"policy_data_schema": {
		"type": "object",
		"properties": {
			"requiredDocumentID": {
				"type": "string",
				"description": "DID of the terms document the requester must accept.",
			},
			"notAfter": {
				"type": "string",
				"description": "ISO-8601 UTC datetime by which the compute environment must shut down.",
			},
		},
		"required": ["requiredDocumentID", "notAfter"],
	},
}

# for whom the condition holds
subjects contains agreement.subject if {
	some agreement in input.inputs.agreement
	agreement.claims.agreementInfo.documentID == input.policy_data.requiredDocumentID
	some compute in input.inputs.computeEnvironment

	# ISO-8601 UTC datetimes of one format compare chronologically as strings.
	compute.claims.hasComputeProfile.profile.shutsDownAt <= input.policy_data.notAfter
}

output := {"allow": count(subjects) > 0, "parameters": {"subject": sort(subjects)}}
