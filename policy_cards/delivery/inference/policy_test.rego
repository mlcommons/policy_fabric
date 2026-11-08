package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

digest(value) := testlib.credential("ScriptHashCredential", testlib.script, {"scriptHash": value})

test_requirements if {
	subpolicy.requirements == {"Script": ["ScriptHashCredential"]}
}

test_runs_the_digest_of_the_script_being_sent if {
	held := [digest("sha256:old"), digest("sha256:new")]
	r := subpolicy.result with input as testlib.inference_input([], held, {}, {"script_digest": "sha256:new"})
	r.decision
	r.credential == {
		"subject": testlib.script,
		"claims": {"name": "do_inference", "parameters": {"script_digest": "sha256:new"}},
	}
	r.verification_tasks == [{"index": 1}]
}

test_denies_a_script_whose_digest_was_never_approved if {
	held := [digest("sha256:abc")]
	r := subpolicy.result with input as testlib.inference_input([], held, {}, {"script_digest": "sha256:tampered"})
	not r.decision
	not r.credential
}

test_denies_a_request_that_names_no_digest if {
	held := [digest("sha256:abc")]
	not subpolicy.result.decision with input as testlib.inference_input([], held, {}, {})
}

test_denies_a_digest_of_another_script if {
	held := [testlib.about_someone_else(digest("sha256:abc"))]
	not subpolicy.result.decision with input as testlib.inference_input([], held, {}, {"script_digest": "sha256:abc"})
}

test_ignores_an_untrusted_digest if {
	held := [testlib.untrusted(digest("sha256:abc"))]
	not subpolicy.result.decision with input as testlib.inference_input([], held, {}, {"script_digest": "sha256:abc"})
}
