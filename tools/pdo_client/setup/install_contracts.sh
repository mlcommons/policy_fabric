set -e
# Build and install the contract families.
SCRIPT_DIR=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
: "${PDO_CONTRACTS_ROOT:?Missing environment variable PDO_CONTRACTS_ROOT}"
: "${PDO_INSTALL_ROOT:?Missing environment variable PDO_INSTALL_ROOT}"

CONTRACT_FAMILIES=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Build and install the contract families into PDO_INSTALL_ROOT.

Options:
  -f, --families "F1 F2"   Contract families to build (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -f|--families) CONTRACT_FAMILIES="$2"; shift 2 ;;
        -h|--help)     usage; exit 0 ;;
        *)             echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$CONTRACT_FAMILIES" ] || { echo "Missing required option: -f/--families" >&2; usage >&2; exit 1; }

source ${SCRIPT_DIR}/activate_env.sh

echo "SET(CONTRACT_FAMILIES ${CONTRACT_FAMILIES})" > ${PDO_CONTRACTS_ROOT}/Local.cmake
make -C ${PDO_CONTRACTS_ROOT}
make -C ${PDO_CONTRACTS_ROOT} install
