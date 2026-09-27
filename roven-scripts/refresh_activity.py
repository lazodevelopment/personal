#!/usr/bin/env python3
# ============================================================================
# ROVEN - refresh_activity.py
# Build ID: JC-ROVEN-ACTIVITY-0730-001
#
# Writes activity.json for the homepage ticker from REAL Firestore data.
#
# The rules that keep this honest, and they are not negotiable:
#   - Only real events. Nothing is invented, padded or seeded.
#   - Anonymized: role + metro + how long ago. Never a candidate name, never
#     an employer name (an employer's own listings are public, but a scrolling
#     "X hired someone" feed is a different thing and needs their consent).
#   - If there are fewer than MIN_ITEMS real events, the file is written with
#     an empty list and the ticker stays hidden. A four-row ticker looks worse
#     than none, and a padded one would make us the thing we criticise.
#
# Run it nightly alongside the other scheduled jobs.
#
# Usage: python refresh_activity.py --key serviceAccount.json --out C:\\Users\\kurvh\\roven-site
# ============================================================================

import argparse
import json
import os
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, firestore

MIN_ITEMS = 6
MAX_ITEMS = 14


def ago(dt, now):
    if dt is None:
        return ""
    try:
        secs = (now - dt).total_seconds()
    except Exception:
        return ""
    if secs < 0:
        return "just now"
    mins = secs / 60
    if mins < 60:
        return f"{int(mins)}m ago"
    hours = mins / 60
    if hours < 24:
        return f"{int(hours)}h ago"
    days = hours / 24
    if days < 30:
        return f"{int(days)}d ago"
    return ""


def metro_of(job):
    city = (job.get("locationCity") or "").strip()
    state = (job.get("locationState") or "").strip()
    if job.get("remote"):
        return "Remote"
    if city and state:
        return f"{city}, {state}"
    return city or state or "United States"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(args.key))
    db = firestore.client()
    now = datetime.now(timezone.utc)

    items = []

    # ---- confirmed hires (the strongest possible signal) ----
    try:
        for snap in (db.collection("applications")
                     .where("candidateConfirmed", "==", True).stream()):
            a = snap.to_dict() or {}
            when = a.get("hiredAt") or a.get("appliedAt")
            label = ago(when, now)
            if not label:
                continue
            job = {}
            if a.get("jobId"):
                job = (db.collection("jobs").document(a["jobId"])
                       .get().to_dict() or {})
            title = (job.get("title") or "").strip()
            if not title:
                continue
            items.append({"what": f"{title} \u2014 hired",
                          "where": metro_of(job), "ago": label,
                          "_t": when, "_kind": "hire"})
    except Exception as exc:
        print(f"  ! hires query failed: {exc}")

    # ---- newly active listings ----
    try:
        for snap in (db.collection("jobs")
                     .where("status", "==", "active").stream()):
            j = snap.to_dict() or {}
            when = j.get("confirmedOpenAt") or j.get("createdAt")
            label = ago(when, now)
            if not label:
                continue
            title = (j.get("title") or "").strip()
            if not title:
                continue
            items.append({"what": title, "where": metro_of(j), "ago": label,
                          "_t": when, "_kind": "job"})
    except Exception as exc:
        print(f"  ! jobs query failed: {exc}")

    items.sort(key=lambda x: x["_t"] or now, reverse=True)
    for i in items:
        i.pop("_t", None)
        i.pop("_kind", None)
    items = items[:MAX_ITEMS]

    enough = len(items) >= MIN_ITEMS
    payload = {
        "generated": now.isoformat(),
        "items": items if enough else [],
        "count": len(items),
    }
    path = os.path.join(args.out, "activity.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)

    if enough:
        print(f"  wrote activity.json with {len(items)} real items - "
              f"ticker will show.")
    else:
        print(f"  only {len(items)} real events (need {MIN_ITEMS}). "
              f"activity.json written empty - ticker stays hidden. "
              f"This is correct: no padding, no fake rows.")


if __name__ == "__main__":
    main()
