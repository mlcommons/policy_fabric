set -e
#
# Run the webapp on this machine, against a containerized policy engine.
#
# The counterpart of docker_start_webapp.sh, and the difference is worth knowing:
# a webapp running on the host has Docker, so it starts each guardian itself
# rather than writing the command out for a host-side watcher to run (see
# app/guardian_launcher.py). Everything else -- the ledger, the enclave services,
# the registries, the guardians it starts, the FL server -- is still in
# containers.
#
# The PDO client it drives is a bare-metal install: set PDO_INSTALL_ROOT and
# PDO_CONTRACTS_ROOT to point at one. The defaults are the paths the client image
# uses internally, which is also where onboarding.md has you extract a copy to.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

export PDO_INSTALL_ROOT="${PDO_INSTALL_ROOT:-/pdo_install}"
export PDO_CONTRACTS_ROOT="${PDO_CONTRACTS_ROOT:-/pdo-contracts}"

[ -f "${PDO_INSTALL_ROOT}/bin/activate" ] || {
    echo "No PDO client at PDO_INSTALL_ROOT=${PDO_INSTALL_ROOT}." >&2
    echo "See onboarding.md for how to get one." >&2
    exit 1
}

SCRATCH_DIR="${SCRATCH_DIR:-/tmp/pdo_scratch}"
WEBAPP_PORT="${WEBAPP_PORT:-8000}"
MY_HOST="$(hostname -I | awk '{print $1}')"

# The FL server the Federated page offers first, and how a guardian container
# names that same server from inside itself. They differ because a container
# cannot reach a host-published port as "localhost"; run.sh maps in the host
# gateway alias for it.
export FL_SERVER_URL="${FL_SERVER_URL:-http://localhost:${FL_SERVER_PORT:-7920}}"
export FL_SERVER_URL_FROM_GUARDIAN="${FL_SERVER_URL_FROM_GUARDIAN:-http://host.docker.internal:${FL_SERVER_PORT:-7920}}"

bash "$SCRIPT_DIR/pdo_client/webapp/cleanup.sh" --scratch "$SCRATCH_DIR" || true

# Set WEBAPP_NORELOAD when something else is driving the app -- the browser test
# does. Editing a source file otherwise restarts the server under it and kills
# whatever flow was mid-request.
NORELOAD=()
[ -n "${WEBAPP_NORELOAD:-}" ] && NORELOAD=(--noreload)

bash "$SCRIPT_DIR/pdo_client/webapp/run.sh" \
    "${NORELOAD[@]}" \
    --interface "${WEBAPP_INTERFACE:-127.0.0.1}" \
    --port "$WEBAPP_PORT" \
    --cert-path /tmp/pdo_ledger/ccf/keys/networkcert.pem \
    --site-toml /tmp/pdo_services/services/etc/site.toml \
    --keys-folder /tmp/pdo_keys \
    --scratch "$SCRATCH_DIR" \
    --ledger-url "http://$MY_HOST:6600" \
    --service-host "$MY_HOST" \
    --asset-registry-url "http://$MY_HOST:8001" \
    --template-registry-url "http://$MY_HOST:8002"
