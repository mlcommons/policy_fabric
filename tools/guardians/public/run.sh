INTERFACE=""
PORT=""
DATA_PATH=""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the public (unguarded) asset server. Unlike the download and inference
guardians this needs no PDO client and no container -- it is a plain Python
process serving one file to anyone who asks.

Options:
  -n, --interface IFACE    Interface to bind (required)
  -p, --port PORT          Port to bind (required)
  -d, --data-path PATH     Host data file to serve (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -n|--interface) INTERFACE="$2"; shift 2 ;;
        -p|--port)      PORT="$2"; shift 2 ;;
        -d|--data-path) DATA_PATH="$2"; shift 2 ;;
        -h|--help)      usage; exit 0 ;;
        *)              echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$INTERFACE" ] || { echo "Missing required option: -n/--interface" >&2; usage >&2; exit 1; }
[ -n "$PORT" ]      || { echo "Missing required option: -p/--port" >&2; usage >&2; exit 1; }
[ -n "$DATA_PATH" ] || { echo "Missing required option: -d/--data-path" >&2; usage >&2; exit 1; }

exec python3 -u "${SCRIPT_DIR}/server.py" \
    --interface "$INTERFACE" \
    --port "$PORT" \
    --data-path "$DATA_PATH"
