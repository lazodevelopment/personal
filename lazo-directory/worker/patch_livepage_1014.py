r"""patch_livepage_1014.py - JC-LAZO-LIVEPAGE-1014
A vendor URL with no built page used to 404 until the nightly build (Olivia
Layne Studios, approved 2026-10-14, had no page). Now, on a miss, the worker
looks the vendor up in Firestore and serves the shell from
generate/live_shells.py with the vendor's name, id and slug in place; the
page's live hydration fills everything else. Misses are remembered for a
minute so stray URLs do not each cost a query.
"""
from pathlib import Path

P = Path(__file__).resolve().parent / "src" / "index.js"
s = P.read_text(encoding="utf-8")
TAG = "JC-LAZO-LIVEPAGE-1014"
if TAG in s:
    raise SystemExit("already patched")


def rep(old, new):
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"anchor found {n}x: {old[:70]!r}")
    s = s.replace(old, new)


rep("""    let obj = await env.SITE.get(key);
    if (!obj) {
      obj = await env.SITE.get("404.html");""", """    let obj = await env.SITE.get(key);
    // JC-LAZO-LIVEPAGE-1014: a vendor approved since the last build has a page now
    if (!obj && gm) {
      const live = await livePage(key, env);
      if (live) return withTracker(req, withRegion(req, live));
    }
    if (!obj) {
      obj = await env.SITE.get("404.html");""")

rep("""// JC-LAZO-WORKER-1014-PLUS-001: everything the couple adds beyond the basics.""", r"""// JC-LAZO-LIVEPAGE-1014: the vendor page for a listing the nightly build has not
// reached yet. key = "<metro>/<category>/<slug>/index.html".
const _liveMiss = new Map();   // key -> time of a recent "no such vendor"
async function fsRunQuery(structuredQuery) {
  const r = await fetch(`https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents:runQuery`, {
    method: "POST", headers: { ...(await fsHeaders()), "content-type": "application/json" },
    body: JSON.stringify({ structuredQuery }) });
  if (!r.ok) return [];
  return (await r.json()).filter((x) => x.document).map((x) => x.document);
}
async function livePage(key, env) {
  const m = key.match(/^([a-z0-9-]+)\/([a-z0-9-]+)\/([a-z0-9_-]+)\/index\.html$/);
  if (!m) return null;
  const [, metro, cat, slug] = m;
  const seen = _liveMiss.get(key);
  if (seen && Date.now() - seen < 60000) return null;
  const shell = await env.SITE.get(`_live/shell/${metro}/${cat}.html`);
  if (!shell) { _liveMiss.set(key, Date.now()); return null; }
  // the vendor: a hand-added listing by its id, else any vendor with this slug
  let id = null, f = null;
  const fits = (x) => {
    const g = (k) => fsVal(x[k]);
    if (g("delisted") === true) return false;
    if (!(g("categories") || []).includes(cat)) return false;
    return g("metroId") === metro || (g("serviceMetros") || []).includes(metro);
  };
  const manual = await fsDoc("vendors", `manual-${metro}-${slug}`);
  if (manual && fits(manual)) { id = `manual-${metro}-${slug}`; f = manual; }
  if (!f) {
    const docs = await fsRunQuery({ from: [{ collectionId: "vendors" }],
      where: { fieldFilter: { field: { fieldPath: "slug" }, op: "EQUAL", value: { stringValue: slug } } }, limit: 8 });
    const d = docs.find((x) => fits(x.fields || {}));
    if (d) { id = d.name.split("/").pop(); f = d.fields; }
  }
  if (!f) { _liveMiss.set(key, Date.now()); if (_liveMiss.size > 2000) _liveMiss.clear(); return null; }
  const name = String(fsVal(f.name) || "").trim() || "This vendor";
  const htmlEsc = (t) => t.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const jsEsc = (t) => JSON.stringify(t).slice(1, -1).replace(/</g, "\\u003c").replace(/>/g, "\\u003e").replace(/&/g, "\\u0026").replace(/'/g, "\\u0027");
  const fill = (part, esc) => part.replace(/ZZLZNAMEZZ/g, esc(name)).replace(/ZZLZIDZZ/g, id).replace(/zzlzslugzz/g, slug);
  let html = await shell.text();
  html = html.replace(/name=ZZLZNAMEZZ/g, "name=" + encodeURIComponent(name));
  // script blocks get JS escaping, everything else HTML escaping
  html = html.split(/(<script\b[^>]*>[\s\S]*?<\/script>)/i).map((p) => fill(p, p.startsWith("<script") ? jsEsc : htmlEsc)).join("");
  // the vendor's own words make a better description than the template's
  const bio = String(fsVal(f.bio) || "").replace(/\s+/g, " ").trim();
  if (bio) {
    const d = htmlEsc(bio.length > 158 ? bio.slice(0, 155).replace(/\s+\S*$/, "") + "\u2026" : bio);
    html = html.replace(/(<meta (?:name="description"|property="og:description"|name="twitter:description") content=")[^"]*"/g, `$1${d}"`);
  }
  const cover = String(fsVal(f.coverUrl) || "");
  if (/^https:\/\//.test(cover)) html = html.replace(/(<meta (?:property="og:image"|name="twitter:image") content=")[^"]*"/g, `$1${htmlEsc(cover)}"`);
  return new Response(html, { headers: {
    "content-type": "text/html; charset=utf-8",
    "cache-control": "public, max-age=60, s-maxage=60",
    "strict-transport-security": "max-age=31536000; includeSubDomains",
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
    "x-lazo": "live-page" } });
}

// JC-LAZO-WORKER-1014-PLUS-001: everything the couple adds beyond the basics.""")

P.write_text(s, encoding="utf-8", newline="\n")
print("patched")
