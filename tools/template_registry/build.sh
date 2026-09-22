SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TEMPLATE_REGISTRY_IMAGE=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Build the template_registry Docker image.

Options:
  -i, --image IMAGE        Image tag to build (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image) TEMPLATE_REGISTRY_IMAGE="$2"; shift 2 ;;
        -h|--help)  usage; exit 0 ;;
        *)          echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$TEMPLATE_REGISTRY_IMAGE" ] || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }

docker build -t $TEMPLATE_REGISTRY_IMAGE -f $SCRIPT_DIR/Dockerfile $SCRIPT_DIR
