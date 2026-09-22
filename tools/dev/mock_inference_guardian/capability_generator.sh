#!/usr/bin/env bash
set -euo pipefail

OUTPUT="./capability.b64"
METHOD_NAME="do_inference"

usage() {
    cat <<EOF
Usage: $(basename "$0") HASH

Write a capability package authorizing HASH, base64-encoded, to $OUTPUT.
Real capabilities are encrypted, this one is b64-encoded. Anyway, the FL client
shouldn't try to parse it at all (it shouldn't care whether it is encrypted or
b64-encoded. It is just a blob.)
EOF
}

case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    "")        echo "Missing required argument: HASH" >&2; usage >&2; exit 1 ;;
esac

HASH="$1"

b64() { base64 -w 0; }

rand_b64() { head -c "$1" /dev/urandom | b64; }

json_escape() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }

OPERATION=$(printf '{"nonce":"%s","request_identifier":"%s","method_name":"%s","parameters":{"script_digest":"%s"}}' \
    "$(rand_b64 32)" \
    "$(rand_b64 8)" \
    "$METHOD_NAME" \
    "$(json_escape "$HASH")")

CAPABILITY=$(printf '{"minted_identity":"%s","operation":{"encrypted_session_key":"%s","session_key_iv":"%s","encrypted_message":"%s"}}' \
    "$(rand_b64 32)" \
    "$(rand_b64 256)" \
    "$(rand_b64 16)" \
    "$(printf '%s' "$OPERATION" | b64)")

printf '%s' "$CAPABILITY" | b64 > "$OUTPUT"

cat >&2 <<EOF
Capability written to $OUTPUT ($(wc -c < "$OUTPUT") bytes, base64).

Redeem it with:

  ./redeem.py -f $OUTPUT -c $HASH
EOF
