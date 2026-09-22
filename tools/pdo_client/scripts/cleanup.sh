SCRIPT_DIR=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
: "${PDO_INSTALL_ROOT:?Missing environment variable PDO_INSTALL_ROOT}"
: "${PDO_CONTRACTS_ROOT:?Missing environment variable PDO_CONTRACTS_ROOT}"

rm -rf ${PDO_INSTALL_ROOT}
rm -rf ${PDO_CONTRACTS_ROOT}/build
