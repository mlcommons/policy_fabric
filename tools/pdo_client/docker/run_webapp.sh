WEBAPP_IMAGE=""
INTERFACE=""
PORT=""
LEDGER_CERT_PATH=""
SITE_TOML_SOURCE=""
USER_KEYS_FOLDER=""
SCRATCH_DIR=""
LEDGER_URL=""
SERVICE_HOST=""
ASSET_REGISTRY_URL=""
TEMPLATE_REGISTRY_URL=""
SEED_SCRIPT=""
CSRF_TRUSTED_ORIGINS=""
# The FL server runs on the host, so the containerized webapp reaches it through
# the host-gateway alias mapped in below rather than as "localhost".
FL_SERVER_URL="http://host.docker.internal:7920"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the webapp from the merged PDO client image. Host files and the scratch dir
are bind-mounted onto fixed in-container paths, and configuration is forwarded
to /webapp/run.sh as args (no .env file involved).

Options:
  -i, --image IMAGE              Docker image to run (required)
  -n, --interface IFACE          Host interface to publish (required)
  -p, --port PORT                Host port to publish (required)
  -c, --cert-path PATH           Ledger network cert on the host (required)
  -s, --site-toml PATH           Site toml source on the host (required)
  -k, --keys-folder DIR          User keys folder on the host (required)
  -S, --scratch DIR              Host scratch dir for generated PDO state (required)
  -l, --ledger-url URL           PDO ledger URL (required)
  -H, --service-host HOST        Service site host (required)
  -a, --asset-registry-url URL   Asset registry URL (required)
  -t, --template-registry-url URL Template registry URL (required)
  -e, --seed PATH                Seed script (a PDO flow) on the host, run after
                                 bootstrap and before the dev server (optional)
  -F, --fl-server-url URL        FL server the inference action submits jobs to,
                                 as addressable from inside this container
                                 (default: $FL_SERVER_URL)
  -o, --csrf-trusted-origins ORIGINS
                                 Comma-separated origins to add to Django's CSRF
                                 trust list, for when the port is reached through
                                 an HTTPS tunnel rather than localhost (optional)
  -h, --help                     Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image)                WEBAPP_IMAGE="$2"; shift 2 ;;
        -n|--interface)            INTERFACE="$2"; shift 2 ;;
        -p|--port)                 PORT="$2"; shift 2 ;;
        -c|--cert-path)            LEDGER_CERT_PATH="$2"; shift 2 ;;
        -s|--site-toml)            SITE_TOML_SOURCE="$2"; shift 2 ;;
        -k|--keys-folder)          USER_KEYS_FOLDER="$2"; shift 2 ;;
        -S|--scratch)              SCRATCH_DIR="$2"; shift 2 ;;
        -l|--ledger-url)           LEDGER_URL="$2"; shift 2 ;;
        -H|--service-host)         SERVICE_HOST="$2"; shift 2 ;;
        -a|--asset-registry-url)   ASSET_REGISTRY_URL="$2"; shift 2 ;;
        -t|--template-registry-url) TEMPLATE_REGISTRY_URL="$2"; shift 2 ;;
        -e|--seed)                 SEED_SCRIPT="$2"; shift 2 ;;
        -F|--fl-server-url)        FL_SERVER_URL="$2"; shift 2 ;;
        -o|--csrf-trusted-origins) CSRF_TRUSTED_ORIGINS="$2"; shift 2 ;;
        -h|--help)                 usage; exit 0 ;;
        *)                         echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$WEBAPP_IMAGE" ]          || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$INTERFACE" ]             || { echo "Missing required option: -n/--interface" >&2; usage >&2; exit 1; }
[ -n "$PORT" ]                  || { echo "Missing required option: -p/--port" >&2; usage >&2; exit 1; }
[ -n "$LEDGER_CERT_PATH" ]      || { echo "Missing required option: -c/--cert-path" >&2; usage >&2; exit 1; }
[ -n "$SITE_TOML_SOURCE" ]      || { echo "Missing required option: -s/--site-toml" >&2; usage >&2; exit 1; }
[ -n "$USER_KEYS_FOLDER" ]      || { echo "Missing required option: -k/--keys-folder" >&2; usage >&2; exit 1; }
[ -n "$SCRATCH_DIR" ]           || { echo "Missing required option: -S/--scratch" >&2; usage >&2; exit 1; }
[ -n "$LEDGER_URL" ]            || { echo "Missing required option: -l/--ledger-url" >&2; usage >&2; exit 1; }
[ -n "$SERVICE_HOST" ]          || { echo "Missing required option: -H/--service-host" >&2; usage >&2; exit 1; }
[ -n "$ASSET_REGISTRY_URL" ]    || { echo "Missing required option: -a/--asset-registry-url" >&2; usage >&2; exit 1; }
[ -n "$TEMPLATE_REGISTRY_URL" ] || { echo "Missing required option: -t/--template-registry-url" >&2; usage >&2; exit 1; }

# Ensure the host scratch dir exists so the bind mount has a source.
mkdir -p "$SCRATCH_DIR"

# Docker creates a missing bind-mount source as an empty *directory*, so
# starting before the ledger has written its cert does not fail here -- it fails
# much later, as an IsADirectoryError inside bootstrap, and leaves a directory
# named networkcert.pem behind that breaks every subsequent run. Check first.
for f in "$LEDGER_CERT_PATH" "$SITE_TOML_SOURCE"; do
    [ -f "$f" ] || { echo "Not a file: $f (has the policy engine finished starting?)" >&2; exit 1; }
done
[ -d "$USER_KEYS_FOLDER" ] || { echo "Not a directory: $USER_KEYS_FOLDER" >&2; exit 1; }

# The webapp runs in a container with no Docker access, so it cannot start
# guardians itself. Instead it writes each guardian start command as a shell
# script into a directory shared with the host (a subdir of the scratch mount);
# this launcher watches that directory and runs each script on the host. The
# command it writes invokes the run.sh of whichever guardian the owner chose, so
# the webapp is told each guardian directory's host path.
#
# It needs that directory for two different things, though: the *command* it
# writes runs on the host, but the *manifests* it discovers guardians from are
# read inside the container (app/guardian_registry.py). So the directory is also
# mounted, at the same absolute path, and one value serves both.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
GUARDIANS_DIR_HOST="$REPO_ROOT/guardians"
GUARDIAN_WATCH_DIR="$SCRATCH_DIR/guardian_requests"
mkdir -p "$GUARDIAN_WATCH_DIR"

# The FL server's run.sh goes through the same watcher, for the one case where the
# webapp starts a server rather than joining one. Only its host path is needed --
# the command runs out there, so nothing reads this file in here.
FL_SERVER_DIR_HOST="$REPO_ROOT/fl_server"

# Optional seed: bind-mount the host script onto a fixed container path and
# forward it to run.sh. Both arrays are empty when no seed was requested.
SEED_MOUNT=()
SEED_ARG=()
if [ -n "$SEED_SCRIPT" ]; then
    [ -f "$SEED_SCRIPT" ] || { echo "Seed script not found: $SEED_SCRIPT" >&2; exit 1; }
    SEED_MOUNT=(--volume "${SEED_SCRIPT}:/tmp/seed.py")
    SEED_ARG=(--seed /tmp/seed.py)
fi

# Bind-mount host files onto fixed container paths, then forward those paths
# (and the rest of the config) to /webapp/run.sh as args. PDO_INSTALL_ROOT and
# PDO_CONTRACTS_ROOT come from the image, so run.sh needs no --install-root.
docker run --rm --user "$(id -u):0" --name policies_web_client \
    -p $INTERFACE:$PORT:8000 \
    --add-host host.docker.internal:host-gateway \
    --env CONTAINERIZED_DEPLOYMENT=true \
    --env CSRF_TRUSTED_ORIGINS="$CSRF_TRUSTED_ORIGINS" \
    --env GUARDIANS_DIR="$GUARDIANS_DIR_HOST" \
    --env FL_SERVER_DIR="$FL_SERVER_DIR_HOST" \
    --env FL_SERVER_URL="$FL_SERVER_URL" \
    --volume ${LEDGER_CERT_PATH}:/tmp/networkcert.pem \
    --volume ${SITE_TOML_SOURCE}:/tmp/site.toml \
    --volume ${USER_KEYS_FOLDER}:/tmp/user_keys \
    --volume ${SCRATCH_DIR}:/tmp/scratch \
    --volume ${GUARDIANS_DIR_HOST}:${GUARDIANS_DIR_HOST}:ro \
    "${SEED_MOUNT[@]}" \
    $WEBAPP_IMAGE /webapp/run.sh \
        --interface 0.0.0.0 --port 8000 \
        --ledger-url "$LEDGER_URL" \
        --service-host "$SERVICE_HOST" \
        --cert-path /tmp/networkcert.pem \
        --site-toml /tmp/site.toml \
        --keys-folder /tmp/user_keys \
        --scratch /tmp/scratch \
        --asset-registry-url "$ASSET_REGISTRY_URL" \
        --template-registry-url "$TEMPLATE_REGISTRY_URL" \
        "${SEED_ARG[@]}" &
WEBAPP_PID=$!

# Stop the webapp container when this launcher exits.
trap 'docker rm -f policies_web_client >/dev/null 2>&1 || true' EXIT INT TERM

# Guardian deploy watcher: run each guardian start command the webapp drops into
# the watch dir, then delete the request. run.sh blocks for the container's
# lifetime, so each command runs in the background.
echo "[run_webapp] watching $GUARDIAN_WATCH_DIR for guardian deploy requests"
while kill -0 "$WEBAPP_PID" 2>/dev/null; do
    for f in "$GUARDIAN_WATCH_DIR"/*.sh; do
        [ -e "$f" ] || continue
        script="$(cat "$f")"
        rm -f "$f"
        echo "[run_webapp] deploying guardian from $(basename "$f")"
        bash -c "$script" >> "$GUARDIAN_WATCH_DIR/guardian_deploy.log" 2>&1 &
    done
    sleep 2
done

wait "$WEBAPP_PID"
