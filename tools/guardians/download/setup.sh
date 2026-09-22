set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

: "${PDO_INSTALL_ROOT?Missing environment variable PDO_INSTALL_ROOT}"

${PDO_INSTALL_ROOT}/bin/pip install -r ${SCRIPT_DIR}/requirements.txt
${PDO_INSTALL_ROOT}/bin/pip install -e ${SCRIPT_DIR}