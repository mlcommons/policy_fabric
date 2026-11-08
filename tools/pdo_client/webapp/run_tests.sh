#!/bin/bash
# Unit tests of the webapp: the readiness checklist, trust panel and schema
# helpers, and the pages and endpoints over a fake directory, template registry
# and ledger. Nothing here talks to a ledger or a registry.
#
# Needs the PDO client environment (the rego and identity families installed),
# as in the client image:
#
#     PYTHON=/pdo_install/bin/python ./run_tests.sh [test labels...]

set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON=${PYTHON:-python3}
SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT

export PDO_LEDGER_URL=http://ledger.invalid PDO_LEDGER_TYPE=ccf F_SERVICE_HOST=localhost \
    LEDGER_CERT_PATH="$SCRATCH/cert" SITE_TOML_SOURCE="$SCRATCH/site.toml" \
    USER_KEYS_FOLDER="$SCRATCH/keys" PREFERRED_ESERVICE_URL=random \
    ASSET_REGISTRY_URL=http://assets.invalid TEMPLATE_REGISTRY_URL=http://templates.invalid \
    SCRATCH_DIR="$SCRATCH" PDO_LOG_FILE=__screen__ PDO_LOG_LEVEL=warn
export PDO_INSTALL_ROOT=${PDO_INSTALL_ROOT:-/pdo_install}
export PDO_CONTRACTS_ROOT=${PDO_CONTRACTS_ROOT:-$SCRATCH}

cd "$SCRIPT_DIR"
"$PYTHON" manage.py test "${@:-app.tests}"
