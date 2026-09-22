MOCK_GUARDIAN_IMAGE=""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Build the mock inference guardian Docker image.

Options:
  -i, --image IMAGE          Image tag to build (default: pdo_mock_inference_guardian:dev)
  -h, --help                 Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image) MOCK_GUARDIAN_IMAGE="$2"; shift 2 ;;
        -h|--help)  usage; exit 0 ;;
        *)          echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

MOCK_GUARDIAN_IMAGE="${MOCK_GUARDIAN_IMAGE:-pdo_mock_inference_guardian:dev}"

docker build -f ${SCRIPT_DIR}/Dockerfile -t $MOCK_GUARDIAN_IMAGE ${SCRIPT_DIR}
