# !/bin/bash
set -e

LEDGER_WS=""
PDO_LEDGER_IMAGE=""
INTERFACE=""
LEDGER_PORT=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the PDO ledger (CCF) container.

Options:
  -w, --workspace DIR      Ledger workspace dir (required)
  -i, --image IMAGE        Ledger image to run (required)
  -n, --interface IFACE    Host network interface (required)
  -p, --port PORT          Ledger port (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -w|--workspace) LEDGER_WS="$2"; shift 2 ;;
        -i|--image)     PDO_LEDGER_IMAGE="$2"; shift 2 ;;
        -n|--interface) INTERFACE="$2"; shift 2 ;;
        -p|--port)      LEDGER_PORT="$2"; shift 2 ;;
        -h|--help)      usage; exit 0 ;;
        *)              echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$LEDGER_WS" ] || { echo "Missing required option: -w/--workspace" >&2; usage >&2; exit 1; }
[ -n "$PDO_LEDGER_IMAGE" ]           || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$INTERFACE" ] || { echo "Missing required option: -n/--interface" >&2; usage >&2; exit 1; }
[ -n "$LEDGER_PORT" ]                || { echo "Missing required option: -p/--port" >&2; usage >&2; exit 1; }
[ "$LEDGER_PORT" = "6600" ]          || { echo "Invalid -p/--port: must be 6600 (got '$LEDGER_PORT')" >&2; exit 1; }

# Cleanup. The container writes its network keys into this directory as its own
# uid (1000), which is not necessarily the host user's, so the transfer
# directory is opened up rather than left at the host user's default mode.
rm -rf ${LEDGER_WS}
mkdir -p ${LEDGER_WS}/ccf/keys
chmod -R 0777 ${LEDGER_WS}

# Run ledger
docker run --rm --network host --name ccf_container \
    --volume $LEDGER_WS:/project/pdo/xfer/ \
    --entrypoint /project/pdo/tools/start_ccf.sh $PDO_LEDGER_IMAGE -m build -i "$INTERFACE" --start
