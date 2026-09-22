set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PDO_CONTRACTS_DIR=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Build the PDO ledger/services images from a local pdo-contracts checkout.

Options:
  -d, --contracts-dir DIR  Local pdo-contracts directory (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -d|--contracts-dir) PDO_CONTRACTS_DIR="$2"; shift 2 ;;
        -h|--help)          usage; exit 0 ;;
        *)                  echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$PDO_CONTRACTS_DIR" ] || { echo "Missing required option: -d/--contracts-dir" >&2; usage >&2; exit 1; }

# Some config
TMP_PDO_CONTRACTS_DIR=/tmp/pdo-contracts
PDO_VERSION=0.4.29
PDO_DEBUG_BUILD=1
PDO_LOG_LEVEL=debug

# Copy the local repo into a tmp folder so the build can't disturb the
# working tree.
rm -rf $TMP_PDO_CONTRACTS_DIR
cp -r $PDO_CONTRACTS_DIR $TMP_PDO_CONTRACTS_DIR

PDO_SOURCE_ROOT=$TMP_PDO_CONTRACTS_DIR/private-data-objects
cd $PDO_SOURCE_ROOT
git checkout -B tmp_branch
cp $SCRIPT_DIR/make.loc $PDO_SOURCE_ROOT/docker/

# Build the pdo images
PDO_SOURCE_ROOT=$PDO_SOURCE_ROOT \
    PDO_VERSION=$PDO_VERSION \
    PDO_DEBUG_BUILD=$PDO_DEBUG_BUILD \
    PDO_LOG_LEVEL=$PDO_LOG_LEVEL \
    make -C $PDO_SOURCE_ROOT/docker all
PDO_SOURCE_ROOT=$PDO_SOURCE_ROOT \
    PDO_VERSION=$PDO_VERSION \
    PDO_DEBUG_BUILD=$PDO_DEBUG_BUILD \
    PDO_LOG_LEVEL=$PDO_LOG_LEVEL \
    make -C $PDO_SOURCE_ROOT/docker clean_repository
