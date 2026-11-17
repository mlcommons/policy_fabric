set -e
# usage: docker_start_guardian.sh <data file>, the file the download guardian serves
# (make_tutorial_files.sh writes /tmp/asset_data.txt)
DATA_PATH="${1:?usage: docker_start_guardian.sh <data file>}"
INTERFACE="$(hostname -I | awk '{print $1}')"
bash guardians/download/run.sh \
    --image mlcommons/toy_guardian:v3 \
    --interface $INTERFACE \
    --port 7900 \
    --sservice-port 7901 \
    --guardian-host $INTERFACE \
    --data-path "$DATA_PATH" &