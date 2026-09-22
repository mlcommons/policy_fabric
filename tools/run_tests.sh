# run policy client webapp (bare metal)
: "${PF_WORKSPACE:?Missing environment variable PF_WORKSPACE}"
export PDO_INSTALL_ROOT=$PF_WORKSPACE/pdo_install
export PDO_CONTRACTS_ROOT=$PF_WORKSPACE/pdo-contracts

MY_HOST="$(hostname -I | awk '{print $1}')"
# bash pdo_client/scripts/run_cli.sh \
#     --cert-path /tmp/pdo_ledger/ccf/keys/networkcert.pem \
#     --site-toml /tmp/pdo_services/services/etc/site.toml \
#     --host $MY_HOST \
#     --ledger-url http://$MY_HOST:6600

bash pdo_client/scripts/run_python.sh \
    --cert-path /tmp/pdo_ledger/ccf/keys/networkcert.pem \
    --site-toml /tmp/pdo_services/services/etc/site.toml \
    --host $MY_HOST \
    --ledger-url http://$MY_HOST:6600 \
    --guardian-url http://$MY_HOST:7900 \
    --keys-folder /tmp/pdo_keys

