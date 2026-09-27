# Atavia Booking Functions — Deploy Guide (v1 · 2026-07-15)

Project: **atavia-c29cd** · Runtime: **python312** (cloud-side — your local
3.14 is fine, deploys don't use it) · Region: **us-central1**

## Pre-deploy checklist
1. **Blaze plan** on atavia-c29cd (Functions + outbound API calls require it).
   Firebase console → bottom-left plan badge.
2. Firebase CLI logged into the account that owns atavia-c29cd:
   `firebase login:list` — switch with `firebase login` if needed.
3. Secrets set (values prompted interactively, never land in files):

```powershell
cd C:\Users\kurvh\atavia-booking
firebase use atavia-c29cd
firebase functions:secrets:set SIGNWELL_API_KEY
firebase functions:secrets:set STAX_API_KEY
firebase functions:secrets:set RESEND_API_KEY
firebase functions:secrets:set GRATUITY_SECRET
```
For GRATUITY_SECRET paste any long random string, e.g. output of:
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```
(STAX_API_KEY can be a placeholder string until the Stax key arrives —
the deploy just needs the secret to exist.)

## Deploy
```powershell
firebase deploy --only functions
```
Endpoints after deploy:
- https://us-central1-atavia-c29cd.cloudfunctions.net/book_submit
- https://us-central1-atavia-c29cd.cloudfunctions.net/signwell_webhook
- https://us-central1-atavia-c29cd.cloudfunctions.net/stax_webhook
- https://us-central1-atavia-c29cd.cloudfunctions.net/gratuity
- charge_balances runs daily 9:00 AM Phoenix (no URL)

## Wire webhooks (one-time, after deploy)
SignWell (registers via API — run once with your key):
```powershell
$env:SIGNWELL_API_KEY="<key>"
python -c "import os,sys; sys.path.insert(0,'functions'); from lib.signwell import SignWell; print(SignWell(os.environ['SIGNWELL_API_KEY']).register_webhook('https://us-central1-atavia-c29cd.cloudfunctions.net/signwell_webhook'))"
```
Stax: dashboard → Settings → Webhooks → add the stax_webhook URL
(create_transaction events).

## Test-mode smoke test (before any live money)
```powershell
$body = @{
  package_id="petite"; payment_option="standard"
  client_names="Test & Client"; email="YOUR_TEST_EMAIL"
  phone="(602) 555-0100"; mailing_address="1 Test St"
  city_state_zip="Phoenix, AZ 85004"; governing_state="Arizona"
  event_date="2026-12-12"; ceremony_venue="Test Venue"; agree_terms=$true
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "https://us-central1-atavia-c29cd.cloudfunctions.net/book_submit" -ContentType "application/json" -Body $body
```
Expected: signature request email arrives (SignWell test mode — not legally
binding, doesn't count toward billing). Sign it → check Functions logs for
the webhook → Stax sandbox invoice fires.

## Go-live flips (in main.py)
- `TEST_MODE = False`
- Confirm both `TODO[first-test-event]` webhook-verification blocks were
  resolved during testing (never go live accepting unverified webhooks).
- Swap Stax test key → production key: `firebase functions:secrets:set STAX_API_KEY`
  then redeploy.

## Firestore rules note
`bookings` is written ONLY by these functions (Admin SDK bypasses rules).
Make sure client rules deny direct access:
```
match /bookings/{id} { allow read, write: if false; }
```

## Known [VERIFY] items (blocked on Stax test key)
lib/stax.py endpoint paths/payloads follow Stax's public Fattmerchant docs;
smoke-test each marked call against the sandbox before go-live.
