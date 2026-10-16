# Email verification at signup (2026-10-16)

Nothing here is deployed or committed. Built in the parent session; the off-platform client work runs alongside it in its own session.

## What was built

| Piece | File | State |
|---|---|---|
| Six-digit code: `sendEmailCode`, `verifyEmailCode` | `lazo-functions/functions-dashboard/verify.js` | tested, 40/40 (`node test/verify-flow.js`) |
| Signup domain check: `blockBadSignupEmail` (beforeUserCreated) | same file + `disposable-domains.txt` (9,892 domains) | tested |
| Wired into the dashboard codebase | `functions-dashboard/index.js` (last two lines) | loads |
| Code screen, gate on login and cold open | `app-patches/Auth_master_v24.txt` (from `patch_auth_v24.py`, base v23) | phone compile passes, analyzer 0 errors / same 6 warnings as v23; not seen on a device |
| Rules: verified email for everything but the user's own doc | `lazo-directory/firestore.rules` (JC-LAZO-RULES-1016-021) | 17/17 via the Rules test API; the same cases against HEAD fail 5, as expected |
| Grandfather existing accounts (`legacy` claim) | `lazo-functions/scripts/mark_legacy_users.js` | dry run: 33 accounts, 4 verified, 29 to mark |

## Deploy order (each step waits for Jesse)

1. **Identity Platform**: the blocking function needs Firebase Auth upgraded to Identity Platform (Firebase console > Authentication > Settings). Free at this size. Jesse does this in the console.
2. **Functions**: only the three verification functions: `firebase deploy --only functions:dashboard:sendEmailCode,functions:dashboard:verifyEmailCode,functions:dashboard:blockBadSignupEmail`, as lazodevelopment@gmail.com. A full `functions:dashboard` deploy would also create June's bell feed (7 feed* triggers, never deployed) and the off-platform functions, and would update payCheckout, which breaks lead payments on /f/ until the new worker is out. The booking claim inside verifyEmailCode stays off until `JOIN_CLAIM_ON_VERIFY=on` is set in functions-dashboard/.env, which happens in the off-platform deploy: worker, then all of functions:dashboard, then the six default functions, in one sitting, with its own approval.
3. **Auth v24**: paste into FlutterFlow, publish web, and ship an iOS/Android build. It depends on the off-platform session's Auth v23 being final.
4. **Legacy script**: `GOOGLE_CLOUD_QUOTA_PROJECT=lazo-513ec node scripts/mark_legacy_users.js --before <v24 publish time> --apply`.
5. **Wait at least one hour** so every signed-in token picks up the claim.
6. **Rules**: diff against live first (live ruleset 7e8623d1, Oct 14 13:02Z), then `firebase deploy --only firestore:rules`. The file also carries two changes that are not live yet: June's bell (`juneFeed`, 1014-019, committed but never deployed) and the off-platform session's `referredBy` lock (1016-020).

## Known gaps

- **Store builds**: until the iOS/Android builds with Auth v24 are live, a new signup on an old build gets no code screen and, once the rules are deployed, is stuck. Ship the store builds before step 6.
- **Reopening mid-signup**: an account that closes the app on the code screen comes back through FlutterFlow's router. If the router sends it straight to a dashboard instead of this page, the rules block it there and it sees errors, not the code screen. Check the Router page; if needed, add a small gate to Couple and Vendor (after Vendor v199).
- **welcomeVendor** still fires when the users doc gets role vendor, which happens before the code, so a fake vendor address still gets one welcome email. welcomeCouple waits for couples/{uid}, which now needs a verified email.
- **Storage rules** are not in this repo, so uploads are not gated.
## Booking claim (agreed with the off-platform session)

- **One email:** join.js sends its own confirm link only while `functions-dashboard/verify.js` does not exist, so once both ship she gets the code, never a second link. The file name must stay `verify.js`.
- **The server claims:** `verifyEmailCode` calls join.js `claimLeadThreads` straight after setting emailVerified, passing the join link's inquiryId, t and step. It returns the result as `claim`, and Auth v24 shows it with v23's claim messages, so a mismatch hint is never emailed twice. A failed claim never blocks verification.
- **Older accounts:** an older unverified account (legacy claim) that arrives through a join link is still asked for the code. The legacy claim only skips the code when there's no booking to claim.
- Tests: verify-flow 44/44, offplatform-flow 90/90.
