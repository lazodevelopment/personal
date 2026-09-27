"""patch_wwseo.py - JC-LAZO-WWSEO-0919-002
Worker changes for wedding-website SEO:
  1. renderCoupleSite strips the template's <!-- lz-seo --> block (the demo
     page's canonical/share tags/JSON-LD) before hydrating a couple's site.
  2. Public (no passcode) couple sites get a canonical and Event JSON-LD.
  3. GET /sitemap-couples.xml lists every public couple site from Firestore.
Idempotent: refuses to run twice (looks for the build id).
  python worker\\patch_wwseo.py
"""
from pathlib import Path

P = Path(__file__).resolve().parent / "src" / "index.js"
s = P.read_text(encoding="utf-8")
if "JC-LAZO-WWSEO-0919-002" in s:
    raise SystemExit("already applied")


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"anchor {old[:70]!r}: found {n}, wanted {count}")
    s = s.replace(old, new)


# 1. strip the demo page's SEO block
rep("  let html = await asset.text();\n\n  // 3. the payload",
    "  let html = await asset.text();\n"
    "  // JC-LAZO-WWSEO-0919-002: the demo page's canonical, share tags and JSON-LD\n"
    "  // describe the TEMPLATE. A couple's site gets its own below.\n"
    "  html = html.replace(/<!-- lz-seo -->[\\s\\S]*?<!-- \\/lz-seo -->\\n?/, \"\");\n\n  // 3. the payload")

# 2. canonical + Event JSON-LD for public sites
rep('  html = html.replace("</head>", og + inject + "\\n</head>");',
    '  // JC-LAZO-WWSEO-0919-002: a public couple site is a page worth finding - guests\n'
    '  // search "<names> wedding". Canonical (the /w/ URL takes ?palette etc.) and an\n'
    '  // Event when the date is known, else a plain WebPage. Passcode sites get nothing.\n'
    '  let seo = "";\n'
    '  if (!priv) {\n'
    '    seo += `<link rel="canonical" href="${pageUrl}">\\n`;\n'
    '    const ld = { "@context": "https://schema.org", "@type": "WebPage", name: title, url: pageUrl, description: desc };\n'
    '    if (/^\\d{4}-\\d{2}-\\d{2}$/.test(payload.dateIso)) {\n'
    '      ld["@type"] = "Event";\n'
    '      ld.startDate = payload.dateIso;\n'
    '      ld.eventStatus = "https://schema.org/EventScheduled";\n'
    '      ld.eventAttendanceMode = "https://schema.org/OfflineEventAttendanceMode";\n'
    '      if (payload.venueName || payload.venueAddress) {\n'
    '        ld.location = { "@type": "Place", name: payload.venueName || payload.venueAddress };\n'
    '        if (payload.venueAddress) ld.location.address = payload.venueAddress;\n'
    '      }\n'
    '      if (payload.names) ld.organizer = { "@type": "Person", name: payload.names };\n'
    '    }\n'
    '    if (image) ld.image = image;\n'
    '    seo += `<script type="application/ld+json">${JSON.stringify(ld).replace(/</g, "\\\\u003c")}</script>\\n`;\n'
    '  }\n'
    '  html = html.replace("</head>", seo + og + inject + "\\n</head>");')

# 3. the couples sitemap
rep("async function renderCoupleSite(slug, env) {",
    '''// JC-LAZO-WWSEO-0919-002: every public couple site, one sitemap. Passcode sites
// and sites with no names yet stay out. Cached six hours at the edge.
async function couplesSitemap() {
  const key = new Request("https://meetlazo.com/sitemap-couples.xml");
  let r = await caches.default.match(key);
  if (r) return r;
  const locs = [];
  let pageToken = "";
  for (let i = 0; i < 40; i++) {
    const u = `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/weddingSites`
      + "?pageSize=300&mask.fieldPaths=passcode&mask.fieldPaths=names"
      + (pageToken ? `&pageToken=${encodeURIComponent(pageToken)}` : "");
    let j;
    try {
      const rr = await fetch(u, { headers: { accept: "application/json" } });
      if (!rr.ok) break;
      j = await rr.json();
    } catch (e) { break; }
    for (const d of (j.documents || [])) {
      const slug = String(d.name || "").split("/").pop();
      if (!/^[a-z0-9\\-]{1,80}$/.test(slug)) continue;
      const f = d.fields || {};
      if (fsVal(f.passcode)) continue;
      if (!fsVal(f.names)) continue;
      const lm = String(d.updateTime || "").slice(0, 10);
      locs.push(`<url><loc>https://meetlazo.com/w/${slug}/</loc>${lm ? `<lastmod>${lm}</lastmod>` : ""}</url>`);
    }
    pageToken = j.nextPageToken || "";
    if (!pageToken) break;
  }
  const xml = '<?xml version="1.0" encoding="UTF-8"?>\\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\\n'
    + locs.join("\\n") + "\\n</urlset>";
  r = new Response(xml, { headers: { "content-type": "application/xml; charset=utf-8",
    "cache-control": "public, max-age=3600, s-maxage=21600", "x-lazo-couples": String(locs.length) } });
  await caches.default.put(key, r.clone());
  return r;
}

async function renderCoupleSite(slug, env) {''')

rep('    const wMatch = url.pathname.match(/^\\/w\\/([a-z0-9\\-]{1,80})\\/?$/);',
    '    if (url.pathname === "/sitemap-couples.xml" && req.method === "GET") return couplesSitemap();\n'
    '    const wMatch = url.pathname.match(/^\\/w\\/([a-z0-9\\-]{1,80})\\/?$/);')

P.write_text(s, encoding="utf-8", newline="\n")
print("worker/src/index.js patched")
