set -e
SCRIPT_DIR=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
SCRIPTS_DIR=${SCRIPT_DIR}
: "${PDO_INSTALL_ROOT:?Missing environment variable PDO_INSTALL_ROOT}"
: "${PDO_CONTRACTS_ROOT:?Missing environment variable PDO_CONTRACTS_ROOT}"

LEDGER_CERT_PATH=""
SITE_TOML_SOURCE=""
F_SERVICE_HOST=""
PDO_LEDGER_URL=""
USER_KEYS_FOLDER=""
GUARDIAN_URL=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the rego-contract python test against a running ledger + services +
guardian. User keys must already exist in --keys-folder; generate them first
with generate_user_keys.sh.

Options:
  -c, --cert-path PATH     Ledger network cert (required)
  -s, --site-toml PATH     Site toml source (required)
  -H, --host HOST          Service host / F_SERVICE_HOST (required)
  -l, --ledger-url URL     Ledger URL (required)
  -g, --guardian-url URL   Guardian URL (required)
  -k, --keys-folder DIR    Existing user keys folder (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -c|--cert-path)   LEDGER_CERT_PATH="$2"; shift 2 ;;
        -s|--site-toml)   SITE_TOML_SOURCE="$2"; shift 2 ;;
        -H|--host)        F_SERVICE_HOST="$2"; shift 2 ;;
        -l|--ledger-url)  PDO_LEDGER_URL="$2"; shift 2 ;;
        -g|--guardian-url) GUARDIAN_URL="$2"; shift 2 ;;
        -k|--keys-folder) USER_KEYS_FOLDER="$2"; shift 2 ;;
        -h|--help)        usage; exit 0 ;;
        *)                echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$LEDGER_CERT_PATH" ] || { echo "Missing required option: -c/--cert-path" >&2; usage >&2; exit 1; }
[ -n "$SITE_TOML_SOURCE" ] || { echo "Missing required option: -s/--site-toml" >&2; usage >&2; exit 1; }
[ -n "$F_SERVICE_HOST" ]   || { echo "Missing required option: -H/--host" >&2; usage >&2; exit 1; }
[ -n "$PDO_LEDGER_URL" ]   || { echo "Missing required option: -l/--ledger-url" >&2; usage >&2; exit 1; }
[ -n "$GUARDIAN_URL" ]     || { echo "Missing required option: -g/--guardian-url" >&2; usage >&2; exit 1; }
[ -n "$USER_KEYS_FOLDER" ] || { echo "Missing required option: -k/--keys-folder" >&2; usage >&2; exit 1; }

source ${SCRIPT_DIR}/../setup/activate_env.sh

PYTHON_TEST_DIR=${PDO_CONTRACTS_ROOT}/rego-contract/test/python

export LEDGER_CERT_PATH SITE_TOML_SOURCE F_SERVICE_HOST PDO_LEDGER_URL USER_KEYS_FOLDER GUARDIAN_URL
python ${PYTHON_TEST_DIR}/startup.py
python ${PYTHON_TEST_DIR}/stateless_test.py
python ${PYTHON_TEST_DIR}/cleanup.py
