package pf.components.geographical_restriction

import rego.v1

# GeographicalRestriction, the card component of Geographical Restriction (DUO_0000022):
# the requester's organisation is located in a country the owner allows.
#   location  LocationCredential  about the requester, locatedAt.country
# -> DownloadGrantCredential about the requester.
interface := {
	"output": "DownloadGrantCredential",
	"inputs": {"location": {"type": "LocationCredential", "role": "User"}},
	"policy_data_schema": {
		"type": "object",
		"properties": {"allowedCountries": {
			"type": "array",
			"items": {"type": "string"},
			"description": "Countries the owner allows.",
		}},
		"required": ["allowedCountries"],
	},
}

output := [grant |
	some location in input.inputs.location
	location.claims.locatedAt.country in input.policy_data.allowedCountries
	grant := {
		"type": "DownloadGrantCredential",
		"subject": location.subject,
		"claims": {},
		"evidence": evidence([location]),
	}
]

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
