TEMPLATE_REGISTRY_IMAGE=""
INTERFACE=""
PORT=""
CREDENTIALS_DIR=""
POLICY_CARDS_DIR=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the template_registry container.

Options:
  -i, --image IMAGE           Docker image to run (required)
  -n, --interface IFACE       Host interface to publish (required)
  -p, --port PORT             Host port to publish (required)
  -c, --credentials-dir DIR   Host folder of credential JSON Schemas (required)
  -d, --policy-cards-dir DIR  Host folder of policy-card subfolders (required)
  -h, --help                  Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image)           TEMPLATE_REGISTRY_IMAGE="$2"; shift 2 ;;
        -n|--interface)       INTERFACE="$2"; shift 2 ;;
        -p|--port)            PORT="$2"; shift 2 ;;
        -c|--credentials-dir) CREDENTIALS_DIR="$2"; shift 2 ;;
        -d|--policy-cards-dir) POLICY_CARDS_DIR="$2"; shift 2 ;;
        -h|--help)            usage; exit 0 ;;
        *)                    echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$TEMPLATE_REGISTRY_IMAGE" ] || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$INTERFACE" ]               || { echo "Missing required option: -n/--interface" >&2; usage >&2; exit 1; }
[ -n "$PORT" ]                    || { echo "Missing required option: -p/--port" >&2; usage >&2; exit 1; }
[ -n "$CREDENTIALS_DIR" ]         || { echo "Missing required option: -c/--credentials-dir" >&2; usage >&2; exit 1; }
[ -n "$POLICY_CARDS_DIR" ]        || { echo "Missing required option: -d/--policy-cards-dir" >&2; usage >&2; exit 1; }

# seed_templates reads these folders (they are not baked into the image), so
# bind-mount them onto the container paths the image's CMD passes to run.sh
# (/templates/credentials and /templates/policy_cards). docker -v needs absolute
# paths, so resolve each (which also verifies it is an existing directory).
CREDENTIALS_ABS="$( cd "$CREDENTIALS_DIR" 2>/dev/null && pwd )"   || { echo "Missing credentials folder: $CREDENTIALS_DIR" >&2; exit 1; }
POLICY_CARDS_ABS="$( cd "$POLICY_CARDS_DIR" 2>/dev/null && pwd )" || { echo "Missing policy_cards folder: $POLICY_CARDS_DIR" >&2; exit 1; }

# Replace any registry already running under this name, the way the guardians
# do. Without this a restart onto a new image fails on the name, leaving the old
# container answering on the port -- which looks like the new one, with the old
# one's seeded templates.
docker rm -f template_registry_container >/dev/null 2>&1 || true

docker run --rm --user "$(id -u):0" --name template_registry_container \
    -p $INTERFACE:$PORT:8000 \
    -v "$CREDENTIALS_ABS":/templates/credentials:ro \
    -v "$POLICY_CARDS_ABS":/templates/policy_cards:ro \
    $TEMPLATE_REGISTRY_IMAGE
