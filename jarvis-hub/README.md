# JARVIS hub

Personal command center for Jesse: live status and business metrics for Atavia, Elizabeth Scott,
Lazo, Roven and LeaseReputation, weather with Doppler radar, an inbox brief, alerts to your phone,
live webcam feeds, a Claude-powered assistant you can talk to, and a wall mode for a TV.

Live: https://jarvis-hub.floral-credit-e4f0.workers.dev (Cloudflare account d16dd804, same as Lazo).

## Sign-in
- **Google**: only the addresses in `ALLOWED_EMAILS` (wrangler.toml; currently jesse@briskhealth.com).
  Needs a Google OAuth client ID set as the secret `GOOGLE_CLIENT_ID` (see Setup below).
- **Access key**: `.hub-key` (gitignored). Also the `x-hub-key` header for scripts. Kept as a fallback.

## What runs where
| Piece | Where | Cadence |
|---|---|---|
| Dashboard + API + brain + TTS | Cloudflare Worker `src/index.js`, page `src/hub.html` | on request |
| Uptime checks, down/up alerts, unanswered-lead nudges | Worker cron (`[triggers]`) | every 5 min |
| Inbox brief (Gmail → `brief`) | Claude scheduled task `jarvis-inbox-brief` (runs while the Claude app is open) | hourly 7am–9pm |
| Business metrics (Firestore → `metrics`) | `collect_metrics.py` via Task Scheduler "JARVIS metrics" | hourly |

## Setup (one-time secrets)
```powershell
cd C:\Users\kurvh\jarvis-hub
npx wrangler secret put ANTHROPIC_API_KEY     # the brain (console.anthropic.com → API keys)
npx wrangler secret put ELEVENLABS_API_KEY    # natural British voice (elevenlabs.io → profile → API keys)
npx wrangler secret put GOOGLE_CLIENT_ID      # Google sign-in (see below)
npx wrangler secret put RESEND_API_KEY        # optional: email alerts as well as push
```
Google client ID: console.cloud.google.com → APIs & Services → Credentials → Create credentials →
OAuth client ID → Web application. Authorized JavaScript origins: `https://jarvis-hub.floral-credit-e4f0.workers.dev`
(add your custom domain too). No redirect URI is needed. Paste the client ID into the secret above.

Phone push: **Pushover** (pushover.net, $5 one-time per platform). Create an account, install the app,
copy your User Key from the dashboard, then Create an Application called JARVIS and copy its API Token:
```powershell
npx wrangler secret put PUSHOVER_USER
npx wrangler secret put PUSHOVER_TOKEN
```
Test with the TEST PUSH button. (ntfy.sh is also wired via `NTFY_TOPIC` but its free server rate-limits
Cloudflare's shared egress IPs, so it only works intermittently from the worker.)

ElevenLabs voice: defaults to "George". To use another, set `ELEVENLABS_VOICE_ID` under `[vars]`.

## Metrics collector
Uses the service-account keys already on this PC for Lazo, Roven and LeaseReputation.
Atavia and Elizabeth Scott have no server key here: in the Firebase console for each project
(Project settings → Service accounts → Generate new private key) and save the file as
`secrets/atavia-c29cd.json` and `secrets/elizabeth-scott-738e5.json`. The next hourly run picks them up.
```powershell
C:\Users\kurvh\lazo-directory\.venv\Scripts\python.exe collect_metrics.py --dry-run   # print, don't post
```
Log: `collect_metrics.log`.

## Run locally / deploy
```powershell
npx wrangler dev --port 8790          # HUB_KEY unset locally, so the page is open
npx wrangler whoami                   # must show d16dd804...
npx wrangler deploy
```

## API (cookie or `x-hub-key`)
- `GET /api/config` which features are configured.
- `GET /api/status` (`?fresh=1` to force) site checks + uptime memory.
- `GET /api/weather?lat&lon&place`, `GET /api/alerts?lat&lon` (NWS).
- `POST /api/chat {text, messages}` → `{reply, actions, messages}`.
- `POST /api/tts {text}` → audio/mpeg (ElevenLabs).
- `GET|POST /api/state` keys: `brief`, `webcams`, `notes`, `place`, `metrics`, `alerts`, `chat`.
- `POST /api/test-alert`.

### Brief shape (posted by the inbox routine)
```json
{"brief":{"at":"ISO","account":"…","note":"…","items":[{"from":"","when":"","received":"ISO","subject":"","snippet":"","url":"","needs_reply":true}]}}
```
`needs_reply` + `received` drive the 2-hour unanswered-lead nudge.

### Metrics shape (posted by the collector)
```json
{"metrics":{"collectedAt":"ISO","businesses":{"lazo":{"headline":[{"label":"","value":0,"money":false,"delta":0,"deltaUnit":"","deltaLabel":""}],"series":{"name":"","values":[],"color":""},"upcoming":[{"date":"YYYY-MM-DD","title":""}],"counts":{}}}}}
```

## What JARVIS does now (round two)
- **Attention strip** in the header: sites down/slow, emails needing reply, unanswered Lazo inquiries, pending claims/jobs, leads this week, balances due, NWS alerts, queued actions, today's calendar. Click a chip to jump there.
- **Drill-downs**: click any business tile for cash-in by month, response-time history, recent bookings (with NOTE buttons), leads by source, pending decisions (with APPROVE/REJECT) and upcoming dates.
- **Streaming brain**: `/api/chat` is server-sent events. All live facts are pre-loaded into the prompt (one model round for most questions) and the voice starts on the first sentence.
- **Actions with confirmation**: JARVIS proposes (`request_action`), you press CONFIRM, the item goes to the queue at `/api/queue`. Executing it needs the "hands" script on the PC (see below). `draft_reply` shows an editable draft with an Open-in-Gmail button; nothing is sent automatically.
- **Three daily briefs**: `BRIEF_HOURS = "5:morning,12:afternoon,18:evening"` (local). Each is written from the live context, sees the earlier briefs of the day so it only reports what is new, is voiced by ElevenLabs, and pushes its first lines to your phone. The last 7 are kept (`briefs` in KV, audio under `brief_audio_<id>` for 8 days) and selectable in the Briefing panel. GENERATE makes one now for the current time of day; `/api/morning/run?slot=evening` forces a slot.
- **Staleness alerts**: the 5-minute cron alerts once when a PC-fed feed stops (metrics > 2 h, traffic or scores > 25 min, inbox brief > 3 h during the day) and again when it returns; stale feeds show in the attention strip and System line.
- **Money**: 12-month stacked cash-in per business from Firestore payment records (deposits, balances, gratuities, Pro charges, placement fees). Zoho/Stripe are mirrored by those records; direct API pulls would need their credentials, which live in Secret Manager.
- **Memory**: `remember`/`forget` tools plus the Memory panel; facts are in every prompt.
- **Watchfulness**: on every metrics post, JARVIS compares with the previous snapshot (lead drops ≥60% from a base of 5+, pending pile-ups, unanswered inquiries) and every 5 minutes checks response time against the 24h median (alerts when 2.5× slower and over 1.5 s). Search Console isn't wired (needs OAuth).
- **Calendar**: set `CAL_ICS_URL` to your Google Calendar's "Secret address in iCal format" (Calendar settings → Integrate calendar). Events merge into Upcoming and the brain's context; refreshed hourly.
- **Conversation mode** (devices with a mic): JARVIS listens after each reply; speaking over him interrupts. Wake word "Jarvis" also works.
- **Visualizer**: the core renders a live frequency ring from the audio while JARVIS speaks (and from the mic while listening).
- **Phone**: bottom nav (JARVIS / OPS / WEATHER / FEEDS / MORE), one view at a time.

### Hands (executing confirmed actions)
The hub only queues actions. A small script on the PC would poll `GET /api/queue`, perform the Firestore write with the
same credentials as the collector, and `POST /api/queue/result {id, ok, message}`. The exact writes each admin tool
makes are documented in the queue item kinds: `roven_approve_job` → jobs/{id} status active; `roven_reject_job` → rejected;
`roven_approve_employer` → employers doc + custom claim + application approved (approve_employer.py);
`lazo_claim` → vendors claimedBy/claimStatus/verified + users vendorId + claimRequests approved (Vendor admin queue);
`booking_note` → bookings/{id} admin_notes arrayUnion({at,text,by}); `lazo_inquiry_responded` → status responded + respondedAt.
Writing that executor was blocked by the assistant's permission rules (it changes production business data unattended), so it is left for Jesse to add or approve explicitly.

## Gmail bridges (the email that actually works)
`gmail_bridge.gs` is a Google Apps Script you paste into each Gmail account (script.google.com). It runs on Google's
servers every 5 minutes, posts the inbox to `POST /api/inbox` (triaged by Claude: needs-reply, summary, priority, kind),
and, once deployed as a web app, lets the hub archive, mark read, reply and send through that account. Steps are in the
file header and behind CONNECT INBOX on the hub. Bridged data (`brief.source = "bridge"`) outranks the old hourly
Claude-routine snapshot, so the `jarvis-inbox-brief` scheduled task can be disabled once the accounts are connected.
Email actions (`email_reply`, `email_archive`, `email_read`, `email_send`) execute immediately on CONFIRM; everything
else still goes to the hands script.

## Watch (added 2026-10-02)
- **Collector** `collect_watch.py` (Task Scheduler "JARVIS watch", every 15 min) posts KV `watch`:
  `payments` (Atavia + ES bookings with `balance_due_at` in the last/next 7 days: charged, failed + Zoho error, link sent, due),
  `social` (posted today? from `jovi-social/posted.json` and `brand-social/<brand>/posted.json`),
  `search` (Search Console daily clicks/impressions, 42 days, every property the LR service account
  `site-builder@lease-reputation.iam.gserviceaccount.com` can read; cached 3 h) and `ios` (App Store listings, because
  Apple's lookup API refuses Cloudflare). `--only social` / `--only payments,search,ios` post just those sections;
  the hub merges sections, so the PC and a cloud feeder can share the key.
- **Hub** `watchWatch` alerts + pushes: declined balance charge (once per attempt), balance charged, brands not posted by 7 pm,
  Search Console impressions down 50%+ (last 3 days vs prior 4 weeks), Search Console not connected (weekly).
  Alerts from one run are written in a single KV write (`flushAlerts`); KV is eventually consistent and back-to-back
  read-modify-writes lost alerts.
- **App stores** `appStores` (hourly cron + on each watch post): Lazo iOS/Android, Jovi iOS (search "Jovi Health"), plus
  anything added with the brain's `watch_app` tool (KV `apps_watch`). Pushes when an app first goes live, a version
  changes, or a listing disappears. Apple/Google review emails landing in a bridged inbox also push.
- **Executor watchdog**: approved actions still pending after 10 min raise an alert (the hands script isn't running).
- **Follow-ups** `makeFollowups` (hourly): leads/clients/bookings that need a reply and waited 24 h+ get a Sonnet-drafted
  reply from the full thread (via the Gmail bridge). They appear at the top of Decisions with REVIEW & SEND (normal
  confirm card, sends through the bridge) or SKIP. `POST /api/followups/run?dry=1&minAge=1` drafts without storing.
- **Trips** KV `trips`: brain tools `add_trip` / `remove_trip`, or + TRIP in Upcoming. On the day the 5-min cron keeps the
  flight in `track_req`, pushes wheels-up and landed, and on landing sets home (TX/AZ) when the trip says so.
- **Radio alarm**: Radio panel checkbox (per device). At the morning brief hour (`/api/config` `briefHours`) it plays
  the fresh morning brief, then fades in the selected station over 60 s; if the brief isn't ready by :20 it plays the
  radio alone. The page must be open on that device.

## Cloud feeder (prepared, not yet run)
`cloud/setup_feeder.ps1 -Project <id>` creates an e2-micro VM with its own service account (read-only Firestore on the
five projects, no key files) and moves flights, traffic/sports/decisions, metrics, cameras and payments/search/iOS
there via cron (`cloud/crontab.txt`, `cloud/install.sh`, which also tests whether the VM can reach the feeds that
refuse Cloudflare). The PC keeps the social check and the executor. Run with `-DryRun` first.

## Acting on what he sees (added 2026-10-03, evening)
- **First replies**: when a bridged inbox delivers a new lead/client/booking thread (needs_reply, human sender, under 6 h old), `ingestInbox` queues `makeFollowups({first:true})`, which drafts from the full thread plus the business **playbook** (KV `playbook`, edited behind PLAYBOOK in the Inbox panel) and the booked dates in `metrics`. The draft lands at the top of Decisions with REVIEW & SEND, and a push says "New lead: reply drafted". 24 h follow-ups work the same way.
- **Close the day**: CLOSE THE DAY in Decisions, or say "close the day". `closeItems()` gathers ready drafts, pending decisions, un-drafted needs-reply emails, declined charges and stuck queue items; `closeStep` speaks each with buttons (SEND/SKIP, APPROVE/REJECT, DRAFT, NEXT, STOP) and `closeVoice` maps spoken answers to them. Offered aloud once when the evening brief lands with items open.
- **Cash forecast**: `collect_metrics.py` emits `detail.forecast` (unpaid balances by due week, 13 weeks) and `detail.pastDue`; the rollup gives `money.forecast`, `forecast90`, `pastDue`, `pastDueTotal`, `yoy` (same 7 days a year ago, films only; `has_history` false until a business is a year old). Money panel shows a NEXT 90 DAYS block; the brain gets CASH FORECAST and YEAR-AGO lines.
- **Monday review**: slot `weekly` at 06:00 home time on Mondays (hourly cron), prompt in `SLOT_PROMPTS.weekly`; appears in the Briefing dropdown as WEEKLY. `POST /api/morning/run?slot=weekly` runs one now.
- **Competitors**: KV `competitors` [{url,label,business}] via the Watch panel form, the brain tool `watch_competitor`, or "scan competitors now". `scanCompetitors` (Sundays 20:00, or `POST /api/competitors/scan`) strips each page to text, keeps `$` price lines with context in `competitor_snaps`, and records real differences (an amount that appeared or vanished, not just re-ordered text) in `competitor_changes`, pushing each one. The Monday review reads them.
- **Remaining inboxes**: filled bridge scripts for lazo, roven, lr and brisk are in `secrets/bridges/` (gitignored); each is pasted into Apps Script while signed in as that account, `setup` run, deployed as a web app, `setup` run again.

## Using it
- **Ctrl+K** focuses the console. Type anything; JARVIS answers from live tools (status, weather, brief, metrics, notes) and can open links.
- **Voice**: the TALK button and the "wake word" option only appear when a microphone exists. Hold **J** to talk.
- **Wall mode**: every embeddable feed in a full-screen grid with clock, weather and system state. Click a feed to enlarge it, click again to return. `/wall` or the header link. Esc exits.
- **Radar map**: Esri dark base tiles (no key needed) under RainViewer radar frames.
- **Radar**: RainViewer frames (past 2 h + 30 min nowcast). Play/scrub. Click a day in the forecast for that day's hourly curve.
- Install as an app: browser menu → Install / Add to Home Screen.
