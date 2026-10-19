"""generate/couple_outreach_inquiries.py - JC-LAZO-COUPLES-1019

Phase 1 of the "come plan on Lazo" couples campaign: pull every marketplace inquiry (Zola / The Knot) that the
brands' own inquiry pipelines already store in Firestore `inquiries` (written by inquiry_webhook from the Gmail
intake scripts since 2026-09-28, and by the sites' contact forms), one brand project at a time, into
generate/data/couples/inquiries-<brand>.json. Nothing sends, nothing is written to Firestore.

    python generate\couple_outreach_inquiries.py atavia      (project atavia-c29cd, ADC)
    python generate\couple_outreach_inquiries.py es          (project elizabeth-scott-738e5, ADC)
"""
import json, sys
from datetime import datetime
from pathlib import Path

from google.cloud import firestore

PROJECTS = {"atavia": "atavia-c29cd", "es": "elizabeth-scott-738e5"}
OUT = Path(__file__).resolve().parent / "data" / "couples"
FIELDS = ["first_name", "last_name", "email", "phone", "event_date_raw", "found_us", "venue", "landing", "referrer",
          "source", "status", "created_at", "auto_replied_at", "message"]


def main():
    brand = sys.argv[1]
    # --account <gcloud account>: read with that signed-in gcloud account's token (danbrenmedia@gmail.com can read
    # both brand projects); without it the application default credentials are used.
    creds = None
    if "--account" in sys.argv:
        import subprocess
        from google.oauth2.credentials import Credentials
        acct = sys.argv[sys.argv.index("--account") + 1]
        tok = subprocess.check_output(["gcloud", "auth", "print-access-token", "--account=" + acct], shell=True, text=True).strip()
        creds = Credentials(tok)
    db = firestore.Client(project=PROJECTS[brand], credentials=creds)
    rows = []
    for d in db.collection("inquiries").stream():
        x = d.to_dict() or {}
        row = {"id": d.id, "brand": brand}
        for f in FIELDS:
            v = x.get(f)
            if isinstance(v, datetime):
                v = v.isoformat()
            row[f] = v
        rows.append(row)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"inquiries-{brand}.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
    by = {}
    for r in rows:
        k = f"{r.get('source')}/{r.get('found_us')}"
        by[k] = by.get(k, 0) + 1
    print(brand, len(rows), "inquiries", json.dumps(by))
    cs = sorted(r["created_at"] for r in rows if r.get("created_at"))
    if cs:
        print("created_at range", cs[0], "->", cs[-1])


if __name__ == "__main__":
    main()
