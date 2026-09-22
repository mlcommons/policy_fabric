SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PDO_CLIENT_IMAGE=""
REPOSITORY=""
BRANCH=""
CONTRACT_FAMILIES=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Build the PDO client + webapp image (build context is the pdo_client folder).

Options:
  -i, --image IMAGE        Image tag to build (required)
  -r, --repository URL     pdo-contracts git repository (required)
  -b, --branch BRANCH      Branch to check out (required)
  -f, --families "F1 F2"   Contract families to build (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image)      PDO_CLIENT_IMAGE="$2"; shift 2 ;;
        -r|--repository) REPOSITORY="$2"; shift 2 ;;
        -b|--branch)     BRANCH="$2"; shift 2 ;;
        -f|--families)   CONTRACT_FAMILIES="$2"; shift 2 ;;
        -h|--help)       usage; exit 0 ;;
        *)               echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$PDO_CLIENT_IMAGE" ]  || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$REPOSITORY" ]        || { echo "Missing required option: -r/--repository" >&2; usage >&2; exit 1; }
[ -n "$BRANCH" ]            || { echo "Missing required option: -b/--branch" >&2; usage >&2; exit 1; }
[ -n "$CONTRACT_FAMILIES" ] || { echo "Missing required option: -f/--families" >&2; usage >&2; exit 1; }

# Build context is the parent (pdo_client) so the Dockerfile can COPY
# setup/ + scripts/ + webapp/. The merged Dockerfile lives at the repo root.
docker build -t $PDO_CLIENT_IMAGE \
    --build-arg REPOSITORY=$REPOSITORY \
    --build-arg BRANCH=$BRANCH \
    --build-arg CONTRACT_FAMILIES="$CONTRACT_FAMILIES" \
    -f ${SCRIPT_DIR}/Dockerfile ${SCRIPT_DIR}
