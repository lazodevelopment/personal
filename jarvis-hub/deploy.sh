#!/bin/bash
# Deploy the JARVIS hub with its own Cloudflare token (JARVIS_CF_TOKEN in ../lazo-directory/.env, account d16dd804),
# so it works no matter which account the shared `wrangler login` is pointing at.
#   bash deploy.sh            deploy
#   bash deploy.sh tail       live logs
#   bash deploy.sh kv KEY     read a KV value
set -e
cd "$(dirname "$0")"
TOK="$(grep '^JARVIS_CF_TOKEN=' ../lazo-directory/.env | head -1 | cut -d= -f2- | tr -d '"'"'"' \r')"
[ -n "$TOK" ] || { echo "JARVIS_CF_TOKEN missing from ../lazo-directory/.env (store it with lazo-directory/deploy/set_secret.ps1 JARVIS_CF_TOKEN)"; exit 1; }
export CLOUDFLARE_API_TOKEN="$TOK" CLOUDFLARE_ACCOUNT_ID=d16dd804f8ecdb56655189fa806f43af
case "${1:-deploy}" in
  deploy) npx wrangler deploy 2>&1 | grep -E "Version|ERROR|error|schedule" ;;
  tail) shift; npx wrangler tail jarvis-hub --format pretty "$@" ;;
  kv) npx wrangler kv key get --namespace-id 1592670000454ad4b1cfe3967d837f37 "$2" --remote ;;
  secret) npx wrangler secret put "$2" ;;
  *) echo "usage: deploy.sh [deploy|tail|kv KEY|secret NAME]"; exit 2 ;;
esac
