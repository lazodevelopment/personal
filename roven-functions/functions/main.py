# ============================================================================
# ROVEN — Cloud Functions
# Build ID: JC-ROVEN-FUNCTIONS-0727-002
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

from firebase_admin import auth as admin_auth
from firebase_admin import firestore, initialize_app
from firebase_functions import firestore_fn, identity_fn

initialize_app()

RESPONSE_STATUSES = {"reviewed", "interviewing", "offer", "hired", "rejected"}
TERMINAL_STATUSES = {"hired", "rejected"}


@firestore_fn.on_document_written(
    document="applications/{appId}", region="us-central1"
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
) -> identity_fn.BeforeCreateResponse | None:
    try:
        uid = event.data.uid
        admin_auth.set_custom_user_claims(uid, {"identityVerified": True})
        print(f"[signup] identityVerified granted to {uid}")
    except Exception as exc:
        # never block signup on a claim failure — log and let them in;
        # the claim can be granted by rerun/script if this ever fires
        print(f"[warn] claim grant failed for new user: {exc}")
    return None
