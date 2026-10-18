"""outreach_export.py - JC-LAZO-OUTREACH-1018: a Smartlead batch from the outreach collection.

Reads outreach/{vendorId} (written by outreach_emails.py --push), applies the campaign rules and writes the
CSV Smartlead imports (one row per address, custom fields for the email's merge tags). With --mark the
exported docs move to status=queued under a batch id, so the next export never repeats them.

    python generate\\outreach_export.py --metro phoenix --limit 200                 # dry run: prints what it would take
    python generate\\outreach_export.py --metro phoenix --limit 200 --mark 2026-10-20-phx-1
    python generate\\outreach_export.py --metro phoenix --metro denver --min-score 60 --mark ...

Rules (all adjustable by flag): status == listed; site == ok; best address score >= --min-score (75 = own-domain
or a named free-mail box); not noWedding/parked/hijacked; one row per WEBSITE (sharedBy > 1 collapses to the
best-scored vendor, the others are marked skipped:shared); addresses never repeated across vendors.

Columns: email, first_name, last_name, company_name, metro, category, page_url, claim_url, stop_url,
signup_url, vendor_id, token, score, kind. Smartlead merge tags use the column names ({{company_name}}...).
After the send, the Smartlead CSV export (sent/bounced/replied/unsubscribed) goes back in with --import-events.
"""
import argparse, csv, json, os, sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config.metros import METROS  # noqa: E402

OUT_DIR = ROOT / "generate" / "data" / "outreach" / "batches"
SITE = "https://meetlazo.com/"
APP = "https://app.meetlazo.com/"
METRO_NAME = {m["id"]: m["name"] for m in METROS}


def client():
    import firebase_admin
    from firebase_admin import credentials, firestore
    cred = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or r"C:\Users\kurvh\secrets\lazo-513ec-admin.json"
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(cred))
    return firestore.client()


def pick(docs, a):
    """[(doc, data)] -> rows that pass the rules, one per website, no address twice."""
    by_site = defaultdict(list)
    for d, v in docs:
        if v.get("status") != "listed" or v.get("site") != "ok" or not v.get("best"):
            continue
        fl = v.get("flags") or {}
        if (fl.get("noWedding") and not a.include_nowedding) or fl.get("parked") or fl.get("hijacked"):
            continue
        em = (v.get("emails") or [{}])[0]
        if int(em.get("score") or 0) < a.min_score:
            continue
        if a.kind and em.get("kind") not in a.kind:
            continue
        by_site[v.get("website")].append((d, v, em))
    rows, shared_skips, seen_addr = [], [], set()
    for site, group in by_site.items():
        group.sort(key=lambda x: -int(x[2].get("score") or 0))
        best, rest = group[0], group[1:]
        shared_skips.extend(x[0] for x in rest)
        d, v, em = best
        if em["addr"] in seen_addr:
            shared_skips.append(d)
            continue
        seen_addr.add(em["addr"])
        rows.append((d, v, em))
    rows.sort(key=lambda x: (-int(x[2].get("score") or 0), x[1].get("name", "")))
    return rows[: a.limit or None], shared_skips


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--metro", action="append", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-score", type=int, default=75)
    ap.add_argument("--kind", action="append", choices=["own-domain", "free-mail", "other-domain"])
    ap.add_argument("--include-nowedding", action="store_true")
    ap.add_argument("--mark", help="batch id; marks exported docs status=queued")
    a = ap.parse_args()
    db = client()
    docs = []
    for mid in a.metro:
        for d in db.collection("outreach").where("metroId", "==", mid).stream():
            docs.append((d, d.to_dict()))
    rows, shared = pick(docs, a)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{a.mark or 'dryrun-' + datetime.now().strftime('%Y%m%d-%H%M')}.csv"
    path = OUT_DIR / name
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["email", "first_name", "last_name", "company_name", "metro", "category", "page_url", "claim_url", "stop_url", "signup_url",
                    "vendor_id", "token", "score", "kind"])
        for d, v, em in rows:
            tok = v["token"]
            w.writerow([em["addr"], "", "", v.get("name", ""), METRO_NAME.get(v.get("metroId"), v.get("metroId")), (v.get("categories") or [""])[0],
                        v.get("pageUrl", ""), f"{SITE}claim/{tok}", f"{SITE}claim/{tok}/stop", f"{APP}?claim={d.id}", d.id, tok, em.get("score"), em.get("kind")])
    print(f"{len(docs):,} outreach docs in {', '.join(a.metro)}; {len(rows):,} rows exported to {path}; {len(shared):,} skipped as a shared website")
    if a.mark:
        batch, n = db.batch(), 0
        from firebase_admin import firestore
        for d, v, em in rows:
            batch.set(d.ref, {"status": "queued", "batch": a.mark, "queuedAt": firestore.SERVER_TIMESTAMP, "sendTo": em["addr"]}, merge=True)
            n += 1
            if n % 400 == 0:
                batch.commit(); batch = db.batch()
        for d in shared:
            batch.set(d.ref, {"status": "skipped", "skipWhy": "shared-website", "batch": a.mark}, merge=True)
            n += 1
            if n % 400 == 0:
                batch.commit(); batch = db.batch()
        batch.commit()
        print(f"marked {len(rows):,} queued + {len(shared):,} skipped under batch {a.mark}")


if __name__ == "__main__":
    main()
