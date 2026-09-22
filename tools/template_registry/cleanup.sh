SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
pkill -f "$SCRIPT_DIR/manage.py runserver"
rm $SCRIPT_DIR/db.sqlite3