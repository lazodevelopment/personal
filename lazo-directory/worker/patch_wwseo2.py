"""patch_wwseo2.py - JC-LAZO-WWSEO-0919-010
Worker: the seven new templates join TEMPLATES, and GET /api/couples?q= backs
the /couples/ search page (public, no-passcode sites, names substring match,
20 results). The couple list is fetched once and cached six hours; the
couples sitemap now reads the same list. Refuses to run twice.
  python worker\\patch_wwseo2.py
"""
from pathlib import Path

P = Path(__file__).resolve().parent / "src" / "index.js"
s = P.read_text(encoding="utf-8")
if "JC-LAZO-WWSEO-0919-010" in s:
    raise SystemExit("already applied")


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"anchor {old[:70]!r}: found {n}, wanted {count}")
    s = s.replace(old, new)


rep('const TEMPLATES = ["sage","noir","dune","fete","tide","flora","atelier","verona","shore","summit","ranch","starlit","frost"];',
    '// JC-LAZO-WWSEO-0919-010: harvest, aquarelle, prism, meadow, gilded, marigold, papel\n'
    'const TEMPLATES = ["sage","noir","dune","fete","tide","flora","atelier","verona","shore","summit","ranch","starlit","frost",\n'
    '                   "harvest","aquarelle","prism","meadow","gilded","marigold","papel"];')

# replace the sitemap's inline fetch with a shared, cached list
start = s.index("// JC-LAZO-WWSEO-0919-002: every public couple site, one sitemap.")
end = s.index("async function renderCoupleSite(slug, env) {")
s = s[:start] + '''// JC-LAZO-WWSEO-0919-010: every public couple site (no passcode, has names),
// fetched once from Firestore and cached six hours. Feeds the couples sitemap
// and the /couples/ search. Sites with a passcode never appear anywhere.
async function listPublicCouples() {
  const key = new Request("https://meetlazo.com/_internal/public-couples.json");
  const hit = await caches.default.match(key);
  if (hit) { try { return await hit.json(); } catch (e) {} }
  const out = [];
  let pageToken = "";
  for (let i = 0; i < 40; i++) {
    const u = `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/weddingSites`
      + "?pageSize=300&mask.fieldPaths=passcode&mask.fieldPaths=names&mask.fieldPaths=dateIso"
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
      const names = String(fsVal(f.names) || "").trim();
      if (!names) continue;
      out.push({ slug, names, dateIso: String(fsVal(f.dateIso) || ""), lm: String(d.updateTime || "").slice(0, 10) });
    }
    pageToken = j.nextPageToken || "";
    if (!pageToken) break;
  }
  await caches.default.put(key, new Response(JSON.stringify(out), {
    headers: { "content-type": "application/json", "cache-control": "public, max-age=21600" } }));
  return out;
}

// JC-LAZO-WWSEO-0919-002: every public couple site, one sitemap.
async function couplesSitemap() {
  const list = await listPublicCouples();
  const locs = list.map(c => `<url><loc>https://meetlazo.com/w/${c.slug}/</loc>${c.lm ? `<lastmod>${c.lm}</lastmod>` : ""}</url>`);
  const xml = '<?xml version="1.0" encoding="UTF-8"?>\\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\\n'
    + locs.join("\\n") + "\\n</urlset>";
  return new Response(xml, { headers: { "content-type": "application/xml; charset=utf-8",
    "cache-control": "public, max-age=3600, s-maxage=21600", "x-lazo-couples": String(locs.length) } });
}

// JC-LAZO-WWSEO-0919-010: /api/couples?q=<name> for the /couples/ search page.
async function couplesSearch(url) {
  const q = String(url.searchParams.get("q") || "").trim().toLowerCase().replace(/\\s+/g, " ");
  const headers = { "content-type": "application/json", "cache-control": "public, max-age=300", "access-control-allow-origin": "*" };
  if (q.length < 2 || q.length > 60) return new Response("[]", { headers });
  const list = await listPublicCouples();
  const words = q.split(" ").filter(Boolean);
  const hits = list.filter(c => { const n = c.names.toLowerCase(); return words.every(w => n.includes(w)); })
    .sort((a, b) => (b.dateIso || "").localeCompare(a.dateIso || ""))
    .slice(0, 20)
    .map(c => ({ slug: c.slug, names: c.names, dateIso: c.dateIso }));
  return new Response(JSON.stringify(hits), { headers });
}

''' + s[end:]

rep('    if (url.pathname === "/sitemap-couples.xml" && req.method === "GET") return couplesSitemap();',
    '    if (url.pathname === "/sitemap-couples.xml" && req.method === "GET") return couplesSitemap();\n'
    '    if (url.pathname === "/api/couples" && req.method === "GET") return couplesSearch(url);')

P.write_text(s, encoding="utf-8", newline="\n")
print("worker/src/index.js patched (templates + /api/couples)")
