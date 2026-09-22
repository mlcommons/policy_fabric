# !/bin/bash
set -e

SERVICES_WS=""
LEDGER_CERT_PATH=""
PDO_LEDGER_URL=""
PDO_SERVICES_IMAGE=""
INTERFACE=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the PDO services container.

Options:
  -w, --workspace DIR      Services workspace dir (required)
  -c, --cert-path PATH     Ledger cert path to copy in (required)
  -l, --ledger-url URL     Ledger URL (required)
  -i, --image IMAGE        Services image to run (required)
  -n, --interface IFACE    Host network interface (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -w|--workspace)  SERVICES_WS="$2"; shift 2 ;;
        -c|--cert-path)  LEDGER_CERT_PATH="$2"; shift 2 ;;
        -l|--ledger-url) PDO_LEDGER_URL="$2"; shift 2 ;;
        -i|--image)      PDO_SERVICES_IMAGE="$2"; shift 2 ;;
        -n|--interface)  INTERFACE="$2"; shift 2 ;;
        -h|--help)       usage; exit 0 ;;
        *)               echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$PDO_LEDGER_URL" ]             || { echo "Missing required option: -l/--ledger-url" >&2; usage >&2; exit 1; }
[ -n "$PDO_SERVICES_IMAGE" ]         || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$INTERFACE" ] || { echo "Missing required option: -n/--interface" >&2; usage >&2; exit 1; }
[ -n "$SERVICES_WS" ] || { echo "Missing required option: -w/--workspace" >&2; usage >&2; exit 1; }
[ -n "$LEDGER_CERT_PATH" ] || { echo "Missing required option: -c/--cert-path" >&2; usage >&2; exit 1; }

# Cleanup. As with the ledger, the container writes into this directory as its
# own uid (1000), which is not necessarily the host user's.
rm -rf ${SERVICES_WS}
mkdir -p ${SERVICES_WS}/services/etc
mkdir -p ${SERVICES_WS}/ccf/keys

# Copy ledger keys
cp -r $LEDGER_CERT_PATH ${SERVICES_WS}/ccf/keys/
chmod -R 0777 ${SERVICES_WS}

# Run services
docker run --rm --network host --name services_container \
    --volume ${SERVICES_WS}:/project/pdo/xfer/ \
    --entrypoint /project/pdo/tools/start_services.sh $PDO_SERVICES_IMAGE -m build -c 5 -i $INTERFACE -l $PDO_LEDGER_URL
