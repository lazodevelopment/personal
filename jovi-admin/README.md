# Jovi Staff app (business admin + EHR)

No-build static site. Firebase Auth + Firestore on project `kurv-health`, the same database the member app writes to.

- `index.html` shell → `assets/js/app.js` (login, sidebar, router) → `assets/js/pages/admin/*.js` (business side, no PHI) and `assets/js/pages/ehr/*.js` (clinical side).
- `assets/js/data.js` is the only place that knows collection paths and field names. It mirrors the member app's schema (see `SCHEMA.md`). If the app changes a field, change it here.
- Roles live in Firestore `staff/{uid}` (`role`: superadmin | admin | exec | clinician | support, `active`, `name`). Bootstrap the first superadmin by creating that document in the Firebase console for your own Auth uid.
- `firestore.rules` is the proposed rule set (staff read/write gated by role). Review and deploy it with `firebase deploy --only firestore:rules --project kurv-health` from a folder that has it in `firebase.json`. FlutterFlow may overwrite rules on its own deploys, so keep this file as the source of truth.
- Every staff write to member data also appends to `audit_logs` (who, what, when).

Local preview: `npx serve -l 8769 C:\Users\kurvh\jovi-admin` (add localhost to Firebase Auth authorized domains if sign-in is refused).

Deploy (PowerShell):

    cd C:\Users\kurvh\jovi-admin; npx wrangler pages deploy . --project-name jovi-admin --branch main --commit-dirty=true

Then add `jovi-admin.pages.dev` (and the custom domain) to Firebase Auth → Settings → Authorized domains.

## Tier 1–3 additions (2026-09-23)
- Note templates & smart phrases (`note_templates`, `smart_phrases`; Templates page). Type `.rtc` etc. at the end of a field to expand.
- Ambient scribe: the browser transcribes live with the Web Speech API (no audio leaves the device); `functions/scribe.js` drafts SOAP JSON with Claude (`claude-sonnet-5`). Secret: `firebase functions:secrets:set ANTHROPIC_API_KEY`.
- Orders: `orders` collection, signed from the note; `transmitOrder` callable with Surescripts / Labcorp / Quest adapters (`functions/orders.js`). Secrets: SURESCRIPTS_CLIENT_ID, SURESCRIPTS_CLIENT_SECRET, LABCORP_API_KEY, QUEST_API_KEY. Results inbound via `labResultsWebhook` (header `x-webhook-token` = LAB_WEBHOOK_TOKEN) into `users/{uid}/lab_results` with `reviewed:false`.
- Fax: `fax_outbox` / `fax_inbox`, `sendFax` + `faxInboundWebhook` (Phaxio; secrets PHAXIO_KEY, PHAXIO_SECRET, PHAXIO_WEBHOOK_TOKEN).
- FHIR R4 read API: `functions/fhir.js` → `https://us-central1-kurv-health.cloudfunctions.net/fhir/Patient/{uid}` etc. with a staff Firebase ID token as Bearer.
- Provider scheduling: `staff/{uid}.schedule` (hours, clinics, slot length, telehealth), `schedule_blocks`, `waitlist`, `requests.providerId/providerName/room`.
- Intake & consent: `users/{uid}/intake`, `users/{uid}/consents` (signature PNG in Storage `users/{uid}/consents/`).
- Care gaps page (rules evaluated client-side), access log per patient (`audit_logs` where target == users/{uid}), 15-minute idle sign-out, exam-room mode (Alt+K).
- Coverage snapshot + instant settlement on sign (`users/{uid}/transactions` type `clinic_visit`), after-visit summary push on sign.

Deploy functions (from kurv-functions, never a bare `--only functions`):

    firebase deploy --only functions:scribe,functions:transmitOrder,functions:labResultsWebhook,functions:sendFax,functions:faxInboundWebhook,functions:fhir --project kurv-health
    firebase deploy --only firestore:rules,storage --project kurv-health
