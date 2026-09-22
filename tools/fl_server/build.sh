FL_SERVER_IMAGE=""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Build the FL server Docker image.

Options:
  -i, --image IMAGE          Image tag to build (required)
  -h, --help                 Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image) FL_SERVER_IMAGE="$2"; shift 2 ;;
        -h|--help)  usage; exit 0 ;;
        *)          echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

[ -n "$FL_SERVER_IMAGE" ] || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }

docker build -f ${SCRIPT_DIR}/Dockerfile -t $FL_SERVER_IMAGE ${SCRIPT_DIR}
