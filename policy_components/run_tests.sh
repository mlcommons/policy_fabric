#!/usr/bin/env bash
# Run the components' Rego unit tests, then check every component against its
# component.json on OPA and regorus, every card graph against its vectors, and every card
# that keeps its meaning against the single Rego module it was before.
#
# Needs opa, python3 with jsonschema and the regorus bindings, PDO_CONTRACTS_ROOT (a
# pdo-contracts checkout, for the graph reference implementation in
# rego-contract/pdo/rego/graph), and the repository's history back to its first commit.
set -euo pipefail

: "${PDO_CONTRACTS_ROOT:?set PDO_CONTRACTS_ROOT to a pdo-contracts checkout}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

opa test "$here"
cd "$here/tests"
PYTHONPATH="$PDO_CONTRACTS_ROOT/rego-contract:$here/../tools/policy_catalog" python3 -m unittest -v test_components test_cards
