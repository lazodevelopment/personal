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

Custom domain later: add `june.meetlazo.com` to the worker in the Cloudflare dash (Workers → june-hub →
Settings → Domains). Email/password sign-in works from any origin; if Google or Apple sign-in is wanted
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

- The brief is written when the vendor opens June, not pushed at 7am (the worker holds no vendor
  credential overnight). The functions-dashboard email covers the morning nudge.
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

## To decide later

- Vendors sign in to June once more in the browser, since the app's session cannot be handed across. If that turns out to be friction, the hub can accept a short-lived token the app mints (a callable returns a custom token; the hub exchanges it at Identity Toolkit), and the Talk to June button would open it already signed in.
