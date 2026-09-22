set -e
SCRIPT_DIR=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
SCRIPTS_DIR=${SCRIPT_DIR}
: "${PDO_INSTALL_ROOT:?Missing environment variable PDO_INSTALL_ROOT}"
: "${PDO_CONTRACTS_ROOT:?Missing environment variable PDO_CONTRACTS_ROOT}"

LEDGER_CERT_PATH=""
SITE_TOML_SOURCE=""
F_SERVICE_HOST=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the legacy rego system test via 'make test' on the local install.

Options:
  -c, --cert-path PATH     Ledger network cert (required)
  -s, --site-toml PATH     Site toml source (required)
  -H, --host HOST          Service host / F_SERVICE_HOST (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -c|--cert-path) LEDGER_CERT_PATH="$2"; shift 2 ;;
        -s|--site-toml) SITE_TOML_SOURCE="$2"; shift 2 ;;
        -H|--host)      F_SERVICE_HOST="$2"; shift 2 ;;
        -h|--help)      usage; exit 0 ;;
        *)              echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$LEDGER_CERT_PATH" ] || { echo "Missing required option: -c/--cert-path" >&2; usage >&2; exit 1; }
[ -n "$SITE_TOML_SOURCE" ] || { echo "Missing required option: -s/--site-toml" >&2; usage >&2; exit 1; }
[ -n "$F_SERVICE_HOST" ]   || { echo "Missing required option: -H/--host" >&2; usage >&2; exit 1; }

source ${SCRIPT_DIR}/../setup/activate_env.sh
bash ${SCRIPTS_DIR}/prepare_site.sh \
    --cert-path "$LEDGER_CERT_PATH" \
    --site-toml "$SITE_TOML_SOURCE" \
    --host "$F_SERVICE_HOST" \
    --pdo-home "$PDO_HOME"

TEST_LIST=^system-rego-script make -C ${PDO_CONTRACTS_ROOT} test
