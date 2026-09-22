MY_HOST=$(hostname -I | awk '{print $1}')

# run policy client cli test
bash pdo_client/docker/run_cli.sh \
    --image mlcommons/pdo_base_client:v2 \
    --cert-path /tmp/pdo_ledger/ccf/keys/networkcert.pem \
    --site-toml /tmp/pdo_services/services/etc/site.toml \
    --host $MY_HOST \
    --ledger-url http://$MY_HOST:6600 \
    --eservice-url random

# run policy client python test
bash pdo_client/docker/run_python.sh \
    --image mlcommons/pdo_base_client:v2 \
    --cert-path /tmp/pdo_ledger/ccf/keys/networkcert.pem \
    --site-toml /tmp/pdo_services/services/etc/site.toml \
    --host $MY_HOST \
    --ledger-url http://$MY_HOST:6600 \
    --guardian-url http://$MY_HOST:7900 \
    --keys-folder /tmp/pdo_keys