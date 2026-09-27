"""patch_unfurl.py - JC-LAZO-UNFURL-0920-001
GET /api/unfurl?u=<page url> -> {image, title, site, url}. The couple app's
dream board pastes a Pinterest pin, an Etsy listing, a blog post, anything,
and this turns it into the picture and a caption by reading the page's
og:image / twitter:image / og:title. Direct image URLs come straight back.
Cached a day at the edge; CORS open so Flutter web can call it. Refuses to
run twice.
  python worker\\patch_unfurl.py
"""
from pathlib import Path

P = Path(__file__).resolve().parent / "src" / "index.js"
s = P.read_text(encoding="utf-8")
if "JC-LAZO-UNFURL-0920-001" in s:
    raise SystemExit("already applied")


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"anchor {old[:70]!r}: found {n}, wanted {count}")
    s = s.replace(old, new)


rep('    if (url.pathname === "/api/nearby") return nearbyPlaces(url, env);',
    '    if (url.pathname === "/api/unfurl" && req.method === "GET") return unfurl(url);\n'
    '    if (url.pathname === "/api/nearby") return nearbyPlaces(url, env);')

rep("// JC-LAZO-WWSEO-0919-010: /api/couples?q=<name> for the /couples/ search page.",
    r'''// JC-LAZO-UNFURL-0920-001: a page URL -> its picture and title, for the dream board.
const UNFURL_UA = "Mozilla/5.0 (compatible; LazoBot/1.0; +https://meetlazo.com) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36";
async function unfurl(url) {
  const headers = { "content-type": "application/json", "access-control-allow-origin": "*", "cache-control": "public, max-age=86400" };
  const raw = String(url.searchParams.get("u") || "").trim();
  let target;
  try { target = new URL(raw); } catch (e) { return new Response(JSON.stringify({ error: "bad url" }), { status: 400, headers }); }
  if (target.protocol !== "https:" && target.protocol !== "http:") return new Response(JSON.stringify({ error: "bad url" }), { status: 400, headers });
  if (/^(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(target.hostname)) return new Response(JSON.stringify({ error: "bad url" }), { status: 400, headers });
  const key = new Request("https://meetlazo.com/_unfurl/" + encodeURIComponent(target.href));
  const hit = await caches.default.match(key);
  if (hit) return hit;
  // A direct image needs no page.
  if (/\.(jpe?g|png|webp|gif|avif)(\?|$)/i.test(target.pathname + target.search)) {
    const r = new Response(JSON.stringify({ image: target.href, title: "", site: target.hostname.replace(/^www\./, ""), url: target.href }), { headers });
    await caches.default.put(key, r.clone());
    return r;
  }
  let html = "";
  let finalUrl = target.href;
  try {
    const rr = await fetch(target.href, { headers: { "user-agent": UNFURL_UA, accept: "text/html,*/*" }, redirect: "follow", cf: { cacheTtl: 3600 } });
    finalUrl = rr.url || finalUrl;
    const ct = rr.headers.get("content-type") || "";
    if (/^image\//i.test(ct)) {
      const r = new Response(JSON.stringify({ image: finalUrl, title: "", site: target.hostname.replace(/^www\./, ""), url: finalUrl }), { headers });
      await caches.default.put(key, r.clone());
      return r;
    }
    html = (await rr.text()).slice(0, 400000);
  } catch (e) {
    return new Response(JSON.stringify({ error: "fetch failed" }), { status: 502, headers });
  }
  const meta = (names) => {
    for (const n of names) {
      const m = html.match(new RegExp(`<meta[^>]+(?:property|name)=["']${n}["'][^>]*content=["']([^"']+)["']`, "i"))
        || html.match(new RegExp(`<meta[^>]+content=["']([^"']+)["'][^>]*(?:property|name)=["']${n}["']`, "i"));
      if (m && m[1]) return m[1].replace(/&amp;/g, "&").replace(/&#x27;|&#39;/g, "'").replace(/&quot;/g, '"').trim();
    }
    return "";
  };
  let image = meta(["og:image:secure_url", "og:image", "twitter:image", "twitter:image:src"]);
  if (!image) {
    const m = html.match(/<link[^>]+rel=["']image_src["'][^>]*href=["']([^"']+)["']/i);
    if (m) image = m[1];
  }
  if (image && !/^https?:/i.test(image)) { try { image = new URL(image, finalUrl).href; } catch (e) { image = ""; } }
  let title = meta(["og:title", "twitter:title"]);
  if (!title) { const m = html.match(/<title[^>]*>([^<]{1,200})<\/title>/i); if (m) title = m[1].trim(); }
  title = title.replace(/\s+/g, " ").slice(0, 140);
  const site = meta(["og:site_name"]) || target.hostname.replace(/^www\./, "");
  const r = new Response(JSON.stringify({ image, title, site, url: finalUrl }), { headers });
  await caches.default.put(key, r.clone());
  return r;
}

// JC-LAZO-WWSEO-0919-010: /api/couples?q=<name> for the /couples/ search page.''')

P.write_text(s, encoding="utf-8", newline="\n")
print("worker/src/index.js patched (/api/unfurl)")
