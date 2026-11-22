package pf.components.geographical_restriction

import rego.v1

# GeographicalRestriction, the card component of Geographical Restriction (DUO_0000022):
# the requester's organisation is located in a country the owner allows.
#   location  LocationCredential  about the requester, locatedAt.country
# -> Decision about the requester.
interface := {
	"output": "Decision",
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

# for whom the condition holds
subjects contains location.subject if {
	some location in input.inputs.location
	location.claims.locatedAt.country in input.policy_data.allowedCountries
}

output := {"allow": count(subjects) > 0, "parameters": {"subject": sort(subjects)}}
