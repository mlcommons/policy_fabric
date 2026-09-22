rm -rf /tmp/pdo_keys
mkdir -p /tmp/pdo_keys
bash pdo_client/docker/generate_user_keys.sh \
    --keys-folder /tmp/pdo_keys \
    --image mlcommons/pdo_base_client:v2 \
    --users "user1 user2 user3 user4 user5 data_owner data_user vc_issuer hospital_a hospital_b"
