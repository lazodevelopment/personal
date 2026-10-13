# Bonica cancellation — email draft + steps

## 1. Before anything else (today)
1. Open admin.ataviaweddings.com → Cathleen Bonica → **Cancel** (reason: "Client cancelled by phone 2026-10-12; retainer retained, no balance charge").
   This flips status to `cancelled`, which is the only thing that stops the daily 7am balance charge
   (charge_balances only touches status == confirmed) and voids any open payment link.
   DO THIS FIRST — the balance was due this week and the scheduler runs every morning.
2. From her booking card copy: event date, package name, agreement/signature date, total investment, retainer date.
3. Regenerate the PDF with those filled in (PowerShell):

   $env:EVENT_DATE="November 7, 2026"; $env:PACKAGE="Signature Film"; $env:TOTAL="$3,200.00"; $env:RETAINER_DATE="July 14, 2026"; $env:CONTRACT_DATE="July 14, 2026"; python $HOME\atavia-cancellations\bonica\make_release.py

   (or just hand-write into the blanks — it is fine either way).
4. Sign the Atavia side, then send her the email below from info@ataviaweddings.com with the PDF attached.
5. When she returns it signed, file it with her contract and reply "Received, your booking is closed."

## 2. Confirmation email (to Cathy@globalfitnesscenter.com)

Subject: Atavia Weddings — your cancellation confirmed, no further charges

Hi Cathleen,

Thank you for calling this morning. I'm sorry to hear you've decided not to move forward, and I want to confirm in writing exactly what you asked for:

- Your videography booking for October 17, 2026 is cancelled as of today.
- No further charges will be made to your card. The remaining balance that was scheduled this week has been cancelled, and your card has been removed from our billing.
- As we discussed, the $500 retainer paid at reservation is non-refundable under your agreement and will be retained; nothing else is owed.

Attached is a one-page Cancellation Acknowledgment that puts all of this in writing for both of us. Please sign and date the Client section and reply with a photo or scan whenever convenient. Once it's back, your booking is formally closed.

I'm genuinely sorry if there was a point where you felt out of touch with us. Our records show [X] emails sent since booking, including your questionnaire and schedule confirmation — if any of those didn't reach you, I'd like to know so we can fix it for the next couple. And if your plans change, the door is open.

Warmly,
[Name]
Atavia Weddings
info@ataviaweddings.com

## 3. Notes
- Communication-gap claim: before sending, pull her thread in info@ataviaweddings.com and the Resend log
  (booking confirmation, contract, questionnaire, follow-ups). Keep that export with the signed release in case
  of a chargeback — Whop/Zoho disputes are won on "services as described + signed non-refundable term + client waiver".
- Don't offer a partial refund of the retainer in writing; the contract and this release both say non-refundable.
- If she refuses to sign, the email itself (her phone request + our confirmation) is still adequate evidence; the release just makes it cleaner.

## 4. So it doesn't happen again (built 2026-10-12, not deployed)
What she actually received in week one: contract (SignWell), signature confirmation, welcome email,
then the Lazo plug on day 3, then nothing until the day-13 "we charge your card tomorrow" email.
That is the sequence that reads as "no communication".

New in atavia-functions-live/bs (JC-ENGAGE-1012):
- Day 2: "What happens next" — who we are, the full timeline to the wedding, balance date restated, direct phone.
- Every 30 days while the wedding is >45 days out: short check-in with one planning tip; skipped within 2 days of the balance charge.
- 7 days before: "One week to go" — what we have on file, questionnaire nag if missing, day-of number.
- Lazo invite moved from day 3 to day 7 so it is never the first non-transactional email.
- Pay-in-full rule: `pif_required_within_days` (server forces PIF for close-in weddings). Shipped OFF (0);
  paste atavia-site/book/PIF-RULE-PASTE.md into the booking page first, then set it to 45.

Deploy (Cloud Shell, ~/bs, same pattern as deploy-functions.sh): charge_balances, book_submit, reservation_due.
