package pf.components.geographical_restriction_test

import rego.v1

import data.pf.components.geographical_restriction

location := {"type": "LocationCredential", "issuer": "did:example:loc-authority", "subject": "did:example:user",
	"claims": {"locatedAt": {"street": "1 Main", "zipCode": "00000", "state": "MA", "country": "US"}}, "evidence": [0]}

grant(locations) := out if {
	out := geographical_restriction.output with input as {
		"inputs": {"location": locations}, "policy_data": {"allowedCountries": ["US", "CA"]}, "request": {},
	}
}

test_a_country_the_owner_allows if {
	grant([location]) == [{"type": "DownloadGrantCredential", "subject": "did:example:user", "claims": {}, "evidence": [0]}]
}

test_a_country_the_owner_does_not_allow if {
	grant([object.union(location, {"claims": {"locatedAt": {"country": "FR"}}})]) == []
}
