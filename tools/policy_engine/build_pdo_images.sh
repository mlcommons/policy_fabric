set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PDO_LEDGER_IMAGE=""
PDO_SERVICES_IMAGE=""
REPOSITORY=""
BRANCH=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Clone pdo-contracts and build the PDO ledger/services Docker images.

Options:
  -l, --ledger-image IMAGE     Tag for the built ledger image (required)
  -s, --services-image IMAGE   Tag for the built services image (required)
  -r, --repository URL         pdo-contracts git repository (required)
  -b, --branch BRANCH          Branch to check out (required)
  -h, --help                   Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -l|--ledger-image)   PDO_LEDGER_IMAGE="$2"; shift 2 ;;
        -s|--services-image) PDO_SERVICES_IMAGE="$2"; shift 2 ;;
        -r|--repository)     REPOSITORY="$2"; shift 2 ;;
        -b|--branch)         BRANCH="$2"; shift 2 ;;
        -h|--help)           usage; exit 0 ;;
        *)                   echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$PDO_LEDGER_IMAGE" ] || { echo "Missing required option: -l/--ledger-image" >&2; usage >&2; exit 1; }
[ -n "$PDO_SERVICES_IMAGE" ] || { echo "Missing required option: -s/--services-image" >&2; usage >&2; exit 1; }
[ -n "$REPOSITORY" ] || { echo "Missing required option: -r/--repository" >&2; usage >&2; exit 1; }
[ -n "$BRANCH" ] || { echo "Missing required option: -b/--branch" >&2; usage >&2; exit 1; }

# Some config.
#
# PDO's own docker Makefile bakes the *building* user's uid/gid into these images
# (PDO_USER_UID / PDO_GROUP_UID default to `id -u` / `id -g`), so a published
# image writes into its bind-mounted transfer directory as whatever uid built it,
# which is not necessarily the uid running it. run_ledger.sh and run_services.sh
# open that directory up rather than assume the two match.
TMP_PDO_CONTRACTS_DIR=/tmp/pdo-contracts
PDO_VERSION=0.4.29
PDO_DEBUG_BUILD=1
PDO_LOG_LEVEL=debug

# Clone and setup the repo
rm -rf $TMP_PDO_CONTRACTS_DIR
git clone $REPOSITORY $TMP_PDO_CONTRACTS_DIR
cd $TMP_PDO_CONTRACTS_DIR
git checkout $BRANCH
git submodule update --init --recursive
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

docker tag pdo_ccf:0.4.29 $PDO_LEDGER_IMAGE
docker tag pdo_services:0.4.29 $PDO_SERVICES_IMAGE
