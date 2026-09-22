ASSET_REGISTRY_IMAGE=""
INTERFACE=""
PORT=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the asset_registry container.

Options:
  -i, --image IMAGE        Docker image to run (required)
  -n, --interface IFACE    Host interface to publish (required)
  -p, --port PORT          Host port to publish (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image)     ASSET_REGISTRY_IMAGE="$2"; shift 2 ;;
        -n|--interface) INTERFACE="$2"; shift 2 ;;
        -p|--port)      PORT="$2"; shift 2 ;;
        -h|--help)      usage; exit 0 ;;
        *)              echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$ASSET_REGISTRY_IMAGE" ] || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$INTERFACE" ]            || { echo "Missing required option: -n/--interface" >&2; usage >&2; exit 1; }
[ -n "$PORT" ]                 || { echo "Missing required option: -p/--port" >&2; usage >&2; exit 1; }

# Replace any registry already running under this name, the way the guardians
# do, so a restart onto a new image does not fail on the name and leave the old
# container answering on the port.
docker rm -f asset_registry_container >/dev/null 2>&1 || true

docker run --rm --user "$(id -u):0" --name asset_registry_container \
    -p $INTERFACE:$PORT:8000 $ASSET_REGISTRY_IMAGE
