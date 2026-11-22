package pf.components.geographical_restriction_test

import rego.v1

import data.pf.components.geographical_restriction

location := {"type": "LocationCredential", "issuer": "did:example:loc-authority", "subject": "did:example:user",
	"claims": {"locatedAt": {"street": "1 Main", "zipCode": "00000", "state": "MA", "country": "US"}}, "evidence": [0]}

condition(locations) := out if {
	out := geographical_restriction.output with input as {
		"inputs": {"location": locations}, "policy_data": {"allowedCountries": ["US", "CA"]}, "request": {},
	}
}

# the component's decision when its condition holds for one subject, and when it holds for none
allowed(subject) := {"allow": true, "parameters": {"subject": [subject]}}

denied := {"allow": false, "parameters": {"subject": []}}

test_a_country_the_owner_allows if {
	condition([location]) == allowed("did:example:user")
}

test_a_country_the_owner_does_not_allow if {
	condition([object.union(location, {"claims": {"locatedAt": {"country": "FR"}}})]) == denied
}
