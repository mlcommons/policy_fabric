#!/bin/bash
: "${INTERFACE?Missing environment variable INTERFACE}"
: "${F_GUARDIAN_HOST?Missing environment variable F_GUARDIAN_HOST}"
: "${PDO_INSTALL_ROOT?Missing environment variable PDO_INSTALL_ROOT}"
: "${PDO_CONTRACTS_ROOT?Missing environment variable PDO_CONTRACTS_ROOT}"
: "${GUARDIAN_DATA_PATH?Missing environment variable GUARDIAN_DATA_PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export PDO_SOURCE_ROOT=${PDO_SOURCE_ROOT:-${PDO_CONTRACTS_ROOT}/private-data-objects}
export PDO_HOME="${PDO_INSTALL_ROOT}/opt/pdo"
export PDO_LEDGER_URL="http://localhost:19088"  # not used?
source ${PDO_SOURCE_ROOT}/build/common-config.sh

# This is sourced mainly for shell helpers like yell, try, and die
source ${PDO_HOME}/bin/lib/common.sh
source ${PDO_INSTALL_ROOT}/bin/activate

# Create key for the guardian services
KEYGEN=${PDO_SOURCE_ROOT}/build/__tools__/make-keys
${KEYGEN} --keyfile ${PDO_HOME}/keys/guardian_service --format pem
${KEYGEN} --keyfile ${PDO_HOME}/keys/guardian_sservice --format pem


# Start the guardian storage service (TODO: this is not used? but an error pops up if not started)
try ${PDO_HOME}/contracts/contracts/scripts/ss_start.sh -c -o ${PDO_HOME}/logs -- \
    --loglevel debug \
    --config guardian_service.toml \
    --config-dir $SCRIPT_DIR \
    --identity guardian_sservice \
    --bind host ${F_GUARDIAN_HOST} \
    --bind interface ${INTERFACE}

sleep 3

# Start the guardian service
try ${PDO_HOME}/contracts/contracts/scripts/gs_start.sh -c -o ${PDO_HOME}/logs -- \
    --loglevel debug \
    --config guardian_service.toml \
    --config-dir $SCRIPT_DIR \
    --identity guardian_service \
    --bind host ${F_GUARDIAN_HOST} \
    --bind interface ${INTERFACE}

tail -f /dev/null