# ELIZABETH SCOTT BOOKING RAIL — DEPLOY PACKAGE
Build: JC-ES-BOOKING-0818-006 · 2026-08-18
Target: Firebase project **elizabeth-scott-738e5** · Python 3.12 · us-central1

## What's in this zip (and what's NOT)

INCLUDED (ES-transformed, verified by rendered-PDF content):
- main.py                              (JC-ES-MAIN-0818-007)
- elizabethscott_contract_generator.py (JC-ES-CONTRACT-0818-003)
- lib/emails.py                        (JC-ES-EMAILS-0818-004)
- lib/signwell.py                      (JC-ES-SIGNWELL-0818-005)
- requirements.txt                     (unchanged from Atavia)
- elizabethscott_packages.TESTFIXTURE.json  — TEST FIXTURE ONLY. Bullets are
  placeholders and brand.phone is (000) 000-0000. REPLACE with the canonical
  JC-ES-PACKAGES-0818-001 file, renamed to elizabethscott_packages.json.
  Prices/hours in the fixture were verified against the live site.

NOT INCLUDED — copy from ~/atavia-src (brand-neutral, reuse as-is):
- lib/stax.py
- lib/questionnaire_schema.py
- lib/__init__.py (if present in the Atavia source)
- fonts/  (CormorantGaramond-var.ttf + Lato-{Regular,Bold,Italic}.ttf —
  generator falls back to Times/Helvetica without them; ship them)
- Any book/booked page assets are separate (site build, not functions)

## Canonical JSON requirements (import-time asserted — deploy FAILS without)
pricing_rules must contain:
  pif_discount: 500
  addon_extra_hour: 175
  addon_second_shooter: 500
  rush_days: 14, rush_fee: 149
  max_extra_hours: <n>
  balance_due_days_before_event: 14   <- NEW KEY (replaces Atavia's
                                         balance_due_days_from_booking)
  (Atavia's "retainer" key is NO LONGER USED — retainer is computed 50%)
brand must contain: name, phone, email, website, parent_company
  optional: accent (hex) — drives the PDF accent color; falls back to #1F1F1F

## Retainer math contract (do not break)
retainer = (total + 1) // 2 in BOTH main.py (book_submit) and the generator
(_retainer_of). If you ever change one, change both.

## Pre-deploy checklist (elizabeth-scott-738e5)
1. Upgrade project to Blaze; create Firestore (native mode, us-central1).
2. Secrets (firebase functions:secrets:set):
   SIGNWELL_API_KEY, STAX_API_KEY  — same values as Atavia (same accounts)
   RESEND_API_KEY                  — same Danbren Resend account
   GRATUITY_SECRET, PROMO_ADMIN_KEY — MINT NEW random strings (per-brand
   HMAC isolation: an Atavia gratuity token must never validate on ES)
3. Resend: verify elizabethscottweddings.com domain BEFORE first live send.
4. Local render test in Cloud Shell BEFORE deploy:
     pip install reportlab && python elizabethscott_contract_generator.py --all
   (renders 22 variants; import-time asserts gate the JSON schema)
5. Deploy all 9 functions:  firebase deploy --only functions
6. Post-deploy: register the SignWell webhook against the NEW
   signwell_webhook URL (SignWell.register_webhook or dashboard), and point
   a Stax webhook at the new stax_webhook URL. The Atavia webhooks stay
   untouched — these are ADDITIONAL endpoints on the same accounts.
7. Verify deployed source by re-pull (gsutil cp the function-source.zip,
   grep for "balance_due_days_before_event" and "Elizabeth Scott, Manager").
   Headers can lie — verify by content.
8. TEST_MODE in main.py is False (production). For an end-to-end sandbox
   run, flip TEST_MODE=True locally first (adds localhost origin +
   SignWell test mode).

## Known follow-ups / flags
- brand.phone: fixture is a placeholder — put the real ES number (site says
  "Text us"; emails currently omit phone and show email + site instead).
- Non-refundability now covers the ENTIRE 50% retainer (standard) — Atavia's
  structure applied to the bigger number. If you want only $500 of it
  non-refundable, that's a clause edit in _c_retainer + _c_cancellation +
  the ack line. Attorney's call.
- Rush dates (<=14 days out) are PIF-ONLY, enforced server-side in
  book_submit (main.py -007) AND to be mirrored on the /book page UI
  (hide/disable the payment-plan option when the chosen date is within 14
  days). The $149 rush fee still applies via compute_pricing.
- DECIDED: the full 50% retainer is non-refundable (standard plan) — as built.
- Stax webhook TODO[first-test-event] carried over from Atavia: confirm the
  envelope on the first sandbox transaction.
- --addon-samples CLI ids assume story/signature/ensemble exist in the
  canonical JSON — verify ids match.
