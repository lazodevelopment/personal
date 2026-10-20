"""JARVIS hands: executes actions Jesse confirmed on the hub. Written at Jesse's explicit request.

Polls the hub's queue every 20 seconds and performs each CONFIRMED change in Firestore using the same
credentials as the metrics collector. Nothing runs unless Jesse pressed CONFIRM on the hub first.
Every write mirrors the existing admin tools exactly:
  roven_approve_job        jobs/{id} {status: active}                          (roven-admin/approve_jobs.py)
  roven_reject_job         jobs/{id} {status: rejected}
  roven_approve_employer   employerApplications -> employers doc + auth claim   (roven-admin/approve_employer.py)
  lazo_claim               claimRequests + vendors + users in one batch         (Vendor app admin queue)
  lazo_listing             listingRequests -> vendors/manual-<metro>-<slug> + users.vendorId   (Vendor app _adminApproveListing)
  booking_note             bookings/{id} admin_notes arrayUnion({at,text,by})   (atavia-admin/index.html addNote)
  lazo_inquiry_responded   inquiries/{id} {status: responded, respondedAt}      (Vendor app)
Run: jarvis_hands.bat, or `python jarvis_hands.py --once` to process the queue a single time.
"""
import json, os, sys, time, subprocess, traceback, warnings
from datetime import datetime, timezone
warnings.filterwarnings("ignore", message=".*without a quota project.*")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from collect_metrics import client_for  # same credential resolution as the collector

HUB = "https://jarvis-hub.floral-credit-e4f0.workers.dev"
KEY = open(os.path.join(HERE, ".hub-key")).read().strip()
BY = "JARVIS · jesse@briskhealth.com"


DONE = os.path.join(HERE, "hands_done.json")   # ids already executed here, so a lost result post never runs a write twice


class HubError(Exception):
    pass


def api(path, body=None):
    args = ["curl", "-s", "-m", "30", "-w", "\n%{http_code}", "-A", "Mozilla/5.0 (JARVIS hands)", "-H", f"x-hub-key: {KEY}", HUB + path]
    if body is not None:
        args += ["-X", "POST", "-H", "content-type: application/json", "--data-binary", json.dumps(body)]
    r = subprocess.run(args, capture_output=True, text=True, timeout=60)
    out, _, code = r.stdout.rpartition("\n")
    if r.returncode != 0 or not code.startswith("2"):
        raise HubError(f"{path}: curl {r.returncode}, HTTP {code or '?'} {out[:120]}")
    return json.loads(out) if out.strip() else None


def load_done():
    try:
        with open(DONE, encoding="utf-8") as f: return json.load(f)
    except Exception: return {}


def save_done(done):
    cutoff = time.time() - 30 * 86400
    done = {k: v for k, v in done.items() if v.get("t", 0) > cutoff}
    tmp = DONE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(done, f)
    os.replace(tmp, DONE)


def db_for(biz):
    db = client_for(biz)
    if db is None: raise RuntimeError(f"no Firestore credentials for {biz} on this machine")
    return db


def roven_job(p, status):
    db = db_for("roven")
    ref = db.collection("jobs").document(p["jobId"]); doc = ref.get()
    if not doc.exists: return False, "job not found"
    if doc.to_dict().get("status") == status: return True, f"already {status}"
    ref.update({"status": status})
    return True, f"{doc.to_dict().get('title', p['jobId'])} → {status}"


def roven_approve_employer(p):
    from google.cloud import firestore
    import firebase_admin
    from firebase_admin import auth
    db = db_for("roven")
    app_ref = db.collection("employerApplications").document(p["employerId"]); app_doc = app_ref.get()
    if not app_doc.exists: return False, "application not found"
    a = app_doc.to_dict()
    if a.get("status") == "approved": return True, "already approved"
    emp_ref = db.collection("employers").document()
    emp_ref.set({"name": a.get("companyName"), "website": a.get("website"), "industry": a.get("industry"), "metro": a.get("metro"),
                 "verified": True, "verificationMethod": "manual_founder", "notifyEmail": a.get("email"), "members": [a.get("uid")],
                 "createdAt": firestore.SERVER_TIMESTAMP, "stats": {"applicationsReceived": 0, "dispositionedCount": 0, "hiresReported": 0}})
    if a.get("uid"):
        try:
            fa = firebase_admin.get_app("roven")
            user = auth.get_user(a["uid"], app=fa)
            claims = dict(user.custom_claims or {}); claims["employerId"] = emp_ref.id
            auth.set_custom_user_claims(a["uid"], claims, app=fa)
        except Exception as e:
            return False, f"employer {emp_ref.id} created but the auth claim failed: {e}"
    app_ref.update({"status": "approved", "employerId": emp_ref.id, "approvedAt": firestore.SERVER_TIMESTAMP})
    return True, f"{a.get('companyName')} approved as employer {emp_ref.id}"


def lazo_claim(p):
    db = db_for("lazo")
    decision = p.get("decision", "approved"); now = datetime.now(timezone.utc)
    req_ref = db.collection("claimRequests").document(p["claimId"]); req = req_ref.get()
    if not req.exists: return False, "claim request not found"
    r = req.to_dict()
    if r.get("status") not in (None, "", "pending", "needs_review"): return True, f"already {r.get('status')}"   # never re-decide an old claim
    if decision != "approved":
        req_ref.update({"status": "rejected", "reviewedAt": now, "reviewedBy": BY})
        return True, f"claim by {r.get('email') or r.get('uid')} rejected"
    vendor_id, uid_ = r.get("vendorId"), r.get("uid")
    if not vendor_id or not uid_: return False, "claim request has no vendorId/uid"
    v = db.collection("vendors").document(vendor_id).get().to_dict() or {}
    if v.get("claimedBy") and v["claimedBy"] != uid_: return False, "vendor already claimed by someone else"
    batch = db.batch()
    batch.update(db.collection("vendors").document(vendor_id), {"claimedBy": uid_, "claimStatus": "claimed", "verified": True, "claimedAt": now})
    batch.set(db.collection("users").document(uid_), {"vendorId": vendor_id}, merge=True)
    batch.update(req_ref, {"status": "approved", "approvedBy": "admin", "actedByUid": "jarvis", "reviewedAt": now, "reviewedBy": BY})
    batch.commit()  # the claimApprovedEmail Cloud Function sends the welcome email on this status change
    return True, f"{v.get('name', vendor_id)} claimed by {r.get('email') or uid_}"


METRO_NAMES = {"dallas-fort-worth": "Dallas-Fort Worth", "raleigh-durham": "Raleigh-Durham", "washington-dc": "Washington DC", "st-louis": "St. Louis", "san-francisco-bay": "San Francisco Bay"}


def lazo_listing(p):
    """Mirror of the Vendor app's _adminApproveListing / _adminDeny for listingRequests: the vendor doc id is
    manual-<metroId>-<slug(businessName)>, created claimed + verified, and the claimant's users doc gets vendorId.
    The Cloud Function onListingDecided emails the vendor on the status change."""
    import re
    db = db_for("lazo")
    ref = db.collection("listingRequests").document(p["requestId"]); doc = ref.get()
    if not doc.exists: return False, "listing request not found"
    r = doc.to_dict(); now = datetime.now(timezone.utc)
    if r.get("status") not in ("pending", "needs_review"): return True, f"already {r.get('status')}"
    if p.get("decision", "approved") != "approved":
        ref.update({"status": "denied", "denyReason": p.get("reason") or "Not approved for listing", "actedByUid": "jarvis", "reviewedAt": now, "reviewedBy": BY})
        return True, f"{r.get('businessName')} denied"
    uid_, name, metro = r.get("uid") or "", r.get("businessName") or "", r.get("metroId") or "phoenix"
    if not uid_ or not name: return False, "request is missing uid or businessName"
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()); slug = re.sub(r"-{2,}", "-", slug).strip("-")[:60]
    vendor_id = f"manual-{metro}-{slug}"
    v_ref = db.collection("vendors").document(vendor_id); v = v_ref.get().to_dict() or {}
    if v.get("claimedBy") and v["claimedBy"] != uid_: return False, f"conflict: {vendor_id} exists and is claimed by someone else"
    label = METRO_NAMES.get(metro) or " ".join(w.capitalize() for w in metro.split("-"))
    cats = [str(c) for c in r.get("categories") or []] if isinstance(r.get("categories"), list) else []
    batch = db.batch()
    batch.set(v_ref, {"placeId": vendor_id, "name": name, "slug": slug, "address": "Serving " + label, "phone": str(r.get("phone") or ""), "website": str(r.get("website") or ""),
                      "metroId": metro, "categories": cats, "score": 65, "reviewCount": 0, "claimStatus": "claimed", "claimedBy": uid_, "verified": True,
                      "source": "manual", "serviceArea": True, "heardAbout": str(r.get("heardAbout") or ""), "seededAt": now}, merge=True)
    batch.set(db.collection("users").document(uid_), {"vendorId": vendor_id}, merge=True)
    batch.update(ref, {"status": "approved", "approvedBy": "admin", "actedByUid": "jarvis", "reviewedAt": now, "reviewedBy": BY})
    batch.commit()
    return True, f"{name} listed as {vendor_id} and claimed by {r.get('email') or uid_}"


def booking_note(p):
    from google.cloud import firestore
    if p.get("business", "atavia") not in ("atavia", "es", "olivialayne"): return False, "booking notes are for atavia, es or olivialayne only"
    if not str(p.get("note") or "").strip(): return False, "empty note"
    db = db_for(p.get("business", "atavia"))
    ref = db.collection("bookings").document(p["bookingId"]); doc = ref.get()
    if not doc.exists: return False, "booking not found"
    ref.update({"admin_notes": firestore.ArrayUnion([{"at": datetime.now(timezone.utc), "text": p["note"], "by": BY}])})
    return True, f"note added to {doc.to_dict().get('client_names', p['bookingId'])}"


def lazo_inquiry_responded(p):
    db = db_for("lazo")
    ref = db.collection("inquiries").document(p["inquiryId"])
    if not ref.get().exists: return False, "inquiry not found"
    ref.update({"status": "responded", "respondedAt": datetime.now(timezone.utc)})
    return True, "marked responded"


HANDLERS = {
    "roven_approve_job": lambda p: roven_job(p, "active"),
    "roven_reject_job": lambda p: roven_job(p, "rejected"),
    "roven_approve_employer": roven_approve_employer,
    "lazo_claim": lazo_claim,
    "lazo_listing": lazo_listing,
    "booking_note": booking_note,
    "lazo_inquiry_responded": lazo_inquiry_responded,
}


def report(done, item_id):
    d = done[item_id]
    try:
        api("/api/queue/result", {"id": item_id, "ok": d["ok"], "message": d["msg"]})
        d["reported"] = True
    except HubError as e:
        print("result not recorded yet (will retry):", e, flush=True)


def once():
    done = load_done()
    for item_id, d in done.items():   # results the hub never acknowledged
        if not d.get("reported"): report(done, item_id)
    pending = api("/api/queue") or []
    for item in pending:
        item_id = item.get("id")
        if not item_id: continue
        if item_id in done:   # ran here already; only the result post was lost
            if not done[item_id].get("reported"): report(done, item_id)
            continue
        try:
            claim = api("/api/queue/claim", {"id": item_id}) or {}
        except HubError as e:
            print("claim failed:", e, flush=True); continue
        if not claim.get("ok"): continue   # cancelled or already taken
        fn = HANDLERS.get(item.get("kind"))
        try:
            ok, msg = (False, "unknown action kind") if not fn else fn(item.get("params") or {})
        except Exception as e:
            ok, msg = False, f"{type(e).__name__}: {str(e)[:160]}"; traceback.print_exc()
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), item.get("summary"), "→", "ok" if ok else "FAILED", msg, flush=True)
        done[item_id] = {"ok": ok, "msg": msg, "t": time.time(), "reported": False}
        save_done(done)   # recorded before the result post, so a failed post can't cause a second run
        report(done, item_id)
    save_done(done)
    return len(pending)


if __name__ == "__main__":
    if "--once" in sys.argv:
        print("processed", once()); sys.exit(0)
    print("JARVIS hands running; polling every 20s", flush=True)
    while True:
        try: once()
        except Exception as e: print("poll error", e, flush=True)
        time.sleep(20)
