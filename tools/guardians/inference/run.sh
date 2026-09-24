GUARDIAN_IMAGE=""
INTERFACE=""
PORT=""
SSERVICE_PORT=""
GUARDIAN_HOST=""
DATA_PATH=""
FL_SERVER_URL=""
# The DID of the asset this guardian holds. The bundled FL client announces it to
# the FL server together with its own ID (below), and the server keeps the pair:
# that is how a requester sees this site in the list of connected ones, and how
# the server knows which capability in a round belongs here.
ASSET_DID=""
ASSET_NAME=""
# The ID the bundled FL client joins the FL server as, and the one each round's
# job for ASSET_DID is addressed to. It must be unique among that server's
# clients. Defaults to the container hostname inside the image, which is unique
# but changes with every container; the webapp passes the guardian's host:port.
FL_CLIENT_ID=""

# Where the host data file is mounted inside the FL client's container, which
# reads it via FL_DATA_PATH (see fl_framework/client.py). Only the client's: the
# guardian core has no dataset, it only answers whether a job may run.
CONTAINER_DATA_PATH="/project/fl_data"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run an inference guardian: two containers from the same image, started and
stopped together.

  guardian core  processes do_inference capabilities and answers yes or no.
                 It has no dataset.
  FL client      holds the dataset, polls the FL server for jobs, and asks the
                 core before running each one. It shares the core's network
                 namespace, so it reaches the core as localhost.

Options:
  -i, --image IMAGE        Docker image to run (required)
  -n, --interface IFACE    Host interface to publish (required)
  -p, --port PORT          Host port to publish (required)
  -s, --sservice-port PORT Host storage-service port to publish (required)
  -g, --guardian-host URL  Guardian Host (required)
  -d, --data-path PATH     Host data file the FL client holds (required). Mounted
                           into the FL client's container only.
  -f, --fl-server-url URL  FL server the bundled client polls for jobs (required)
  -D, --asset-did DID      DID of the asset this guardian holds (required). The
                           bundled client announces it, and the FL server matches
                           a round's capability for this DID to that client.
  -A, --asset-name NAME    Display name for that asset (optional)
  -c, --fl-client-id ID    ID the bundled client joins the FL server as; this
                           site's jobs are addressed to it. Unique per FL server
                           (default: the container hostname)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image)         GUARDIAN_IMAGE="$2"; shift 2 ;;
        -n|--interface)     INTERFACE="$2"; shift 2 ;;
        -p|--port)          PORT="$2"; shift 2 ;;
        -s|--sservice-port) SSERVICE_PORT="$2"; shift 2 ;;
        -g|--guardian-host) GUARDIAN_HOST="$2"; shift 2 ;;
        -d|--data-path)     DATA_PATH="$2"; shift 2 ;;
        -f|--fl-server-url) FL_SERVER_URL="$2"; shift 2 ;;
        -D|--asset-did)     ASSET_DID="$2"; shift 2 ;;
        -A|--asset-name)    ASSET_NAME="$2"; shift 2 ;;
        -c|--fl-client-id)  FL_CLIENT_ID="$2"; shift 2 ;;
        -h|--help)          usage; exit 0 ;;
        *)                  echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$GUARDIAN_IMAGE" ] || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$INTERFACE" ]      || { echo "Missing required option: -n/--interface" >&2; usage >&2; exit 1; }
[ -n "$PORT" ]           || { echo "Missing required option: -p/--port" >&2; usage >&2; exit 1; }
[ -n "$SSERVICE_PORT" ]  || { echo "Missing required option: -s/--sservice-port" >&2; usage >&2; exit 1; }
[ -n "$GUARDIAN_HOST" ]  || { echo "Missing required option: -g/--guardian-host" >&2; usage >&2; exit 1; }
[ -n "$DATA_PATH" ]      || { echo "Missing required option: -d/--data-path" >&2; usage >&2; exit 1; }
[ -n "$FL_SERVER_URL" ]  || { echo "Missing required option: -f/--fl-server-url" >&2; usage >&2; exit 1; }
[ -n "$ASSET_DID" ]      || { echo "Missing required option: -D/--asset-did" >&2; usage >&2; exit 1; }
# Docker silently turns a missing bind-mount source into an empty root-owned
# directory, and the client would then fail on its first job instead of here.
[ -f "$DATA_PATH" ]      || { echo "No data file at $DATA_PATH" >&2; exit 1; }

# One pair of containers per port, so redeploying onto a port replaces what was
# there while a guardian on another port -- another dataset, another policy --
# keeps running. The client's name extends the core's, so clearing
# "pdo-inference-guardian-*" clears both.
CORE_NAME="pdo-inference-guardian-${PORT}"
CLIENT_NAME="${CORE_NAME}-fl-client"
docker rm -f "$CLIENT_NAME" "$CORE_NAME" >/dev/null 2>&1 || true

# The guardian core. No data mount. --add-host lets the FL client, which joins
# this container's network namespace, reach an FL server published on the host
# when the URL names host.docker.internal.
CORE_ID=$(docker run -d --rm --env F_GUARDIAN_HOST=$GUARDIAN_HOST --env INTERFACE=0.0.0.0 --user "$(id -u):0" \
    --add-host host.docker.internal:host-gateway \
    -p $INTERFACE:$PORT:7900 -p $INTERFACE:$SSERVICE_PORT:7901 \
    --name "$CORE_NAME" $GUARDIAN_IMAGE) || { echo "The guardian core did not start" >&2; exit 1; }

# The two go down together: whichever way this script ends, both go. By ID, not
# by name -- a redeploy onto this port removes these containers and starts new
# ones under the same names, and this script's exit must not take those down.
CLIENT_CIDFILE="$(mktemp -u)"
cleanup() {
    docker rm -f "$CORE_ID" $(cat "$CLIENT_CIDFILE" 2>/dev/null) >/dev/null 2>&1 || true
    rm -f "$CLIENT_CIDFILE"
}
trap cleanup EXIT

# The FL client, in the foreground. It holds the dataset, and it is the only
# container that does.
docker run --rm --user "$(id -u):0" --cidfile "$CLIENT_CIDFILE" \
    --network "container:${CORE_ID}" \
    -v "${DATA_PATH}:${CONTAINER_DATA_PATH}:ro" \
    --env "FL_DATA_PATH=${CONTAINER_DATA_PATH}" \
    --env "FL_SERVER_URL=${FL_SERVER_URL}" \
    --env "FL_CLIENT_ID=${FL_CLIENT_ID}" \
    --env "ASSET_DID=${ASSET_DID}" \
    --env "ASSET_NAME=${ASSET_NAME}" \
    --entrypoint bash \
    --name "$CLIENT_NAME" $GUARDIAN_IMAGE /project/inference_guardian/start_fl_client.sh
