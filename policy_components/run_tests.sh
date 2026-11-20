#!/usr/bin/env bash
# Run the components' Rego unit tests, then check every component against its
# component.json on OPA and regorus, every card graph against its graph tests, and every card
# that keeps its meaning against its Rego file at commit 760742d, before cards became graphs.
#
# Needs opa, python3 with jsonschema and the regorus bindings (tests/engine.py says how to
# build them), PDO_CONTRACTS_ROOT (a pdo-contracts checkout, whose
# rego-contract/src/rego/common holds the contract's graph validator and planner), and the
# repository's history back to commit 760742d.
set -euo pipefail

: "${PDO_CONTRACTS_ROOT:?set PDO_CONTRACTS_ROOT to a pdo-contracts checkout}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

opa test "$here"
cd "$here/tests"
PYTHONPATH="$here/../tools/pdo_client/webapp:$here/../tools/policy_catalog" python3 -m unittest -v test_components test_cards
