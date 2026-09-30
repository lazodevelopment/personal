"""JARVIS hands: executes actions Jesse confirmed on the hub. Written at Jesse's explicit request.

Polls the hub's queue every 20 seconds and performs each CONFIRMED change in Firestore using the same
credentials as the metrics collector. Nothing runs unless Jesse pressed CONFIRM on the hub first.
Every write mirrors the existing admin tools exactly:
  roven_approve_job        jobs/{id} {status: active}                          (roven-admin/approve_jobs.py)
  roven_reject_job         jobs/{id} {status: rejected}
  roven_approve_employer   employerApplications -> employers doc + auth claim   (roven-admin/approve_employer.py)
  lazo_claim               claimRequests + vendors + users in one batch         (Vendor app admin queue)
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


def api(path, body=None):
    args = ["curl", "-s", "-H", f"x-hub-key: {KEY}", HUB + path]
    if body is not None:
        args += ["-X", "POST", "-H", "content-type: application/json", "--data-binary", json.dumps(body)]
    r = subprocess.run(args, capture_output=True, text=True, timeout=60)
    return json.loads(r.stdout) if r.stdout.strip() else None


def roven_job(p, status):
    db = client_for("roven")
    ref = db.collection("jobs").document(p["jobId"]); doc = ref.get()
    if not doc.exists: return False, "job not found"
    ref.update({"status": status})
    return True, f"{doc.to_dict().get('title', p['jobId'])} → {status}"


def roven_approve_employer(p):
    from google.cloud import firestore
    import firebase_admin
    from firebase_admin import auth
    db = client_for("roven")
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
    db = client_for("lazo")
    decision = p.get("decision", "approved"); now = datetime.now(timezone.utc)
    req_ref = db.collection("claimRequests").document(p["claimId"]); req = req_ref.get()
    if not req.exists: return False, "claim request not found"
    r = req.to_dict()
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


def booking_note(p):
    from google.cloud import firestore
    db = client_for(p.get("business", "atavia"))
    ref = db.collection("bookings").document(p["bookingId"]); doc = ref.get()
    if not doc.exists: return False, "booking not found"
    ref.update({"admin_notes": firestore.ArrayUnion([{"at": datetime.now(timezone.utc), "text": p["note"], "by": BY}])})
    return True, f"note added to {doc.to_dict().get('client_names', p['bookingId'])}"


def lazo_inquiry_responded(p):
    db = client_for("lazo")
    ref = db.collection("inquiries").document(p["inquiryId"])
    if not ref.get().exists: return False, "inquiry not found"
    ref.update({"status": "responded", "respondedAt": datetime.now(timezone.utc)})
    return True, "marked responded"


HANDLERS = {
    "roven_approve_job": lambda p: roven_job(p, "active"),
    "roven_reject_job": lambda p: roven_job(p, "rejected"),
    "roven_approve_employer": roven_approve_employer,
    "lazo_claim": lazo_claim,
    "booking_note": booking_note,
    "lazo_inquiry_responded": lazo_inquiry_responded,
}


def once():
    pending = api("/api/queue") or []
    for item in pending:
        fn = HANDLERS.get(item.get("kind"))
        try:
            ok, msg = (False, "unknown action kind") if not fn else fn(item.get("params") or {})
        except Exception as e:
            ok, msg = False, f"{type(e).__name__}: {str(e)[:160]}"; traceback.print_exc()
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), item.get("summary"), "→", "ok" if ok else "FAILED", msg, flush=True)
        api("/api/queue/result", {"id": item["id"], "ok": ok, "message": msg})
    return len(pending)


if __name__ == "__main__":
    if "--once" in sys.argv:
        print("processed", once()); sys.exit(0)
    print("JARVIS hands running; polling every 20s", flush=True)
    while True:
        try: once()
        except Exception as e: print("poll error", e, flush=True)
        time.sleep(20)
