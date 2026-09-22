set -e

USER_KEYS_FOLDER=""
USER_NAMES=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Generate PDO user keys.

Options:
  -k, --keys-folder DIR    Folder to write user keys into (required)
  -u, --users "U1 U2 ..."  Space-separated user names (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -k|--keys-folder) USER_KEYS_FOLDER="$2"; shift 2 ;;
        -u|--users)       USER_NAMES="$2"; shift 2 ;;
        -h|--help)        usage; exit 0 ;;
        *)                echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$USER_KEYS_FOLDER" ] || { echo "Missing required option: -k/--keys-folder" >&2; usage >&2; exit 1; }
[ -n "$USER_NAMES" ] || { echo "Missing required option: -u/--users" >&2; usage >&2; exit 1; }

SCRIPT_DIR=$(dirname $(readlink -f ${BASH_SOURCE[0]}))

source ${SCRIPT_DIR}/../setup/activate_env.sh

for name in ${USER_NAMES} ; do
    if [ ! -f ${USER_KEYS_FOLDER}/${name}_private.pem ] ; then
        python $PDO_SOURCE_ROOT/build/__tools__/make-keys \
            --keyfile $USER_KEYS_FOLDER/${name} --format pem
    fi
done