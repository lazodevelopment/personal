# ============================================================================
# ROVEN — Cloud Functions
# Build ID: JC-ROVEN-FUNCTIONS-0801-020
#
# on_application_write: the function that makes dispositions COUNT.
# Fires on every applications/{appId} write and maintains, atomically:
#
#   1. ACCOUNTABILITY TIMESTAMPS on the application itself
#        firstResponseAt  — first time the employer answered (applied -> any
#                           employer status). The raw material for response
#                           rate / response time.
#        dispositionedAt  — when the application reached a terminal answer
#                           (hired / rejected).
#   2. EMPLOYER STATS AGGREGATES on employers/{employerId}.stats
#        applicationsReceived, dispositionedCount, sumResponseHours,
#        avgResponseHours, hiresReported
#   3. THE PLACEMENTS LEDGER on 'hired' — placements/{appId}
#        feeStatus 'waived_founding', feeAmount 0. Built-to-charge from
#        hire #1: activating pricing later is a config change, not a
#        migration. Deterministic doc id (= appId) makes this idempotent.
#   4. VERIFIED WORK HISTORY on 'hired' — users/{uid}/workHistory/{appId}
#        candidateConfirmed starts False; the hire check-in flow (later)
#        flips it True. Employer/job names denormalized at hire time per
#        the reputation spec §8.2.
#
# Loop guard: this function writes timestamp fields back onto the same
# application document, which re-triggers it. We only act when status
# actually changed (or on create), so the echo trigger no-ops.
# ============================================================================

from firebase_admin import firestore, initialize_app
from firebase_functions import firestore_fn, identity_fn

initialize_app()

RESPONSE_STATUSES = {"reviewed", "interviewing", "offer", "hired", "rejected"}
TERMINAL_STATUSES = {"hired", "rejected"}


@firestore_fn.on_document_written(
    document="applications/{appId}",
    region="us-central1",
    secrets=["RESEND_API_KEY"],
)
def on_application_write(
    event: firestore_fn.Event[firestore_fn.Change[firestore_fn.DocumentSnapshot | None]],
) -> None:
    db = firestore.client()
    app_id = event.params["appId"]

    before = event.data.before
    after = event.data.after

    # deletion — nothing to do (rules forbid it anyway)
    if after is None or not after.exists:
        return

    after_data = after.to_dict() or {}
    before_data = (before.to_dict() or {}) if (before is not None and before.exists) else None
    is_create = before_data is None

    employer_id = after_data.get("employerId") or ""
    candidate_uid = after_data.get("candidateUid") or ""
    job_id = after_data.get("jobId") or ""
    new_status = after_data.get("status") or ""
    old_status = (before_data or {}).get("status") or ""

    employer_ref = db.collection("employers").document(employer_id) if employer_id else None

    # ------------------------------------------------------------------
    # CREATE: count the application on the employer's record
    # ------------------------------------------------------------------
    if is_create:
        if employer_ref is not None:
            employer_ref.set(
                {"stats": {"applicationsReceived": firestore.Increment(1)}},
                merge=True,
            )
        _notify_new_application(db, app_id, after_data, employer_id, job_id,
                                candidate_uid)
        print(f"[create] {app_id}: counted for employer {employer_id}")
        return

    # ------------------------------------------------------------------
    # UPDATE: only act on real status transitions (loop guard)
    # ------------------------------------------------------------------
    if new_status == old_status:
        return

    now = firestore.SERVER_TIMESTAMP
    app_ref = db.collection("applications").document(app_id)
    app_updates = {}

    # ---- first employer response ----
    became_response = (
        new_status in RESPONSE_STATUSES
        and after_data.get("firstResponseAt") is None
    )
    if became_response:
        app_updates["firstResponseAt"] = now
        # response-time aggregate (hours from appliedAt to now)
        applied_at = after_data.get("appliedAt")
        if employer_ref is not None:
            stats_update = {"dispositionedCount": firestore.Increment(1)}
            if applied_at is not None:
                try:
                    from datetime import datetime, timezone

                    elapsed_h = (
                        datetime.now(timezone.utc) - applied_at
                    ).total_seconds() / 3600.0
                    if elapsed_h >= 0:
                        stats_update["sumResponseHours"] = firestore.Increment(
                            round(elapsed_h, 2)
                        )
                except Exception as exc:  # aggregate is best-effort
                    print(f"[warn] response-time calc failed: {exc}")
            employer_ref.set({"stats": stats_update}, merge=True)
            _recompute_avg_response(db, employer_id)

    # ---- terminal disposition ----
    if new_status in TERMINAL_STATUSES and after_data.get("dispositionedAt") is None:
        app_updates["dispositionedAt"] = now

    # ---- HIRE: placements ledger + verified work history ----
    if new_status == "hired" and old_status != "hired":
        _record_hire(db, app_id, employer_id, candidate_uid, job_id)

    if app_updates:
        app_ref.set(app_updates, merge=True)

    # ---- tell the candidate what happened ----
    # 'interviewing' is covered by on_interview_proposed and 'hired' by the
    # hire check-in, so those are skipped here to avoid double emails.
    if new_status in ("reviewed", "offer", "rejected"):
        _notify_status_change(db, app_id, after_data, new_status, employer_id,
                              job_id, candidate_uid)

    print(f"[update] {app_id}: {old_status} -> {new_status}")


def _recompute_avg_response(db, employer_id: str) -> None:
    """Recompute avgResponseHours from the running sum/count."""
    try:
        ref = db.collection("employers").document(employer_id)
        snap = ref.get()
        stats = (snap.to_dict() or {}).get("stats") or {}
        count = stats.get("dispositionedCount") or 0
        total = stats.get("sumResponseHours") or 0
        if count > 0:
            ref.set(
                {"stats": {"avgResponseHours": round(total / count, 1)}},
                merge=True,
            )
    except Exception as exc:
        print(f"[warn] avg recompute failed for {employer_id}: {exc}")


def _record_hire(
    db, app_id: str, employer_id: str, candidate_uid: str, job_id: str
) -> None:
    """Write the placement record and the verified work-history entry.
    Deterministic doc ids (= application id) make both writes idempotent —
    re-marking 'hired' can never double-record."""
    now = firestore.SERVER_TIMESTAMP

    # denormalize names at hire time (spec §8.2)
    employer_name = ""
    job_title = ""
    employment_type = ""
    try:
        emp = db.collection("employers").document(employer_id).get()
        employer_name = (emp.to_dict() or {}).get("name") or ""
    except Exception:
        pass
    try:
        job = db.collection("jobs").document(job_id).get()
        jd = job.to_dict() or {}
        job_title = jd.get("title") or ""
        employment_type = jd.get("employmentType") or ""
    except Exception:
        pass

    # 1) placements ledger — built to charge, waived for founding employers
    pricing_tier = "founding"
    try:
        emp_data = db.collection("employers").document(employer_id).get().to_dict() or {}
        pricing_tier = emp_data.get("pricingTier") or "founding"
    except Exception:
        pass

    db.collection("placements").document(app_id).set(
        {
            "applicationId": app_id,
            "employerId": employer_id,
            "employerName": employer_name,
            "candidateUid": candidate_uid,
            "jobId": job_id,
            "jobTitle": job_title,
            "employmentType": employment_type,
            "hiredAt": now,
            "feeStatus": "waived_founding" if pricing_tier == "founding" else "due",
            "feeAmount": 0,
        },
        merge=True,
    )

    # 2) verified work-history entry (candidate confirmation pending)
    if candidate_uid:
        db.collection("users").document(candidate_uid).collection(
            "workHistory"
        ).document(app_id).set(
            {
                "employerId": employer_id,
                "employerName": employer_name,
                "jobId": job_id,
                "jobTitle": job_title,
                "employmentType": employment_type,
                "hiredAt": now,
                "applicationId": app_id,
                "verificationLevel": "platform",
                "candidateConfirmed": False,
                "visibility": "verified_employers",
            },
            merge=True,
        )

    # 3) employer hire count
    if employer_id:
        db.collection("employers").document(employer_id).set(
            {"stats": {"hiresReported": firestore.Increment(1)}},
            merge=True,
        )

    # 4) candidate check-in email — the two-sided hire verification
    try:
        import os as _os

        import requests as _rq2

        cand = db.collection("users").document(candidate_uid).get().to_dict() or {}
        cand_email = cand.get("email")
        first = ((cand.get("display_name") or "").split() or ["there"])[0]
        if cand_email:
            confirm = f"https://app.rovenhr.com/hireCheckIn?appId={app_id}&a=yes"
            deny = f"https://app.rovenhr.com/hireCheckIn?appId={app_id}&a=no"
            html_body = f"""<div style='font-family:Arial,sans-serif;max-width:520px;margin:auto;color:#16202E'>
<h2 style='letter-spacing:-.5px'>Congratulations, {first} — {employer_name} reported hiring you.</h2>
<p><strong>{job_title}</strong> · {employer_name}</p>
<p>Confirming makes this a <strong>verified entry on your Roven work
history</strong> — proof of employment no other platform can give you.
It also keeps employers honest on ours.</p>
<p>
<a href='{confirm}' style='background:#1CA45F;color:#fff;padding:12px 22px;border-radius:100px;text-decoration:none;display:inline-block'>Yes, I was hired</a>
&nbsp;&nbsp;<a href='{deny}' style='color:#C0483B'>This isn't right</a>
</p>
<p style='font-size:12px;color:#5B6874'>Roven — the hiring marketplace with receipts.</p>
</div>"""
            resend_key = _os.environ.get("RESEND_API_KEY", "")
            if resend_key:
                _rq2.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {resend_key}"},
                    json={
                        "from": "Roven <alerts@notify.rovenhr.com>",
                        "to": [cand_email],
                        "subject": f"Confirm your hire at {employer_name}",
                        "html": _wrap_legacy(html_body),
                    },
                    timeout=20,
                )
                print(f"[hire] check-in email sent to {cand_email}")
    except Exception as exc:
        print(f"[warn] check-in email failed: {exc}")

    print(f"[hire] {app_id}: placement + workHistory recorded for {candidate_uid}")


# ============================================================================
# on_user_created: v1 candidate verification.
# Per the onboarding spec, launch-phase identity verification IS the
# email/password signup — so every new account is granted the
# identityVerified custom claim at creation, which is what the security
# rules require before an application can be created. Formal ID
# verification becomes a later, stronger layer without changing this gate.
#
# NOTE (blocking function): returns quickly; the claim is set via the
# Admin SDK. Claims land in the user's very first ID token because this
# runs before token issuance completes.
# ============================================================================


@identity_fn.before_user_created(region="us-central1")
def on_user_created(
    event: identity_fn.AuthBlockingEvent,
) -> identity_fn.BeforeCreateResponse:
    # Claims must be returned in the response for beforeCreate — the user
    # record doesn't exist yet, so Admin-SDK claim writes would fail here.
    # Identity Platform bakes these into the account at creation, so the
    # claim is present in the user's very first ID token.
    print(f"[signup] identityVerified granted at creation "
          f"({event.data.email or event.data.uid})")
    return identity_fn.BeforeCreateResponse(
        custom_claims={"identityVerified": True}
    )


# ============================================================================
# RESUME MATCH ENGINE v1
# parse_resume: callable — candidate uploads a resume to Storage, this sends
#   it to Claude for honest structured extraction (never invents; unknowns are
#   null), and writes the draft to users/{uid}/profileHistory/parsed_resume.
#   The candidate reviews and confirms in the app before it becomes profile.
# on_job_activated: when a job goes active, scores opted-in candidates and
#   emails the best fits via Resend. Deduped per candidate+job in jobPings.
# ============================================================================

import base64
import json as _json

import requests as _rq
from firebase_functions import https_fn, options
from firebase_functions.params import SecretParam

ANTHROPIC_API_KEY = SecretParam("ANTHROPIC_API_KEY")
RESEND_API_KEY = SecretParam("RESEND_API_KEY")

_PARSE_PROMPT = """You are parsing a document uploaded to a hiring platform as \
a resume. FIRST decide whether this document actually IS a resume/CV. \
"isResume" is true ONLY if the document presents a person's employment \
history — at least one job or role they have held. Price sheets, invoices, \
brochures, contracts, menus, flyers, marketing materials, government letters, \
tax documents, IRS/EIN letters, certificates, and ID documents are NOT \
resumes, even when they contain a person's name. THEN, only if it truly is a \
resume, extract ONLY what is actually present. Never invent, never upgrade \
titles, never guess employers or dates. If a field is not clearly present, \
use null. Respond with ONLY a JSON object, no preamble, no markdown fences:
{
  "isResume": boolean,
  "documentType": string,   // your best guess at what the document is, e.g. "resume", "price sheet", "invoice"
  "fullName": string|null,
  "email": string|null,
  "phone": string|null,
  "location": string|null,
  "yearsExperience": number|null,
  "roles": [{"title": string, "company": string|null, "startYear": number|null,
             "endYear": number|null, "summary": string|null}],
  "skills": [string],
  "certifications": [string],
  "lowConfidence": [string]   // names of any fields you are unsure about
}"""

_MEDIA = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}


@https_fn.on_call(
    region="us-central1",
    secrets=[ANTHROPIC_API_KEY],
    memory=options.MemoryOption.MB_512,
    timeout_sec=120,
)
def parse_resume(req: https_fn.CallableRequest):
    if req.auth is None:
        raise https_fn.HttpsError("unauthenticated", "Sign in first.")
    uid = req.auth.uid
    storage_path = (req.data or {}).get("storagePath", "")
    if not storage_path.startswith(f"resumes/{uid}/"):
        raise https_fn.HttpsError("permission-denied", "Not your file.")

    from firebase_admin import storage as admin_storage

    ext = storage_path.rsplit(".", 1)[-1].lower()
    media = _MEDIA.get(ext)
    if media is None:
        raise https_fn.HttpsError(
            "invalid-argument", "Upload a PDF or a photo (PNG/JPG) of your resume."
        )

    blob = admin_storage.bucket().blob(storage_path)
    data = blob.download_as_bytes()
    if len(data) > 8 * 1024 * 1024:
        raise https_fn.HttpsError("invalid-argument", "File too large (8 MB max).")
    b64 = base64.b64encode(data).decode()

    block_type = "document" if media == "application/pdf" else "image"
    resp = _rq.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY.value,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 2000,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": block_type,
                     "source": {"type": "base64", "media_type": media, "data": b64}},
                    {"type": "text", "text": _PARSE_PROMPT},
                ],
            }],
        },
        timeout=90,
    )
    if resp.status_code != 200:
        print(f"[parse_resume] API {resp.status_code}: {resp.text[:200]}")
        raise https_fn.HttpsError("internal", "Couldn't read the resume — try again.")

    text = "".join(
        b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text"
    ).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        parsed = _json.loads(text)
    except Exception:
        raise https_fn.HttpsError("internal", "Couldn't structure the resume — try again.")

    if not parsed.get("isResume", False):
        doc_type = parsed.get("documentType") or "something else"
        raise https_fn.HttpsError(
            "failed-precondition",
            f"That looks like a {doc_type}, not a resume. Upload your actual "
            "resume — the document with your work history on it.",
        )

    # structural backstop: a resume with no work history isn't usable even if
    # the classifier was charitable
    if not parsed.get("roles") and not parsed.get("skills"):
        doc_type = parsed.get("documentType") or "document"
        raise https_fn.HttpsError(
            "failed-precondition",
            f"We couldn't find any work history in that {doc_type}. Upload a "
            "resume that lists the jobs you've held.",
        )

    db = firestore.client()
    db.collection("users").document(uid).collection("profileHistory").document(
        "parsed_resume"
    ).set({
        "parsed": parsed,
        "storagePath": storage_path,
        "status": "pending_review",
        "parsedAt": firestore.SERVER_TIMESTAMP,
    })
    return {"ok": True, "parsed": parsed}


def _score_candidate(job: dict, prefs: dict, profile: dict) -> int:
    score = 0
    title = (job.get("title") or "").lower()
    title_words = set(w for w in title.replace("&", " ").split() if len(w) > 3)

    for want in prefs.get("desiredRoles", []):
        want_words = set(w for w in want.lower().split() if len(w) > 3)
        if title_words & want_words:
            score += 40
            break

    for role in (profile or {}).get("roles", []):
        held = set(w for w in (role.get("title") or "").lower().split() if len(w) > 3)
        if title_words & held:
            score += 25
            break

    desc = (job.get("description") or "").lower()
    skills = [s.lower() for s in (profile or {}).get("skills", [])]
    hits = sum(1 for s in skills if s and s in desc)
    score += min(hits * 5, 20)

    if job.get("remote") or (prefs.get("metro", "").lower() in
                             f"{job.get('locationCity','')}, {job.get('locationState','')}".lower()):
        score += 15

    if job.get("employmentType") in prefs.get("employmentTypes", []) or not prefs.get("employmentTypes"):
        score += 10
    return score


@firestore_fn.on_document_written(
    document="jobs/{jobId}",
    region="us-central1",
    secrets=[RESEND_API_KEY],
    memory=options.MemoryOption.MB_512,
    timeout_sec=300,
)
def on_job_activated(
    event: firestore_fn.Event[firestore_fn.Change[firestore_fn.DocumentSnapshot | None]],
) -> None:
    after = event.data.after
    if after is None or not after.exists:
        return
    job = after.to_dict() or {}
    before = event.data.before
    was_active = bool(before is not None and before.exists
                      and (before.to_dict() or {}).get("status") == "active")
    if job.get("status") != "active" or was_active:
        return

    job_id = event.params["jobId"]
    db = firestore.client()

    employer_name = "a verified employer"
    try:
        emp = db.collection("employers").document(job.get("employerId", "")).get()
        employer_name = (emp.to_dict() or {}).get("name") or employer_name
    except Exception:
        pass

    matches = []
    for snap in db.collection("users").where("matchPrefs.notify", "==", True).stream():
        u = snap.to_dict() or {}
        prefs = u.get("matchPrefs") or {}
        email = u.get("email")
        if not email:
            continue
        profile = {}
        try:
            pr = (db.collection("users").document(snap.id)
                  .collection("profileHistory").document("parsed_resume").get())
            if pr.exists and (pr.to_dict() or {}).get("status") == "confirmed":
                profile = (pr.to_dict() or {}).get("parsed") or {}
        except Exception:
            pass
        s = _score_candidate(job, prefs, profile)
        if s >= 50:
            matches.append((s, snap.id, email, u.get("display_name") or ""))

    matches.sort(reverse=True)
    matches = matches[:20]
    if not matches:
        print(f"[match] job {job_id}: no candidates >= threshold")
        return

    pay = ""
    if job.get("salaryMin"):
        unit = {"HOUR": "/hr", "DAY": "/day", "YEAR": "/yr"}.get(job.get("salaryUnit", ""), "")
        pay = f" · ${job['salaryMin']}"
        if job.get("salaryMax") and job["salaryMax"] != job["salaryMin"]:
            pay += f"-${job['salaryMax']}"
        pay += unit

    sent = 0
    for s, uid, email, name in matches:
        ping_ref = db.collection("jobPings").document(f"{job_id}_{uid}")
        if ping_ref.get().exists:
            continue
        link = f"https://app.rovenhr.com/jobDetail?jobId={job_id}"
        first = (name.split() or ["there"])[0]
        html_body = f"""<div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;color:#16202E">
<h2 style="letter-spacing:-.5px">A role just posted that fits you, {first}.</h2>
<p><strong>{job.get('title','Open role')}</strong><br>
{employer_name} · {job.get('locationCity','')}, {job.get('locationState','')}{pay}</p>
<p>This is a confirmed open role at a verified employer — and on Roven,
every application gets an answer. You're seeing it early because your
profile matches.</p>
<p><a href="{link}" style="background:#1CA45F;color:#fff;padding:12px 22px;border-radius:100px;text-decoration:none;display:inline-block">View &amp; apply</a></p>
<p style="font-size:12px;color:#5B6874">You're receiving this because job alerts are on in your Roven profile. Turn them off anytime in the app.</p>
</div>"""
        try:
            r = _rq.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY.value}"},
                json={
                    "from": "Roven <alerts@notify.rovenhr.com>",
                    "to": [email],
                    "subject": f"{job.get('title','A role')} just posted — you're a fit",
                    "html": _wrap_legacy(html_body),
                },
                timeout=20,
            )
            if r.status_code in (200, 201):
                ping_ref.set({
                    "jobId": job_id, "candidateUid": uid, "score": s,
                    "sentAt": firestore.SERVER_TIMESTAMP,
                })
                sent += 1
            else:
                print(f"[match] resend {r.status_code}: {r.text[:150]}")
        except Exception as exc:
            print(f"[match] send failed for {uid}: {exc}")

    print(f"[match] job {job_id}: {len(matches)} matched, {sent} pinged")

    # ---- tell the employer their role is live and what the engine did ----
    try:
        emp_doc = (db.collection("employers").document(job.get("employerId", ""))
                   .get().to_dict() or {})
        to_emp = emp_doc.get("notifyEmail")
        if to_emp and not job.get("liveEmailSentAt"):
            title = job.get("title") or "Your role"
            if sent > 0:
                engine_line = (
                    f"The match engine already emailed "
                    f"<strong style=\"color:#ffffff\">{sent} matching "
                    f"candidate{'s' if sent != 1 else ''}</strong> about it. "
                    f"They heard before it reached the general feed.")
            else:
                engine_line = (
                    "No candidate matches it yet - the engine keeps watching, "
                    "and the moment someone signs up who fits, they get emailed "
                    "automatically. You do not have to repost.")
            body = f"""
<div style="font-family:Georgia,serif;font-size:22px;font-weight:bold;color:#ffffff;letter-spacing:-.5px;padding-bottom:8px">Your role is live.</div>
<div style="font-family:'Courier New',monospace;font-size:10px;letter-spacing:1.2px;font-weight:bold;color:#3ADB8B;padding-bottom:14px">&#10003; CONFIRMED OPEN &middot; {title.upper()}</div>
<div style="font-family:Arial,sans-serif;font-size:14px;line-height:1.65;color:rgba(255,255,255,.75);padding-bottom:16px">
{engine_line}
</div>
<div style="font-family:Arial,sans-serif;font-size:13px;line-height:1.6;color:rgba(255,255,255,.65);padding-bottom:18px">
Two things worth knowing: your listing runs on a 30-day confirmation clock, so
we will check in before it can go stale &mdash; and every applicant you answer
builds the response record shown publicly on all your listings.
</div>
{_btn("View your pipeline", "https://app.rovenhr.com")}
"""
            if _send_mail(to_emp, f"Live on Roven: {title}", body):
                after.reference.update(
                    {"liveEmailSentAt": firestore.SERVER_TIMESTAMP})
                print(f"[live-mail] employer {to_emp}: sent")
    except Exception as exc:
        print(f"[live-mail] failed: {exc}")


# ============================================================================
# confirm_hire: the candidate's side of hire verification.
# Confirms -> workHistory.candidateConfirmed = True (the verified receipt),
# placements gains candidateConfirmed, application gains candidateConfirmedHire.
# Denies  -> hireDisputes/{appId} opens, placements flagged disputed.
# Auth-gated to the application's own candidate.
# ============================================================================


@https_fn.on_call(region="us-central1")
def confirm_hire(req: https_fn.CallableRequest):
    if req.auth is None:
        raise https_fn.HttpsError("unauthenticated", "Sign in first.")
    uid = req.auth.uid
    data = req.data or {}
    app_id = data.get("appId", "")
    confirmed = bool(data.get("confirmed", False))
    if not app_id:
        raise https_fn.HttpsError("invalid-argument", "Missing appId.")

    db = firestore.client()
    app_ref = db.collection("applications").document(app_id)
    app_snap = app_ref.get()
    if not app_snap.exists:
        raise https_fn.HttpsError("not-found", "Application not found.")
    app = app_snap.to_dict() or {}
    if app.get("candidateUid") != uid:
        raise https_fn.HttpsError("permission-denied", "Not your application.")
    if app.get("status") != "hired":
        raise https_fn.HttpsError(
            "failed-precondition", "This application isn't marked as hired."
        )

    now = firestore.SERVER_TIMESTAMP
    app_ref.set({"candidateConfirmedHire": confirmed,
                 "checkInAt": now}, merge=True)

    wh_ref = (db.collection("users").document(uid)
              .collection("workHistory").document(app_id))
    pl_ref = db.collection("placements").document(app_id)

    if confirmed:
        if wh_ref.get().exists:
            wh_ref.set({"candidateConfirmed": True,
                        "confirmedAt": now}, merge=True)
        if pl_ref.get().exists:
            pl_ref.set({"candidateConfirmed": True}, merge=True)
        print(f"[checkin] {app_id}: confirmed by candidate")
        return {"ok": True, "confirmed": True}

    db.collection("hireDisputes").document(app_id).set({
        "applicationId": app_id,
        "candidateUid": uid,
        "employerId": app.get("employerId", ""),
        "jobId": app.get("jobId", ""),
        "openedAt": now,
        "status": "open",
        "reason": "candidate_denied_hire",
    }, merge=True)
    if pl_ref.get().exists:
        pl_ref.set({"disputed": True}, merge=True)
    print(f"[checkin] {app_id}: DISPUTED by candidate")
    return {"ok": True, "confirmed": False}


# ============================================================================
# generate_job_post: the AI job-post drafter.
# Employer gives a title + rough notes; Claude writes an honest, Roven-voice
# description. Hard rules: never invent pay, benefits, or requirements not
# in the notes; no hiring cliches; specific and human. The employer edits
# and owns the result, and every post still passes pending_review.
# ============================================================================

_DRAFT_PROMPT = """You write job descriptions for Roven, a hiring marketplace \
built on honesty: every job is real, pay is always shown, every application \
gets an answer. Write a FULL, detailed description from the employer's rough \
notes — even if the notes are a single sentence.

WHAT YOU MAY EXPAND: the role itself. Use your knowledge of what this job \
title universally involves in this industry — the standard day-to-day \
duties, tools of the trade, and skills any experienced person in this role \
would recognize. A one-line note about the day-to-day should still become a \
rich, concrete picture of the work.

WHAT YOU MAY NEVER INVENT: employer-specific facts. No pay, benefits, \
perks, schedules, team details, culture claims, company history, or \
requirements beyond what the notes state. If the notes don't mention a \
schedule, don't write one. The role can be vivid; the employer's promises \
must be only theirs.

CONTEXT VS. CLAIMS: the company name, industry, and metro below are \
CONTEXT — they may quietly inform tone and word choice, but you must NOT \
assert them as the scope or subject of the work. Do not say the role is \
about, focused on, or "across" the company's industry unless the NOTES \
say so. Example: a wedding-media company hiring a "web content developer" \
with notes about HTML pages gets a description about web content work — \
not "wedding content" — unless the notes mention weddings.

STYLE:
- Banned: rockstar, ninja, guru, wizard, fast-paced, work hard play hard, \
wear many hats, self-starter, dynamic, synergy, family (as a workplace), \
competitive salary (pay is stated separately and exactly).
- Voice: direct, specific, human. Like a good owner explaining the job \
across a table, not like HR. Short sentences are fine.
- STRUCTURE — use exactly this shape, as plain text with real line breaks \
(\\n\\n between sections, no markdown symbols, no ** or ##):
  Paragraph 1: the work at a glance — 2-3 sentences, concrete.
  Then the line: What you'll do:
  Then 5-8 duty lines, each starting with "\u2022 " — specific, verb-first, \
drawn from the notes plus what the role universally involves.
  Then the line: Who does well here:
  Then 2-4 lines starting with "\u2022 " — the notes' real requirements \
plus what the role genuinely demands. No invented requirements.
  Then, ONLY if the notes mention schedule, gear, pay context, team, or \
growth: one short closing paragraph with those facts.
- 170-300 words total. No greeting, no "join our team" opener, no closing \
pitch, no "About us" section.

Respond with ONLY a JSON object, no fences:
{"description": string}"""


@https_fn.on_call(
    region="us-central1",
    secrets=[ANTHROPIC_API_KEY],
    memory=options.MemoryOption.MB_512,
    timeout_sec=60,
)
def generate_job_post(req: https_fn.CallableRequest):
    if req.auth is None:
        raise https_fn.HttpsError("unauthenticated", "Sign in first.")
    employer_id = (req.auth.token or {}).get("employerId")
    if not employer_id:
        raise https_fn.HttpsError(
            "permission-denied", "Drafting is for verified employer accounts."
        )
    data = req.data or {}
    title = (data.get("title") or "").strip()
    notes = (data.get("notes") or "").strip()
    if len(title) < 3:
        raise https_fn.HttpsError("invalid-argument", "Give the role a title first.")
    if len(notes) < 15:
        raise https_fn.HttpsError(
            "invalid-argument",
            "Give me a few rough notes to work from — what's the work, "
            "what matters, any must-haves.",
        )

    db = firestore.client()
    emp = {}
    try:
        emp = (db.collection("employers").document(employer_id).get().to_dict()
               or {})
    except Exception:
        pass

    context_lines = [
        f"Role title: {title}",
        f"Company: {emp.get('name', '')}",
        f"Industry: {emp.get('industry', '') or 'not stated'}",
        f"Metro: {emp.get('metro', '') or data.get('city', '')}",
        f"Employment type: {data.get('employmentType', 'not stated')}",
        f"Remote: {'yes' if data.get('remote') else 'no/not stated'}",
        f"Employer's rough notes: {notes}",
    ]

    resp = _rq.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY.value,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 900,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text",
                     "text": _DRAFT_PROMPT + "\n\n" + "\n".join(context_lines)},
                ],
            }],
        },
        timeout=45,
    )
    if resp.status_code != 200:
        print(f"[draft] API {resp.status_code}: {resp.text[:200]}")
        raise https_fn.HttpsError("internal", "Couldn't draft just now — try again.")

    text = "".join(
        b.get("text", "") for b in resp.json().get("content", [])
        if b.get("type") == "text"
    ).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        out = _json.loads(text)
        description = (out.get("description") or "").strip()
    except Exception:
        description = text.strip()
    if len(description) < 60:
        raise https_fn.HttpsError("internal", "Draft came back too thin — try again.")

    print(f"[draft] {employer_id}: drafted {len(description)} chars for '{title}'")
    return {"ok": True, "description": description}


# ============================================================================
# ROLE LIFECYCLE + FRESHNESS CONTRACT
# job_status: one employer-gated callable for every status change —
#   pause / close / reopen / confirm_open. Reopen and confirm refresh
#   confirmedOpenAt (the honest age of the "confirmed open" claim) and
#   reopening re-fires the match engine via the inactive->active transition.
# job_freshness_sweep: daily scheduler — day 21 unconfirmed sends the
#   one-tap "still hiring?" email; day 30 unconfirmed expires the listing.
# on_employer_application_created: self-serve intake alert to the founder.
# ============================================================================

from firebase_functions import scheduler_fn


@https_fn.on_call(region="us-central1")
def job_status(req: https_fn.CallableRequest):
    if req.auth is None:
        raise https_fn.HttpsError("unauthenticated", "Sign in first.")
    employer_id = (req.auth.token or {}).get("employerId")
    if not employer_id:
        raise https_fn.HttpsError("permission-denied", "Employer accounts only.")
    data = req.data or {}
    job_id = data.get("jobId", "")
    action = data.get("action", "")
    if not job_id or action not in ("pause", "close", "reopen", "confirm_open"):
        raise https_fn.HttpsError("invalid-argument", "Bad request.")

    db = firestore.client()
    ref = db.collection("jobs").document(job_id)
    snap = ref.get()
    if not snap.exists:
        raise https_fn.HttpsError("not-found", "Job not found.")
    job = snap.to_dict() or {}
    if job.get("employerId") != employer_id:
        raise https_fn.HttpsError("permission-denied", "Not your listing.")

    now = firestore.SERVER_TIMESTAMP
    if action == "pause":
        ref.update({"status": "paused"})
    elif action == "close":
        ref.update({"status": "closed", "closedAt": now})
    elif action in ("reopen", "confirm_open"):
        updates = {
            "confirmedOpenAt": now,
            "confirmedOpen": True,
            "freshnessReminderAt": firestore.DELETE_FIELD,
        }
        if action == "reopen" or job.get("status") in ("expired", "paused", "closed"):
            updates["status"] = "active"
        ref.update(updates)
    print(f"[job_status] {employer_id}: {action} {job_id}")
    return {"ok": True, "action": action}


@scheduler_fn.on_schedule(
    schedule="every day 09:00",
    timezone=scheduler_fn.Timezone("America/Phoenix"),
    region="us-central1",
    secrets=[RESEND_API_KEY],
    memory=options.MemoryOption.MB_512,
)
def job_freshness_sweep(event: scheduler_fn.ScheduledEvent) -> None:
    import os as _os
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz

    db = firestore.client()
    now = _dt.now(_tz.utc)
    resend_key = _os.environ.get("RESEND_API_KEY", "")
    reminded = expired = 0

    for snap in db.collection("jobs").where("status", "==", "active").stream():
        job = snap.to_dict() or {}
        confirmed = job.get("confirmedOpenAt") or job.get("createdAt")
        if confirmed is None:
            continue
        try:
            age_days = (now - confirmed).days
        except Exception:
            continue

        if age_days >= 30:
            snap.reference.update({"status": "expired", "expiredAt": firestore.SERVER_TIMESTAMP})
            expired += 1
            print(f"[freshness] EXPIRED {snap.id}: {job.get('title')} ({age_days}d unconfirmed)")
            continue

        if age_days >= 21 and not job.get("freshnessReminderAt"):
            emp = (db.collection("employers").document(job.get("employerId", ""))
                   .get().to_dict() or {})
            to_email = emp.get("notifyEmail")
            if not to_email or not resend_key:
                print(f"[freshness] no notifyEmail for {snap.id} — skipping reminder")
                continue
            keep = f"https://app.rovenhr.com/roleCheck?jobId={snap.id}&a=yes"
            close = f"https://app.rovenhr.com/roleCheck?jobId={snap.id}&a=no"
            html_body = f"""<div style='font-family:Arial,sans-serif;max-width:520px;margin:auto;color:#16202E'>
<h2 style='letter-spacing:-.5px'>Still hiring for {job.get('title','this role')}?</h2>
<p>Every listing on Roven is a confirmed open role — it's why candidates
trust yours. This one was last confirmed {age_days} days ago. One click
keeps it live for another 30:</p>
<p>
<a href='{keep}' style='background:#1CA45F;color:#fff;padding:12px 22px;border-radius:100px;text-decoration:none;display:inline-block'>Yes — still open</a>
&nbsp;&nbsp;<a href='{close}' style='color:#5B6874'>Role is filled — close it</a>
</p>
<p style='font-size:12px;color:#5B6874'>No response within 9 days and the
listing pauses automatically — reopen anytime with one tap.</p>
</div>"""
            try:
                r = _rq.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {resend_key}"},
                    json={
                        "from": "Roven <alerts@notify.rovenhr.com>",
                        "to": [to_email],
                        "subject": f"Still hiring: {job.get('title','your role')}?",
                        "html": _wrap_legacy(html_body),
                    },
                    timeout=20,
                )
                if r.status_code in (200, 201):
                    snap.reference.update(
                        {"freshnessReminderAt": firestore.SERVER_TIMESTAMP})
                    reminded += 1
            except Exception as exc:
                print(f"[freshness] reminder failed {snap.id}: {exc}")

    print(f"[freshness] sweep done: {reminded} reminded, {expired} expired")

    # ------------------------------------------------------------------
    # Unanswered-application nudge: applications sitting at 'applied' for
    # 3+ days quietly damage the employer's public response record. Warn
    # them once per application so the promise stays true.
    # ------------------------------------------------------------------
    nudged = 0
    try:
        by_employer = {}
        for snap in (db.collection("applications")
                     .where("status", "==", "applied").stream()):
            a = snap.to_dict() or {}
            if a.get("nudgeSentAt"):
                continue
            applied = a.get("appliedAt")
            if applied is None:
                continue
            try:
                waiting_days = (now - applied).days
            except Exception:
                continue
            if waiting_days < 3:
                continue
            eid = a.get("employerId") or ""
            if not eid:
                continue
            by_employer.setdefault(eid, []).append((snap, a, waiting_days))

        for eid, items in by_employer.items():
            emp = (db.collection("employers").document(eid).get().to_dict()
                   or {})
            to_emp = emp.get("notifyEmail")
            if not to_emp or not resend_key:
                continue
            rows = ""
            for _, a, days in items[:8]:
                nm = (a.get("candidateName") or "A candidate")
                rows += (f'<div style="font-family:Arial,sans-serif;'
                         f'font-size:13.5px;line-height:1.9;'
                         f'color:rgba(255,255,255,.8)">&bull; {nm} '
                         f'<span style="color:#E8C46F">&mdash; waiting '
                         f'{days} days</span></div>')
            count = len(items)
            body = f"""
<div style="font-family:Georgia,serif;font-size:22px;font-weight:bold;color:#ffffff;letter-spacing:-.5px;padding-bottom:8px">{count} {'person is' if count == 1 else 'people are'} still waiting.</div>
<div style="font-family:Arial,sans-serif;font-size:14px;line-height:1.65;color:rgba(255,255,255,.75);padding-bottom:14px">
These applicants have not had an answer yet:
</div>
{rows}
<div style="font-family:Arial,sans-serif;font-size:13px;line-height:1.6;color:rgba(255,255,255,.65);padding:14px 0 18px 0">
Your response rate and average response time are published on every listing you
post. A single tap &mdash; review, interview, or pass &mdash; counts as an
answer and keeps that record strong. Passing on someone is a perfectly good
answer; silence is the only wrong one.
</div>
{_btn("Answer them now", "https://app.rovenhr.com")}
"""
            if _send_mail(to_emp, f"{count} applicant{'s' if count != 1 else ''} waiting on you", body):
                for snap, _, _ in items:
                    snap.reference.update(
                        {"nudgeSentAt": firestore.SERVER_TIMESTAMP})
                nudged += count
    except Exception as exc:
        print(f"[nudge] failed: {exc}")

    print(f"[nudge] {nudged} waiting applications flagged to employers")


@firestore_fn.on_document_created(
    document="employerApplications/{appId}",
    region="us-central1",
    secrets=[RESEND_API_KEY],
)
def on_employer_application_created(
    event: firestore_fn.Event[firestore_fn.DocumentSnapshot | None],
) -> None:
    import os as _os

    snap = event.data
    if snap is None:
        return
    a = snap.to_dict() or {}
    resend_key = _os.environ.get("RESEND_API_KEY", "")
    if not resend_key:
        return
    html_body = f"""<div style='font-family:Arial,sans-serif;max-width:520px;margin:auto;color:#16202E'>
<h2>New employer application</h2>
<p><strong>{a.get('companyName','')}</strong> · {a.get('industry','')} · {a.get('metro','')}</p>
<p>Website: {a.get('website','none given')}<br>
Contact: {a.get('contactName','')} ({a.get('contactRole','')})<br>
Account: {a.get('email','')}</p>
<p>Verify the business, then:<br>
<code>python approve_employer.py --key serviceAccount.json --approve {event.params['appId']}</code></p>
</div>"""
    try:
        _rq.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend_key}"},
            json={
                "from": "Roven <alerts@notify.rovenhr.com>",
                "to": ["rovenhr@gmail.com"],
                "subject": f"Employer application: {a.get('companyName','new business')}",
                "html": _wrap_legacy(html_body),
            },
            timeout=20,
        )
        print(f"[emp-apply] alert sent for {a.get('companyName')}")
    except Exception as exc:
        print(f"[emp-apply] alert failed: {exc}")


# ============================================================================
# delete_account: server-side account deletion honoring the privacy policy.
# Purges the user's profile data and files immediately, anonymizes their
# applications (marketplace integrity records persist without identity),
# then deletes the Auth user — Admin SDK, so no requires-recent-login wall.
# ============================================================================

@https_fn.on_call(region="us-central1", timeout_sec=120)
def delete_account(req: https_fn.CallableRequest):
    if req.auth is None:
        raise https_fn.HttpsError("unauthenticated", "Sign in first.")
    uid = req.auth.uid
    db = firestore.client()

    # 1. profileHistory subcollection
    try:
        for d in (db.collection("users").document(uid)
                  .collection("profileHistory").stream()):
            d.reference.delete()
    except Exception as exc:
        print(f"[delete] profileHistory {uid}: {exc}")

    # 2. user doc
    try:
        db.collection("users").document(uid).delete()
    except Exception as exc:
        print(f"[delete] user doc {uid}: {exc}")

    # 3. anonymize applications (docs persist for employer pipeline/stats
    #    integrity; identity is removed)
    try:
        for d in (db.collection("applications")
                  .where("candidateUid", "==", uid).stream()):
            d.reference.update({
                "candidateName": "Deleted user",
                "candidatePhotoUrl": firestore.DELETE_FIELD,
                "candidateDeleted": True,
            })
    except Exception as exc:
        print(f"[delete] applications {uid}: {exc}")

    # 4. storage: resumes + photos
    try:
        from firebase_admin import storage as _storage
        bucket = _storage.bucket()
        for prefix in (f"resumes/{uid}/", f"photos/{uid}/"):
            for blob in bucket.list_blobs(prefix=prefix):
                blob.delete()
    except Exception as exc:
        print(f"[delete] storage {uid}: {exc}")

    # 5. the Auth user itself
    try:
        from firebase_admin import auth as _auth
        _auth.delete_user(uid)
    except Exception as exc:
        print(f"[delete] auth user {uid}: {exc}")
        raise https_fn.HttpsError("internal", "Couldn't complete deletion — contact support@rovenhr.com.")

    print(f"[delete] account {uid} fully deleted")
    return {"ok": True}


# ============================================================================
# INTERVIEW COORDINATION
# The handoff that keeps both sides on-platform through the meeting:
#   - Employer proposes: mode (in_person/video/phone), place-or-link, and
#     up to 3 time slots -> written to applications/{appId}.interview by the
#     employer client (allowed under the existing employer-update rule).
#   - on_interview_proposed (below, folded into a dedicated trigger) emails
#     the candidate a pick-a-time message. Loop-guarded by stamping
#     candidateNotifiedAt.
#   - respond_interview (callable, candidate-gated) records the pick,
#     flips interview.status to 'scheduled', and emails the employer.
#     Candidates never need direct write access to applications.
# ============================================================================

def _fmt_slot(ts) -> str:
    """Render a Firestore timestamp in Phoenix time for email bodies."""
    try:
        from zoneinfo import ZoneInfo
        local = ts.astimezone(ZoneInfo("America/Phoenix"))
        return local.strftime("%a, %b %-d at %-I:%M %p") if hasattr(local, "strftime") else str(ts)
    except Exception:
        try:
            return ts.strftime("%a, %b %d at %I:%M %p UTC")
        except Exception:
            return str(ts)


_MODE_LABEL = {"in_person": "In person", "video": "Video call", "phone": "Phone call"}


@firestore_fn.on_document_written(
    document="applications/{appId}",
    region="us-central1",
    secrets=[RESEND_API_KEY],
)
def on_interview_proposed(
    event: firestore_fn.Event[firestore_fn.Change[firestore_fn.DocumentSnapshot | None]],
) -> None:
    import os as _os

    after = event.data.after
    if after is None or not after.exists:
        return
    a = after.to_dict() or {}
    interview = a.get("interview") or {}
    if interview.get("status") != "proposed" or interview.get("candidateNotifiedAt"):
        return

    db = firestore.client()
    resend_key = _os.environ.get("RESEND_API_KEY", "")
    cand_uid = a.get("candidateUid", "")
    user = (db.collection("users").document(cand_uid).get().to_dict() or {})
    to_email = user.get("email")
    if not to_email or not resend_key:
        after.reference.update({"interview.candidateNotifiedAt": firestore.SERVER_TIMESTAMP})
        return

    job = (db.collection("jobs").document(a.get("jobId", "")).get().to_dict() or {})
    emp = (db.collection("employers").document(a.get("employerId", "")).get().to_dict() or {})
    mode = _MODE_LABEL.get(interview.get("mode", ""), "Interview")
    slots = interview.get("slots") or []
    slot_lines = "".join(
        f"<li style='margin:6px 0'>{_fmt_slot(s)}</li>" for s in slots[:3]
    )
    note = interview.get("note") or ""
    note_html = (f"<p style='color:#5B6874;font-size:13px'>From {emp.get('name','the employer')}: "
                 f"&ldquo;{note}&rdquo;</p>") if note else ""

    html_body = f"""<div style='font-family:Arial,sans-serif;max-width:520px;margin:auto;color:#16202E'>
<h2 style='letter-spacing:-.5px'>{emp.get('name','A verified employer')} wants to interview you</h2>
<p><strong>{job.get('title','The role')}</strong> &middot; {mode}</p>
<p>They proposed these times (Phoenix time):</p>
<ul>{slot_lines}</ul>
{note_html}
<p><a href='https://app.rovenhr.com/myApplications'
style='background:#1CA45F;color:#fff;padding:12px 22px;border-radius:100px;text-decoration:none;display:inline-block'>Pick a time</a></p>
<p style='font-size:12px;color:#5B6874'>Open your applications on Roven to choose a slot &mdash; or tell them none work and they'll propose new times.</p>
</div>"""
    try:
        r = _rq.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend_key}"},
            json={
                "from": "Roven <alerts@notify.rovenhr.com>",
                "to": [to_email],
                "subject": f"Interview request: {job.get('title','your application')} at {emp.get('name','a verified employer')}",
                "html": _wrap_legacy(html_body),
            },
            timeout=20,
        )
        print(f"[interview] proposal email -> {to_email}: {r.status_code}")
    except Exception as exc:
        print(f"[interview] proposal email failed: {exc}")
    after.reference.update({"interview.candidateNotifiedAt": firestore.SERVER_TIMESTAMP})


@https_fn.on_call(region="us-central1", secrets=[RESEND_API_KEY])
def respond_interview(req: https_fn.CallableRequest):
    import os as _os

    if req.auth is None:
        raise https_fn.HttpsError("unauthenticated", "Sign in first.")
    data = req.data or {}
    app_id = data.get("appId", "")
    slot_index = data.get("slotIndex")  # int, or -1 for "none work"
    if not app_id or slot_index is None:
        raise https_fn.HttpsError("invalid-argument", "Bad request.")

    db = firestore.client()
    ref = db.collection("applications").document(app_id)
    snap = ref.get()
    if not snap.exists:
        raise https_fn.HttpsError("not-found", "Application not found.")
    a = snap.to_dict() or {}
    if a.get("candidateUid") != req.auth.uid:
        raise https_fn.HttpsError("permission-denied", "Not your application.")
    interview = a.get("interview") or {}
    if interview.get("status") not in ("proposed", "slots_declined"):
        raise https_fn.HttpsError("failed-precondition", "No open interview proposal.")
    slots = interview.get("slots") or []

    emp = (db.collection("employers").document(a.get("employerId", "")).get().to_dict() or {})
    job = (db.collection("jobs").document(a.get("jobId", "")).get().to_dict() or {})
    resend_key = _os.environ.get("RESEND_API_KEY", "")
    notify = emp.get("notifyEmail")

    if int(slot_index) == -1:
        ref.update({
            "interview.status": "slots_declined",
            "interview.respondedAt": firestore.SERVER_TIMESTAMP,
        })
        if notify and resend_key:
            try:
                _rq.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {resend_key}"},
                    json={
                        "from": "Roven <alerts@notify.rovenhr.com>",
                        "to": [notify],
                        "subject": f"New times needed: {a.get('candidateName','Your candidate')} — {job.get('title','')}",
                        "html": _wrap_legacy(
                            "<div style='font-family:Arial,sans-serif;max-width:520px;margin:auto;color:#16202E'>"
                            f"<h2>None of the proposed times worked</h2>"
                            f"<p><strong>{a.get('candidateName','Your candidate')}</strong> can't make the slots you "
                            f"offered for <strong>{job.get('title','the role')}</strong>. Open your pipeline and "
                            f"propose new times.</p>"
                            "<p><a href='https://app.rovenhr.com/employerHome' "
                            "style='background:#1CA45F;color:#fff;padding:12px 22px;border-radius:100px;"
                            "text-decoration:none;display:inline-block'>Propose new times</a></p></div>"
                        ),
                    },
                    timeout=20,
                )
            except Exception as exc:
                print(f"[interview] decline email failed: {exc}")
        return {"ok": True, "result": "slots_declined"}

    idx = int(slot_index)
    if idx < 0 or idx >= len(slots):
        raise https_fn.HttpsError("invalid-argument", "That time slot doesn't exist.")
    chosen = slots[idx]
    ref.update({
        "interview.status": "scheduled",
        "interview.selectedSlot": chosen,
        "interview.selectedIndex": idx,
        "interview.respondedAt": firestore.SERVER_TIMESTAMP,
    })
    if notify and resend_key:
        mode = _MODE_LABEL.get(interview.get("mode", ""), "Interview")
        where = interview.get("locationOrLink") or ""
        try:
            _rq.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}"},
                json={
                    "from": "Roven <alerts@notify.rovenhr.com>",
                    "to": [notify],
                    "subject": f"Interview confirmed: {a.get('candidateName','Candidate')} — {_fmt_slot(chosen)}",
                    "html": _wrap_legacy(
                        "<div style='font-family:Arial,sans-serif;max-width:520px;margin:auto;color:#16202E'>"
                        f"<h2>Interview confirmed</h2>"
                        f"<p><strong>{a.get('candidateName','Your candidate')}</strong> &middot; "
                        f"{job.get('title','')}</p>"
                        f"<p><strong>{_fmt_slot(chosen)}</strong> (Phoenix time) &middot; {mode}"
                        f"{' &middot; ' + where if where else ''}</p>"
                        "<p style='font-size:12px;color:#5B6874'>It's on your pipeline too. Good luck &mdash; "
                        "answer fast, hire well.</p></div>"
                    ),
                },
                timeout=20,
            )
        except Exception as exc:
            print(f"[interview] confirm email failed: {exc}")
    print(f"[interview] {app_id}: scheduled slot {idx}")
    return {"ok": True, "result": "scheduled"}


# ============================================================================
# WELCOME EMAILS
# Fired by Firestore document creation, never by the auth blocking function -
# a mail failure must never be able to break a signup.
#   on_user_welcome      users/{uid} created        -> candidate welcome
#   on_employer_welcome  employers/{empId} created  -> employer verified email
# Both stamp welcomeSentAt so a retry can't double-send.
# ============================================================================

_MAIL_SHELL = """<!DOCTYPE html><html><body style="margin:0;padding:0;background:#0E141D">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0E141D;padding:28px 12px">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:540px;background:#16202E;border-radius:18px;overflow:hidden;border:1px solid rgba(255,255,255,.10)">
  <tr><td style="padding:26px 30px 0 30px">
    <img src="https://rovenhr.com/logo-white.png" alt="Roven" width="128" height="59" style="display:block;border:0;outline:none;text-decoration:none;width:128px;max-width:128px;height:auto">
    <div style="font-family:'Courier New',monospace;font-size:10px;letter-spacing:3px;color:#1CA45F;font-weight:bold;padding-top:6px">HIRING, PROVEN.</div>
  </td></tr>
  <tr><td style="padding:22px 30px 8px 30px">{body}</td></tr>
  <tr><td style="padding:18px 30px 26px 30px;border-top:1px solid rgba(255,255,255,.09)">
    <div style="font-family:Arial,sans-serif;font-size:11px;line-height:1.6;color:rgba(255,255,255,.38)">
      Roven HR, LLC &middot; 1309 Coffeen Ave, STE 1200, Sheridan, WY 82801<br>
      <a href="https://rovenhr.com" style="color:rgba(255,255,255,.5)">rovenhr.com</a> &middot;
      <a href="https://rovenhr.com/privacy.html" style="color:rgba(255,255,255,.5)">Privacy</a> &middot;
      <a href="https://rovenhr.com/terms.html" style="color:rgba(255,255,255,.5)">Terms</a><br>
      You are receiving this because an account was created with this address.
    </div>
  </td></tr>
</table>
</td></tr></table></body></html>"""


def _btn(label, url):
    return (f'<a href="{url}" style="display:inline-block;background:#1CA45F;'
            f'color:#ffffff;font-family:Arial,sans-serif;font-size:15px;'
            f'font-weight:bold;text-decoration:none;padding:14px 30px;'
            f'border-radius:100px">{label}</a>')


def _step(num, title, text):
    return (f'<table role="presentation" width="100%" cellpadding="0" '
            f'cellspacing="0" style="margin:0 0 12px 0"><tr>'
            f'<td width="34" valign="top">'
            f'<div style="width:26px;height:26px;border-radius:100px;'
            f'background:rgba(28,164,95,.18);border:1px solid rgba(58,219,139,.5);'
            f'color:#3ADB8B;font-family:Arial,sans-serif;font-size:12px;'
            f'font-weight:bold;text-align:center;line-height:26px">{num}</div></td>'
            f'<td valign="top" style="font-family:Arial,sans-serif">'
            f'<div style="font-size:14px;font-weight:bold;color:#ffffff;'
            f'padding-bottom:2px">{title}</div>'
            f'<div style="font-size:13px;line-height:1.55;color:rgba(255,255,255,.68)">'
            f'{text}</div></td></tr></table>')


def _wrap_legacy(html):
    """The older transactional emails were written as standalone white-page
    HTML (dark text, own wrapper div). This drops them into the branded dark
    shell and flips the colours so nothing renders dark-on-dark - the same
    mistake that made the homepage FAQ invisible."""
    body = html.strip()
    # strip the outer wrapper div, whichever quote style it used
    for opener in ("<div style='font-family:Arial,sans-serif;max-width:520px;"
                   "margin:auto;color:#16202E'>",
                   '<div style="font-family:Arial,sans-serif;max-width:520px;'
                   'margin:auto;color:#16202E">'):
        if body.startswith(opener):
            body = body[len(opener):]
            if body.rstrip().endswith("</div>"):
                body = body.rstrip()[: -len("</div>")]
            break
    # dark-page palette
    body = (body
            .replace("color:#5B6874", "color:rgba(255,255,255,.45)")
            .replace("color:#16202E", "color:rgba(255,255,255,.78)"))
    # headings and default text need explicit light colours in email clients
    body = body.replace("<h2>", '<h2 style="font-family:Georgia,serif;'
                                'font-size:22px;font-weight:bold;color:#ffffff;'
                                'letter-spacing:-.5px;margin:0 0 10px">')
    body = body.replace("<h2 style='letter-spacing:-.5px'>",
                        '<h2 style="font-family:Georgia,serif;font-size:22px;'
                        'font-weight:bold;color:#ffffff;letter-spacing:-.5px;'
                        'margin:0 0 10px">')
    body = ('<div style="font-family:Arial,sans-serif;font-size:14px;'
            'line-height:1.6;color:rgba(255,255,255,.78)">' + body + "</div>")
    return _MAIL_SHELL.format(body=body)


def _send_mail(to_email, subject, body_html):
    import os as _os

    key = _os.environ.get("RESEND_API_KEY", "")
    if not key or not to_email:
        return False
    try:
        r = _rq.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "from": "Roven <alerts@notify.rovenhr.com>",
                "to": [to_email],
                "subject": subject,
                "html": _MAIL_SHELL.format(body=body_html),
            },
            timeout=20,
        )
        return r.status_code in (200, 201)
    except Exception as exc:
        print(f"[mail] send failed: {exc}")
        return False


@firestore_fn.on_document_created(
    document="users/{uid}",
    region="us-central1",
    secrets=[RESEND_API_KEY],
)
def on_user_welcome(
    event: firestore_fn.Event[firestore_fn.DocumentSnapshot | None],
) -> None:
    snap = event.data
    if snap is None:
        return
    u = snap.to_dict() or {}
    if u.get("welcomeSentAt"):
        return
    to_email = u.get("email")
    if not to_email:
        return
    name = (u.get("display_name") or "").split(" ")[0].strip()
    greeting = f"Welcome, {name}." if name else "Welcome to Roven."

    body = f"""
<div style="font-family:Georgia,serif;font-size:23px;font-weight:bold;color:#ffffff;letter-spacing:-.5px;padding-bottom:8px">{greeting}</div>
<div style="font-family:Arial,sans-serif;font-size:14px;line-height:1.6;color:rgba(255,255,255,.75);padding-bottom:18px">
You just joined a job board built on receipts. Four things are true here, and
we hold ourselves to all of them:
</div>
<div style="font-family:Arial,sans-serif;font-size:13.5px;line-height:2;color:rgba(255,255,255,.85);padding-bottom:20px">
&#10003;&nbsp; Every job is real and confirmed open &mdash; on a 30-day clock<br>
&#10003;&nbsp; Every employer is verified before they can post<br>
&#10003;&nbsp; Every employer's response rate is public &mdash; ghosting has a scoreboard<br>
&#10003;&nbsp; Jobs come find you, not the other way around
</div>
<div style="font-family:'Courier New',monospace;font-size:10px;letter-spacing:1.5px;font-weight:bold;color:#3ADB8B;padding-bottom:12px">WHAT HAPPENS NEXT</div>
{_step(1, "Finish your work history", "Upload a resume or type it in once. We read it and build your profile - you never retype it into little boxes again.")}
{_step(2, "Tell the engine what you want", "Name the roles and your metro. That is all it needs.")}
{_step(3, "Then wait - seriously", "The moment an employer posts a role that fits you, we email you. Before it reaches the general feed.")}
<div style="padding:18px 0 8px 0">{_btn("Open Roven", "https://app.rovenhr.com")}</div>
<div style="font-family:Arial,sans-serif;font-size:12px;line-height:1.6;color:rgba(255,255,255,.45);padding-bottom:6px">
Roven is free for job seekers. Always. There is no premium tier, no paid
placement, and no way to buy your way up a list &mdash; not by you, and not by
anyone else.<br><br>
Here to hire instead? <a href="https://app.rovenhr.com" style="color:#3ADB8B">Set up your business</a> and we will verify it within one business day.
</div>
"""
    ok = _send_mail(to_email, "You're in - here's how Roven works", body)
    snap.reference.update({"welcomeSentAt": firestore.SERVER_TIMESTAMP})
    print(f"[welcome] candidate {to_email}: {'sent' if ok else 'FAILED'}")


@firestore_fn.on_document_created(
    document="employers/{employerId}",
    region="us-central1",
    secrets=[RESEND_API_KEY],
)
def on_employer_welcome(
    event: firestore_fn.Event[firestore_fn.DocumentSnapshot | None],
) -> None:
    snap = event.data
    if snap is None:
        return
    e = snap.to_dict() or {}
    if e.get("welcomeSentAt"):
        return
    to_email = e.get("notifyEmail")
    if not to_email:
        print("[welcome] employer has no notifyEmail - skipping")
        return
    company = e.get("name") or "your business"

    body = f"""
<div style="font-family:Georgia,serif;font-size:23px;font-weight:bold;color:#ffffff;letter-spacing:-.5px;padding-bottom:6px">{company} is verified.</div>
<div style="font-family:'Courier New',monospace;font-size:10px;letter-spacing:1.5px;font-weight:bold;color:#3ADB8B;padding-bottom:14px">&#10003; VERIFIED EMPLOYER</div>
<div style="font-family:Arial,sans-serif;font-size:14px;line-height:1.6;color:rgba(255,255,255,.75);padding-bottom:18px">
We checked the business by hand. That badge now appears on your profile and on
every role you post &mdash; and it is the reason candidates take your listings
seriously instead of assuming they are bait.
</div>
<div style="font-family:'Courier New',monospace;font-size:10px;letter-spacing:1.5px;font-weight:bold;color:#3ADB8B;padding-bottom:12px">HOW HIRING WORKS HERE</div>
{_step(1, "Post a role - free", "Give us rough notes and our AI writes the description for you. Edit it freely. Nothing gets invented that you did not say.")}
{_step(2, "The engine finds people", "The moment your role goes live, matching candidates get emailed. You do not wait for someone to stumble across it.")}
{_step(3, "Answer everyone", "One tap each: review, interview, offer, or pass. Propose interview times in the app and they pick one.")}
{_step(4, "Pay only when you hire", "One flat fee at the moment an offer is accepted. No hire, no bill - ever.")}
<div style="font-family:Arial,sans-serif;font-size:13px;line-height:1.6;color:rgba(255,255,255,.72);background:rgba(28,164,95,.10);border:1px solid rgba(58,219,139,.35);border-radius:12px;padding:14px 16px;margin:6px 0 4px 0">
<strong style="color:#3ADB8B">Right now you pay nothing at all.</strong> Placement fees are
waived while the marketplace grows. Founding employers &mdash; the first 100
verified nationwide &mdash; stay free for 12 months after pricing activates,
then keep 50% off list pricing for life.
</div>
<div style="padding:16px 0 8px 0">{_btn("Post your first role", "https://app.rovenhr.com")}</div>
<div style="font-family:Arial,sans-serif;font-size:12px;line-height:1.6;color:rgba(255,255,255,.45)">
One thing worth knowing: your response rate, response speed and confirmed hires
are computed automatically and shown publicly on every listing. You cannot edit
it and you cannot buy it &mdash; but answering your applicants quickly turns it
into the cheapest recruiting advantage you have.<br><br>
Questions? Just reply &mdash; a person reads these.
</div>
"""
    ok = _send_mail(to_email, f"{company} is verified on Roven", body)
    snap.reference.update({"welcomeSentAt": firestore.SERVER_TIMESTAMP})
    print(f"[welcome] employer {to_email}: {'sent' if ok else 'FAILED'}")


# ============================================================================
# APPLICATION LIFECYCLE EMAILS
# The promise is "every application gets an answer" - these are the emails
# that make it true instead of aspirational.
#   _notify_new_application   -> employer: someone applied (drives response speed)
#                             -> candidate: we got it, here is their record
#   _notify_status_change     -> candidate: reviewed / offer / passed
# ============================================================================

def _job_and_employer(db, job_id, employer_id):
    job = {}
    emp = {}
    try:
        if job_id:
            job = db.collection("jobs").document(job_id).get().to_dict() or {}
    except Exception:
        pass
    try:
        if employer_id:
            emp = (db.collection("employers").document(employer_id)
                   .get().to_dict() or {})
    except Exception:
        pass
    return job, emp


def _candidate_email(db, uid):
    try:
        u = db.collection("users").document(uid).get().to_dict() or {}
        return u.get("email")
    except Exception:
        return None


def _notify_new_application(db, app_id, a, employer_id, job_id, candidate_uid):
    job, emp = _job_and_employer(db, job_id, employer_id)
    title = job.get("title") or "your role"
    company = emp.get("name") or "the employer"
    cand_name = a.get("candidateName") or "A candidate"
    fit = a.get("fitScore")
    reason = a.get("fitReason") or ""

    # ---- employer: someone applied ----
    to_emp = emp.get("notifyEmail")
    if to_emp:
        fit_line = ""
        if isinstance(fit, (int, float)):
            label = ("Strong match" if fit >= 70 else
                     "Good match" if fit >= 40 else "Outside their usual work")
            fit_line = (f'<div style="font-family:\'Courier New\',monospace;'
                        f'font-size:10px;letter-spacing:1.2px;font-weight:bold;'
                        f'color:#3ADB8B;padding-bottom:10px">'
                        f'FIT: {label.upper()}</div>')
        reason_line = ""
        if reason:
            safe = reason.replace("<", "&lt;").replace(">", "&gt;")
            reason_line = (f'<div style="font-family:Arial,sans-serif;'
                           f'font-size:13px;line-height:1.6;font-style:italic;'
                           f'color:rgba(255,255,255,.72);border-left:2px solid '
                           f'rgba(58,219,139,.5);padding:2px 0 2px 12px;'
                           f'margin-bottom:14px">&ldquo;{safe}&rdquo;</div>')
        body = f"""
<div style="font-family:Georgia,serif;font-size:22px;font-weight:bold;color:#ffffff;letter-spacing:-.5px;padding-bottom:6px">{cand_name} applied.</div>
<div style="font-family:Arial,sans-serif;font-size:14px;line-height:1.6;color:rgba(255,255,255,.75);padding-bottom:14px">{title}</div>
{fit_line}
{reason_line}
<div style="font-family:Arial,sans-serif;font-size:13.5px;line-height:1.6;color:rgba(255,255,255,.7);padding-bottom:16px">
Their full work history is on your pipeline. One tap to review, interview,
make an offer, or pass &mdash; and every answer you give is counted toward the
response record shown publicly on your listings.
</div>
{_btn("Open your pipeline", "https://app.rovenhr.com")}
<div style="font-family:Arial,sans-serif;font-size:12px;line-height:1.6;color:rgba(255,255,255,.45);padding-top:16px">
Fast answers are the whole advantage here. Candidates see how quickly you
respond before they ever apply.
</div>
"""
        ok = _send_mail(to_emp, f"New applicant: {title}", body)
        print(f"[apply-alert] employer {to_emp}: {'sent' if ok else 'FAILED'}")

    # ---- candidate: we got it ----
    to_cand = _candidate_email(db, candidate_uid)
    if to_cand:
        stats = emp.get("stats") or {}
        received = int(stats.get("applicationsReceived") or 0)
        answered = int(stats.get("dispositionedCount") or 0)
        record = ""
        if received > 0:
            pct = round((answered / received) * 100)
            record = (f'<div style="font-family:\'Courier New\',monospace;'
                      f'font-size:10px;letter-spacing:1.2px;font-weight:bold;'
                      f'color:#3ADB8B;padding:2px 0 14px 0">'
                      f'{company.upper()} ANSWERS {pct}% OF APPLICANTS</div>')
        body = f"""
<div style="font-family:Georgia,serif;font-size:22px;font-weight:bold;color:#ffffff;letter-spacing:-.5px;padding-bottom:6px">Your application is in.</div>
<div style="font-family:Arial,sans-serif;font-size:14px;line-height:1.6;color:rgba(255,255,255,.75);padding-bottom:12px">
<strong style="color:#ffffff">{title}</strong> at {company}
</div>
{record}
<div style="font-family:Arial,sans-serif;font-size:13.5px;line-height:1.6;color:rgba(255,255,255,.7);padding-bottom:16px">
They have your work history and your application. Here is what makes this
different from every other job board: <strong style="color:#ffffff">you will
get an answer</strong>. When they review it, pass, or want to talk, we email
you &mdash; and their response rate is public either way.
</div>
{_btn("Track your applications", "https://app.rovenhr.com")}
"""
        ok = _send_mail(to_cand, f"Application received - {title}", body)
        print(f"[apply-ack] candidate {to_cand}: {'sent' if ok else 'FAILED'}")


def _notify_status_change(db, app_id, a, status, employer_id, job_id,
                          candidate_uid):
    to_cand = _candidate_email(db, candidate_uid)
    if not to_cand:
        return
    job, emp = _job_and_employer(db, job_id, employer_id)
    title = job.get("title") or "the role"
    company = emp.get("name") or "The employer"

    if status == "reviewed":
        subject = f"{company} reviewed your application"
        headline = "You have been reviewed."
        copy = (f"{company} has read your application for "
                f"<strong style=\"color:#ffffff\">{title}</strong>. That is a "
                f"real human looking at your work history, not a filter. If "
                f"they want to talk, the next email you get from us will be an "
                f"interview request.")
    elif status == "offer":
        subject = f"An offer from {company}"
        headline = "You have an offer."
        copy = (f"{company} has extended an offer for "
                f"<strong style=\"color:#ffffff\">{title}</strong>. Congratulations "
                f"&mdash; that is the hard part done. Once you accept, confirm "
                f"the hire in the app and it becomes a verified entry on your "
                f"work history: proof you were hired, not just a claim.")
    else:  # rejected
        subject = f"An answer on {title}"
        headline = "A straight answer."
        copy = (f"{company} has passed on your application for "
                f"<strong style=\"color:#ffffff\">{title}</strong>. We know that is "
                f"not what you wanted to read &mdash; but you got a real answer "
                f"instead of silence, and that is the point of this place. Your "
                f"profile stays armed: the moment another role fits you, we "
                f"email you first.")

    body = f"""
<div style="font-family:Georgia,serif;font-size:22px;font-weight:bold;color:#ffffff;letter-spacing:-.5px;padding-bottom:10px">{headline}</div>
<div style="font-family:Arial,sans-serif;font-size:14px;line-height:1.65;color:rgba(255,255,255,.75);padding-bottom:18px">{copy}</div>
{_btn("Open Roven", "https://app.rovenhr.com")}
"""
    ok = _send_mail(to_cand, subject, body)
    print(f"[status-mail] {status} -> {to_cand}: {'sent' if ok else 'FAILED'}")


# ============================================================================
# RESUME BUILDER
#   improve_resume : Claude rewrites weak bullets, drafts a summary, flags
#                    problems. Never invents employers, dates or numbers.
#   build_resume   : renders an ATS-safe PDF and returns a download URL.
#
# Free, unwatermarked, and the file is theirs to take anywhere. That is the
# entire point - every competitor builds it free then charges to download.
# ============================================================================

_RESUME_PROMPT = """You are improving a resume for Roven, a hiring platform \
built on honesty. Rewrite what you are given so it reads clearly and lands \
with a human reader.

WHAT YOU MAY DO:
- Rewrite bullets to be specific, active and verb-first.
- Draft a 2-3 sentence professional summary from the material provided.
- Reorder bullets within a role so the strongest work comes first.
- Fix grammar, tense and formatting inconsistencies.
- Suggest where the candidate could add a number, and say so in "suggestions" \
- do NOT invent the number yourself.

WHAT YOU MAY NEVER DO:
- Invent employers, job titles, dates, degrees, certifications or metrics.
- Add skills the candidate did not list or clearly demonstrate.
- Inflate seniority or scope beyond what the source says.
- Use: rockstar, ninja, guru, results-driven, detail-oriented, team player, \
hard worker, go-getter, synergy, dynamic, passionate about, think outside \
the box. These say nothing.

Respond with ONLY a JSON object, no fences:
{"summary": string,
 "roles": [{"title": string, "company": string, "dates": string,
            "location": string, "bullets": [string]}],
 "skills": [string],
 "suggestions": [string]}

"suggestions" are short, direct notes to the candidate about what would make \
this stronger - missing numbers, gaps worth explaining, sections worth adding."""


@https_fn.on_call(
    region="us-central1",
    secrets=[ANTHROPIC_API_KEY],
    memory=options.MemoryOption.MB_512,
    timeout_sec=90,
)
def improve_resume(req: https_fn.CallableRequest):
    if req.auth is None:
        raise https_fn.HttpsError("unauthenticated", "Sign in first.")
    uid = req.auth.uid
    db = firestore.client()

    data = req.data or {}
    parsed = data.get("profile")
    if not parsed:
        try:
            snap = (db.collection("users").document(uid)
                    .collection("profileHistory").document("parsed_resume")
                    .get())
            parsed = (snap.to_dict() or {}).get("parsed") or {}
        except Exception:
            parsed = {}
    roles = parsed.get("roles") or []
    if not roles:
        raise https_fn.HttpsError(
            "failed-precondition",
            "Add your work history first - there's nothing to improve yet.")

    payload = {
        "roles": roles,
        "skills": parsed.get("skills") or [],
        "certifications": parsed.get("certifications") or [],
        "targetRole": data.get("targetRole") or "",
    }

    resp = _rq.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY.value,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 2500,
            "messages": [{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": _RESUME_PROMPT + "\n\nSOURCE MATERIAL:\n"
                            + _json.dumps(payload, default=str),
                }],
            }],
        },
        timeout=75,
    )
    if resp.status_code != 200:
        print(f"[resume] API {resp.status_code}: {resp.text[:200]}")
        raise https_fn.HttpsError("internal",
                                  "Couldn't improve it just now - try again.")

    text = "".join(b.get("text", "") for b in resp.json().get("content", [])
                   if b.get("type") == "text").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        out = _json.loads(text)
    except Exception:
        raise https_fn.HttpsError("internal", "Couldn't read the result - try again.")

    print(f"[resume] improved for {uid}: {len(out.get('roles', []))} roles")
    return {"ok": True, "improved": out}


@https_fn.on_call(
    region="us-central1",
    memory=options.MemoryOption.MB_512,
    timeout_sec=90,
)
def build_resume(req: https_fn.CallableRequest):
    import os as _os
    import uuid as _uuid
    from urllib.parse import quote as _quote

    if req.auth is None:
        raise https_fn.HttpsError("unauthenticated", "Sign in first.")
    uid = req.auth.uid
    data = req.data or {}
    template = (data.get("template") or "clean").lower()
    if template not in ("clean", "modern", "compact"):
        template = "clean"

    content = data.get("content") or {}
    if not (content.get("roles") or content.get("summary")):
        raise https_fn.HttpsError("invalid-argument",
                                  "Nothing to build yet.")
    contact = content.get("contact") or {}
    if not contact.get("name"):
        raise https_fn.HttpsError("invalid-argument",
                                  "Add your name before downloading.")

    try:
        import resume_templates as _tpl
    except ImportError:
        raise https_fn.HttpsError(
            "internal", "Resume templates unavailable - contact support.")

    tmp = f"/tmp/{uid}_{template}.pdf"
    try:
        _tpl.build_pdf(tmp, content, template)
    except Exception as exc:
        print(f"[resume] build failed for {uid}: {exc}")
        raise https_fn.HttpsError("internal", "Couldn't build the PDF.")

    try:
        from firebase_admin import storage as _storage
        bucket = _storage.bucket()
        safe_name = "".join(ch for ch in str(contact.get("name"))
                            if ch.isalnum() or ch in " -_").strip() or "resume"
        path = f"resumes_generated/{uid}/{safe_name} - Resume.pdf"
        blob = bucket.blob(path)
        token = str(_uuid.uuid4())
        blob.metadata = {"firebaseStorageDownloadTokens": token}
        blob.upload_from_filename(tmp, content_type="application/pdf")
        blob.patch()
        url = (f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/"
               f"{_quote(path, safe='')}?alt=media&token={token}")
    except Exception as exc:
        print(f"[resume] upload failed for {uid}: {exc}")
        raise https_fn.HttpsError("internal", "Couldn't save the PDF.")
    finally:
        try:
            _os.remove(tmp)
        except Exception:
            pass

    try:
        firestore.client().collection("users").document(uid).set(
            {"resumeBuiltAt": firestore.SERVER_TIMESTAMP,
             "resumeTemplate": template}, merge=True)
    except Exception:
        pass

    print(f"[resume] built {template} for {uid}")
    return {"ok": True, "url": url, "template": template}


# ============================================================================
# COVER LETTERS
#   generate_cover_letter : Claude drafts one from the candidate's real
#                           profile and the actual job. Same honesty contract
#                           as everything else - nothing invented.
#   build_cover_letter    : renders the PDF and returns a download URL.
#
# Note the deliberate link to the fit gate: the returned "shortVersion" is
# sized to drop straight into the "why I'm a fit" field on an application,
# so a candidate writes their case once instead of twice.
# ============================================================================

_COVER_PROMPT = """You write cover letters for Roven, a hiring platform built \
on honesty. Write one letter, for one specific job, using only the \
candidate's real background.

HARD RULES:
- Use ONLY the candidate's actual roles, skills and certifications as given. \
NEVER invent employers, dates, metrics, degrees or certifications.
- Never claim enthusiasm for the company's mission, products or values - you \
have no idea whether that is true, and hiring managers can tell.
- No flattery of the employer. No "I have long admired". No "I was excited \
to see".
- Banned: passionate about, results-driven, detail-oriented, team player, \
hard worker, go-getter, dynamic, synergy, fast-paced, rockstar, "perfect \
fit", "I believe I would be a great addition".
- If the candidate's background does NOT obviously match the role, say so \
plainly and make the honest case for why the experience transfers. Do not \
paper over a career change - name it.

STRUCTURE - three short paragraphs, no more:
1. What role they are applying for and the single most relevant thing about \
their background. Direct, no preamble.
2. The specific evidence: what they have actually done that maps to this \
job's requirements. Concrete, drawn from their history.
3. A plain close - availability or willingness to talk. No begging, no \
gratitude theatre.

Total 150-230 words. Write like a competent adult, not an applicant.

Respond with ONLY a JSON object, no fences:
{"body": [string, string, string],
 "shortVersion": string,
 "notes": [string]}

"shortVersion" is the same case compressed to 1-2 sentences (max 280 chars) \
for use as a short application note. "notes" are brief, direct suggestions to \
the candidate about what would strengthen this - missing detail, a number \
worth adding, something only they can supply."""


@https_fn.on_call(
    region="us-central1",
    secrets=[ANTHROPIC_API_KEY],
    memory=options.MemoryOption.MB_512,
    timeout_sec=90,
)
def generate_cover_letter(req: https_fn.CallableRequest):
    if req.auth is None:
        raise https_fn.HttpsError("unauthenticated", "Sign in first.")
    uid = req.auth.uid
    db = firestore.client()
    data = req.data or {}

    # ---- candidate side ----
    user = db.collection("users").document(uid).get().to_dict() or {}
    parsed = {}
    try:
        snap = (db.collection("users").document(uid)
                .collection("profileHistory").document("parsed_resume").get())
        parsed = (snap.to_dict() or {}).get("parsed") or {}
    except Exception:
        pass
    roles = parsed.get("roles") or []
    if not roles:
        raise https_fn.HttpsError(
            "failed-precondition",
            "Add your work history first - a cover letter needs something to "
            "draw on.")

    # ---- job side: either a real listing or a pasted description ----
    job_id = data.get("jobId") or ""
    job, emp = {}, {}
    if job_id:
        job = db.collection("jobs").document(job_id).get().to_dict() or {}
        if job.get("employerId"):
            emp = (db.collection("employers").document(job["employerId"])
                   .get().to_dict() or {})
    role_title = (data.get("roleTitle") or job.get("title") or "").strip()
    job_text = (data.get("jobDescription") or job.get("description")
                or "").strip()
    company = (data.get("company") or emp.get("name") or "").strip()
    if not role_title:
        raise https_fn.HttpsError("invalid-argument",
                                  "Which role is this letter for?")

    payload = {
        "candidate": {
            "name": user.get("display_name") or "",
            "roles": roles,
            "skills": parsed.get("skills") or [],
            "certifications": parsed.get("certifications") or [],
            "metro": ((user.get("matchPrefs") or {}).get("metro") or ""),
        },
        "job": {
            "title": role_title,
            "company": company,
            "description": job_text[:4000],
            "employmentType": job.get("employmentType") or "",
            "location": f"{job.get('locationCity', '')} "
                        f"{job.get('locationState', '')}".strip(),
        },
    }

    resp = _rq.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY.value,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 1600,
            "messages": [{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": _COVER_PROMPT + "\n\nMATERIAL:\n"
                            + _json.dumps(payload, default=str),
                }],
            }],
        },
        timeout=75,
    )
    if resp.status_code != 200:
        print(f"[cover] API {resp.status_code}: {resp.text[:200]}")
        raise https_fn.HttpsError("internal",
                                  "Couldn't draft it just now - try again.")

    text = "".join(b.get("text", "") for b in resp.json().get("content", [])
                   if b.get("type") == "text").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        out = _json.loads(text)
    except Exception:
        raise https_fn.HttpsError("internal",
                                  "Couldn't read the result - try again.")

    body = [p for p in (out.get("body") or []) if p]
    if not body:
        raise https_fn.HttpsError("internal", "Draft came back empty.")

    print(f"[cover] drafted for {uid}: {role_title} @ {company or 'n/a'}")
    return {
        "ok": True,
        "body": body,
        "shortVersion": (out.get("shortVersion") or "")[:280],
        "notes": out.get("notes") or [],
        "roleTitle": role_title,
        "company": company,
    }


@https_fn.on_call(
    region="us-central1",
    memory=options.MemoryOption.MB_512,
    timeout_sec=90,
)
def build_cover_letter(req: https_fn.CallableRequest):
    import os as _os
    import uuid as _uuid
    from datetime import datetime as _dt
    from urllib.parse import quote as _quote

    if req.auth is None:
        raise https_fn.HttpsError("unauthenticated", "Sign in first.")
    uid = req.auth.uid
    data = req.data or {}
    template = (data.get("template") or "clean").lower()
    if template not in ("clean", "modern", "compact"):
        template = "clean"

    body = [p for p in (data.get("body") or []) if p]
    if not body:
        raise https_fn.HttpsError("invalid-argument", "Nothing to build yet.")
    contact = data.get("contact") or {}
    if not contact.get("name"):
        raise https_fn.HttpsError("invalid-argument",
                                  "Add your name before downloading.")

    try:
        import resume_templates as _tpl
    except ImportError:
        raise https_fn.HttpsError("internal", "Templates unavailable.")

    payload = {
        "contact": contact,
        "date": data.get("date") or _dt.utcnow().strftime("%B %d, %Y"),
        "recipient": data.get("recipient") or {},
        "role": data.get("roleTitle") or "",
        "body": body,
        "closing": data.get("closing") or "Sincerely,",
    }

    tmp = f"/tmp/{uid}_cover.pdf"
    try:
        _tpl.build_cover_letter_pdf(tmp, payload, template)
    except Exception as exc:
        print(f"[cover] build failed for {uid}: {exc}")
        raise https_fn.HttpsError("internal", "Couldn't build the PDF.")

    try:
        from firebase_admin import storage as _storage
        bucket = _storage.bucket()
        safe = "".join(ch for ch in str(contact.get("name"))
                       if ch.isalnum() or ch in " -_").strip() or "cover"
        role_bit = "".join(ch for ch in str(data.get("roleTitle") or "")
                           if ch.isalnum() or ch in " -_").strip()
        fname = f"{safe} - Cover Letter{(' - ' + role_bit) if role_bit else ''}.pdf"
        path = f"cover_letters/{uid}/{fname}"
        blob = bucket.blob(path)
        token = str(_uuid.uuid4())
        blob.metadata = {"firebaseStorageDownloadTokens": token}
        blob.upload_from_filename(tmp, content_type="application/pdf")
        blob.patch()
        url = (f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/"
               f"{_quote(path, safe='')}?alt=media&token={token}")
    except Exception as exc:
        print(f"[cover] upload failed for {uid}: {exc}")
        raise https_fn.HttpsError("internal", "Couldn't save the PDF.")
    finally:
        try:
            _os.remove(tmp)
        except Exception:
            pass

    # If this letter belongs to a live application, attach it so the
    # employer sees it on the pipeline card.
    app_id = data.get("appId")
    if app_id:
        try:
            ref = db_ref = firestore.client().collection("applications").document(app_id)
            snap = ref.get()
            if snap.exists and (snap.to_dict() or {}).get("candidateUid") == uid:
                ref.update({"coverLetterUrl": url,
                            "coverLetterAt": firestore.SERVER_TIMESTAMP})
        except Exception as exc:
            print(f"[cover] attach failed: {exc}")

    print(f"[cover] built for {uid}")
    return {"ok": True, "url": url}
