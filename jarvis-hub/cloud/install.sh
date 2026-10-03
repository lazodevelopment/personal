#!/bin/bash
# Runs on the jarvis-feeder VM (called by setup_feeder.ps1 over SSH). Idempotent.
set -e
cd "$HOME/jarvis"
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv curl >/dev/null
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q firebase-admin google-cloud-firestore google-auth requests tzdata
chmod 600 .hub-key
sed "s#__HOME__#$HOME#g" crontab.txt | tr -d '\r' | crontab -
echo "cron installed:"; crontab -l | grep -v '^#'

echo; echo "Can this VM reach the feeds that refuse Cloudflare?"
for u in \
  "https://api.adsb.lol/v2/lat/33.15/lon/-96.82/dist/5" \
  "https://opendata.adsb.fi/api/v2/lat/33.15/lon/-96.82/dist/5" \
  "https://opensky-network.org/api/states/all?lamin=33&lomin=-97&lamax=33.3&lomax=-96.6" \
  "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard" \
  "https://itunes.apple.com/lookup?id=6812863675&country=us" \
  "https://its.txdot.gov/its/DistrictIts/GetCctvStatusListByDistrict?districtCode=DAL"; do
  printf '%-90s %s\n' "$u" "$(curl -s -o /dev/null -m 20 -A 'Mozilla/5.0 (JARVIS hub)' -w '%{http_code}' "$u")"
done

echo; echo "First runs:"
.venv/bin/python collect_watch.py --only payments,search,ios 2>&1 | tail -2
.venv/bin/python collect_metrics.py 2>&1 | tail -3
.venv/bin/python collect_traffic.py 2>&1 | tail -3
.venv/bin/python collect_flights.py 2>&1 | tail -2
