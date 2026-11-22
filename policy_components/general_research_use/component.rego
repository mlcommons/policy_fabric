package pf.components.general_research_use

import rego.v1

# GeneralResearchUse, the card component of General Research Use (DUO_0000042): the
# requester accepted the terms document the owner requires.
#   agreement  AgreementCredential  about the requester, agreementInfo.documentID
# -> Decision about the requester.
interface := {
	"output": "Decision",
	"inputs": {"agreement": {"type": "AgreementCredential", "role": "User"}},
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
}

output := {"allow": count(subjects) > 0, "parameters": {"subject": sort(subjects)}}
