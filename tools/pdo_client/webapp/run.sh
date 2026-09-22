SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Server bind.
INTERFACE=""
PORT=""

# Configuration passed as args and exported as the env vars Django settings
# reads (instead of a .env file).
PDO_LEDGER_URL=""
F_SERVICE_HOST=""
LEDGER_CERT_PATH=""
SITE_TOML_SOURCE=""
USER_KEYS_FOLDER=""
SCRATCH_DIR=""
ASSET_REGISTRY_URL=""
TEMPLATE_REGISTRY_URL=""

# Optional config, with sensible defaults.
PDO_LEDGER_TYPE="ccf"
PREFERRED_ESERVICE_URL="random"
PDO_LOG_FILE="__screen__"
PDO_LOG_LEVEL="warn"

# Optional seed script: a PDO flow run after bootstrap and before runserver.
SEED_SCRIPT=""

# Django's autoreloader restarts the server whenever a source file changes, which
# drops whatever request was in flight. That is what you want while writing code
# and exactly what you do not want under a driven browser: a flow that takes
# minutes dies silently and the failure looks like the flow's.
NORELOAD=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Activate the PDO env, run migrations, bootstrap the local PDO state, then start
the dev server. Configuration is passed as args (exported as env vars that
Django settings reads); no .env file is required.

Options:
  -n, --interface IFACE          Interface for the dev server (required)
  -p, --port PORT                Port for the dev server (required)
  -l, --ledger-url URL           PDO ledger URL (required)
  -H, --service-host HOST        Service site host (required)
  -c, --cert-path PATH           Ledger network cert (required)
  -s, --site-toml PATH           Site toml source (required)
  -k, --keys-folder DIR          User keys folder (required)
  -S, --scratch DIR              Scratch dir for generated PDO state (required)
  -a, --asset-registry-url URL   Asset registry URL (required)
  -t, --template-registry-url URL Template registry URL (required)
      --ledger-type TYPE         Ledger type (default: $PDO_LEDGER_TYPE)
      --preferred-eservice URL   Preferred eservice (default: $PREFERRED_ESERVICE_URL)
      --logfile FILE             PDO log file (default: $PDO_LOG_FILE)
      --loglevel LEVEL           PDO log level (default: $PDO_LOG_LEVEL)
  -e, --seed PATH                Seed script (a PDO flow) to run after bootstrap,
                                 before the dev server starts (optional)
      --noreload                 Do not restart the server when a source file
                                 changes. Use it whenever something else is
                                 driving the app; editing a file mid-flow
                                 otherwise kills the request in flight
  -h, --help                     Show this help and exit

PDO_INSTALL_ROOT and PDO_CONTRACTS_ROOT must be set in the environment by the
caller (they are set in the image; export them for a bare-metal run).
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -n|--interface)            INTERFACE="$2"; shift 2 ;;
        -p|--port)                 PORT="$2"; shift 2 ;;
        -l|--ledger-url)           PDO_LEDGER_URL="$2"; shift 2 ;;
        -H|--service-host)         F_SERVICE_HOST="$2"; shift 2 ;;
        -c|--cert-path)            LEDGER_CERT_PATH="$2"; shift 2 ;;
        -s|--site-toml)            SITE_TOML_SOURCE="$2"; shift 2 ;;
        -k|--keys-folder)          USER_KEYS_FOLDER="$2"; shift 2 ;;
        -S|--scratch)              SCRATCH_DIR="$2"; shift 2 ;;
        -a|--asset-registry-url)   ASSET_REGISTRY_URL="$2"; shift 2 ;;
        -t|--template-registry-url) TEMPLATE_REGISTRY_URL="$2"; shift 2 ;;
        --ledger-type)             PDO_LEDGER_TYPE="$2"; shift 2 ;;
        --preferred-eservice)      PREFERRED_ESERVICE_URL="$2"; shift 2 ;;
        --logfile)                 PDO_LOG_FILE="$2"; shift 2 ;;
        --loglevel)                PDO_LOG_LEVEL="$2"; shift 2 ;;
        -e|--seed)                 SEED_SCRIPT="$2"; shift 2 ;;
        --noreload)                NORELOAD="--noreload"; shift ;;
        -h|--help)                 usage; exit 0 ;;
        *)                         echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$INTERFACE" ]             || { echo "Missing required option: -n/--interface" >&2; usage >&2; exit 1; }
[ -n "$PORT" ]                  || { echo "Missing required option: -p/--port" >&2; usage >&2; exit 1; }
[ -n "$PDO_LEDGER_URL" ]        || { echo "Missing required option: -l/--ledger-url" >&2; usage >&2; exit 1; }
[ -n "$F_SERVICE_HOST" ]        || { echo "Missing required option: -H/--service-host" >&2; usage >&2; exit 1; }
[ -n "$LEDGER_CERT_PATH" ]      || { echo "Missing required option: -c/--cert-path" >&2; usage >&2; exit 1; }
[ -n "$SITE_TOML_SOURCE" ]      || { echo "Missing required option: -s/--site-toml" >&2; usage >&2; exit 1; }
[ -n "$USER_KEYS_FOLDER" ]      || { echo "Missing required option: -k/--keys-folder" >&2; usage >&2; exit 1; }
[ -n "$SCRATCH_DIR" ]           || { echo "Missing required option: -S/--scratch" >&2; usage >&2; exit 1; }
[ -n "$ASSET_REGISTRY_URL" ]    || { echo "Missing required option: -a/--asset-registry-url" >&2; usage >&2; exit 1; }
[ -n "$TEMPLATE_REGISTRY_URL" ] || { echo "Missing required option: -t/--template-registry-url" >&2; usage >&2; exit 1; }

# PDO install roots must be provided by the caller's environment.
[ -n "$PDO_INSTALL_ROOT" ]   || { echo "PDO_INSTALL_ROOT must be set in the environment" >&2; exit 1; }
[ -n "$PDO_CONTRACTS_ROOT" ] || { echo "PDO_CONTRACTS_ROOT must be set in the environment" >&2; exit 1; }

# Export the config as env vars BEFORE sourcing activate_env.sh, so the PDO
# common-config respects PDO_LEDGER_URL (instead of defaulting to localhost)
# and Django settings reads these values from the environment.
export PDO_LEDGER_URL PDO_LEDGER_TYPE F_SERVICE_HOST
export LEDGER_CERT_PATH SITE_TOML_SOURCE USER_KEYS_FOLDER SCRATCH_DIR
export ASSET_REGISTRY_URL TEMPLATE_REGISTRY_URL PREFERRED_ESERVICE_URL
export PDO_LOG_FILE PDO_LOG_LEVEL

# Put the PDO client env in scope (activates the virtualenv and sets PDO_HOME
# etc.) so `python` resolves to the PDO client interpreter. Uses the
# PDO_INSTALL_ROOT / PDO_CONTRACTS_ROOT validated above.
source "${SCRIPT_DIR}/../setup/activate_env.sh"

python $SCRIPT_DIR/manage.py migrate
python $SCRIPT_DIR/manage.py bootstrap
if [ -n "$SEED_SCRIPT" ]; then
    [ -f "$SEED_SCRIPT" ] || { echo "Seed script not found: $SEED_SCRIPT" >&2; exit 1; }
    python -u "$SCRIPT_DIR/manage.py" seed "$SEED_SCRIPT"
fi
exec python -u "$SCRIPT_DIR/manage.py" runserver $NORELOAD "$INTERFACE:$PORT"
