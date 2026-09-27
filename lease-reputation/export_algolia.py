# export_algolia.py — full backup of the community directory from Algolia.
# Needs NO Google access. Run from anywhere:
#   python export_algolia.py
# Output: algolia_communities_backup.json (copy it somewhere safe)

import requests
import json

APP = "6IU3SM5A9Z"
KEY = "4b264a0bb0f23c00ac4a36663ea3adde"  # admin key (browse requires it)

HOSTS = [
    f"{APP}-dsn.algolia.net",
    f"{APP}-1.algolianet.com",
    f"{APP}-2.algolianet.com",
    f"{APP}-3.algolianet.com",
]


def browse(cursor=None):
    last = None
    for host in HOSTS:
        try:
            url = f"https://{host}/1/indexes/communities/browse?hitsPerPage=1000"
            if cursor:
                url += "&cursor=" + cursor
            r = requests.get(url, headers={
                "X-Algolia-Application-Id": APP,
                "X-Algolia-API-Key": KEY,
            }, timeout=60)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError as e:
            last = e
            continue
    raise last


out, cursor = [], None
while True:
    data = browse(cursor)
    out += data.get("hits", [])
    cursor = data.get("cursor")
    print(f"  {len(out)} records...")
    if not cursor:
        break

with open("algolia_communities_backup.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"\nDONE: {len(out)} communities -> algolia_communities_backup.json")
print("Copy this file somewhere safe (not Google Drive).")
