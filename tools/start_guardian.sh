set -e
MY_HOST="$(hostname -I | awk '{print $1}')"
: "${PF_WORKSPACE:?Missing environment variable PF_WORKSPACE}"
echo "dummy_data" > $PF_WORKSPACE/dummy_data.txt

export INTERFACE=$MY_HOST
export F_GUARDIAN_HOST=$MY_HOST
export PDO_INSTALL_ROOT=$PF_WORKSPACE/pdo_install
export PDO_CONTRACTS_ROOT=$PF_WORKSPACE/pdo-contracts
export GUARDIAN_DATA_PATH=$PF_WORKSPACE/dummy_data.txt
bash guardians/download/stop_services.sh
bash guardians/download/start_services.sh &