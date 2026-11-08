package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

session_key(key) := testlib.credential("publicKeyCredential", testlib.requester, {"key": key})

test_requirements if {
	subpolicy.requirements == {"User": ["publicKeyCredential"]}
}

test_delivers_to_the_requested_key if {
	held := [session_key("KEY-A"), session_key("KEY-B")]
	r := subpolicy.result with input as testlib.requester_input(held, {}, {"channel_key": "KEY-B"})
	r.decision
	r.credential == {
		"subject": testlib.requester,
		"claims": {"name": "do_download", "parameters": {"channel_key": "KEY-B"}},
	}
	r.verification_tasks == [{"index": 1}]
}

test_denies_a_requested_key_the_requester_does_not_hold if {
	held := [session_key("KEY-A")]
	r := subpolicy.result with input as testlib.requester_input(held, {}, {"channel_key": "KEY-B"})
	not r.decision
	not r.credential
}

test_denies_a_request_that_names_no_key if {
	held := [session_key("KEY-A")]
	not subpolicy.result.decision with input as testlib.requester_input(held, {}, {})
}

test_denies_a_key_bound_to_someone_else if {
	held := [testlib.about_someone_else(session_key("KEY-A"))]
	not subpolicy.result.decision with input as testlib.requester_input(held, {}, {"channel_key": "KEY-A"})
}

test_ignores_an_untrusted_key if {
	held := [testlib.untrusted(session_key("KEY-A"))]
	not subpolicy.result.decision with input as testlib.requester_input(held, {}, {"channel_key": "KEY-A"})
}
