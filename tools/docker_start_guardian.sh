set -e
INTERFACE="$(hostname -I | awk '{print $1}')"
bash guardians/download/run.sh \
    --image mlcommons/toy_guardian:v2 \
    --interface $INTERFACE \
    --port 7900 \
    --sservice-port 7901 \
    --guardian-host $INTERFACE &