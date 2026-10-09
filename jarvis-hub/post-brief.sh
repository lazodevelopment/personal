#!/usr/bin/env bash
# Post a JSON state payload (read from stdin) to the JARVIS hub.
# Usage: bash /c/Users/kurvh/jarvis-hub/post-brief.sh <<'EOF'
#        {"brief":{...}}
#        EOF
# Prints the HTTP status on the first line and the response body after it.
# The hub key is read from .hub-key next to this script and never printed.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEY="$(cat "$HERE/.hub-key")"
BODY="$(mktemp)"
trap 'rm -f "$BODY"' EXIT
STATUS="$(curl -s -o "$BODY" -w '%{http_code}' -X POST \
  -H 'content-type: application/json' \
  -H "x-hub-key: $KEY" \
  --data-binary @- \
  https://jarvis-hub.floral-credit-e4f0.workers.dev/api/state)"
echo "$STATUS"
cat "$BODY"
echo
[ "$STATUS" = "200" ]
