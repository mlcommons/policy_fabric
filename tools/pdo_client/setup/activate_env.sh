# Sourced by setup, test, and entrypoint scripts to put the PDO client env in
# scope (works both inside the image and on a bare-metal install).
: "${PDO_INSTALL_ROOT:?Missing environment variable PDO_INSTALL_ROOT}"
: "${PDO_CONTRACTS_ROOT:?Missing environment variable PDO_CONTRACTS_ROOT}"

export PDO_SOURCE_ROOT=${PDO_SOURCE_ROOT:-${PDO_CONTRACTS_ROOT}/private-data-objects}
source ${PDO_SOURCE_ROOT}/build/common-config.sh
source ${PDO_INSTALL_ROOT}/bin/activate
export PDO_JUPYTER_ROOT=${PDO_HOME}/notebooks
