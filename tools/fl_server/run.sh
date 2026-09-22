FL_SERVER_IMAGE=""
INTERFACE=""
PORT=""
NAME=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the mock FL server in a container: the job board the federated flow goes
through. It is reached from two directions -- the webapp submits rounds to it and
the FL client bundled with every inference guardian polls it -- so the published
port has to be reachable from both.

Options:
  -i, --image IMAGE        Docker image to run (required)
  -n, --interface IFACE    Host interface to publish (required)
  -p, --port PORT          Host port to publish (required)
  -N, --name NAME          Container name (default: pdo-fl-server-PORT). One
                           server per name, so a second name is a second,
                           independent job board.
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image)     FL_SERVER_IMAGE="$2"; shift 2 ;;
        -n|--interface) INTERFACE="$2"; shift 2 ;;
        -p|--port)      PORT="$2"; shift 2 ;;
        -N|--name)      NAME="$2"; shift 2 ;;
        -h|--help)      usage; exit 0 ;;
        *)              echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$FL_SERVER_IMAGE" ] || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$INTERFACE" ]       || { echo "Missing required option: -n/--interface" >&2; usage >&2; exit 1; }
[ -n "$PORT" ]            || { echo "Missing required option: -p/--port" >&2; usage >&2; exit 1; }

CONTAINER_NAME="${NAME:-pdo-fl-server-${PORT}}"
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

docker run --rm --user "$(id -u):0" \
    -p $INTERFACE:$PORT:7920 \
    --name "$CONTAINER_NAME" $FL_SERVER_IMAGE \
    --interface 0.0.0.0 --port 7920
