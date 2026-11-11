package pf.components.not_for_profit_non_commercial_use_only

import rego.v1

# NotForProfitNonCommercialUseOnly, the card component of Not-for-Profit, Non-Commercial Use
# Only (DUO_0000018): the requester's legal form is one the owner treats as not-for-profit,
# and an intended use names no purpose the owner treats as commercial.
#   legalDesignation  LegalDesignationCredential  about the requester, hasLegalForm
#   intendedDataUse   IntendedDataUseCredential   about the project, useOnlyFor.purposes
# -> DownloadGrantCredential about the requester.
interface := {
	"output": "DownloadGrantCredential",
	"inputs": {
		"legalDesignation": {"type": "LegalDesignationCredential", "role": "User"},
		"intendedDataUse": {"type": "IntendedDataUseCredential", "role": "User"},
	},
	"policy_data_schema": {
		"type": "object",
		"properties": {
			"nonprofitLegalForms": {
				"type": "array",
				"items": {"type": "string"},
				"description": "ISO 20275 ELF codes the owner treats as not-for-profit.",
			},
			"prohibitedPurposes": {
				"type": "array",
				"items": {"type": "string"},
				"description": "Purposes that make a use commercial.",
			},
		},
		"required": ["nonprofitLegalForms", "prohibitedPurposes"],
	},
}

output := [grant |
	some designation in input.inputs.legalDesignation
	designation.claims.hasLegalForm in input.policy_data.nonprofitLegalForms
	some use in input.inputs.intendedDataUse
	non_commercial(use.claims.useOnlyFor.purposes, input.policy_data.prohibitedPurposes)
	grant := {
		"type": "DownloadGrantCredential",
		"subject": designation.subject,
		"claims": {},
		"evidence": evidence([designation, use]),
	}
]

# Taken as arguments, a purposes claim or prohibited list that is missing fails the check;
# read inside the negation, it would pass.
non_commercial(purposes, prohibited) if {
	every purpose in purposes {
		not purpose in prohibited
	}
}

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
