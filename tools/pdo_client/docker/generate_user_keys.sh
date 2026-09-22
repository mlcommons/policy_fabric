set -e

USER_KEYS_FOLDER=""
IMAGE=""
# list of user names to generate keys for
USER_NAMES=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Generate PDO user keys.

Options:
  -k, --keys-folder DIR    Folder to write user keys into (required)
  -i, --image IMAGE        PDO client image to run (required)
  -u, --users "U1 U2 ..."  Space-separated user names (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -k|--keys-folder) USER_KEYS_FOLDER="$2"; shift 2 ;;
        -i|--image)       IMAGE="$2"; shift 2 ;;
        -u|--users)       USER_NAMES="$2"; shift 2 ;;
        -h|--help)        usage; exit 0 ;;
        *)                echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$USER_KEYS_FOLDER" ] || { echo "Missing required option: -k/--keys-folder" >&2; usage >&2; exit 1; }
[ -n "$IMAGE" ] || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$USER_NAMES" ] || { echo "Missing required option: -u/--users" >&2; usage >&2; exit 1; }


# create user keys
docker run --rm --user "$(id -u):0" --volume ${USER_KEYS_FOLDER}:/tmp/users_keys \
    $IMAGE \
    /scripts/generate_user_keys.sh \
    --keys-folder /tmp/users_keys \
    --users "${USER_NAMES}"
