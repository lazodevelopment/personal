# Deploy: engagement emails + pay-in-full within 45 days (Atavia + ES), 2026-10-12

**STATUS 2026-10-12 night: ALL STEPS DONE for both brands.** Atavia functions deployed by Jesse from Cloud Shell (book_submit + charge_balances ACTIVE), Atavia site deployed via wrangler. ES steps 3, 4 and 5 were done earlier the same evening (functions deployed from the live source tree with
the patch script via local gcloud as danbrenmedia@gmail.com; both Pages projects deployed via the Atavia wrangler
login). 

Everything below is built, dry-run tested, and staged. Four production actions remain, and all four
are blocked from the Claude session (gcloud = credential materialization, wrangler = account login).
Each is one command.

## 1. Atavia functions (Cloud Shell, account info@ataviaweddings.com, project atavia-c29cd)
Upload `C:\Users\kurvh\atavia-functions-live\bs\cloudshell-engage-1012.py` with Cloud Shell's
"Upload file", then paste the single line from
`C:\Users\kurvh\atavia-functions-live\bs\cloudshell-engage-1012-command.txt`.

What it does to the live `~/bs` source, in place, with `.pre-engage1012.bak` backups:
- appends `meet_your_team`, `planning_checkin`, `final_week` to `lib/emails.py`
- inserts `_send_engagement` into `main.py`, calls it from the daily `charge_balances` job
- `pif_required_within_days = 45` in `atavia_packages.json` + the server rule in `book_submit`
- Lazo invite delay 3 -> 7 days
- compiles, then deploys only `book_submit` and `charge_balances`. Env vars are NOT touched
  (Atavia stays on Zoho).
Ends with `ATAVIA-ENGAGE-DEPLOY-DONE`.

## 2. Atavia site (booking page)
Already built and staged in `C:\Users\kurvh\atavia-deploy`. Needs the Atavia wrangler login:

```
cd C:\Users\kurvh\atavia-deploy; npx wrangler pages deploy . --project-name=ataviaweddings --commit-dirty=true
```

Change: picking a wedding date within 45 days hides the Standard Plan, selects Pay in Full, and shows
a one-line note. Deploy the site and the functions together (either order, same sitting).

## 3. ES functions (Cloud Shell, account danbrenmedia@gmail.com, project elizabeth-scott-738e5)
Upload `C:\Users\kurvh\es-functions\bs\cloudshell-engage-1012.py`, then paste the line from
`C:\Users\kurvh\es-functions\bs\cloudshell-engage-1012-command.txt`.

Same mechanics as Atavia, different content:
- `planning_roadmap` (day 3), `studio_note` (every 6 weeks, one question each), `final_details`
  (10 days out, asks for a one-word "confirmed" reply)
- `_send_milestones` in the daily job; Lazo invite 3 -> 8 days
- `pif_required_within_days = 45` (stacks on the existing 14-day rush rule)
- JC-ES-NEXT-1012 (added later on 2026-10-12, same script, same run): the booking confirmation email now
  carries a "What happens next" timeline (now / questionnaire / six-week notes / ten days out / wedding day /
  after), and the booking form gains an optional `wedding_website` field that lands on the booking doc, in
  the NEW BOOKING CONFIRMED owner alert, and on the admin booking card.
- deploys `whop_setup`, `book_submit`, `signwell_webhook`, `whop_webhook`, `charge_balances` with the existing
  ES secrets (the welcome email is sent from the two webhooks, so they must ship too); env untouched.
Ends with `ES-ENGAGE-DEPLOY-DONE`.

## 4. ES site (booking page)
Staged in `C:\Users\kurvh\es-deploy\book\index.html`:

```
cd C:\Users\kurvh\es-deploy; npx wrangler pages deploy . --project-name=elizabethscott --commit-dirty=true
```

Change: dates within 45 days grey out the Payment Plan chip and show a note, same as the 14-day rush
behaviour today. Also (NEXT-1012): optional "Wedding Website" field under Reception Venue.

## 5. ES admin (booking card shows the wedding website)
```
cd C:/Users/kurvh/es-admin; npx wrangler pages deploy . --project-name=elizabethscott-admin
```
(wrangler login info@ataviaweddings.com, which owns that Pages project.)

## What existing couples will get on the first run
The sweeps look at every confirmed booking, so on the first morning after deploy:
- couples who booked in the last 21 days get the day-2 (Atavia) / day-3 (ES) intro email once;
- couples who booked longer ago skip the intro and, if their wedding is more than 45 days out and
  not within 2 days of a balance charge, get one check-in / studio note that morning, then every
  30 days (Atavia) / 6 weeks (ES);
- anyone 2 to 7 days (Atavia) / 3 to 10 days (ES) from their wedding gets the final email.
Every send is stamped on the booking, so nothing repeats.

## Rollback
Cloud Shell: `cp main.py.pre-engage1012.bak main.py; cp lib/emails.py.pre-engage1012.bak lib/emails.py`
then re-run the same deploy line. Sites: redeploy from `index.html.bak-pif1012` in each `book/`.
