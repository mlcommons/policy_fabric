#!/usr/bin/env bash
# Run every authority card's Rego unit tests, then the checks across them: each
# issues a standard fact about a holder, with claims that satisfy its schema.
#
# Needs opa (or $OPA), regorus (or $REGORUS) and python3 with jsonschema.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tests="$here/../policy_cards/tests"
export OPA="${OPA:-$(command -v opa || true)}"
[ -n "$OPA" ] || { echo "error: opa binary not found; set OPA=/path/to/opa" >&2; exit 1; }
export REGORUS="${REGORUS:-$(command -v regorus || true)}"
[ -n "$REGORUS" ] || { echo "error: regorus binary not found; set REGORUS=/path/to/regorus" >&2; exit 1; }

status=0
while read -r test; do
    folder="$(dirname "$test")"
    echo "== ${folder#"$here"/}"
    "$OPA" test "$folder" "$tests/testlib.rego" || status=1
done < <(find "$here" -name policy_test.rego | sort)

echo "== across authorities"
( cd "$tests" && python3 -m unittest -v test_authority_cards ) || status=1

exit "$status"
