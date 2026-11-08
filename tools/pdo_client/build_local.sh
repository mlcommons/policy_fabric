SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PDO_CLIENT_IMAGE=""
BASE_IMAGE=""
CONTRACTS_DIR=""
CONTRACT_FAMILIES="identity-contract authority-contract rego-contract"

usage() {
    cat <<USAGE
Usage: $(basename "$0") [options]

Build a client image whose contract families come from a local pdo-contracts
checkout, layered on a released client image (see Dockerfile.local). Use it to
run unpushed contract changes in the whole stack; build.sh is the release path.

Options:
  -i, --image IMAGE        Image tag to build (required)
  -B, --base-image IMAGE   Released client image to build on (required)
  -c, --contracts DIR      Local pdo-contracts checkout (required)
  -f, --families "F1 F2"   Families to take from the checkout
                           (default: $CONTRACT_FAMILIES)
  -h, --help               Show this help and exit
USAGE
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image)      PDO_CLIENT_IMAGE="$2"; shift 2 ;;
        -B|--base-image) BASE_IMAGE="$2"; shift 2 ;;
        -c|--contracts)  CONTRACTS_DIR="$2"; shift 2 ;;
        -f|--families)   CONTRACT_FAMILIES="$2"; shift 2 ;;
        -h|--help)       usage; exit 0 ;;
        *)               echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

[ -n "$PDO_CLIENT_IMAGE" ] || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$BASE_IMAGE" ]       || { echo "Missing required option: -B/--base-image" >&2; usage >&2; exit 1; }
[ -d "$CONTRACTS_DIR" ]    || { echo "Missing or not a directory: -c/--contracts" >&2; usage >&2; exit 1; }

set -e
CONTEXT=$(mktemp -d)
trap 'rm -rf "$CONTEXT"' EXIT

mkdir -p "$CONTEXT/contracts"
for family in $CONTRACT_FAMILIES; do
    mkdir -p "$CONTEXT/contracts/$family"
    tar -C "$CONTRACTS_DIR/$family" --exclude=build --exclude=__pycache__ --exclude='*.pyc' -cf - . \
        | tar -C "$CONTEXT/contracts/$family" -xf -
done
for part in setup scripts webapp .dockerignore; do
    cp -r "$SCRIPT_DIR/$part" "$CONTEXT/$part"
done

docker build -t "$PDO_CLIENT_IMAGE" \
    --build-arg BASE_IMAGE="$BASE_IMAGE" \
    --build-arg CONTRACT_FAMILIES="$CONTRACT_FAMILIES" \
    -f "$SCRIPT_DIR/Dockerfile.local" "$CONTEXT"
