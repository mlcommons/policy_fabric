docker ps -q --filter ancestor=mlcommons/pdo_toy_asset_registry:v2 | xargs -r docker stop
docker ps -q --filter ancestor=mlcommons/pdo_toy_template_registry:v2 | xargs -r docker stop
docker ps -q --filter ancestor=mlcommons/pdo_base_client:v2 | xargs -r docker stop
docker ps -q --filter ancestor=mlcommons/toy_guardian:v2 | xargs -r docker stop
docker ps -q --filter ancestor=mlcommons/toy_inference_guardian:v2 | xargs -r docker stop
docker ps -q --filter ancestor=mlcommons/pdo_fl_server:v2 | xargs -r docker stop
docker ps -q --filter ancestor=mlcommons/pdo_ledger:v2 | xargs -r docker stop
docker ps -q --filter ancestor=mlcommons/pdo_services:v2 | xargs -r docker stop

# guardians/public runs as a plain Python process, not a container
pkill -f "guardians/public/server.py"
