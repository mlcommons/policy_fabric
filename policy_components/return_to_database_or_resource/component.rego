package pf.components.return_to_database_or_resource

import rego.v1

# ReturnToDatabaseOrResource, the card component of Return to Database or Resource
# (DUO_0000029): the requester accepted the owner's terms document, and a compute node is
# attested to handle results securely.
#   agreement           AgreementCredential           about the requester, agreementInfo.documentID
#   computeEnvironment  ComputeEnvironmentCredential  about a compute node, hasComputeProfile.profile.SecureHandlingOfResults
# -> DownloadGrantCredential about the requester.
interface := {
	"output": "DownloadGrantCredential",
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

output := [grant |
	some agreement in input.inputs.agreement
	agreement.claims.agreementInfo.documentID == input.policy_data.requiredDocumentID
	some compute in input.inputs.computeEnvironment
	compute.claims.hasComputeProfile.profile.SecureHandlingOfResults == true
	grant := {
		"type": "DownloadGrantCredential",
		"subject": agreement.subject,
		"claims": {},
		"evidence": evidence([agreement, compute]),
	}
]

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
