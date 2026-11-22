package pf.components.allow_if_all_test

import rego.v1

import data.pf.components.allow_if_all

decide(decisions) := out if {
	out := allow_if_all.output with input as {"inputs": {"decisions": decisions}, "policy_data": {}, "request": {}}
}

card := {"allow": true, "parameters": {"subject": ["did:example:user"]}}

key := {"allow": true, "parameters": {"subject": ["did:example:user"], "channel_key": ["KEY"]}}

test_every_decision_allows if {
	decide([card, key]) == {"allow": true, "parameters": {"subject": ["did:example:user"], "channel_key": ["KEY"]}}
}

test_one_decision_is_itself if {
	decide([key]) == key
}

test_a_decision_that_denies if {
	decide([card, {"allow": false, "parameters": {}}]).allow == false
}

test_the_values_are_intersected if {
	two := {"allow": true, "parameters": {"subject": ["did:example:other", "did:example:user"]}}
	decide([two, key]).parameters.subject == ["did:example:user"]
}

test_no_value_in_common_denies if {
	other := {"allow": true, "parameters": {"subject": ["did:example:other"]}}
	decide([card, other]) == {"allow": false, "parameters": {"subject": []}}
}

test_a_parameter_one_decision_does_not_name_is_not_restricted_by_it if {
	keys := {"allow": true, "parameters": {"channel_key": ["KEY", "OTHER"]}}
	decide([card, keys, key]) == {"allow": true, "parameters": {"subject": ["did:example:user"], "channel_key": ["KEY"]}}
}
