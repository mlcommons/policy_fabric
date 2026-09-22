PDO_CLIENT_IMAGE=""
GUARDIAN_IMAGE=""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Build the guardian Docker image.

Options:
  -c, --client-image IMAGE   Base PDO client image (required)
  -i, --image IMAGE          Image tag to build (required)
  -h, --help                 Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -c|--client-image) PDO_CLIENT_IMAGE="$2"; shift 2 ;;
        -i|--image)        GUARDIAN_IMAGE="$2"; shift 2 ;;
        -h|--help)         usage; exit 0 ;;
        *)                 echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

[ -n "$PDO_CLIENT_IMAGE" ]  || { echo "Missing required option: -c/--client-image" >&2; usage >&2; exit 1; }
[ -n "$GUARDIAN_IMAGE" ]    || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }

docker build --build-arg PDO_CLIENT_IMAGE=$PDO_CLIENT_IMAGE -f ${SCRIPT_DIR}/Dockerfile -t $GUARDIAN_IMAGE ${SCRIPT_DIR}