MOCK_GUARDIAN_IMAGE=""
INTERFACE=""
PORT=""
NAME=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the mock inference guardian in a container.

Options:
  -i, --image IMAGE        Docker image to run (default: pdo_mock_inference_guardian:dev)
  -n, --interface IFACE    Host interface to publish (default: 127.0.0.1)
  -p, --port PORT          Host port to publish (default: 7900)
  -N, --name NAME          Container name (default: pdo-mock-guardian-PORT)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image)     MOCK_GUARDIAN_IMAGE="$2"; shift 2 ;;
        -n|--interface) INTERFACE="$2"; shift 2 ;;
        -p|--port)      PORT="$2"; shift 2 ;;
        -N|--name)      NAME="$2"; shift 2 ;;
        -h|--help)      usage; exit 0 ;;
        *)              echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

MOCK_GUARDIAN_IMAGE="${MOCK_GUARDIAN_IMAGE:-pdo_mock_inference_guardian:dev}"
INTERFACE="${INTERFACE:-127.0.0.1}"
PORT="${PORT:-7900}"

CONTAINER_NAME="${NAME:-pdo-mock-guardian-${PORT}}"
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

docker run --rm --user "$(id -u):0" \
    --add-host host.docker.internal:host-gateway \
    -p $INTERFACE:$PORT:7900 \
    --name "$CONTAINER_NAME" $MOCK_GUARDIAN_IMAGE
