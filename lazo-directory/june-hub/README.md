# June hub: the Lazo vendor's own assistant

JARVIS for vendors. Every claimed vendor signs in with their Lazo login and gets June: today's brief read
aloud in a British voice, who is waiting on a reply, this week's weddings and consults with their forecast,
money, the page's views and rank, metro weather with NWS alerts, local and industry news, and a streaming
chat that reads their real data and acts (send a message, add or complete a task, tag, move a stage) only
after they tap Confirm. Per-vendor memory ("remember that…").

Worker `june-hub` on the Lazo Cloudflare account (d16dd804), KV namespace `JUNE`
(857b7d96321a495a897c3898fdf3b75a). Source: `src/index.js` (worker), `src/june.html` (the page),
`src/metros.json` (exported from `config/metros.py`; re-run the one-liner in "Metros" below when metros change).

## How it stays safe

- The page signs in to Firebase Auth over REST (email + password straight to Google; the worker never
  sees the password) and sends the ID token on every call. The worker verifies it with Google's JWKs,
  exactly like `worker/src/auth.js` on the site worker.
- Every Firestore read and write is made AS THE VENDOR with that token over the REST API, so
  `firestore.rules` decides what June can see and do. There is no service account and no admin key here.
  Vendor A can never see vendor B: the rules would refuse the query.
- The vendor behind a login = `users/{uid}.vendorId` (owner or invited manager), else the vendor whose
  `claimedBy` is the uid. Cached in KV for 30 minutes.
- Actions are confirm-first. `request_action` only queues a card; `/api/act` runs it when the vendor taps
  Confirm. June cannot book, mark lost, or touch money; `open_thread` sends them to the dashboard for that.
- The model only phrases numbers the worker computed; the context is built from Firestore, never guessed.

## Pieces

| Piece | Where | Notes |
|---|---|---|
| Brief | `makeBrief` | Once per vendor per local day (cached `brief_<vendorId>`), Sonnet 5.5 at medium effort, ~200 words spoken prose. ElevenLabs audio stored in KV (`brief_audio_<vendorId>`, 2 days). ↻ rewrites it with fresh numbers. Written on demand when the vendor opens June; the existing 7am three-line email from functions-dashboard is untouched. |
| Data | `snapshot` | Threads (`inquiries` where vendorId), consults (booked, next 60 days), invoices (collection group where vendorId), vendor doc (views d7/d7Prev, rank, reviews, tier, badges). Mirrors the June tools in `functions-dashboard/mcp.js`. |
| Weather | `weatherFor` | Open-Meteo at the metro centre, 14 days, plus NWS active alerts. Each booked wedding/consult inside 14 days carries the day's forecast. KV cache 10 min per metro. |
| News | `localNews`, `industryNews` | Google News RSS: the metro's geo section and a wedding-industry search. 20 min / 60 min caches. |
| Chat | `chat` | SSE stream, Sonnet 5.5, tools: lazo_pipeline, lazo_thread, lazo_search, lazo_upcoming, lazo_money, open_thread, remember, forget, request_action. |
| Voice | `elevenlabs` | Voice id `JUNE_VOICE_ID` (default Lily, British). Flash model for chat replies, turbo for the brief. Browser en-GB voice as fallback. |
| Visualizer | `june.html` CORE | The JARVIS living core on deep plum: idle gold, listening rose, thinking light plum, speaking ivory-gold. |

## Deploy (Jesse)

```bash
cd C:\Users\kurvh\lazo-directory\june-hub
npx wrangler whoami            # must be the d16dd804 account (memory: lazo-deploy-accounts)
npx wrangler deploy
npx wrangler secret put ANTHROPIC_API_KEY
npx wrangler secret put ELEVENLABS_API_KEY
```

Without `ELEVENLABS_API_KEY` June speaks with the browser's British voice. Without `ANTHROPIC_API_KEY`
the panels still work; the brief and the chat say the key is missing.

The Anthropic key already lives in Secret Manager for the Firebase functions. To copy it across without
it ever appearing on screen:

```bash
"C:\Users\kurvh\google-cloud-sdk\bin\gcloud" secrets versions access latest --secret=ANTHROPIC_API_KEY --project=lazo-513ec | npx wrangler secret put ANTHROPIC_API_KEY
```

Custom domain: `june.meetlazo.com` is a Workers custom domain in wrangler.toml (`routes`), created on deploy; the workers.dev address keeps working. `PUBLIC_URL` (email links) points at it; the dashboard's `kJuneHubUrl` should move to it in the next vendor patch. Email/password sign-in works from any origin; if Google or Apple sign-in is wanted
later, that domain must also be added to Firebase Auth → Authorized domains.

Local: `npx wrangler dev` (KV is simulated locally; sign in with a real Lazo vendor login to see data).

## Linking from the vendor dashboard

Add a "Talk to June" button in the vendor dashboard (FlutterFlow) that opens the hub URL with
`launchUrl`; the vendor signs in once and the refresh token keeps them signed in. A webview inside the
app works too, same URL.

## Metros

```bash
python -c "import json,sys; sys.path.insert(0,'config'); from metros import METROS; json.dump({m['id']:{'name':m['name'],'state':m['state'],'display':m.get('display',m['name']+', '+m['state']),'lat':m['center'][0],'lon':m['center'][1]} for m in METROS}, open('june-hub/src/metros.json','w'), indent=0)"
```
(run from `C:\Users\kurvh\lazo-directory`).

## Known limits (v1)

- The brief is written on open, or at the vendor's hour by the cron once they turn alerts on (round two).
- `send_message` creates the message as the vendor and sets `status: responded`; the thread's
  `lastMessageAt/lastMessageRole/lastMessagePreview` patch is attempted and ignored if the rules refuse it
  (the app's own send path may rely on a function for those).
- Wedding-day weather uses the metro centre, not the venue address.
- Tasks due today come from `nextTaskTitle/nextTaskAt` on the inquiry (no collection-group rule for tasks).

## Social posting (June Studio)

Auto-posting to Instagram and Facebook is gated to `vendors.tier == 'studio'`. Every tier gets
`draft_post`: June writes a caption in the vendor's voice and pairs it with a showcase cover (galleries
the couple consented to feature, `vendors.showcases[]`) or a portfolio photo (`vendors.gallery[]`); the
card offers Copy caption and Open Instagram. Studio vendors with accounts connected also get Post and
a schedule picker on the same card.

Provider: Ayrshare (Business plan, one Ayrshare profile per vendor, stored in KV `social_<vendorId>`).
Vendors link their own Instagram and Facebook through Ayrshare's hosted page (`/api/social/connect`
returns the link). Posts go through `/api/social/post` (caption, one photo from the allowed set,
platforms, optional scheduleDate) and are logged in KV `posts_<vendorId>`.

To switch it on (Jesse): sign up for Ayrshare Business, then
```bash
npx wrangler secret put AYRSHARE_API_KEY
npx wrangler secret put AYRSHARE_PRIVATE_KEY     # the PEM from Ayrshare -> Profiles -> Generate JWT
```
and set `AYRSHARE_DOMAIN` in wrangler.toml to the domain Ayrshare shows, then deploy. Until then the
Social panel tells Studio vendors it is switching on shortly, and drafting still works.

Later, to drop the per-post cost: a Lazo Meta app with `instagram_content_publish` and
`pages_manage_posts` through App Review, swapping `ayr()` for the Graph API behind the same routes.
Instagram needs JPEG media at a public URL; showcase covers are served by the site worker.

## Round two (2026-10-05): triage, alerts, pricing, reviews, availability, the Monday review, reminders

| Piece | How |
|---|---|
| Triage + first replies | `POST /api/triage`: one Sonnet call over the waiting threads (last six messages each) returns priority 1-3, a one-line why, and a first reply drafted from the vendor's packages, saved replies and FAQ. Cached in KV `triage_<vendorId>` keyed by the thread's last message. The Waiting panel sorts by priority and offers "Use June's draft", which opens the normal confirm card. Off-platform leads already arrive in `inquiries` by SMS/email (leads.js), so a reply from June reaches them by text and email through `onLeadMessage`. |
| 7am brief by email, nudges, reminders | Alerts panel -> `POST /api/subscribe` stores the vendor's Firebase refresh token encrypted (AES-GCM under `JUNE_SECRET`) in KV `sub_<vendorId>`. The cron (`*/15 * * * *`, `runCron`) mints an ID token from it, takes a snapshot as the vendor, and at their hour writes the brief (plus the Monday review on Mondays) and emails it through Resend; nudges once per lead message after two hours; emails reminders when due. Eight vendors per pass, least recently served first. Turn off = refresh token deleted. `POST /api/cron` (owner) runs a pass by hand. |
| Signed-in hand-off from the app | `functions-dashboard/june-token.js` (`juneToken` callable, build 022) mints a one-hour custom token; dashboard v181 (`patch_vendor_v181.py`) opens `kJuneHubUrl?t=<token>`; the page exchanges it with `signInWithCustomToken` and strips the param. Falls back to the plain URL. Deploy: `firebase deploy --only functions:dashboard` from `C:\Users\kurvh\lazo-functions`. |
| Pricing | `metroStats/{metro}__{category}` (priceFrom p25/p50/p75, medianReplyMin) against `vendors.startingPrice` and `packages[]`; Pricing panel and "Am I priced right". June quotes only from packages. |
| Reviews | Top-level `reviews` where vendorId plus `vendors/{id}/reviews`; Reviews panel; weddings past two days without a review get "Ask for a review" -> `request_action review_request` (message to the couple, KV `asked_<vendorId>` so she asks once). |
| Availability | `check_date` tool (booked, held, consults, blocked); `block_date` / `unblock_date` actions patch `vendors.unavailableDates`. |
| Monday review | `makeBrief(..., "weekly")` from `weekStats` (last 7 vs prior 7: leads by createdAt, replies by respondedAt, bookings by bookedAt, cash by paidAt, views d7 vs d7Prev); KV `weekly_<vendorId>`; auto on Mondays, button any day; audio like the brief. |
| Saved replies + FAQ | In the context and the triage prompt; June drafts in the vendor's own wording. |
| Reminders | KV `reminders_<vendorId>`; `set_reminder` / `complete_reminder` tools; Reminders panel with add, +1h, Done, delete (`/api/reminders`); due ones are spoken on open and emailed by the cron; daily/weekly repeat rolls forward. Times resolve in the vendor's timezone (`localToIso`). |

Secrets to add for round two (Jesse):
```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))" | npx wrangler secret put JUNE_SECRET
```
```bash
& "C:\Users\kurvh\google-cloud-sdk\bin\gcloud.cmd" secrets versions access latest --secret=RESEND_API_KEY --project=lazo-513ec | npx wrangler secret put RESEND_API_KEY
```
Rotating `JUNE_SECRET` invalidates every stored refresh token; vendors just turn alerts on again.

## Radio (2026-10-05)

A second `<audio>` beside June's voice, in the Radio card: Radio Paradise (main, mellow, rock, global; they publish their streams for third-party players) and three Global stations (Classic FM, Classic FM Calm, Smooth Chill; the same streams JARVIS plays). June ducks it to 15% while she speaks or listens and brings it back after; the core turns sage and follows the music when the stream allows cross-origin audio, otherwise it plays without driving the core. Voice: "June, play Classic FM", "play some music", "stop the radio", "louder", "quieter". Station and volume remembered per browser. Conversation mode does not auto-listen while the radio is on. Note: Global's streams are offered for personal listening; if June's vendor count grows, swap them for stations with an explicit third-party licence (the list is `RADIO` in june.html).

## To decide later

- (done 2026-10-05) The app hands the vendor to June signed in, through the juneToken callable and dashboard v181.

## June for couples (2026-10-07)

The same hub serves couples, free. A login that is not a vendor (no `users/{uid}.vendorId`) resolves to a
couple: `users/{uid}.coupleUid` (a partner on a shared plan) or the uid itself, and `src/couple.js` takes over.
Everything is read AS THE COUPLE: `couples/{cid}` (names, weddingDate, metroId, budgetTotal, guestEstimate,
keyDates), `couples/{cid}/plan` (one doc per category: status needed/researching/booked/skipped, vendorName,
budgetPlanned/budgetActual), `guests`, `dayof`, `shopping`, `inquiries` where coupleUid (their vendor threads),
each thread's `tasks` assigned to the couple and `invoices`, `consults` where coupleUid, and their
`weddingSites` doc with its `rsvps`. The page switches on `state.s.kind` (`body[data-kind="couple"]` hides the
vendor-only cards and shows Your team, Guests and The day; Money becomes budget vs committed).

Chat tools: lazo_thread, lazo_guests, lazo_find_vendors (directory search in their metro by category slug),
lazo_prices (metroStats), lazo_timeline, lazo_shopping, open_thread, remember/forget, set_reminder /
complete_reminder. Confirm-first actions (request_action): send_message to a vendor, complete_task, set_team
(status / vendorName / planned / actual), add_guest, set_rsvp, add_shopping, tick_shopping, add_moment,
set_details (weddingDate / budgetTotal / guestEstimate). Booking, signing, paying and reviews stay in the app.
KV keys are suffixed `_c_<cid>` (memory, queue, brief, brief_audio, reminders). No cron/email alerts for
couples yet (the brief is written when they open June). `COUPLE_APP_URL` (default https://app.meetlazo.com/)
is where open_thread sends them.

App hand-off: `app-patches/patch_couple_v145.py` adds a gold "Talk to June" button beside "Ask June" in the
couple dashboard (juneToken callable → `?t=`; any signed-in uid works). Jesse pastes v145 into FlutterFlow.
