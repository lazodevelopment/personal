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
