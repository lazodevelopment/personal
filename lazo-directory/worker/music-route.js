// JC-LAZO-WORKER-0912-MUSIC-001
// Drop into the lazo-directory Cloudflare Worker (meetlazo.com), next to the
// /icon/<host> route. Proxies the iTunes Search API for the couple app's
// Music page so results are cached at the edge and never rate-limited per
// couple. No key, no auth. The widget falls back to itunes.apple.com
// directly if this route is missing, so it is an optimisation, not a
// dependency.
//
//   if (url.pathname === '/music/search') return musicSearch(url, ctx);

async function musicSearch(url, ctx) {
  const q = (url.searchParams.get('q') || '').trim().slice(0, 120);
  const cors = {
    'content-type': 'application/json; charset=utf-8',
    'access-control-allow-origin': '*',
    'cache-control': 'public, max-age=86400',
  };
  if (q.length < 2) return new Response('{"results":[]}', { headers: cors });
  const cache = caches.default;
  const key = new Request('https://meetlazo.com/music/search?q=' + encodeURIComponent(q.toLowerCase()));
  let res = await cache.match(key);
  if (res) return res;
  const up = await fetch(
    'https://itunes.apple.com/search?term=' + encodeURIComponent(q) + '&entity=song&limit=25&country=US',
    { headers: { accept: 'application/json' }, cf: { cacheTtl: 86400 } }
  );
  if (!up.ok) return new Response('{"results":[]}', { status: 502, headers: cors });
  res = new Response(await up.text(), { headers: cors });
  ctx.waitUntil(cache.put(key, res.clone()));
  return res;
}
