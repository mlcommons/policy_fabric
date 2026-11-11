package pf.components.not_for_profit_organisation_use_only

import rego.v1

# NotForProfitOrganisationUseOnly, the card component of Not-for-Profit Organisation Use
# Only (DUO_0000045): the requester acts for an organisation of a legal form the owner
# accepts as not-for-profit.
#   legalDesignation  LegalDesignationCredential  about the requester, hasLegalForm
# -> DownloadGrantCredential about the requester.
interface := {
	"output": "DownloadGrantCredential",
	"inputs": {"legalDesignation": {"type": "LegalDesignationCredential", "role": "User"}},
	"policy_data_schema": {
		"type": "object",
		"properties": {"nonprofitLegalForms": {
			"type": "array",
			"items": {"type": "string"},
			"description": "ISO 20275 ELF codes the owner accepts as not-for-profit.",
		}},
		"required": ["nonprofitLegalForms"],
	},
}

output := [grant |
	some designation in input.inputs.legalDesignation
	designation.claims.hasLegalForm in input.policy_data.nonprofitLegalForms
	grant := {
		"type": "DownloadGrantCredential",
		"subject": designation.subject,
		"claims": {},
		"evidence": evidence([designation]),
	}
]

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
