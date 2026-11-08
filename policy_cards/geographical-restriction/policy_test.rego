package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

location(country) := testlib.credential("LocationCredential", testlib.requester, {"locatedAt": {
	"street": "1 Main",
	"zipCode": "00000",
	"state": "MA",
	"country": country,
}})

data_ := {"allowedCountries": ["US", "CA"]}

test_requirements if {
	subpolicy.requirements == {"User": ["LocationCredential"]}
}

test_allows_an_allowed_country if {
	r := subpolicy.result with input as testlib.requester_input([location("US")], data_, {})
	r.decision
	r.verification_tasks == [{"index": 0}]
	r.vc_supplied_verification_tasks == []
	not "credential" in object.keys(r)
}

test_denies_another_country if {
	not subpolicy.result.decision with input as testlib.requester_input([location("FR")], data_, {})
}

test_denies_a_location_of_someone_else if {
	c := testlib.about_someone_else(location("US"))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, {})
}

test_ignores_an_untrusted_location if {
	c := testlib.untrusted(location("US"))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, {})
}

test_flags_only_the_trusted_copy if {
	held := [testlib.untrusted(location("US")), location("US")]
	r := subpolicy.result with input as testlib.requester_input(held, data_, {})
	r.decision
	r.verification_tasks == [{"index": 1}]
}

test_denies_without_allowed_countries if {
	not subpolicy.result.decision with input as testlib.requester_input([location("US")], {}, {})
}
