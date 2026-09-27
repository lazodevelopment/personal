# backfill_algolia.py — push every community doc into the Algolia index.
# Idempotent (upserts by doc id): safe to run any number of times, safe to
# run alongside the extension's own backfill.
#
# Run from C:\Users\kurvh\lease-reputation (needs serviceAccountKey.json):
#   python backfill_algolia.py

import requests
import firebase_admin
from firebase_admin import credentials, firestore

APP_ID = "6IU3SM5A9Z"
ADMIN_KEY = "4b264a0bb0f23c00ac4a36663ea3adde"
INDEX = "communities"
FIELDS = ["name", "nameLower", "address", "reputationScore",
          "reviewCount", "photoRef"]

# Algolia publishes fallback hosts for exactly the DNS failure we hit on
# the primary — flush() walks them in order until one connects.
HOSTS = [
    f"{APP_ID}.algolia.net",
    f"{APP_ID}-1.algolianet.com",
    f"{APP_ID}-2.algolianet.com",
    f"{APP_ID}-3.algolianet.com",
]

firebase_admin.initialize_app(credentials.Certificate("serviceAccountKey.json"))
db = firestore.client()

batch, total = [], 0


def flush():
    global batch, total
    if not batch:
        return
    last_err = None
    for host in HOSTS:
        try:
            r = requests.post(
                f"https://{host}/1/indexes/{INDEX}/batch",
                json={"requests": batch},
                headers={
                    "X-Algolia-Application-Id": APP_ID,
                    "X-Algolia-API-Key": ADMIN_KEY,
                },
                timeout=60,
            )
            r.raise_for_status()
            total += len(batch)
            print(f"  pushed {total} (via {host})")
            batch = []
            return
        except requests.exceptions.ConnectionError as e:
            last_err = e
            continue
    raise last_err


for doc in db.collection("communities").stream():
    d = doc.to_dict() or {}
    body = {k: d.get(k) for k in FIELDS if d.get(k) is not None}
    ts = d.get("createdAt")
    if ts is not None and hasattr(ts, "timestamp"):
        body["createdAt"] = int(ts.timestamp() * 1000)
    ts = d.get("lastReviewAt")
    if ts is not None and hasattr(ts, "timestamp"):
        body["lastReviewAt"] = int(ts.timestamp() * 1000)
    body["objectID"] = doc.id
    batch.append({"action": "updateObject", "body": body})
    if len(batch) >= 500:
        flush()
flush()
print(f"Done — {total} records in the '{INDEX}' index.")
