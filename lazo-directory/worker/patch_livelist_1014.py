r"""patch_livelist_1014.py - JC-LAZO-LIVELIST-1014
A claimed vendor the nightly build has not reached yet is missing from their
city's category list. On a category page the worker now asks Firestore for
the claimed vendors in that metro (cached a minute per isolate) and adds a
card for any that are not on the page, at the top with the other claimed
vendors. The card is the same markup category.html renders.
"""
from pathlib import Path

P = Path(__file__).resolve().parent / "src" / "index.js"
s = P.read_text(encoding="utf-8")
TAG = "JC-LAZO-LIVELIST-1014"
if TAG in s:
    raise SystemExit("already patched")


def rep(old, new):
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"anchor found {n}x: {old[:70]!r}")
    s = s.replace(old, new)


rep("""    const ext = key.split(".").pop();
    const cache = key.startsWith("assets/")""", """    // JC-LAZO-LIVELIST-1014: claimed vendors newer than the build join their list now
    const lm = key.match(/^([a-z0-9-]+)\\/([a-z0-9-]+)\\/index\\.html$/);
    if (lm && LIVE_CATS.has(lm[2])) {
      const out = await liveList(lm[1], lm[2], obj);
      if (out) return withTracker(req, withRegion(req, out));
      if (obj.bodyUsed) obj = await env.SITE.get(key);   // the body was read; fetch it again
    }
    const ext = key.split(".").pop();
    const cache = key.startsWith("assets/")""")

rep("""// JC-LAZO-LIVEPAGE-1014: the vendor page for a listing the nightly build has not""", r"""// JC-LAZO-LIVELIST-1014: category lists that include vendors approved today.
const LIVE_CATS = new Set(["wedding-photographers", "wedding-videographers", "wedding-venues", "wedding-planners",
  "wedding-djs", "wedding-florists", "wedding-caterers", "wedding-cakes", "hair-and-makeup", "wedding-officiants",
  "wedding-transportation", "wedding-rentals", "wedding-bands", "wedding-invitations", "day-of-coordination"]);
const _claimedByMetro = new Map();   // metro -> {at, list}
async function claimedIn(metro) {
  const c = _claimedByMetro.get(metro);
  if (c && Date.now() - c.at < 60000) return c.list;
  const docs = await fsRunQuery({ from: [{ collectionId: "vendors" }],
    where: { compositeFilter: { op: "AND", filters: [
      { fieldFilter: { field: { fieldPath: "metroId" }, op: "EQUAL", value: { stringValue: metro } } },
      { fieldFilter: { field: { fieldPath: "claimStatus" }, op: "EQUAL", value: { stringValue: "claimed" } } }] } },
    limit: 300 });
  const list = docs.map((d) => {
    const f = d.fields || {}, g = (k) => fsVal(f[k]);
    return { id: d.name.split("/").pop(), name: String(g("name") || ""), slug: String(g("slug") || ""),
      cats: g("categories") || [], delisted: g("delisted") === true, verified: g("verified") === true,
      bio: String(g("bio") || ""), address: String(g("address") || ""), website: String(g("website") || ""),
      thumb: String(g("coverUrl") || (g("gallery") || [])[0] || g("logoUrl") || ""), price: String(g("priceRangeDisplay") || "") };
  }).filter((v) => v.name && v.slug && !v.delisted);
  _claimedByMetro.set(metro, { at: Date.now(), list });
  return list;
}
async function liveList(metro, cat, obj) {
  let list;
  try { list = (await claimedIn(metro)).filter((v) => v.cats.includes(cat)); } catch (e) { return null; }
  if (!list.length) return null;
  let html = await obj.text();
  const missing = list.filter((v) => !html.includes(`href="/${metro}/${cat}/${v.slug}/"`));
  if (!missing.length) return new Response(html, { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "public, max-age=60, s-maxage=60", "x-lazo": "live-list" } });
  const e = (t) => String(t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const cards = missing.map((v) => {
    const bio = v.bio.replace(/\s+/g, " ").trim();
    const snip = bio.length > 140 ? bio.slice(0, 137).replace(/\s+\S*$/, "") + "…" : bio;
    const city = (v.address.split(",").map((x) => x.trim())[1] || v.address).replace(/\s+\d{5}.*$/, "");
    const thumb = /^https:\/\//.test(v.thumb)
      ? `<span class="vc2-thumb" style="background-image:url('${e(v.thumb)}')" aria-hidden="true"></span>`
      : `<span class="vc2-thumb" style="background-image:linear-gradient(135deg,rgba(61,28,59,.66),rgba(82,40,79,.45)),url('/assets/photos/${cat}.jpg')" aria-hidden="true"></span>`;
    return `<li class="vendor-card vc2 vc2-claimed" data-search="${e((v.name + " " + v.address).toLowerCase())}" data-styles="" data-sde="0" data-drone="0" data-film="0" data-lead="" data-lgbtq="0" data-set="" data-catering="0" data-byo="0" data-cerrec="0" data-lodging="0" data-pets="0">`
      + thumb + `<div class="vc2-main"><a class="vc2-name" href="/${metro}/${cat}/${e(v.slug)}/">${e(v.name)}</a>`
      + `<p class="vc2-meta"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#D9B77C" stroke-width="2.4"><path d="M12 21s-7-6.1-7-11a7 7 0 1 1 14 0c0 4.9-7 11-7 11z"/><circle cx="12" cy="10" r="2.6"/></svg> ${e(city)}${v.website ? " &nbsp;&middot;&nbsp; Has website" : ""}</p>`
      + (snip ? `<p class="vc2-bio">&ldquo;${e(snip)}&rdquo;</p>` : "")
      + `<div class="vc2-chips">${v.verified ? '<span class="ch-ver">&#10022; LAZO VERIFIED</span>' : ""}${v.price ? `<span class="ch-price">${e(v.price)}</span>` : ""}</div></div>`
      + `<span class="vc2-go" aria-hidden="true">&rarr;</span></li>`;
  }).join("");
  const at = html.indexOf('<ol class="vendor-list" id="vlist">');
  if (at < 0) return null;
  const pos = at + '<ol class="vendor-list" id="vlist">'.length;
  html = html.slice(0, pos) + cards + html.slice(pos);
  return new Response(html, { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "public, max-age=60, s-maxage=60", "x-lazo": "live-list" } });
}

// JC-LAZO-LIVEPAGE-1014: the vendor page for a listing the nightly build has not""")

P.write_text(s, encoding="utf-8", newline="\n")
print("patched")
