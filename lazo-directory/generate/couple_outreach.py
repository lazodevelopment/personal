"""generate/couple_outreach.py - JC-LAZO-COUPLES-1019: the "come plan on Lazo" couples list.

Phase 1, step 2. Merges every inquiry file in generate/data/couples/ (inquiries-atavia.json and inquiries-es.json from
couple_outreach_inquiries.py, inquiries-es-gmail.json / inquiries-atavia-gmail.json from the mailbox backfills) into
ONE row per couple (by email, across brands), applies the two rules that keep a couple off the list, writes
generate/data/couples/couples.csv and prints the Phase 1 numbers. Nothing sends.

    python generate\\couple_outreach.py            # merge + CSV + numbers
    python generate\\couple_outreach.py --push     # also upsert Firestore coupleOutreach/{id} in lazo-513ec

Rules:
  relay_only    the address is a marketplace relay (@vmkt-message.zola.com, @zola.com, @member.theknot.com) or missing:
                stored as skipped, never mailed.
  wedding_past  the wedding date is before today: stored as skipped.
  Only marketplace inquiries (Zola / The Knot) are on the list; a site inquiry that says "Instagram" is not.

Firestore (lazo-513ec, admin-only like `outreach`: no rule names coupleOutreach, so clients get the default deny):
  coupleOutreach/{sha256(email)[:28]}
    email, names, firstName, brands[atavia|es], marketplaces[Zola|The Knot], weddingDate, venue, state,
    firstInquiry, lastInquiry, inquiries, refs[], token (url-safe 22), status listed|skipped (later queued, sent,
    clicked, replied, bounced, unsubscribed, signedUp), skipWhy relay_only|wedding_past, source backfill-1019,
    createdAt, updatedAt.
  An existing doc keeps its token and its status unless it is still listed/skipped (a sent or unsubscribed couple is
  never reset by a re-run); every other field is refreshed from the files.
"""
import argparse, csv, hashlib, json, os, re, secrets, sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "generate" / "data" / "couples"
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

RELAY_RX = re.compile(r"@(vmkt-message\.zola\.com|zola\.com|member\.theknot\.com|theknot\.com|weddingpro\.com)$", re.I)
MARKETPLACES = {"zola": "Zola", "the knot": "The Knot", "theknot": "The Knot", "knot": "The Knot"}
SOURCE = "backfill-1019"
TODAY = date.today()


def iso_date(v):
    """'2027-10-02', '2027-10-02T..', or '' -> 'YYYY-MM-DD' or ''."""
    s = str(v or "").strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
        except ValueError:
            return ""
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def state_of(venue):
    m = re.search(r",\s*([A-Z]{2})\b\s*$", str(venue or "").strip())
    return m[1] if m else ""


def first_name(names):
    n = str(names or "").strip()
    n = re.split(r"\s*(?:&|\band\b|\+|/)\s*", n)[0]
    return n.split()[0] if n.split() else ""


def norm_rows(path):
    """Either file shape -> [{brand, marketplace, names, email, weddingDate, venue, inquiredAt, ref}]."""
    rows = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for r in rows:
        if "found_us" in r or "event_date_raw" in r:          # Firestore export (couple_outreach_inquiries.py)
            mp = MARKETPLACES.get(str(r.get("found_us") or "").strip().lower())
            names = " ".join(x for x in [str(r.get("first_name") or "").strip(), str(r.get("last_name") or "").strip()] if x)
            out.append({"brand": r.get("brand"), "marketplace": mp, "names": names, "email": str(r.get("email") or "").strip().lower(),
                        "weddingDate": iso_date(r.get("event_date_raw")), "venue": str(r.get("venue") or "").strip(),
                        "inquiredAt": str(r.get("created_at") or "")[:10], "ref": f"{r.get('brand')}:inquiries/{r.get('id')}"})
        else:                                                  # mailbox backfill (LazoCouples.gs exportInquiries / es-gmail)
            mp = MARKETPLACES.get(str(r.get("marketplace") or "").strip().lower())
            out.append({"brand": r.get("brand"), "marketplace": mp, "names": str(r.get("names") or "").strip(),
                        "email": str(r.get("email") or "").strip().lower(), "weddingDate": iso_date(r.get("wedding_date")),
                        "venue": str(r.get("venue") or "").strip(), "inquiredAt": str(r.get("inquired_at") or "")[:10],
                        "ref": f"{r.get('brand')}:gmail/{r.get('gmail_thread') or r.get('thread') or ''}"})
    return out


def couple_id(row):
    if row["email"]:
        return hashlib.sha256(row["email"].encode()).hexdigest()[:28]
    return hashlib.sha256(f"noemail|{row['brand']}|{row['names'].lower()}".encode()).hexdigest()[:28]


def build():
    files = sorted(DATA.glob("inquiries-*.json"))
    if not files:
        sys.exit(f"no inquiries-*.json in {DATA}; run couple_outreach_inquiries.py first")
    inq = []
    per_file = {}
    for f in files:
        rows = norm_rows(f)
        per_file[f.name] = len(rows)
        inq.extend(rows)
    not_mp = [r for r in inq if not r["marketplace"]]
    inq = [r for r in inq if r["marketplace"]]

    couples = {}
    for r in sorted(inq, key=lambda x: x["inquiredAt"]):
        cid = couple_id(r)
        c = couples.get(cid)
        if not c:
            c = couples[cid] = {"id": cid, "email": r["email"], "names": r["names"], "brands": [], "marketplaces": [], "weddingDate": "",
                                "venue": "", "firstInquiry": r["inquiredAt"], "lastInquiry": r["inquiredAt"], "inquiries": 0, "refs": []}
        c["inquiries"] += 1
        c["lastInquiry"] = max(c["lastInquiry"], r["inquiredAt"])
        c["firstInquiry"] = min(c["firstInquiry"], r["inquiredAt"]) if c["firstInquiry"] else r["inquiredAt"]
        if r["brand"] not in c["brands"]:
            c["brands"].append(r["brand"])
        if r["marketplace"] not in c["marketplaces"]:
            c["marketplaces"].append(r["marketplace"])
        if r["weddingDate"]:
            c["weddingDate"] = r["weddingDate"]       # latest notice wins
        if r["venue"]:
            c["venue"] = r["venue"]
        if r["names"] and (not c["names"] or len(r["names"]) > len(c["names"])):
            c["names"] = r["names"]
        if r["ref"] not in c["refs"]:
            c["refs"].append(r["ref"])
    for c in couples.values():
        c["firstName"] = first_name(c["names"])
        c["state"] = state_of(c["venue"])
        relay = not c["email"] or bool(RELAY_RX.search(c["email"]))
        past = bool(c["weddingDate"]) and date.fromisoformat(c["weddingDate"]) < TODAY
        c["status"] = "skipped" if (relay or past) else "listed"
        c["skipWhy"] = "relay_only" if relay else ("wedding_past" if past else "")

    # ---- Phase 1 numbers ----
    print(f"files: {json.dumps(per_file)}")
    print(f"inquiries: {len(inq)} marketplace" + (f" (+{len(not_mp)} not a marketplace inquiry, dropped)" if not_mp else ""))
    print("  by brand:", dict(Counter(r["brand"] for r in inq)))
    print("  by marketplace:", dict(Counter(r["marketplace"] for r in inq)))
    cs = list(couples.values())
    real = [c for c in cs if c["skipWhy"] != "relay_only"]
    relay = [c for c in cs if c["skipWhy"] == "relay_only"]
    print(f"distinct couples: {len(cs)} = {len(real)} with a real address + {len(relay)} relay-only / no address")
    print(f"  cross-brand duplicates (same email, both studios): {sum(1 for c in cs if len(c['brands']) > 1)}")
    print("  real, by brand:", dict(Counter(b for c in real for b in c["brands"])), " by marketplace:", dict(Counter(m for c in real for m in c["marketplaces"])))
    listed = [c for c in cs if c["status"] == "listed"]
    past = [c for c in cs if c["skipWhy"] == "wedding_past"]
    print(f"wedding past (skipped): {len(past)}   no wedding date: {sum(1 for c in real if not c['weddingDate'])}")
    print(f"LISTED (future or undated wedding, real address): {len(listed)}")
    print("  listed by brand:", dict(Counter(b for c in listed for b in c["brands"])), " by marketplace:", dict(Counter(m for c in listed for m in c["marketplaces"])))
    print("  listed by wedding year:", dict(sorted(Counter(c["weddingDate"][:4] or "none" for c in listed).items())))
    print("  listed by state (top):", Counter(c["state"] or "?" for c in listed).most_common(12))
    return cs


def write_csv(cs):
    cols = ["couple_id", "status", "skip_why", "email", "names", "first_name", "brands", "marketplaces", "wedding_date", "venue", "state",
            "first_inquiry", "last_inquiry", "inquiries", "refs"]
    with (DATA / "couples.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for c in sorted(cs, key=lambda x: (x["status"] != "listed", x["firstInquiry"])):
            w.writerow([c["id"], c["status"], c["skipWhy"], c["email"], c["names"], c["firstName"], "|".join(c["brands"]), "|".join(c["marketplaces"]),
                        c["weddingDate"], c["venue"], c["state"], c["firstInquiry"], c["lastInquiry"], c["inquiries"], "|".join(c["refs"])])
    print(f"wrote {DATA / 'couples.csv'} ({len(cs)} rows)")


def push(cs):
    sys.path.insert(0, str(ROOT / "generate"))
    import outreach_export as X
    from firebase_admin import firestore
    db = X.client()
    col = db.collection("coupleOutreach")
    old = {d.id: d.to_dict() for d in col.stream()}
    n_new = n_upd = n_kept = 0
    batch, pending = db.batch(), 0
    for c in cs:
        o = old.get(c["id"]) or {}
        doc = {k: c[k] for k in ("email", "names", "firstName", "brands", "marketplaces", "weddingDate", "venue", "state",
                                 "firstInquiry", "lastInquiry", "inquiries", "refs")}
        doc["token"] = o.get("token") or secrets.token_urlsafe(16)
        if o.get("status") in (None, "", "listed", "skipped"):
            doc["status"], doc["skipWhy"] = c["status"], c["skipWhy"]
        else:
            n_kept += 1                                   # queued/sent/unsubscribed/...: never reset
        doc["source"] = o.get("source") or SOURCE
        doc["updatedAt"] = firestore.SERVER_TIMESTAMP
        if not o:
            doc["createdAt"] = firestore.SERVER_TIMESTAMP
            n_new += 1
        else:
            n_upd += 1
        batch.set(col.document(c["id"]), doc, merge=True)
        pending += 1
        if pending >= 400:
            batch.commit(); batch, pending = db.batch(), 0
    if pending:
        batch.commit()
    print(f"push: coupleOutreach {n_new} new, {n_upd} updated ({n_kept} kept their status), {len(old)} were there before")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--push", action="store_true", help="upsert coupleOutreach in lazo-513ec")
    a = ap.parse_args()
    cs = build()
    write_csv(cs)
    if a.push:
        push(cs)


if __name__ == "__main__":
    main()
