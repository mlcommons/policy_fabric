set -e
# Clone pdo-contracts into PDO_CONTRACTS_ROOT and check out the wanted branch.
: "${PDO_CONTRACTS_ROOT:?Missing environment variable PDO_CONTRACTS_ROOT}"

REPOSITORY=""
BRANCH=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Clone pdo-contracts into PDO_CONTRACTS_ROOT and check out the branch.

Options:
  -r, --repository URL     pdo-contracts git repository (required)
  -b, --branch BRANCH      Branch to check out (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -r|--repository) REPOSITORY="$2"; shift 2 ;;
        -b|--branch)     BRANCH="$2"; shift 2 ;;
        -h|--help)       usage; exit 0 ;;
        *)               echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$REPOSITORY" ] || { echo "Missing required option: -r/--repository" >&2; usage >&2; exit 1; }
[ -n "$BRANCH" ]     || { echo "Missing required option: -b/--branch" >&2; usage >&2; exit 1; }

git clone ${REPOSITORY} ${PDO_CONTRACTS_ROOT}
cd ${PDO_CONTRACTS_ROOT}
git checkout ${BRANCH}
git submodule update --init --recursive
