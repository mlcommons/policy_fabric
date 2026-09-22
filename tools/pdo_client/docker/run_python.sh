PDO_CLIENT_IMAGE=""
LEDGER_CERT_PATH=""
SITE_TOML_SOURCE=""
F_SERVICE_HOST=""
PDO_LEDGER_URL=""
USER_KEYS_FOLDER=""
GUARDIAN_URL=""
usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the python test in the client container. Mounts the host files (including
pre-generated user keys) and invokes the same scripts/run_python.sh inside
the container. Generate the keys first with generate_user_keys.sh.

Options:
  -i, --image IMAGE        Client image to run (required)
  -c, --cert-path PATH     Ledger network cert (required)
  -s, --site-toml PATH     Site toml source (required)
  -H, --host HOST          Service host / F_SERVICE_HOST (required)
  -l, --ledger-url URL     Ledger URL (required)
  -k, --keys-folder DIR    Existing user keys folder to mount (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image)       PDO_CLIENT_IMAGE="$2"; shift 2 ;;
        -c|--cert-path)   LEDGER_CERT_PATH="$2"; shift 2 ;;
        -s|--site-toml)   SITE_TOML_SOURCE="$2"; shift 2 ;;
        -H|--host)        F_SERVICE_HOST="$2"; shift 2 ;;
        -l|--ledger-url)  PDO_LEDGER_URL="$2"; shift 2 ;;
        -k|--keys-folder) USER_KEYS_FOLDER="$2"; shift 2 ;;
        -g|--guardian-url) GUARDIAN_URL="$2"; shift 2 ;;
        -h|--help)        usage; exit 0 ;;
        *)                echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$PDO_CLIENT_IMAGE" ] || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$LEDGER_CERT_PATH" ] || { echo "Missing required option: -c/--cert-path" >&2; usage >&2; exit 1; }
[ -n "$SITE_TOML_SOURCE" ] || { echo "Missing required option: -s/--site-toml" >&2; usage >&2; exit 1; }
[ -n "$F_SERVICE_HOST" ]   || { echo "Missing required option: -H/--host" >&2; usage >&2; exit 1; }
[ -n "$PDO_LEDGER_URL" ]   || { echo "Missing required option: -l/--ledger-url" >&2; usage >&2; exit 1; }
[ -n "$USER_KEYS_FOLDER" ] || { echo "Missing required option: -k/--keys-folder" >&2; usage >&2; exit 1; }
[ -n "$GUARDIAN_URL" ]     || { echo "Missing required option: -g/--guardian-url" >&2; usage >&2; exit 1; }

# Override the default CMD to run the python runner inside the container.
docker run --rm --name policies_client_container \
    --user "$(id -u):0" \
    --env PYTHONUNBUFFERED=1 \
    --volume ${LEDGER_CERT_PATH}:/tmp/networkcert.pem \
    --volume ${SITE_TOML_SOURCE}:/tmp/site.toml \
    --volume ${USER_KEYS_FOLDER}:/tmp/user_keys \
    $PDO_CLIENT_IMAGE /scripts/run_python.sh \
    --cert-path /tmp/networkcert.pem \
    --site-toml /tmp/site.toml \
    --host "$F_SERVICE_HOST" \
    --ledger-url "$PDO_LEDGER_URL" \
    --guardian-url "$GUARDIAN_URL" \
    --keys-folder /tmp/user_keys
