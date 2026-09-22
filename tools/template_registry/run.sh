SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INTERFACE=""
PORT=""
CREDENTIALS_DIR=""
POLICY_CARDS_DIR=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run migrations, seed the templates and the dev admin user, then start the dev
server.

Options:
  -n, --interface IFACE       Interface for the dev server (required)
  -p, --port PORT             Port for the dev server (required)
  -c, --credentials-dir DIR   Folder of credential JSON Schemas (required)
  -d, --policy-cards-dir DIR  Folder of policy-card subfolders (required)
  -h, --help                  Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -n|--interface)       INTERFACE="$2"; shift 2 ;;
        -p|--port)            PORT="$2"; shift 2 ;;
        -c|--credentials-dir) CREDENTIALS_DIR="$2"; shift 2 ;;
        -d|--policy-cards-dir) POLICY_CARDS_DIR="$2"; shift 2 ;;
        -h|--help)            usage; exit 0 ;;
        *)                    echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$INTERFACE" ]        || { echo "Missing required option: -n/--interface" >&2; usage >&2; exit 1; }
[ -n "$PORT" ]             || { echo "Missing required option: -p/--port" >&2; usage >&2; exit 1; }
[ -n "$CREDENTIALS_DIR" ]  || { echo "Missing required option: -c/--credentials-dir" >&2; usage >&2; exit 1; }
[ -n "$POLICY_CARDS_DIR" ] || { echo "Missing required option: -d/--policy-cards-dir" >&2; usage >&2; exit 1; }

# seed_templates reads these from the environment.
export CREDENTIALS_DIR POLICY_CARDS_DIR

python $SCRIPT_DIR/manage.py migrate
# Seed the policy/credential templates from the folders given above.
python $SCRIPT_DIR/manage.py seed_templates
# Dev-only admin user for the Django admin dashboard at /admin/.
DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_PASSWORD=admin \
DJANGO_SUPERUSER_EMAIL=admin@example.com \
python $SCRIPT_DIR/manage.py createsuperuser --noinput
exec python -u "$SCRIPT_DIR/manage.py" runserver "$INTERFACE:$PORT"
