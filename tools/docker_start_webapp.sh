SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

rm -rf $SCRIPT_DIR/pdo_scratch
mkdir -p $SCRIPT_DIR/pdo_scratch


INTERFACE="$(hostname -I | awk '{print $1}')"
# 8000 is what the tutorial and the devcontainer's forwarded port expect;
# WEBAPP_PORT is for a host that already has something there.
bash pdo_client/docker/run_webapp.sh \
    --csrf-trusted-origins "${CSRF_TRUSTED_ORIGINS:-}" \
    --image mlcommons/pdo_base_client:v2 \
    --interface 127.0.0.1 \
    --port "${WEBAPP_PORT:-8000}" \
    --cert-path /tmp/pdo_ledger/ccf/keys/networkcert.pem \
    --site-toml /tmp/pdo_services/services/etc/site.toml \
    --keys-folder /tmp/pdo_keys \
    --scratch $SCRIPT_DIR/pdo_scratch \
    --ledger-url http://$INTERFACE:6600 \
    --service-host $INTERFACE \
    --asset-registry-url http://$INTERFACE:8001 \
    --template-registry-url http://$INTERFACE:8002
    # --seed $SCRIPT_DIR/pdo_client/webapp/seeds/example_seed.py