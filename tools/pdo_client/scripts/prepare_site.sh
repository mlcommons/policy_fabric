set -e
# Copy the ledger network cert and the site toml into the locations the client
# expects under PDO_HOME.

LEDGER_CERT_PATH=""
SITE_TOML_SOURCE=""
F_SERVICE_HOST=""
PDO_HOME=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Copy the ledger network cert and site toml into the client's PDO_HOME.

Options:
  -c, --cert-path PATH     Ledger network cert (required)
  -s, --site-toml PATH     Site toml source (required)
  -H, --host HOST          Service host / F_SERVICE_HOST (required)
  -d, --pdo-home DIR       PDO_HOME directory (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -c|--cert-path) LEDGER_CERT_PATH="$2"; shift 2 ;;
        -s|--site-toml) SITE_TOML_SOURCE="$2"; shift 2 ;;
        -H|--host)      F_SERVICE_HOST="$2"; shift 2 ;;
        -d|--pdo-home)  PDO_HOME="$2"; shift 2 ;;
        -h|--help)      usage; exit 0 ;;
        *)              echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$LEDGER_CERT_PATH" ] || { echo "Missing required option: -c/--cert-path" >&2; usage >&2; exit 1; }
[ -n "$SITE_TOML_SOURCE" ] || { echo "Missing required option: -s/--site-toml" >&2; usage >&2; exit 1; }
[ -n "$F_SERVICE_HOST" ]   || { echo "Missing required option: -H/--host" >&2; usage >&2; exit 1; }
[ -n "$PDO_HOME" ]         || { echo "Missing required option: -d/--pdo-home" >&2; usage >&2; exit 1; }

PDO_LEDGER_KEY_ROOT=${PDO_HOME}/etc/keys/ledger
mkdir -p ${PDO_LEDGER_KEY_ROOT}
cp ${LEDGER_CERT_PATH} ${PDO_LEDGER_KEY_ROOT}/networkcert.pem
mkdir -p ${PDO_HOME}/etc/sites
cp ${SITE_TOML_SOURCE} ${PDO_HOME}/etc/sites/${F_SERVICE_HOST}.toml
