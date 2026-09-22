SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SCRATCH_DIR=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Stop the dev server, remove the sqlite db, and delete the scratch dir.

Options:
  -S, --scratch DIR        Scratch dir to delete (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -S|--scratch) SCRATCH_DIR="$2"; shift 2 ;;
        -h|--help)    usage; exit 0 ;;
        *)            echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$SCRATCH_DIR" ] || { echo "Missing required option: -S/--scratch" >&2; usage >&2; exit 1; }

pkill -f "$SCRIPT_DIR/manage.py runserver"
rm -f $SCRIPT_DIR/db.sqlite3
rm -rf "$SCRATCH_DIR"
