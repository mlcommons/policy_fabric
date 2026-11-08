package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

declared_use(diseases) := testlib.credential(
	"IntendedDataUseCredential",
	testlib.script,
	{"useOnlyFor": {"purposes": ["research"], "diseases": diseases}},
)

data_ := {"allowedDiseases": ["MONDO:0005148"]}

test_requirements_are_about_the_script_only if {
	subpolicy.requirements == {"Script": ["IntendedDataUseCredential"]}
}

test_allows_a_script_declaring_an_allowed_disease if {
	r := subpolicy.result with input as testlib.inference_input([], [declared_use(["MONDO:0005148"])], data_, {})
	r.decision
	r.verification_tasks == [{"index": 0}]
	not "credential" in object.keys(r)
}

test_denies_a_script_declaring_another_disease if {
	held := [declared_use(["MONDO:0000001"])]
	not subpolicy.result.decision with input as testlib.inference_input([], held, data_, {})
}

test_denies_a_declaration_about_another_script if {
	held := [testlib.about_someone_else(declared_use(["MONDO:0005148"]))]
	not subpolicy.result.decision with input as testlib.inference_input([], held, data_, {})
}

test_ignores_an_untrusted_declaration if {
	held := [testlib.untrusted(declared_use(["MONDO:0005148"]))]
	not subpolicy.result.decision with input as testlib.inference_input([], held, data_, {})
}
