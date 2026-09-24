#!/bin/bash
# Start the FL client: the process that holds the dataset. It runs in its own
# container, beside the guardian core's and sharing its network namespace, so it
# reaches the core as localhost and the core never sees the data.
: "${PDO_INSTALL_ROOT?Missing environment variable PDO_INSTALL_ROOT}"
: "${FL_DATA_PATH?Missing environment variable FL_DATA_PATH}"
: "${FL_SERVER_URL?Missing environment variable FL_SERVER_URL}"
: "${ASSET_DID?Missing environment variable ASSET_DID}"

source ${PDO_INSTALL_ROOT}/bin/activate

export GUARDIAN_CORE_URL="${GUARDIAN_CORE_URL:-http://localhost:7900}"
exec python -u -m fl_framework
