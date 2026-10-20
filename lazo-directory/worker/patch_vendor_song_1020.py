r"""patch_vendor_song_1020.py - JC-LAZO-VSONG-1020-001: a vendor's storefront song.

Adds GET /music/song?v=<vendorId> to the lazo-site worker: reads vendors/{id}.song
({title, artist, art, trackId, preview, autoplay, loop} - the same map the couple
sites keep in weddingSites.song), resolves it through siteSong() (Deezer ids are
refreshed to a live clip, every clip goes through /music/preview for CORS) and
answers JSON with CORS. lazo.js mounts the player on the storefront from it.

    python worker\patch_vendor_song_1020.py
"""
from pathlib import Path

p = Path(__file__).resolve().parent / "src" / "index.js"
s = p.read_text(encoding="utf-8")
TAG = "JC-LAZO-VSONG-1020-001"
assert TAG not in s, "already patched"

route_anchor = '    if (url.pathname === "/music/search") return musicSearch(url);\n'
assert s.count(route_anchor) == 1
s = s.replace(route_anchor, route_anchor +
    '    if (url.pathname === "/music/song") return vendorSong(url);  // ' + TAG + '\n')

fn_anchor = "\n// JC-LAZO-GALLERY-0912-006: passcode compared as sha256"
assert s.count(fn_anchor) == 1
fn = r'''
// JC-LAZO-VSONG-1020-001: a vendor's storefront song. vendors/{id}.song holds the
// same map the couple sites keep (title, artist, art, trackId, preview, autoplay,
// loop); the storefront's lazo.js asks here so the clip is live (Deezer links
// expire) and carries CORS. Cached five minutes per vendor, so a song picked in
// the app plays on the storefront within minutes.
async function vendorSong(url) {
  const id = (url.searchParams.get("v") || "").trim();
  const h = { "content-type": "application/json; charset=utf-8", "access-control-allow-origin": "*", "cache-control": "public, max-age=300" };
  if (!/^[A-Za-z0-9_-]{1,120}$/.test(id)) return new Response('{"song":null}', { status: 400, headers: { ...h, "cache-control": "no-store" } });
  const key = new Request("https://meetlazo.com/music/song?v=" + encodeURIComponent(id), { method: "GET" });
  const hit = await caches.default.match(key);
  if (hit) return hit;
  let song = null;
  try {
    const f = await fsDoc("vendors", id);
    if (f && fsVal(f.delisted) !== true) song = await siteSong(fsVal(f.song));
  } catch (e) {}
  const res = new Response(JSON.stringify({ song }), { headers: h });
  await caches.default.put(key, res.clone());
  return res;
}
'''
s = s.replace(fn_anchor, fn + fn_anchor)
p.write_text(s, encoding="utf-8")
print("patched", p)
