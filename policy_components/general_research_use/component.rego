package pf.components.general_research_use

import rego.v1

# GeneralResearchUse, the card component of General Research Use (DUO_0000042): the
# requester accepted the terms document the owner requires.
#   agreement  AgreementCredential  about the requester, agreementInfo.documentID
# -> DownloadGrantCredential about the requester.
interface := {
	"output": "DownloadGrantCredential",
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

output := [grant |
	some agreement in input.inputs.agreement
	agreement.claims.agreementInfo.documentID == input.policy_data.requiredDocumentID
	grant := {
		"type": "DownloadGrantCredential",
		"subject": agreement.subject,
		"claims": {},
		"evidence": evidence([agreement]),
	}
]

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
