ESERVICE=""

usage() {
    cat <<EOF
Usage: $(basename "$0") -e N

Dump an eservice log from the running services_container.

Options:
  -e, --eservice N         Eservice number (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -e|--eservice) ESERVICE="$2"; shift 2 ;;
        -h|--help)     usage; exit 0 ;;
        *)             echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

: "${ESERVICE:?Missing required argument --eservice}"

docker exec services_container bash -c "cat /project/pdo/run/opt/pdo/logs/eservice${ESERVICE}.log"
