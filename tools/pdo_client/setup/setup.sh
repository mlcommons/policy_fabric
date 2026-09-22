set -e
SCRIPT_DIR=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
: "${PDO_INSTALL_ROOT:?Missing environment variable PDO_INSTALL_ROOT}"
: "${PDO_CONTRACTS_ROOT:?Missing environment variable PDO_CONTRACTS_ROOT}"

CONTRACT_FAMILIES=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Build and install the PDO client + contracts into PDO_INSTALL_ROOT.
Assumes system deps are installed (setup/install_system_deps.sh) and
pdo-contracts is already checked out at PDO_CONTRACTS_ROOT.

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

bash ${SCRIPT_DIR}/install_pdo_client.sh
bash ${SCRIPT_DIR}/install_contracts.sh --families "$CONTRACT_FAMILIES"
