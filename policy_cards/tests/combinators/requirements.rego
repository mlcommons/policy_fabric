# A copy of REGO_REQUIREMENTS_COMBINATOR in pdo-contracts rego-contract/src/rego/rego_combinators.h,
# so the combination tests merge module results exactly as the policy agent does.
# Keep the two identical.

package combine

import rego.v1

all_roles contains role if {
    some req in input.subpolicy_requirements
    some role in object.keys(req)
}

merged[role] := types if {
    some role in all_roles
    types := {t |
        some req in input.subpolicy_requirements
        some t in object.get(req, role, [])
    }
}

result := {
    "requirements": merged,
    "roles": [role | some role in all_roles],
}
