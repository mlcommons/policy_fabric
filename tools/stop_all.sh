bash guardians/download/stop_services.sh
bash guardians/inference/stop_services.sh
bash pdo_client/webapp/cleanup.sh --scratch /tmp/pdo_scratch

# guardians/public runs as a plain Python process, not a container
pkill -f "guardians/public/server.py"

docker ps -q --filter ancestor=mlcommons/pdo_toy_asset_registry:v2 | xargs -r docker stop
docker ps -q --filter ancestor=mlcommons/pdo_toy_template_registry:v2 | xargs -r docker stop
docker ps -q --filter ancestor=mlcommons/toy_guardian:v2 | xargs -r docker stop
docker ps -q --filter ancestor=mlcommons/toy_inference_guardian:v2 | xargs -r docker stop
docker ps -q --filter ancestor=mlcommons/pdo_fl_server:v2 | xargs -r docker stop
docker ps -q --filter ancestor=mlcommons/pdo_ledger:v2 | xargs -r docker stop
docker ps -q --filter ancestor=mlcommons/pdo_services:v2 | xargs -r docker stop
