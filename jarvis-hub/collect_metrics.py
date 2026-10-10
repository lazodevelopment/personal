"""JARVIS metrics collector.

Reads each business's Firestore with the service-account keys already on this machine,
summarises bookings / revenue / leads / vendors / jobs / reviews, and POSTs the result to the
hub (KV key "metrics"). Runs hourly from Task Scheduler (collect_metrics.bat).

Credentials, in order of preference per project:
  1. jarvis-hub/secrets/<project>.json     (drop a Firebase service-account JSON here)
  2. the existing keys the other tools use  (Lazo, Roven, LeaseReputation)
  3. Application Default Credentials (`gcloud auth application-default login`) — used for
     Atavia (atavia-c29cd) and Elizabeth Scott (elizabeth-scott-738e5), whose org policy forbids key files.
     The signed-in account needs the Viewer role on each project (Firebase → Users and permissions).
"""
import json, os, re, sys, subprocess, traceback, warnings
warnings.filterwarnings("ignore", message=".*without a quota project.*")
from datetime import datetime, timedelta, timezone, date
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
HUB = "https://jarvis-hub.floral-credit-e4f0.workers.dev"
NOW = datetime.now(timezone.utc)
TODAY = NOW.date()
D7, D14, D30, D60, W8 = (NOW - timedelta(days=n) for n in (7, 14, 30, 60, 56))

PROJECTS = {
    "atavia": ("atavia-c29cd", []),
    "es": ("elizabeth-scott-738e5", []),
    "lazo": ("lazo-513ec", [r"C:\Users\kurvh\secrets\lazo-513ec-admin.json"]),
    "roven": ("roven-7efea", [r"C:\Users\kurvh\roven-admin\serviceAccount.json"]),
    "lr": ("lease-reputation", [r"C:\Users\kurvh\lease-reputation\serviceAccountKey.json"]),
}


def key_for(biz):
    pid, fallbacks = PROJECTS[biz]
    cands = [os.path.join(HERE, "secrets", pid + ".json"), os.path.join(HERE, "secrets", biz + ".json")] + fallbacks
    return next((c for c in cands if os.path.exists(c)), None)


def adc_client(pid):
    """Application Default Credentials (gcloud auth application-default login) — no key file on disk."""
    try:
        import google.auth
        from google.cloud import firestore as gcf
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/datastore"])
        creds = creds.with_quota_project(pid)
        # refresh once up front so an expired Workspace session fails in a second, not after 5 minutes of retries
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        return gcf.Client(project=pid, credentials=creds)
    except Exception as e:
        msg = str(e)
        if "Reauthentication" in msg or "invalid_grant" in msg or "RefreshError" in type(e).__name__:
            raise RuntimeError("Google sign-in expired: run `gcloud auth application-default login` on the PC")
        print(f"{pid}: ADC unavailable ({type(e).__name__}: {msg[:120]})")
        return None


def client_for(biz):
    import firebase_admin
    from firebase_admin import credentials, firestore
    key = key_for(biz)
    pid = PROJECTS[biz][0]
    if not key:
        return adc_client(pid)
    try:
        app = firebase_admin.get_app(biz)
    except ValueError:
        app = firebase_admin.initialize_app(credentials.Certificate(key), {"projectId": pid}, name=biz)
    return firestore.client(app)


def ts(v):
    """Normalise Firestore Timestamp / ISO string / epoch to an aware datetime, else None."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v / (1000 if v > 1e11 else 1), tz=timezone.utc)
    if isinstance(v, str):
        s = v.strip()
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc) if len(s) > 10 else datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    if hasattr(v, "seconds"):
        return datetime.fromtimestamp(v.seconds, tz=timezone.utc)
    return None


def num(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def first(d, *names):
    for n in names:
        if d.get(n) is not None:
            return d[n]
    return None


def weekly(dts, weeks=8):
    """Counts per ISO week for the last `weeks` weeks, oldest first."""
    buckets = [0] * weeks
    start = NOW - timedelta(days=7 * weeks)
    for t in dts:
        if t and t >= start:
            i = min(weeks - 1, int((t - start).days // 7))
            buckets[i] += 1
    return buckets


def delta(cur, prev):
    return cur - prev


def count(q):
    try:
        res = q.count().get()
        return int(res[0][0].value)
    except Exception:
        return len(list(q.stream()))


def stream(col, select=None, **where):
    from google.cloud.firestore_v1.base_query import FieldFilter
    q = col
    for k, v in where.items():
        q = q.where(filter=FieldFilter(*v)) if isinstance(v, tuple) else q.where(filter=FieldFilter(k, "==", v))
    if select:
        q = q.select(select)
    return [d.to_dict() | {"_id": d.id} for d in q.stream()]


# ---------------- Atavia / Elizabeth Scott (same schema) ----------------
def collect_films(db):
    books = stream(db.collection("bookings"))
    live = [b for b in books if not b.get("test_mode") and not str(b.get("status", "")).startswith(("abandoned", "cancel"))]
    signed = [b for b in live if b.get("signed_at") or b.get("status") in ("signed", "confirmed", "awaiting_payment")]
    created = lambda b: ts(b.get("created_at"))

    def revenue(since, until):
        total = 0.0
        for b in live:
            dep = ts(b.get("deposit_paid_at"))
            if dep and since <= dep < until:
                total += num(first(b, "invoice_amount") or (b.get("pif_total") if b.get("payment_option") == "pif" else b.get("retainer")))
            bal = ts(b.get("balance_paid_at"))
            if bal and since <= bal < until:
                total += num(b.get("balance"))
        try:
            for g in db.collection_group("gratuities").stream():
                gd = g.to_dict(); at = ts(gd.get("at"))
                if at and since <= at < until:
                    total += num(gd.get("amount"))
        except Exception:
            pass
        return total

    rev30, rev_prev = revenue(D30, NOW), revenue(D60, D30)
    booked30 = [b for b in signed if created(b) and created(b) >= D30]
    booked_prev = [b for b in signed if created(b) and D60 <= created(b) < D30]
    leads = []
    for col in ("inquiries", "leads"):
        try:
            leads += stream(db.collection(col), select=["created_at", "found_us", "email", "status"])
        except Exception:
            pass
    leads_full = leads
    l7 = sum(1 for l in leads if ts(l.get("created_at")) and ts(l.get("created_at")) >= D7)
    l_prev = sum(1 for l in leads if ts(l.get("created_at")) and D14 <= ts(l.get("created_at")) < D7)
    pipeline = sum(num(b.get("balance")) for b in signed if not b.get("balance_paid_at"))
    upcoming = []
    for b in signed:
        raw = b.get("event_date_raw") or b.get("event_date")
        try:
            d = date.fromisoformat(str(raw)[:10])
        except (TypeError, ValueError):
            continue
        if d >= TODAY:
            venue = (b.get("ceremony_venue") or b.get("reception_venue") or "").strip()
            parts = [x.strip() for x in venue.split(",") if x.strip()]
            where = ", ".join(parts[-2:]) if len(parts) >= 2 else ""
            if not where:
                csz = (b.get("city_state_zip") or "").strip()
                m = re.match(r"^(.*?),\s*([A-Z]{2})\b", csz)
                if m: where = f"{m.group(1)}, {m.group(2)}"
            upcoming.append({"id": b["_id"], "date": d.isoformat(), "title": f"{b.get('client_names') or b.get('email') or 'Wedding'} · {b.get('package_name') or b.get('package_id') or ''}".strip(" ·"), "venue": venue[:80], "where": where[:60]})
    upcoming.sort(key=lambda e: e["date"])
    # monthly cash-in for the money view (deposits + balances + gratuities by paid date)
    months = defaultdict(float)
    for b in live:
        dep = ts(b.get("deposit_paid_at"))
        if dep: months[dep.strftime("%Y-%m")] += num(first(b, "invoice_amount") or (b.get("pif_total") if b.get("payment_option") == "pif" else b.get("retainer")))
        bal = ts(b.get("balance_paid_at"))
        if bal: months[bal.strftime("%Y-%m")] += num(b.get("balance"))
    try:
        for g in db.collection_group("gratuities").stream():
            gd = g.to_dict(); at = ts(gd.get("at"))
            if at: months[at.strftime("%Y-%m")] += num(gd.get("amount"))
    except Exception:
        pass
    # cash forecast: unpaid balances by the week they fall due (13 weeks), plus anything already past due
    forecast = defaultdict(lambda: {"amount": 0.0, "items": []}); past_due = []
    for b in signed:
        if b.get("balance_paid_at") or b.get("test_mode"): continue
        due = ts(b.get("balance_due_at")); amt = num(b.get("balance"))
        if not due or amt <= 0: continue
        who = (b.get("client_names") or b.get("email") or "?")[:40]
        if due < NOW - timedelta(days=1):
            past_due.append({"who": who, "amount": round(amt), "due": due.date().isoformat(), "attempts": int(b.get("balance_attempts") or 0)})
        elif due < NOW + timedelta(days=91):
            wk = (due.date() - timedelta(days=due.weekday())).isoformat()   # Monday of that week
            forecast[wk]["amount"] += amt; forecast[wk]["items"].append(f"{who} ${round(amt):,}")
    # the same trailing 7 days one year ago (bookings signed, cash in, leads)
    Y7, Y0 = NOW - timedelta(days=372), NOW - timedelta(days=365)
    yoy = {"bookings": sum(1 for b in signed if created(b) and Y7 <= created(b) < Y0),
           "revenue": round(revenue(Y7, Y0)),
           "leads": sum(1 for l in leads if ts(l.get("created_at")) and Y7 <= ts(l.get("created_at")) < Y0),
           "bookings_now": sum(1 for b in signed if created(b) and created(b) >= D7), "revenue_now": round(revenue(D7, NOW)), "leads_now": l7,
           "has_history": any(created(b) and created(b) < Y0 for b in signed)}
    recent = sorted([b for b in live if created(b)], key=created, reverse=True)[:12]
    src = defaultdict(int)
    for l in leads_full:
        t = ts(l.get("created_at"))
        if t and t >= NOW - timedelta(days=90): src[str(l.get("found_us") or "unknown").strip()[:30] or "unknown"] += 1
    detail = {
        "recent": [{"id": b["_id"], "names": b.get("client_names") or b.get("email") or "?", "date": str(b.get("event_date_raw") or "")[:10], "package": b.get("package_name") or b.get("package_id") or "", "total": round(num(b.get("total"))), "status": b.get("status"), "balance": round(num(b.get("balance"))), "balance_paid": bool(b.get("balance_paid_at"))} for b in recent],
        "leadsBySource": dict(sorted(src.items(), key=lambda kv: -kv[1])[:8]),
        "monthly": {k: round(v) for k, v in sorted(months.items())[-12:]},
        "forecast": {k: {"amount": round(v["amount"]), "items": v["items"][:6]} for k, v in sorted(forecast.items())},
        "pastDue": sorted(past_due, key=lambda x: x["due"]),
    }
    return {
        "detail": detail,
        "headline": [
            {"label": "Revenue 30d", "value": round(rev30), "money": True, "delta": round(rev30 - rev_prev), "deltaUnit": "$", "deltaLabel": "vs prior 30d"},
            {"label": "Booked 30d", "value": len(booked30), "delta": delta(len(booked30), len(booked_prev)), "deltaLabel": "vs prior 30d"},
            {"label": "Leads 7d", "value": l7, "delta": delta(l7, l_prev), "deltaLabel": "vs prior 7d"},
            {"label": "Balances due", "value": round(pipeline), "money": True},
        ],
        "series": {"name": "bookings / week", "values": weekly([created(b) for b in signed]), "color": "#39f0a8"},
        "upcoming": upcoming[:8],
        "counts": {"bookings_live": len(live), "signed": len(signed), "upcoming": len(upcoming)},
        "yoy": yoy,
    }


# ---------------- Lazo ----------------
def collect_lazo(db):
    from google.cloud.firestore_v1.base_query import FieldFilter
    vendors = count(db.collection("vendors"))
    claimed = count(db.collection("vendors").where(filter=FieldFilter("claimStatus", "==", "claimed")))
    claims_pending = count(db.collection("claimRequests").where(filter=FieldFilter("status", "==", "pending")))
    couples = stream(db.collection("couples"), select=["createdAt", "weddingDate"])
    cts = [ts(c.get("createdAt")) for c in couples]
    c7 = sum(1 for t in cts if t and t >= D7); c_prev = sum(1 for t in cts if t and D14 <= t < D7)
    inq = stream(db.collection("inquiries"), select=["createdAt", "status", "vendorName", "vendorId", "coupleName", "email"])
    i7 = sum(1 for i in inq if ts(i.get("createdAt")) and ts(i.get("createdAt")) >= D7)
    i_prev = sum(1 for i in inq if ts(i.get("createdAt")) and D14 <= ts(i.get("createdAt")) < D7)
    inq_new = sum(1 for i in inq if i.get("status") == "new")
    # sign-up health: users docs are written by the app right after Firebase Auth sign-up, so a day with couples but no
    # users (or no users at all while the 7-day average says there should be) means sign-up is broken (Sep 29 - Oct 9 2026)
    from collections import Counter
    users = stream(db.collection("users"), select=["created_time", "createdAt", "signupSource", "role"])   # FlutterFlow writes created_time
    for u in users: u["_t"] = ts(first(u, "created_time", "createdAt"))
    uts = sorted(u["_t"] for u in users if u["_t"])
    D1, D8 = NOW - timedelta(days=1), NOW - timedelta(days=8)
    u24 = sum(1 for t in uts if t >= D1); u7 = sum(1 for t in uts if t >= D7); u_prev = sum(1 for t in uts if D14 <= t < D7)
    avg_day = round(sum(1 for t in uts if D8 <= t < D1) / 7, 1)
    c24 = sum(1 for t in cts if t and t >= D1)
    cl_ts = [ts(c.get("createdAt")) for c in stream(db.collection("claimRequests"), select=["createdAt"])]
    def daily(dts, days=14):
        return [sum(1 for t in dts if t and t.date() == TODAY - timedelta(days=i)) for i in range(days - 1, -1, -1)]
    signups = {"days": [(TODAY - timedelta(days=i)).isoformat() for i in range(13, -1, -1)], "users": daily(uts), "couples": daily(cts),
               "inquiries": daily([ts(i.get("createdAt")) for i in inq]), "claims": daily(cl_ts), "lastUserAt": uts[-1].isoformat() if uts else None,
               "sources": dict(Counter(("claim" if (u.get("signupSource") or {}).get("claim") else (u.get("role") or "couple")) for u in users if u["_t"] and u["_t"] >= D14))}
    hours_since = round((NOW - uts[-1]).total_seconds() / 3600, 1) if uts else None
    u14 = sum(1 for t in uts if t >= D14); gap_hours = round(14 * 24 / u14) if u14 >= 3 else None   # typical hours between sign-ups at current volume
    charges = stream(db.collection("proCharges"), select=["amount", "createdAt", "status"])
    ok = lambda c: str(c.get("status", "")).lower() not in ("failed", "refunded", "void", "declined")
    rev30 = sum(num(c.get("amount")) for c in charges if ok(c) and ts(c.get("createdAt")) and ts(c.get("createdAt")) >= D30) / 100
    rev_prev = sum(num(c.get("amount")) for c in charges if ok(c) and ts(c.get("createdAt")) and D60 <= ts(c.get("createdAt")) < D30) / 100
    subs = count(db.collection("proSubscriptions").where(filter=FieldFilter("status", "==", "active")))
    upcoming = []
    for c in couples:
        w = c.get("weddingDate")
        try:
            d = ts(w).date() if not isinstance(w, str) else date.fromisoformat(w[:10])
        except (TypeError, ValueError, AttributeError):
            continue
        if d and TODAY <= d <= TODAY + timedelta(days=45):
            upcoming.append({"date": d.isoformat(), "title": "Couple wedding day (app)"})
    pending = []
    try:
        for c in stream(db.collection("claimRequests"), status="pending"):
            pending.append({"id": c["_id"], "kind": "lazo_claim", "label": f"claim: {c.get('businessName') or c.get('vendorName') or c.get('vendorId')} by {c.get('email') or c.get('uid')}"})
    except Exception:
        pass
    for i in sorted([i for i in inq if i.get("status") == "new"], key=lambda i: ts(i.get("createdAt")) or NOW, reverse=True)[:10]:
        pending.append({"id": i["_id"], "kind": "lazo_inquiry_responded", "label": f"inquiry {str(i.get('vendorName') or i.get('vendorId') or '')} from {i.get('coupleName') or i.get('email') or 'couple'}"})
    months = defaultdict(float)
    for c in charges:
        t = ts(c.get("createdAt"))
        if t and ok(c): months[t.strftime("%Y-%m")] += num(c.get("amount")) / 100
    return {
        "detail": {"pending": pending, "monthly": {k: round(v) for k, v in sorted(months.items())[-12:]}, "signups": signups},
        "headline": [
            {"label": "New users 24h", "value": u24, "delta": delta(u24, round(avg_day)), "deltaLabel": "vs 7d avg/day"},
            {"label": "New users 7d", "value": u7, "delta": delta(u7, u_prev), "deltaLabel": "vs prior 7d"},
            {"label": "New couples 7d", "value": c7, "delta": delta(c7, c_prev), "deltaLabel": "vs prior 7d"},
            {"label": "Vendor inquiries 7d", "value": i7, "delta": delta(i7, i_prev), "deltaLabel": "vs prior 7d"},
            {"label": "Claimed vendors", "value": f"{claimed:,} / {vendors:,}"},
            {"label": "Pro revenue 30d", "value": round(rev30), "money": True, "delta": round(rev30 - rev_prev), "deltaUnit": "$", "deltaLabel": "vs prior 30d"},
        ],
        "series": {"name": "new couples / week", "values": weekly(cts), "color": "#19d3ff"},
        "upcoming": sorted(upcoming, key=lambda e: e["date"])[:3],
        "counts": {"vendors": vendors, "claimed": claimed, "claims_pending": claims_pending, "inquiries_unanswered": inq_new, "couples": len(couples), "pro_active": subs,
                   "users": len(users), "users_24h": u24, "couples_24h": c24, "signup_avg_day": avg_day, "hours_since_signup": hours_since, "signup_gap_hours": gap_hours},
    }


# ---------------- Roven ----------------
def collect_roven(db):
    employers = stream(db.collection("employers"), select=["status", "pricingTier", "name"])
    jobs = stream(db.collection("jobs"), select=["status", "createdAt", "title", "employerId"])
    apps = stream(db.collection("applications"), select=["appliedAt", "status"])
    placements = stream(db.collection("placements"), select=["hiredAt", "feeStatus", "feeAmount"])
    pend_emp = count(db.collection("employerApplications"))
    ats = [ts(a.get("appliedAt")) for a in apps]
    a7 = sum(1 for t in ats if t and t >= D7); a_prev = sum(1 for t in ats if t and D14 <= t < D7)
    active = sum(1 for j in jobs if j.get("status") == "active"); review = sum(1 for j in jobs if j.get("status") == "pending_review")
    fees_due = sum(num(p.get("feeAmount")) for p in placements if p.get("feeStatus") == "due")
    hires30 = sum(1 for p in placements if ts(p.get("hiredAt")) and ts(p.get("hiredAt")) >= D30)
    pending = [{"id": j["_id"], "kind": "roven_approve_job", "label": f"job pending review: {j.get('title')}"} for j in jobs if j.get("status") == "pending_review"]
    try:
        pending += [{"id": e["_id"], "kind": "roven_approve_employer", "label": f"employer application: {e.get('companyName')} ({e.get('email')})"} for e in stream(db.collection("employerApplications"), status="pending")]
    except Exception:
        pass
    months = defaultdict(float)
    for p in placements:
        t = ts(p.get("hiredAt"))
        if t and p.get("feeStatus") == "paid": months[t.strftime("%Y-%m")] += num(p.get("feeAmount"))
    return {
        "detail": {"pending": pending, "monthly": {k: round(v) for k, v in sorted(months.items())[-12:]}, "recent": [{"id": j["_id"], "names": j.get("title") or "job", "date": (ts(j.get("createdAt")) or NOW).strftime("%Y-%m-%d"), "status": j.get("status")} for j in sorted(jobs, key=lambda j: ts(j.get("createdAt")) or NOW, reverse=True)[:8]]},
        "headline": [
            {"label": "Applications 7d", "value": a7, "delta": delta(a7, a_prev), "deltaLabel": "vs prior 7d"},
            {"label": "Active jobs", "value": active, "delta": review, "deltaUnit": " pending review", "deltaLabel": ""},
            {"label": "Employers", "value": len(employers), "delta": pend_emp, "deltaUnit": " awaiting approval", "deltaLabel": ""},
            {"label": "Fees due", "value": round(fees_due), "money": True, "delta": hires30, "deltaUnit": " hires 30d", "deltaLabel": ""},
        ],
        "series": {"name": "applications / week", "values": weekly(ats), "color": "#ffb340"},
        "upcoming": [],
        "counts": {"employers": len(employers), "jobs_active": active, "jobs_pending_review": review, "applications": len(apps), "placements": len(placements)},
    }


# ---------------- LeaseReputation ----------------
def collect_lr(db):
    from google.cloud.firestore_v1.base_query import FieldFilter
    reviews = [d.to_dict() for d in db.collection_group("reviews").select(["createdAt", "status", "rating"]).stream()]
    rts = [ts(r.get("createdAt")) for r in reviews]
    r7 = sum(1 for t in rts if t and t >= D7); r_prev = sum(1 for t in rts if t and D14 <= t < D7)
    pending_reviews = sum(1 for r in reviews if r.get("status") in ("pending", "pending_review"))
    users = stream(db.collection("users"), select=["createdAt"])
    uts = [ts(u.get("createdAt")) for u in users]
    u7 = sum(1 for t in uts if t and t >= D7); u_prev = sum(1 for t in uts if t and D14 <= t < D7)
    ver_pending = count(db.collection("verifications").where(filter=FieldFilter("status", "==", "pending")))
    claims_pending = count(db.collection("claimRequests").where(filter=FieldFilter("status", "==", "pending")))
    reports = count(db.collection("reports"))
    return {
        "detail": {"monthly": {}},
        "headline": [
            {"label": "Reviews 7d", "value": r7, "delta": delta(r7, r_prev), "deltaLabel": "vs prior 7d"},
            {"label": "New users 7d", "value": u7, "delta": delta(u7, u_prev), "deltaLabel": "vs prior 7d"},
            {"label": "Verifications pending", "value": ver_pending},
            {"label": "Claims pending", "value": claims_pending, "delta": reports, "deltaUnit": " reports", "deltaLabel": ""},
        ],
        "series": {"name": "reviews / week", "values": weekly(rts), "color": "#7be8ff"},
        "upcoming": [],
        "counts": {"reviews": len(reviews), "reviews_pending": pending_reviews, "users": len(users)},
    }


COLLECTORS = {"atavia": collect_films, "es": collect_films, "lazo": collect_lazo, "roven": collect_roven, "lr": collect_lr}


def main():
    out = {"collectedAt": NOW.isoformat(), "businesses": {}}
    for biz, fn in COLLECTORS.items():
        try:
            db = client_for(biz)
            if db is None:
                out["businesses"][biz] = {"error": "needs access", "hint": "run: gcloud auth application-default login (as an account with Viewer on this project)"}
                print(f"{biz}: no credential")
                continue
            out["businesses"][biz] = fn(db)
            print(f"{biz}: ok", json.dumps(out["businesses"][biz]["headline"]))
        except Exception as e:
            msg = str(e)
            out["businesses"][biz] = {"error": msg if "Google sign-in expired" in msg else f"{type(e).__name__}: {msg[:160]}"}
            print(f"{biz}: FAILED {msg[:160]}")
            if "Google sign-in expired" not in msg: traceback.print_exc()
    # money view: 12 months of cash-in across businesses
    allm = set()
    for b in out["businesses"].values():
        allm.update((b.get("detail") or {}).get("monthly", {}).keys())
    cur = NOW.strftime("%Y-%m"); last = (NOW.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    ym_list = sorted(allm | {cur, last})[-12:]
    months = []
    for ym in ym_list:
        row = {"ym": ym}
        for biz, b in out["businesses"].items():
            row[biz] = (b.get("detail") or {}).get("monthly", {}).get(ym, 0)
        row["total"] = sum(v for k, v in row.items() if k not in ("ym", "total"))
        months.append(row)
    monday = (TODAY - timedelta(days=TODAY.weekday()))
    weeks = []
    for i in range(13):
        wk = (monday + timedelta(days=7 * i)).isoformat(); row = {"week": wk, "total": 0, "items": []}
        for biz, b in out["businesses"].items():
            f = ((b.get("detail") or {}).get("forecast") or {}).get(wk)
            if f: row[biz] = f["amount"]; row["total"] += f["amount"]; row["items"] += [f"{biz}: {x}" for x in f["items"]]
        weeks.append(row)
    past_due = [dict(x, business=biz) for biz, b in out["businesses"].items() for x in ((b.get("detail") or {}).get("pastDue") or [])]
    out["money"] = {"months": months, "thisMonth": next((m["total"] for m in months if m["ym"] == cur), 0), "lastMonth": next((m["total"] for m in months if m["ym"] == last), 0),
                    "forecast": weeks, "forecast90": sum(w["total"] for w in weeks), "pastDue": past_due, "pastDueTotal": sum(x["amount"] for x in past_due),
                    "yoy": {biz: b.get("yoy") for biz, b in out["businesses"].items() if b.get("yoy")}}
    body = json.dumps({"metrics": out})
    if "--dry-run" in sys.argv:
        print(body); return
    key = open(os.path.join(HERE, ".hub-key")).read().strip()
    r = subprocess.run(["curl", "-s", "-X", "POST", "-H", "content-type: application/json", "-H", f"x-hub-key: {key}", "--data-binary", "@-", HUB + "/api/state"],
                       input=body, capture_output=True, text=True, timeout=60)
    print("posted:", r.stdout.strip() or r.stderr.strip())


if __name__ == "__main__":
    main()
