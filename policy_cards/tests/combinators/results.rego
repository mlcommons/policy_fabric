# A copy of REGO_RESULTS_COMBINATOR in pdo-contracts rego-contract/src/rego/rego_combinators.h,
# so the combination tests merge module results exactly as the policy agent does.
# Keep the two identical.

package combine

import rego.v1

# every subpolicy allowed
all_allowed if {
    every o in input.subpolicy_outputs {
        o.decision == true
    }
}

# the credentials the subpolicies describe
credentials := [o.credential | some o in input.subpolicy_outputs; o.credential]

# the policy allows only if every subpolicy allowed and exactly one described
# the credential to issue
default decision := false
decision if {
    all_allowed
    count(credentials) == 1
}

reason := "a module denied the request" if {
    not all_allowed
} else := "no module describes the credential" if {
    count(credentials) == 0
} else := "more than one module describes the credential" if {
    count(credentials) > 1
}

# every distinct trusted-issuer task any subpolicy flagged. The whole task is
# kept; sets deduplicate identical tasks structurally.
task_set := {task |
    some o in input.subpolicy_outputs
    some task in o.verification_tasks
}

verification_tasks := [task | some task in task_set]

# every distinct supplied-key task any subpolicy flagged (each carries its own
# key and key_type).
vc_supplied_task_set := {task |
    some o in input.subpolicy_outputs
    some task in o.vc_supplied_verification_tasks
}

vc_supplied_verification_tasks := [task | some task in vc_supplied_task_set]

result := {
    "decision": true,
    "verification_tasks": verification_tasks,
    "vc_supplied_verification_tasks": vc_supplied_verification_tasks,
    "credential": credentials[0],
} if decision

result := {"decision": false, "reason": reason} if not decision
