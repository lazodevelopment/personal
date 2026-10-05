"""Tell the JARVIS hub that a social post went out, so the "posted today" check no longer depends on files on this PC.

Usage:  python report_post.py <brand> <day-or-file> <media_id> [linkedin_urn|null]
brand: jovi | atavia | elizabethscott | trylazo | lazovendors | roven | leasereputation
"""
import json, os, sys, urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
HUB = "https://jarvis-hub.floral-credit-e4f0.workers.dev"
KEY = open(os.path.join(HERE, ".hub-key")).read().strip()


def main():
    if len(sys.argv) < 4:
        print(__doc__); sys.exit(2)
    body = {"brand": sys.argv[1], "day": sys.argv[2], "media_id": sys.argv[3], "linkedin_urn": (sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "null" else None), "at": datetime.now().strftime("%Y-%m-%d")}
    req = urllib.request.Request(HUB + "/api/social/posted", data=json.dumps(body).encode(), headers={"content-type": "application/json", "x-hub-key": KEY}, method="POST")
    print(urllib.request.urlopen(req, timeout=30).read().decode()[:200])


if __name__ == "__main__":
    main()
