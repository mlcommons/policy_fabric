set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The FL server is reached from two directions: the webapp submits rounds to it
# and each inference guardian's FL client polls it, so it binds every interface.
#
# It is a long-lived service, deliberately not started by the webapp: a federated
# round is submitted to an FL server that is already there, chosen by whoever
# asks for the round. FL_SERVER_PORT lets a second one run beside the first.
bash ${SCRIPT_DIR}/fl_server/run.sh \
    --image "${FL_SERVER_IMAGE:-mlcommons/pdo_fl_server:v2}" \
    --interface 0.0.0.0 \
    --port "${FL_SERVER_PORT:-7920}" &
