set -e

# pdo-contracts revision the client image (and therefore the compiled contract
# binaries) is built from. It must be one that carries rego_token's
# create_capability op and the guardian request context, since the inference
# flow issues a capability the FL client redeems later rather than redeeming it
# inline.
REPOSITORY=https://github.com/mlcommons/pdo-contracts
BRANCH=a4323c18a2f9dc3e54652c0a08c9692b2d13dacc

# Bumped together whenever the images are rebuilt, so a new build never
# overwrites the tag a running deployment already pulled.
TAG=v2

bash asset_registry/build.sh \
    --image mlcommons/pdo_toy_asset_registry:$TAG

bash template_registry/build.sh \
    --image mlcommons/pdo_toy_template_registry:$TAG

bash pdo_client/build.sh \
    --image mlcommons/pdo_base_client:$TAG \
    --repository $REPOSITORY \
    --branch $BRANCH \
    --families "exchange-contract identity-contract authority-contract rego-contract"

bash guardians/download/build.sh \
    --image mlcommons/toy_guardian:$TAG \
    --client-image mlcommons/pdo_base_client:$TAG

bash guardians/inference/build.sh \
    --image mlcommons/toy_inference_guardian:$TAG \
    --client-image mlcommons/pdo_base_client:$TAG

# The FL server stands outside the PDO stack entirely -- a stdlib-only image off
# python:slim, sharing none of the layers above -- because it is the one component
# here that a federation would run itself.
bash fl_server/build.sh \
    --image mlcommons/pdo_fl_server:$TAG

# guardians/public is a plain Python process; nothing to build.

# The ledger and the services carry the CCF app and the enclaves the client talks
# to, so they are not independent of the revision above: a client built from one
# pdo-contracts revision and a ledger built from another disagree about the
# contract-registration schema, and every contract creation fails. Build all of
# them from $BRANCH or none of them.
bash policy_engine/build_pdo_images.sh \
    --ledger-image mlcommons/pdo_ledger:$TAG \
    --services-image mlcommons/pdo_services:$TAG \
    --repository $REPOSITORY \
    --branch $BRANCH

docker push mlcommons/pdo_toy_asset_registry:$TAG
docker push mlcommons/pdo_toy_template_registry:$TAG
docker push mlcommons/pdo_base_client:$TAG
docker push mlcommons/toy_guardian:$TAG
docker push mlcommons/toy_inference_guardian:$TAG
docker push mlcommons/pdo_fl_server:$TAG
docker push mlcommons/pdo_ledger:$TAG
docker push mlcommons/pdo_services:$TAG
