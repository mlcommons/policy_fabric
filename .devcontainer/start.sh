#!/usr/bin/env bash
#
# Codespaces startup: bring up the whole PDO stack and the webapp, then print the
# URL to open. Run automatically by the devcontainer's postStartCommand; safe to
# re-run (it skips startup when the webapp is already running).
#
# It does NOT run the demo seed — the tutorial creates everything by hand.

set -eEuo pipefail

REPO="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
# The docker_*.sh orchestration scripts below invoke their per-service helpers by
# relative path, so they have to run from the tools/ directory that holds them.
TOOLS="$REPO/tools"
cd "$TOOLS"

# Where the Docker daemon keeps its images, and roughly the room they need
# there: about 8GB unpacked — they share most of their layers, so well under the
# sum of the sizes `docker images` lists for them — plus headroom for the
# concurrent pulls below, which hold their compressed downloads at the same time.
DOCKER_ROOT=/var/lib/docker
[ -d "$DOCKER_ROOT" ] || DOCKER_ROOT=/
REQUIRED_GB=12

# Report a failure and stop, but leave the codespace created: a non-zero exit
# from the postStartCommand aborts container creation altogether and hands the
# user a bare recovery container, with none of this workspace to debug from.
abort() {
    cat >&2 <<EOF

============================================================
 STARTUP FAILED: $*

$(df -h "$DOCKER_ROOT" | sed 's/^/ /')

 Re-run once the cause is fixed:  bash .devcontainer/start.sh
============================================================
EOF
    exit 0
}
trap 'abort "command failed: $BASH_COMMAND"' ERR

# Poll a command until it succeeds, giving up after a deadline so a service that
# never comes up fails the startup instead of hanging it forever.
wait_for() {
    local description="$1" timeout="$2"
    shift 2
    local deadline=$(( SECONDS + timeout ))
    until "$@" >/dev/null 2>&1; do
        if [ "$SECONDS" -ge "$deadline" ]; then
            echo "Timed out after ${timeout}s waiting for $description" >&2
            return 1
        fi
        sleep 2
    done
}

# Already up? nothing to do.
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^policies_web_client$'; then
    echo "PDO webapp already running — open the forwarded port 8000."
    exit 0
fi

echo "==> Waiting for the Docker daemon"
wait_for "the Docker daemon" 300 docker info

# Filling the disk partway through a pull reports only "no space left on device"
# against an unnamed layer, so measure the room the images need before starting.
available_gb=$(df -BG --output=avail "$DOCKER_ROOT" | tail -n 1 | tr -dc '0-9')
if [ "$available_gb" -lt "$REQUIRED_GB" ]; then
    abort "only ${available_gb}GB free under $DOCKER_ROOT, and the images need about ${REQUIRED_GB}GB. Reclaim space with 'docker system prune -a', or recreate the codespace on a machine type with a larger disk."
fi

# Pull the images up front so the timed waits in the start scripts below are
# meaningful (otherwise the first `docker run` would also be pulling). The pulls
# are independent of each other, so run them concurrently.
echo "==> Pulling images (first run only; this can take a few minutes)"
PULL_PIDS=()
PULL_IMAGES=()
for img in \
    mlcommons/pdo_ledger:v2 \
    mlcommons/pdo_services:v2 \
    mlcommons/pdo_base_client:v2 \
    mlcommons/pdo_toy_asset_registry:v2 \
    mlcommons/pdo_toy_template_registry:v2 \
    mlcommons/toy_guardian:v2 \
    mlcommons/toy_inference_guardian:v2 \
    mlcommons/pdo_fl_server:v2 ; do
    docker pull --quiet "$img" >/dev/null &
    PULL_PIDS+=("$!")
    PULL_IMAGES+=("$img")
done
# Wait on every pull before reporting, so one failure names its own image rather
# than surfacing as an unattributed layer error from whichever pull hit it.
PULL_FAILED=""
for i in "${!PULL_PIDS[@]}"; do
    wait "${PULL_PIDS[$i]}" || PULL_FAILED="$PULL_FAILED ${PULL_IMAGES[$i]}"
done
[ -z "$PULL_FAILED" ] || abort "could not pull:$PULL_FAILED"

echo "==> Generating user keys"
bash docker_generate_user_keys.sh

echo "==> Starting the policy engine (ledger + services)"
bash docker_start_policy_engine.sh

# The services container writes site.toml once every enclave service is
# registered; the webapp needs that file to configure its PDO client.
echo "==> Waiting for the enclave services"
wait_for "the enclave services" 600 test -f /tmp/pdo_services/services/etc/site.toml

echo "==> Starting the asset and template registries"
bash docker_start_registries.sh
# Both registries are small Django apps whose images are already local by now,
# so a short fixed pause covers the two of them.
sleep 10

echo "==> Creating the tutorial files"
bash make_tutorial_files.sh

# The inference tutorial's job board. Both the webapp (which submits rounds) and
# the FL client bundled with each inference guardian (which announces itself to it
# and claims work from it) talk to it, so it comes up before either of them -- a
# client that starts with no server to announce to is a site nobody can see.
echo "==> Starting the FL server"
nohup bash start_fl_server.sh > /tmp/pdo_fl_server.log 2>&1 &
wait_for "the FL server" 120 curl -sf http://localhost:7920/info

echo "==> Starting the webapp (with the guardian deploy watcher)"
export CSRF_TRUSTED_ORIGINS="https://*.app.github.dev,https://*.githubpreview.dev"
nohup bash docker_start_webapp.sh > /tmp/pdo_webapp.log 2>&1 &

echo "==> Giving the WebUI a moment to come up on port 8000"
sleep 10

cat <<EOF

============================================================
 Open the forwarded URL for port 8000 (see the "Ports" tab),
 then follow the tutorial.

 Webapp logs:    /tmp/pdo_webapp.log
 FL server logs: /tmp/pdo_fl_server.log
 Guardian logs:  $TOOLS/pdo_scratch/guardian_requests/guardian_deploy.log
 Data files:     /tmp/asset_data.txt (download tutorial)
                 /tmp/hospital_a_cohort.csv, /tmp/hospital_b_cohort.csv
                 and /tmp/inference_script.py (federated inference tutorial)
============================================================
EOF
