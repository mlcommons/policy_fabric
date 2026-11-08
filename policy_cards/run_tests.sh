#!/usr/bin/env bash
# Run every policy and delivery card's Rego unit tests, then the checks across
# cards: manifests against their rules, facts against the credential vocabulary,
# parameter schemas, agreement with regorus, and cards combined on one asset the
# way the policy agent combines them.
#
# Each folder is tested on its own: every module is package subpolicy, which is
# also why the policy agent evaluates each in its own engine.
#
# Needs opa (or $OPA), regorus (or $REGORUS) and python3 with jsonschema.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export OPA="${OPA:-$(command -v opa || true)}"
[ -n "$OPA" ] || { echo "error: opa binary not found; set OPA=/path/to/opa" >&2; exit 1; }
export REGORUS="${REGORUS:-$(command -v regorus || true)}"
[ -n "$REGORUS" ] || { echo "error: regorus binary not found; set REGORUS=/path/to/regorus" >&2; exit 1; }

status=0
while read -r test; do
    folder="$(dirname "$test")"
    echo "== ${folder#"$here"/}"
    "$OPA" test "$folder" "$here/tests/testlib.rego" || status=1
done < <(find "$here" -name policy_test.rego | sort)

echo "== across cards"
( cd "$here/tests" && python3 -m unittest -v test_policy_cards ) || status=1

exit "$status"
