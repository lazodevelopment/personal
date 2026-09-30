# Lazo Directory Engine — Day 1 Build

Nationwide-architected, tranche-released. T1 = Phoenix / Denver / DFW.
Runs on your machine (PowerShell, Python 3.14 via `python`). All secrets in `.env` only.

## One-time setup
```powershell
cd C:\Users\kurvh\lazo-directory
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env    # then fill values in Notepad — never commit .env
```
Also one-time, in the repo root:
```powershell
firebase deploy --only firestore:rules --project lazo-513ec   # or paste firestore.rules in console
```
Cloudflare (dash or CLI): create R2 bucket `lazo-site` on the Lazo account d16dd804 (NOT f2ddc254, which is Atavia's - `npx wrangler whoami` must show ...43af before any deploy); create an R2 API token
(Object Read & Write) and put its keys in `.env`.

## Local smoke test — no keys needed
```powershell
python generate\build.py --mock mockdata\phoenix_sample.json
# open dist\index.html and dist\phoenix\wedding-photographers\index.html in a browser
```

## Seed T1 (costs real money — dry-run first)
```powershell
python seed\places_seeder.py --tranche 1 --dry-run     # shows est. calls + $ before anything runs
python seed\places_seeder.py --metro phoenix            # then one metro at a time
python seed\places_seeder.py --metro denver
python seed\places_seeder.py --metro dallas-fort-worth
```
Seeder is resumable (checkpoints in `seed\.checkpoints`), dedupes by place_id,
skips permanently-closed businesses, and stores ToS-safe fields only
(no Google reviews/ratings/photos are stored — our trust data is first-party).

## Build + deploy
```powershell
python generate\build.py --tranche 7                    # Firestore -> dist\  (7 = all metros; the tranche sets the homepage vendor total + market count, so never build with less)
cd worker; npx wrangler deploy; cd ..                   # the R2-serving worker
python deploy\upload_r2.py                              # sync dist -> R2
```
Then in Cloudflare dash: Workers → lazo-site → add custom domain `meetlazo.com`.

## Swap in the final logo (when Batul delivers)
Replace `generate\static\logo.svg` with the final bold mark SVG, rebuild, redeploy assets:
```powershell
python generate\build.py --tranche 7
python deploy\upload_r2.py --prefix assets
```

## Nightly regeneration (same pattern as lr-nightly.bat)
Create `C:\Users\kurvh\lazo-nightly.bat`:
```
cd C:\Users\kurvh\lazo-directory
call .venv\Scripts\activate.bat
python generate\build.py --tranche 7
python deploy\upload_r2.py
```
Task Scheduler → daily 3:30 AM (staggered after lr-nightly at 3:00).

## SEO plumbing (2026-09-21)
- build.py writes each vendor's final URL slug back to Firestore (`vendors/{id}.slug`); the couple app's "View full Lazo profile" button depends on it.
- Metro and category pages link to the six nearest metros within 260 mi (`near=` in build.py, `<!-- lz-near -->` in the templates).
- IndexNow: `python deploy\indexnow.py --since today` (or `--prefix rochester`). Key in deploy/indexnow.key, ownership file `dist/<key>.txt` must be at the site root. deploy_site.py runs it as step 6/6.

## Hotels near venues (2026-09-21)
- `python seed\hotels_osm.py` pulls hotels/motels per metro from OpenStreetMap (Overpass; VK mirror first) into data/hotels_osm.json, cached per metro in data/hotels_cache/. Free, ODbL, may be published indefinitely (the page credits OSM). Re-run with `--refresh` yearly, and once for any new metro.
- build.py attaches the six nearest named hotels within 15 mi to every wedding-venues page (section + LodgingBusiness ItemList JSON-LD). No data file = no section.

## Stub content pass + tiered sitemaps (2026-09-22, CONTENT-0922 / SEO-0922)
- Every vendor page gets an "Around <locality>" block computed from data we hold (distance/direction from downtown, nearest venue, venues within 10 mi, same-category peers within 3/10 mi, hotels within 5 mi, communities served from neighbours' localities) plus LocalBusiness.areaServed. Search Console's 2026-09-22 exports showed rejected pages were 99% vendor stubs with 62% shared vocabulary; this adds facts that differ per page. Patch: generate/patch_build_content0922.py.
- Sitemaps are per tier (hubs / rich / venues / vendors / templates / couples) so GSC reports indexing per tier. Patch: generate/patch_build_sitemaps0922.py. sync_dist.py writes sitemap-templates.xml.

## Adding a metro (nationwide path)
1. Add a dict to `config/metros.py` with grid tiles + tranche number.
2. `python seed\places_seeder.py --metro <id>`
3. Rebuild + sync. No code changes — that's the deal we made.

## What's deliberately NOT here yet
- Algolia indexing (first week, when search UI lands on category pages)
- Cost-guide + cultural/lazo-ceremony pages (need verified pricing data model)
- Spanish `/es/` layer (T2)
- Claim flow (FlutterFlow app slice — next build session)

## Photos, placed + guest photos (2026-09-29, JC-LAZO-*-0929)
- Couple sites take positioned photos: `weddingSites.heroPhoto` / `storyPhoto` are `{url, x, y, zoom}` (x/y 0..1 = the point that stays in view, zoom 1..3 around it), `siteGalleryFocus` one `{x, y, zoom}` per gallery photo. The dashboard's "Position your photo" sheet (v136, app-patches/patch_couple_v136.py) and the site apply the same maths (object-position + transform-origin). The header falls back to the home photo (`coverUrl` + `coverFocus`), then the template's stock picture; a live site never shows the demo couple in the story slot.
- Guests add photos from their phones: from the wedding day (or `?photos=1`) the site shows "Share the day as you saw it"; the page shrinks each photo to 2000px and POSTs to `/api/w/{slug}/photos` (worker/src/guestphotos.js). Files live in the **lazo-galleries** bucket under `guest/{slug}/` (deploy_site.py never touches that bucket), served at `/w/{slug}/photo/{id}.jpg`. `guestPhotosOn` (default on) and `guestPhotosNote` come from the editor; removing a photo from the dashboard writes its id to `guestPhotosRemoved` and the worker deletes the object on its next listing (the doc is world-readable, so hiding would not be enough). Limits: 10 MB, JPEG/PNG/WebP by magic bytes, 1,000 per site.
- Templates: `python wedding-websites\patch_photos_templates.py` (idempotent; _base.html + the 20 live templates), then `sync_dist.py` + `upload_r2.py --prefix wedding-websites`, and `cd worker; npx wrangler deploy` (whoami must be the Lazo account).

## The site, live (2026-09-29, JC-LAZO-*-0929-LIVE)
- Worker (worker/src/sitefeatures.js): `/api/w/{slug}/weather` (Open-Meteo, venue point from the nearby cache, Places, or the "City, ST" in the address; only inside 16 days), `POST /api/translate` (Workers AI m2m100, `[ai]` binding, each string cached a month), `/w/{slug}/cards` (printable QR table cards), `/w/{slug}/playlist` (the DJ page). Payload gains timelineOn/timeline, seatingOn, mealOptions, galleryUrl, translateOn; vendorTeam entries may carry vendorId + url.
- Templates (`python wedding-websites\patch_live_templates.py`): hour by hour with Now/Next on the day, forecast card, Find your seat, personal RSVP links (`?i={guestId}` reads weddingSites/{slug}/invites/{id}; RSVP carries meal/plusOnes/invite), linked vendor credits with Check your date, gallery hand-off, language pill, `?wall=1` slideshow.
- Rules: weddingSites/{slug}/seating (public read), invites (get only, never list), playlist (public read); all written by the couple. rsvps accept `invite`.
- Dashboard v137 (app-patches/patch_couple_v137.py): publish mirrors the Day-of timeline (vendor-only moments filtered), the seating chart and the song requests; LIVE ON THE DAY editor section; Personal RSVP link per guest; thank-you tracker; Live links card. The sources (dayof, guests, musicRequests) are couple-private, which is why they are mirrored rather than read by the worker.
- Not done: texting June over SMS (no phone number/provider in this project) and June reading the timeline/seating (her brain is in functions-dashboard, a separate repo).

## More for the site (2026-09-29, JC-LAZO-*-0929 DAYB4 / HOLD / MORE)
- worker/src/auth.js verifies the partner's Firebase ID token (Google JWKs, RS256) and confirms they own the site; reads that need the couple's rights go to Firestore REST with that token so the rules decide. Used by `POST /api/w/{slug}/day-before` (the day-before email through Resend: needs RESEND_API_KEY; optional DAYB4_FROM), `GET /api/w/{slug}/photos?pending=1` and `POST /api/w/{slug}/photos/approve`.
- Moderation: weddingSites.guestPhotosHold sends uploads to guest/{slug}/pending/; approve copies to the live prefix. `/w/{slug}/photos/download` zips the wall in the browser (fflate).
- Templates (`python wedding-websites\patch_more_templates.py`): whole-day .ics + Google Calendar, weddingSites.events cards with per-event RSVP (`events` on the reply), hotelAddress directions, the seat finder draws the room from seating/main tables + canvas.
- Dashboard v138 (app-patches/patch_couple_v138.py): day-before sheet, hold switch + Waiting list + Zip, events editor, hotel address, seating mirror with tables. Apple Wallet passes were skipped: they need an Apple Pass Type certificate the project does not hold.

## Couple dashboard v139 - the review fixes (2026-09-29)
app-patches/patch_couple_v139.py (v138 -> v139): the data-loss fixes from the 2026-09-29 review (setup un-booking vendors, inquiries under the Browse category, Knot/Zola CSV losing surnames, dream-board reverts, slug collisions, RSVP import wiping edits, date pickers after the wedding, per-partner tour/notification flags, partner invite on phones, timeline past midnight), sheet fixes (budget rows, tip chips), weather back-off, messages by activity with hello/lost states, post-wedding June steps, Notifications row, chapters list/edit/delete, guest search + delete confirm, registry prefill + long-press edit, and the text bugs. Still open from the review: Browse "ranked" needs a score field + composite index; money (paid invoices, accepted proposals) still does not feed budgetActual; the dead v91 team card, saved card and messages preview remain unwired; the website editor is still one long dialog.

## Couple dashboard v140 - the open items (2026-09-29)
app-patches/patch_couple_v140.py (v139 -> v140): Browse merges a top-24-by-score query (composite index vendors: categories contains / metroId / score desc, in firestore.indexes.json) into the unordered page; paid invoices write plan/{cat}.paid.{inquiryId} and accepted proposals plan/{cat}.quoted.{inquiryId} (+ budgetPlanned when empty), spent = max(typed, paid); the v91 team card heads Vendor team; the Saved tile opens the saved-vendors sheet; _messagesPreview/_budgetMini/_browseCardTile/_seedStarterTimeline removed; the website editor has a section jump bar, is modal, and Cancel confirms.

## Selling the wedding website (2026-09-29, JC-LAZO-WWI-0929-SELL)
- `python wedding-websites\patch_hub_sell.py` adds the "Built for the day itself" section (ten screenshot cards, a strip of four more, the Knot/Zola comparison table) and five "Everything included" rows to wedding-websites/index.html. Idempotent (lz-sell markers).
- Screenshots (Flora - blush; Sage read too green): `python wedding-websites\_preview.py flora && python wedding-websites\_mock_now.py flora` builds _preview/flora-now.html (clock pinned to 5:40 pm, mocked seat finder / wall / forecast / invite, ?shot=<selector> shifts a section to the top), served by `.claude/launch.json` (ww-preview, port 8090) and captured with headless Chrome (`chrome --headless=new --window-size=1280,800 --virtual-time-budget=8000 --screenshot=...`). WebP copies live in generate/static/ww-*.webp so build.py ships them to /assets/; PNG originals in generate/static/ww/ are not copied.

- Patch order matters: patch_photos, patch_live and patch_more each strip and re-append their scripts before </body>, so re-running one moves it after the others. patch_more now defers to DOMContentLoaded so it never depends on order.

## Peony (2026-09-29, JC-LAZO-WWT-0929-PEONY)
- The twenty-first template: wedding-websites/themes_peony.py (merged into make_themes.THEMES), themes.json entry, hub card + filters + SEO, worker TEMPLATES, dashboard v141 (picker + palettes). Build: `make_themes.py peony`, `apply_feel.py peony`, `patch_seo.py peony`, then the three 0929 patches with `peony`, then `patch_hub_cards.py`, `patch_hub_filters.py`, `patch_hub_seo.py`.
- The hub's sales screenshots are shot on Peony (`_mock_now.py peony` uses PHOTOS_BY_SLUG for its own hero/story photos); the CTA links ?template=peony.

- Default design is Peony (2026-09-29): dashboard v142 (app-patches/patch_couple_v142.py) and worker renderCoupleSite fall back to peony instead of fete.

## Search visibility (2026-09-29, JC-LAZO-WWSEO-0929-FEATURES)
- Diagnosis: site launched 2026-09-21; Google had indexed the home page and vendor pages but nothing under /wedding-websites/ (site: query empty), and "lazo" queries return the lasso ceremony. Pages return 200, no noindex, sitemap-templates.xml is in the index, home nav + vendor pages link the hub - the gap is crawl age and topical authority, not plumbing.
- Done: five feature landing pages from `wedding-websites\make_features.py` (guest-photo-sharing, find-your-table, spanish-wedding-website, day-of-timeline, vs-zola-the-knot) linked from the hub's comparison block; Organization.alternateName widened (Meet Lazo, meetlazo, ...); IndexNow submitted for the templates and the feature pages.
- Manual, in Search Console: URL inspection > Request indexing for /wedding-websites/, /wedding-websites/peony/ and the five feature pages; confirm sitemap-templates.xml shows as Success under Sitemaps.

- App Store (2026-09-30): "Lazo: Wedding Planner" id 6812863675 is live; base.html carries the apple-itunes-app smart banner and _footer.html links the listing ("Get the iPhone app"). Android pending.

- Home (2026-09-30, JC-LAZO-HOME-0930-APP): generate/patch_home_app0930.py puts the app section (Apple store screenshots /assets/app-*.webp, App Store badge) under the hero, removes the vendor claim tile from the couples home, and hides the featured row for a metro with no claimed vendors (was "No <city> vendor has claimed yet"). Applies to the template and dist/index.html.
