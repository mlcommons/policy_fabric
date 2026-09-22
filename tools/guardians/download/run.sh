GUARDIAN_IMAGE=""
INTERFACE=""
PORT=""
SSERVICE_PORT=""
GUARDIAN_HOST=""
DATA_PATH=""

# Where the host data file is mounted inside the container; the guardian
# operation reads it via the GUARDIAN_DATA_PATH env var (see download.py).
CONTAINER_DATA_PATH="/project/guardian_data"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the guardian container.

Options:
  -i, --image IMAGE        Docker image to run (required)
  -n, --interface IFACE    Host interface to publish (required)
  -p, --port PORT          Host port to publish (required)
  -s, --sservice-port PORT Host storage-service port to publish (required)
  -g, --guardian-host URL            Guardian Host (required)
  -d, --data-path PATH     Host data file to serve (optional). Mounted into the
                           container and exposed as GUARDIAN_DATA_PATH.
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image)     GUARDIAN_IMAGE="$2"; shift 2 ;;
        -n|--interface) INTERFACE="$2"; shift 2 ;;
        -p|--port)      PORT="$2"; shift 2 ;;
        -s|--sservice-port) SSERVICE_PORT="$2"; shift 2 ;;
        -g|--guardian-host) GUARDIAN_HOST="$2"; shift 2 ;;
        -d|--data-path) DATA_PATH="$2"; shift 2 ;;
        -h|--help)      usage; exit 0 ;;
        *)              echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$GUARDIAN_IMAGE" ] || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$INTERFACE" ]      || { echo "Missing required option: -n/--interface" >&2; usage >&2; exit 1; }
[ -n "$PORT" ]           || { echo "Missing required option: -p/--port" >&2; usage >&2; exit 1; }
[ -n "$SSERVICE_PORT" ]  || { echo "Missing required option: -s/--sservice-port" >&2; usage >&2; exit 1; }
[ -n "$GUARDIAN_HOST" ]   || { echo "Missing required option: -g/--guardian-host" >&2; usage >&2; exit 1; }
[ -n "$DATA_PATH" ]       || { echo "Missing required option: -d/--data-path" >&2; usage >&2; exit 1; }

# Replace any guardian already running under this name so a redeploy is idempotent.
docker rm -f pdo-guardian >/dev/null 2>&1 || true

docker run --rm --env F_GUARDIAN_HOST=$GUARDIAN_HOST --env INTERFACE=0.0.0.0 --user "$(id -u):0" \
    -v "${DATA_PATH}:${CONTAINER_DATA_PATH}:ro" \
    --env "GUARDIAN_DATA_PATH=${CONTAINER_DATA_PATH}" \
    -p $INTERFACE:$PORT:7900 -p $INTERFACE:$SSERVICE_PORT:7901 --name pdo-guardian $GUARDIAN_IMAGE

# docker run --rm --env F_GUARDIAN_HOST=localhost --user "$(id -u):0" \
#     --network host --name pdo-guardian $GUARDIAN_IMAGE
