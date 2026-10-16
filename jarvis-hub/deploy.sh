#!/bin/bash
# Deploy the JARVIS hub with its own Cloudflare token (JARVIS_CF_TOKEN in ../lazo-directory/.env, account d16dd804),
# so it works no matter which account the shared `wrangler login` is pointing at.
#   bash deploy.sh            deploy
#   bash deploy.sh tail       live logs
#   bash deploy.sh kv KEY     read a KV value
#   bash deploy.sh vm         copy the feeder scripts + crontab to the jarvis-feeder VM and reinstall the crontab
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
  vm) G="gcloud compute --project lazo-513ec --account lazodevelopment@gmail.com"
      $G scp --zone us-central1-a collect_flights.py collect_traffic.py collect_metrics.py collect_cams.py collect_watch.py collect_ships.py jarvis_hands.py cloud/crontab.txt jarvis-feeder:jarvis/
      $G ssh jarvis-feeder --zone us-central1-a --command 'cd ~/jarvis && sed "s#__HOME__#$HOME#g" crontab.txt | tr -d "\r" | crontab - && crontab -l | grep -vc "^#" && md5sum *.py | sort -k2' ;;
  *) echo "usage: deploy.sh [deploy|tail|kv KEY|secret NAME|vm]"; exit 2 ;;
esac
