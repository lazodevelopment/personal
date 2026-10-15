"""site_facts_delist.py - JC-LAZO-SITEFACTS-1014: delist vendors whose own website shows they are not a wedding business.

The list (generate/data/site-facts/_delist-1014.json, {placeId: [category, reason]}) came from the 2026-10-13 crawl:
readable sites (150+ words) that never mention weddings in body, title or description, minus florists / caterers /
DJs / limo companies / venues whose name says they do the job, plus the expired domains taken over by gambling spam.
A 25-row random check was 25/25 non-wedding (bounce houses, print shops, supermarkets, breweries, county clerks).
Approved by Jesse 2026-10-14.

Each doc gets delisted=true, delistedReason, delistedAt; the nightly then serves 410 from _gone.json. Claimed,
verified or reviewed vendors are never touched.

    python generate\\site_facts_delist.py --dry-run
    python generate\\site_facts_delist.py
    python generate\\site_facts_delist.py --undo        # put every one of them back
"""
import argparse, json, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIST = ROOT / "generate" / "data" / "site-facts" / "_delist-1014.json"
REASON = "sitefacts-1014: not a wedding business"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--undo", action="store_true")
    ap.add_argument("--list", default=str(LIST), help="JC-LAZO-DELIST-1014B: e.g. generate/data/site-facts/_delist-1014b.json")
    ap.add_argument("--tag", default="sitefacts-1014", help="delistedReason prefix; --undo only restores this tag")
    a = ap.parse_args()
    rows = json.loads(Path(a.list).read_text(encoding="utf-8"))
    import firebase_admin
    from firebase_admin import credentials, firestore
    firebase_admin.initialize_app(credentials.Certificate(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
                                                          or r"C:\Users\kurvh\secrets\lazo-513ec-admin.json"))
    db = firestore.client()
    ids = sorted(rows)
    done = skipped = missing = 0
    for i in range(0, len(ids), 400):
        refs = [db.collection("vendors").document(x) for x in ids[i:i + 400]]
        batch = db.batch()
        for d in db.get_all(refs):
            if not d.exists:
                missing += 1
                continue
            v = d.to_dict() or {}
            if a.undo:
                if (v.get("delistedReason") or "").startswith(a.tag):
                    batch.update(d.reference, {"delisted": firestore.DELETE_FIELD, "delistedReason": firestore.DELETE_FIELD,
                                               "delistedAt": firestore.DELETE_FIELD})
                    done += 1
                continue
            if v.get("claimedBy") or v.get("verified") or int(v.get("reviewCount") or 0) > 0 or v.get("delisted"):
                skipped += 1
                continue
            batch.update(d.reference, {"delisted": True, "delistedReason": f"{a.tag}: {rows[d.id][1]}",
                                       "delistedAt": firestore.SERVER_TIMESTAMP})
            done += 1
        if not a.dry_run:
            batch.commit()
        print(f"  {min(i + 400, len(ids)):,}/{len(ids):,}", flush=True)
    verb = "would change" if a.dry_run else ("restored" if a.undo else "delisted")
    print(f"{verb} {done:,}; skipped {skipped:,} (claimed/verified/reviewed/already delisted); {missing:,} no longer exist")


if __name__ == "__main__":
    main()
