# Atavia Weddings — Website

A fast, static, multi-page site for **ataviaweddings.com**, built to be hosted on **Cloudflare Pages**. Dark editorial-luxury aesthetic (charcoal / copper / ivory, Cormorant Garamond + Inter) matching the packages page and print collateral.

---

## ⚡ Two things to do before you go live

1. **Connect the booking form.** The contact form uses [Formspree](https://formspree.io). Open `contact.html`, find `action="https://formspree.io/f/YOUR_FORM_ID"`, and replace `YOUR_FORM_ID` with your real form ID (create a form at formspree.io → it gives you an ID like `xdorwqab`). If you regenerate the site, change it in `_src/pages/contact.html` and re-run the build. Until this is set, the form shows a friendly "not connected yet" message instead of submitting.

2. **Preview the gallery.** All 349 photos load from your public Google Cloud Storage bucket (`atavia_bucket`) through a free image proxy (**images.weserv.nl**) that serves fast, web-sized copies and caches them — this keeps your Storage bandwidth low and the page quick. Each image automatically falls back to the direct bucket original if the proxy is ever unavailable, so nothing breaks. Nothing to do here except confirm it looks right on a preview deploy. If you'd rather not depend on a third-party proxy, see **"Gallery images"** below.

---

## Deploying to Cloudflare Pages

### Option A — Drag & drop (fastest)
1. Sign in to the Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** → **Upload assets**.
2. Drag the **entire `atavia-site` folder contents** (not the folder itself — the files inside it, so `index.html` is at the top level).
3. Give the project a name and deploy. Cloudflare gives you a `*.pages.dev` URL immediately.
4. Add your domain: project → **Custom domains** → add `ataviaweddings.com` and `www.ataviaweddings.com`, then follow the DNS steps.

### Option B — Git (recommended for ongoing edits)
1. Push this folder to a GitHub/GitLab repo.
2. Cloudflare Pages → **Create** → **Connect to Git** → pick the repo.
3. Build settings: **Framework preset:** None. **Build command:** *(leave blank)* — the HTML is already built. **Build output directory:** `/` (repo root).
4. Deploy. Every push auto-publishes.

> If you'd rather have Cloudflare run the build, set the build command to `python3 _src/build.py` and keep output directory `/`.

### Clean URLs
Links use `/about`, `/packages`, etc. (no `.html`). Cloudflare Pages serves `about.html` at `/about` automatically — no config needed. `404.html` is served automatically for unknown paths. `_redirects` handles legacy paths (e.g. `/book-now` → `/contact`).

---

## Editing the site

All pages are assembled from shared parts so the nav, footer, and `<head>` stay identical everywhere. **Don't edit the top-level `.html` files directly** — they're generated. Edit the sources, then rebuild.

```
python3 _src/build.py
```

- **Nav / footer:** `_src/partials/nav.html`, `_src/partials/footer.html`
- **Page content:** `_src/pages/*.html` (one file per page — just the body)
- **Titles, meta descriptions, canonical URLs:** the `PAGES` list at the top of `_src/build.py`
- **Styles:** `assets/css/site.css` — **not generated**, edit directly
- **Behavior (menus, lightboxes, counters):** `assets/js/site.js` — **not generated**, edit directly

### Venue directory (programmatic SEO — this is the growth engine)
Targets the highest-intent query in the funnel: the bride has already booked her venue and searches *"<Venue> wedding videographer"*.

**Structure** (4 levels, all generated):
```
/venues/                              master hub — every state
/venues/texas/                        state hub  — every city in TX
/venues/texas/dallas/                 city hub   — every venue in Dallas
/venues/texas/dallas/the-olana        venue page — the money page
```
Linked from the footer ("Venue directory"). Each venue page cross-links 6 sibling venues, its city hub, and its metro page.

**To scale to thousands of pages:**
1. Get a Google Places API key (enable *Places API (New)* in Google Cloud).
2. `pip install requests` then set the key:
   `export GOOGLE_PLACES_API_KEY="..."`  (Windows: `set GOOGLE_PLACES_API_KEY=...`)
3. Add cities to `TARGETS` in `_src/fetch_venues.py` (it already ships ~140 cities across all all 50 states — add 500 more to go bigger).
4. Run it:
   ```
   python3 _src/fetch_venues.py --dry-run     # preview, writes nothing
   python3 _src/fetch_venues.py               # fetch + append to _src/venues_data.py
   python3 _src/fetch_venues.py --state TX    # one state at a time
   ```
5. Regenerate: `python3 _src/gen_venues.py && python3 _src/build.py`

The fetcher **dedupes on place_id**, so re-running is safe and cheap. It filters for quality (4.0+ rating, 8+ reviews, real venue types) and rejects florists/planners/photographers. Sitemaps auto-split into 2,000-URL chunks with a `sitemap.xml` index.

**Three things to know:**
- **Cost:** Places Text Search is billed per request (~$32/1k), but Google gives a monthly free credit that covers a run of this size. Check current pricing before a huge run.
- **Google's terms:** Places data has caching restrictions. This build stores only factual business info (name, city, address) — it does **not** republish Google's ratings, reviews, or photos. Keep it that way, and re-run the fetcher periodically to refresh.
- **Legal:** every page carries a nominative-fair-use disclaimer (not affiliated with / endorsed by the venue) — same as the LeaseReputation build. Worth running past your attorney since you're naming branded venues.

**Biggest upgrade available:** tell me which venues you've actually shot at, and those pages get "we've filmed here" + real photos. Those will convert far better than the rest.

### Guides (`/guides/`)
Six cornerstone articles generated by `_src/gen_guides.py` (edit the `GUIDES` list, re-run, then `build.py`). They rank for top-of-funnel queries brides search *before* booking — and, just as importantly, they give the venue directory the topical authority it needs. Thousands of thin directory pages with no supporting content look like a doorway farm to Google; real guides are what make it look like a real business.

### Lead attribution
Every booking request now tells you where it came from. `site.js` records the visitor's landing page, referrer, and the last **venue page** they viewed; the contact form ships those as hidden fields (`Venue`, `Venue Page`, `Landing Page`, `Referrer`). So a Formspree email will say *"came from The Carlisle Room, Dallas."* That's how you find out which venue pages actually convert — and which deserve real photos.

### Reviews & stars (important)
Star ratings in Google search come from your **Google Business Profile**, not from schema markup. Google stopped honouring self-serving review markup for local businesses in 2019, so adding `AggregateRating` to your own site will *not* produce stars. If you want stars in search: claim/complete your Google Business Profile and collect reviews there. The site does show your real Knot rating (5.0 from 12 reviews) as visible social proof, linked to the profile.

### Location pages
Two things, both generated by `_src/gen_locations.py` (edit, then run `python3 _src/gen_locations.py && python3 _src/build.py`):

- **8 metro pages** at URLs like `/minneapolis-wedding-videographer` — each with unique local copy, real venues, and its own LocalBusiness schema. Edit the `METROS` list to add/change cities. Currently: Minneapolis, Boston, Phoenix/Scottsdale, Los Angeles, New York City, Chicago, Miami, Atlanta, Dallas.
- **One nationwide hub** at `/nationwide-wedding-videographer` that boldly says you serve all all 50 states, lists every state (linking the 8 that have a metro page), and targets national terms like "nationwide wedding videographer." This is the reassurance page for a bride in any state — and it avoids the SEO risk of 50 near-identical state pages.

Both are added to the sitemap automatically; the footer's "Serving Nationwide" strip shows the metros plus a link to the hub. Colorado and Texas were left out of the metros on purpose (52 Eighty / 83 Weddings territory). The metro venue names are well-known examples — double-check them against where you actually shoot. To go deeper in a real market later, add it to `METROS` (cities out-convert states); the hub already covers the rest.


`blog.html` currently shows an elegant "coming soon" state with a commented-out post-card template inside `_src/pages/blog.html`. Copy that card into a `<div class="cards cards--3"> … </div>` grid to start publishing.

### Swapping images
Any `src="https://firebasestorage.googleapis.com/…atavia-c29cd…"` points at your Firebase Storage — upload a new file there and paste its URL. To change gallery photos in bulk, edit `_src/gen_gallery.py` (it prints the gallery grid markup) or edit the `<figure>` items directly in `_src/pages/gallery.html`.

### Gallery images
The gallery lives in a public Google Cloud Storage bucket, `gs://atavia_bucket/Site Files/`, as `gallery-01 (1).jpg` … `gallery-01 (349).jpg`. Thumbnails and the lightbox load through the **images.weserv.nl** proxy (fast, cached, web-sized), with a built-in fallback to the direct bucket URL. Everything is generated by `_src/gen_gallery.py` — change `COUNT`, the bucket path, or the proxy sizes there and re-run it, then rebuild.

To change or add photos: upload to the same bucket/folder and bump `COUNT` (or adjust the naming) in `gen_gallery.py`.

**To drop the third-party proxy entirely** and serve fully from your own infrastructure: add the **Resize Images** Firebase extension to the bucket, run its backfill on the existing 349, then tell me the resized-file naming and I'll point the grid straight at those (no proxy). Or, to go proxy-free right now, edit `gen_gallery.py` so `weserv()` just returns the direct bucket URL — the page will work, but it'll serve full-resolution originals.

**The header/footer logo** (`atavia_primary_logo`) also loads from your Wix CDN. It's the same image your live site uses, so it works today — but it's the one asset you'll most want bundled locally. Send me the PNG (or export it from Wix) and I'll drop it into `assets/img/` and point the header and footer at the local copy.

---

## What's already handled

- **SEO:** per-page `<title>` + meta description, canonical tags, Open Graph + Twitter cards, `sitemap.xml`, `robots.txt`, and your Google Search Console verification tag (already embedded in every page's `<head>`).
- **Structured data:** LocalBusiness JSON-LD on the home page (name, phone, email, Instagram).
- **Social/OG image:** your Firebase `atavia16.png`.
- **Accessibility:** keyboard-focus styles, reduced-motion support, alt text, skip-friendly semantics.
- **Responsive:** mobile menu + fluid layouts down to small phones.

## Contact details baked into the site
Phone (336) 537-9590 · info@ataviaweddings.com · Instagram @ataviaweddings · © Atavia Weddings LLC.
To change any of these, update `_src/partials/nav.html`, `_src/partials/footer.html`, and `_src/pages/contact.html`, then rebuild.

## File map
```
atavia-site/
├── index.html, about.html, packages.html, …   ← generated pages (don't edit)
├── 404.html, sitemap.xml, robots.txt, _redirects
├── assets/
│   ├── css/site.css        ← styles (edit here)
│   ├── js/site.js          ← scripts (edit here)
│   └── img/favicon.svg
└── _src/                   ← sources
    ├── build.py            ← run this to regenerate pages
    ├── gen_gallery.py      ← helper for the gallery grid
    ├── partials/           ← nav + footer
    └── pages/              ← page bodies (edit here)
```
