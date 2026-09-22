#!/usr/bin/env bash
# Compose FL-IS and FL-DS exactly the way rego_policy_agent does: evaluate each
# subpolicy in its own engine, then merge with the contract's combinators
# (extracted verbatim from rego-contract/src/rego/rego_combinators.h).
set -uo pipefail

CARDS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPA="${OPA:-$(command -v opa || true)}"
if [[ -z "${OPA}" ]]; then
    echo "error: opa binary not found; set OPA=/path/to/opa" >&2
    exit 1
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

IS="$CARDS/inference-institution-specific-restriction/policy.rego"
DS="$CARDS/inference-disease-specific-research/policy.rego"

cat > "$WORK/requirements_combinator.rego" <<'REGO'
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
REGO

cat > "$WORK/results_combinator.rego" <<'REGO'
package combine

import rego.v1

default decision := false
decision if {
    every o in input.subpolicy_outputs {
        o.decision == true
    }
}

task_set := {task |
    some o in input.subpolicy_outputs
    some task in object.get(o, "verification_tasks", [])
}

verification_tasks := [task | some task in task_set]

vc_supplied_task_set := {task |
    some o in input.subpolicy_outputs
    some task in object.get(o, "vc_supplied_verification_tasks", [])
}

vc_supplied_verification_tasks := [task | some task in vc_supplied_task_set]

operation := object.union_n([op |
    some o in input.subpolicy_outputs
    op := object.get(o, "operation", {})
])

result := {
    "decision": decision,
    "verification_tasks": verification_tasks,
    "vc_supplied_verification_tasks": vc_supplied_verification_tasks,
    "operation": operation,
}
REGO

# The presentation a requester would build for the two policies together: one VP
# per role, indices global across both roles.
cat > "$WORK/input.json" <<'JSON'
{
  "policy_data": {
    "allowedInstitutions": ["did:example:university"],
    "allowedDiseases": ["MONDO:0005148"]
  },
  "presentations": {
    "User": [
      {"type": "AffiliationCredential", "issuer": "did:example:university",
       "subject": "did:pdo:user-wallet",
       "claims": {"isMemberOf": "did:example:university", "typeOfMembership": "student"},
       "index": 0},
      {"type": "publicKeyCredential", "issuer": "did:example:key-authority",
       "subject": "did:pdo:user-wallet", "claims": {"key": "CHANNELKEY"}, "index": 1},
      {"type": "WalletVerifyingKeyCredential", "issuer": "did:example:wallet-key-authority",
       "subject": "did:pdo:user-wallet", "claims": {"verifying_key": "WALLETPEM"}, "index": 2}
    ],
    "Script": [
      {"type": "ScriptOwnershipCredential", "issuer": "did:pdo:user-wallet",
       "subject": "did:pdo:script-asset", "claims": {"ownedBy": "did:pdo:user-wallet"},
       "index": 3},
      {"type": "ScriptHashCredential", "issuer": "did:example:script-authority",
       "subject": "did:pdo:script-asset", "claims": {"scriptHash": "sha256:abc"},
       "index": 4},
      {"type": "IntendedDataUseCredential", "issuer": "did:example:dac",
       "subject": "did:pdo:script-asset",
       "claims": {"useOnlyFor": {"purposes": ["research"], "diseases": ["MONDO:0005148"]}},
       "index": 5}
    ]
  }
}
JSON

status=0
check() {  # check <label> <actual> <expected>
    if [ "$2" == "$3" ]; then
        echo "PASS  $1"
    else
        echo "FAIL  $1"
        echo "        expected: $3"
        echo "        actual:   $2"
        status=1
    fi
}

# ---- requirements: what the contract stores at set_rego_policy time -----------
is_req=$($OPA eval -f raw -d "$IS" 'data.subpolicy.requirements')
ds_req=$($OPA eval -f raw -d "$DS" 'data.subpolicy.requirements')
echo "{\"subpolicy_requirements\": [$is_req, $ds_req]}" > "$WORK/req_input.json"
merged_req=$($OPA eval -f raw -d "$WORK/requirements_combinator.rego" -i "$WORK/req_input.json" 'data.combine.result')

roles=$(echo "$merged_req" | python3 -c 'import json,sys; print(",".join(sorted(json.load(sys.stdin)["roles"])))')
check "merged roles are User and Script" "$roles" "Script,User"

user_types=$(echo "$merged_req" | python3 -c 'import json,sys; print(",".join(sorted(json.load(sys.stdin)["requirements"]["User"])))')
check "merged User types come from the one subpolicy that uses that role" "$user_types" \
    "AffiliationCredential,WalletVerifyingKeyCredential,publicKeyCredential"

script_types=$(echo "$merged_req" | python3 -c 'import json,sys; print(",".join(sorted(json.load(sys.stdin)["requirements"]["Script"])))')
check "merged Script types union both subpolicies" "$script_types" \
    "IntendedDataUseCredential,ScriptHashCredential,ScriptOwnershipCredential"

# ---- results: what the contract merges at issue time -------------------------
is_res=$($OPA eval -f raw -d "$IS" -i "$WORK/input.json" 'data.subpolicy.result')
ds_res=$($OPA eval -f raw -d "$DS" -i "$WORK/input.json" 'data.subpolicy.result')
echo "{\"subpolicy_outputs\": [$is_res, $ds_res]}" > "$WORK/res_input.json"
merged=$($OPA eval -f raw -d "$WORK/results_combinator.rego" -i "$WORK/res_input.json" 'data.combine.result')

decision=$(echo "$merged" | python3 -c 'import json,sys; print(json.load(sys.stdin)["decision"])')
check "combined decision allows" "$decision" "True"

op=$(echo "$merged" | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["operation"], sort_keys=True))')
check "operations deep-merge into one do_inference" "$op" \
    '{"name": "do_inference", "parameters": {"channel_key": "CHANNELKEY", "script_digest": "sha256:abc"}}'

# The six presented credentials must each be verified exactly once, by whichever
# path fits: five against their registered issuer, the self-issued ownership
# credential against the wallet key. Indices are deduplicated across subpolicies --
# the script hash is flagged by both and must appear once.
issuer_idx=$(echo "$merged" | python3 -c 'import json,sys; print(",".join(str(t["index"]) for t in sorted(json.load(sys.stdin)["verification_tasks"], key=lambda t: t["index"])))')
check "issuer-verified credentials, deduplicated" "$issuer_idx" "0,1,2,4,5"

covered=$(echo "$merged" | python3 -c '
import json,sys
m = json.load(sys.stdin)
idx = [t["index"] for t in m["verification_tasks"]] + [t["index"] for t in m["vc_supplied_verification_tasks"]]
print("dup" if len(idx) != len(set(idx)) else ",".join(map(str, sorted(idx))))')
check "every presented credential verified exactly once" "$covered" "0,1,2,3,4,5"

supplied=$(echo "$merged" | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["vc_supplied_verification_tasks"], sort_keys=True))')
check "ownership still verified against the wallet key" "$supplied" \
    '[{"index": 3, "key": "WALLETPEM", "key_type": "ec"}]'

# ---- one subpolicy denying denies the whole request --------------------------
python3 - "$WORK/input.json" "$WORK/bad.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
data["policy_data"]["allowedDiseases"] = ["MONDO:9999999"]
json.dump(data, open(sys.argv[2], "w"))
PY
is_bad=$($OPA eval -f raw -d "$IS" -i "$WORK/bad.json" 'data.subpolicy.result')
ds_bad=$($OPA eval -f raw -d "$DS" -i "$WORK/bad.json" 'data.subpolicy.result')
echo "{\"subpolicy_outputs\": [$is_bad, $ds_bad]}" > "$WORK/bad_res.json"
bad_decision=$($OPA eval -f raw -d "$WORK/results_combinator.rego" -i "$WORK/bad_res.json" 'data.combine.result' \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["decision"])')
check "out-of-scope disease denies even though FL-IS allowed" "$bad_decision" "False"

exit "$status"
