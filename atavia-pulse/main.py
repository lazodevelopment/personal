# pulse/main.py -- JC-ATV-PULSE-0910-006 (006: no availability doc - any date can be staffed; 003: packages_viewers_30d; 002: create-time fallback)
"""public_pulse: the social-proof numbers the Atavia site shows.

Runs from Cloud Scheduler (every 6 hours) and writes Firestore public/pulse:
  visitors_30d   real visits in the last 30 days (sessions, bots filtered the way the admin page filters)
  visitors_7d    same, last 7 days
  packages_viewers_30d  distinct real visits that opened the packages page in the last 30 days
  inquiries_30d  couples who raised a hand in the last 30 days: contact inquiries + booking starts (leads)
                 + bookings, de-duplicated by email, test bookings excluded
  updated_at     server timestamp

The doc is world-readable (rules: match /public/{doc} { allow read: if true; }); the site reads it with
the public web key. Nothing else about sessions, leads or bookings leaves the project.

GET ?debug=1 returns the breakdown as JSON and does not write.
"""
import datetime as dt
import json
import re

import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import functions_framework

firebase_admin.initialize_app()

WINDOW_DAYS = 30

# Same non-people rules as admin visitors.html (JC-ATV-BOTGATE-0909-001).
BOT_RE = re.compile(
    r"bot|crawl|spider|slurp|lighthouse|facebookexternalhit|facebot|meta-externalagent|whatsapp|twitterbot|"
    r"linkedinbot|pinterest|slackbot|discordbot|telegrambot|applebot|bingpreview|headlesschrome|phantomjs|"
    r"petalbot|ahrefs|semrush|mj12|screaming frog|gtmetrix|pingdom|uptimerobot|preview|snapchat|"
    r"skypeuripreview|embedly|google-inspectiontool|yandex|baidu|duckduckbot", re.I)
DC_CITIES = {"Boardman", "Ashburn", "The Dalles", "Council Bluffs", "Prineville", "Umatilla", "Forest City",
             "Altoona", "Hilliard", "Papillion", "Sterling", "Quincy"}
META_UTM = re.compile(r"^(ig|fb|msg|an)$", re.I)

# Timestamp / email field names differ a little between inquiries, leads and bookings; try each.
TS_FIELDS = ("created_at", "createdAt", "created", "submitted_at", "lead_at", "booked_at", "timestamp", "t")
EMAIL_FIELDS = ("email", "client_email", "lead_email", "customer_email", "contact_email")


def _ts(d):
    for k in TS_FIELDS:
        v = d.get(k)
        if isinstance(v, dt.datetime):
            return v if v.tzinfo else v.replace(tzinfo=dt.timezone.utc)
    return None


def _email(d):
    for k in EMAIL_FIELDS:
        v = d.get(k)
        if isinstance(v, str) and "@" in v:
            return v.strip().lower()
    return ""


def _is_bot_session(s):
    if s.get("bot") is True:
        return True
    if BOT_RE.search(s.get("ua") or ""):
        return True
    try:
        pages = int(s.get("page_count") or 1)
    except (TypeError, ValueError):
        pages = 1
    city = s.get("city")
    if city in DC_CITIES and pages <= 1:
        a, b = s.get("first_seen"), s.get("last_seen")
        if not (isinstance(a, dt.datetime) and isinstance(b, dt.datetime)) or (b - a).total_seconds() < 15:
            return True
    no_geo = not city and not isinstance(s.get("lat"), (int, float))
    if not s.get("engaged") and no_geo and META_UTM.match(s.get("utm_source") or "") and pages <= 1:
        return True
    return False


def _real_sessions(db, since):
    """Real (non-bot) sessions started in the window, keyed by id, plus totals."""
    real, total = {}, 0
    q = db.collection("sessions").where(filter=FieldFilter("first_seen", ">=", since))
    for doc in q.stream():
        s = doc.to_dict() or {}
        total += 1
        if not _is_bot_session(s):
            real[doc.id] = s
    return real, total, total - len(real)


def _count_page_viewers(db, since, real, prefix="/packages"):
    """Distinct real sessions that opened a page under `prefix`: landing/last page first, then the hit trail."""
    viewers = set()
    for sid, s in real.items():
        if str(s.get("landing") or "").startswith(prefix) or str(s.get("page") or "").startswith(prefix):
            viewers.add(sid)
    try:
        q = db.collection_group("hits").where(filter=FieldFilter("t", ">=", since)).select(["path"])
        for h in q.stream():
            sid = h.reference.parent.parent.id
            if sid in real and str(h.get("path") or "").startswith(prefix):
                viewers.add(sid)
    except Exception as e:  # no collection-group index yet: read each session's trail instead
        print("hits collection-group query unavailable, reading per session: " + str(e)[:160])
        for sid in real:
            if sid in viewers:
                continue
            for h in db.collection("sessions").document(sid).collection("hits").select(["path"]).stream():
                if str(h.get("path") or "").startswith(prefix):
                    viewers.add(sid)
                    break
    return len(viewers)


def _count_inquiries(db, since):
    emails, anon, per = set(), 0, {}
    for coll in ("inquiries", "leads", "bookings"):
        n = 0
        for doc in db.collection(coll).stream():
            d = doc.to_dict() or {}
            if coll == "bookings" and d.get("test_mode") is True:
                continue
            t = _ts(d) or getattr(doc, "create_time", None)
            if not t or t < since:
                continue
            e = _email(d)
            if e:
                if e in emails:
                    continue
                emails.add(e)
            else:
                anon += 1
            n += 1
        per[coll] = n
    return len(emails) + anon, per


@functions_framework.http
def public_pulse(request):
    db = firestore.client()
    now = dt.datetime.now(dt.timezone.utc)
    since30 = now - dt.timedelta(days=WINDOW_DAYS)
    since7 = now - dt.timedelta(days=7)

    real30, total30, bots30 = _real_sessions(db, since30)
    real7, total7, bots7 = _real_sessions(db, since7)
    packages30 = _count_page_viewers(db, since30, real30)
    inquiries30, per = _count_inquiries(db, since30)

    out = {
        "visitors_30d": len(real30),
        "visitors_7d": len(real7),
        "packages_viewers_30d": packages30,
        "inquiries_30d": inquiries30,
        "window_days": WINDOW_DAYS,
    }
    detail = {**out, "sessions_30d_total": total30, "sessions_30d_bots": bots30,
              "sessions_7d_total": total7, "sessions_7d_bots": bots7,
              "inquiries_by_collection": per,
              "computed_at": now.isoformat()}
    print("public_pulse " + json.dumps(detail))

    if request.args.get("debug"):
        return (json.dumps(detail, indent=1), 200, {"content-type": "application/json"})

    db.collection("public").document("pulse").set({**out, "updated_at": firestore.SERVER_TIMESTAMP})
    return (json.dumps(out), 200, {"content-type": "application/json"})
