// functions/api/geo.js (build JC-ATV-BOTGATE-0909-001) — lives in C:\Users\kurvh\atavia-site\functions\api\geo.js
// robocopy carries it into es-deploy; Cloudflare Pages serves it at /api/geo
//
// Returns where the visitor is, what network the request came from, and a bot verdict.
// esw-track.js uses the verdict to keep Meta's ad-link checks, link-preview fetchers and
// other non-people out of the visitor stats. Nothing here blocks anything: flagged visits
// are still written (bot:true, one doc, no trail) so the admin page can count them as hidden.

// Networks whose traffic is never a couple browsing. Meta's own servers — ad review,
// link-safety checks and in-app prefetch — all arrive as AS32934 (Facebook, Inc.).
const BOT_ASN = new Set([32934]);

// Cloud / hosting networks. Not a verdict on their own (a planner at a big company can sit
// behind one) — the tracker only uses `dc` to refuse the "sat still for 8s" fallback, so a
// visitor from one of these still counts the moment they scroll or tap.
const HOSTING_ASN = new Set([
  15169, 396982,        // Google LLC, Google Cloud
  16509, 14618,         // Amazon / AWS
  8075,                 // Microsoft / Azure
  14061,                // DigitalOcean
  24940,                // Hetzner
  16276,                // OVH
  63949,                // Linode
  20473,                // Vultr / Choopa
  31898,                // Oracle Cloud
  45102, 132203,        // Alibaba, Tencent
]);
const HOSTING_RE = /amazon|aws|google llc|google cloud|microsoft|azure|digitalocean|hetzner|ovh|linode|vultr|choopa|oracle|alibaba|tencent|contabo|leaseweb|m247|datacamp|hostinger|godaddy|ionos|scaleway/i;

// Fetchers that execute JavaScript. esw-track.js already skips these client-side; this is
// belt-and-braces for anything that reaches /api/geo some other way.
const BOT_UA = /bot|crawl|spider|slurp|facebookexternalhit|facebot|meta-externalagent|headlesschrome|phantomjs|lighthouse|preview|python-requests|curl\/|wget\//i;

export function onRequestGet({ request }) {
  const cf = request.cf || {};
  const ua = request.headers.get('user-agent') || '';
  const asn = Number(cf.asn) || null;
  const org = cf.asOrganization || null;

  let why = null;
  if (asn && BOT_ASN.has(asn)) why = 'meta network';
  else if (cf.verifiedBotCategory) why = 'verified bot: ' + cf.verifiedBotCategory;
  else if (BOT_UA.test(ua)) why = 'crawler user-agent';

  const dc = !why && ((asn && HOSTING_ASN.has(asn)) || (org ? HOSTING_RE.test(org) : false));

  return new Response(JSON.stringify({
    city: cf.city || null,
    region: cf.regionCode || cf.region || null,
    country: cf.country || null,
    lat: cf.latitude ? Number(cf.latitude) : null,
    lng: cf.longitude ? Number(cf.longitude) : null,
    asn: asn,
    org: org,
    dc: !!dc,
    bot: !!why,
    why: why,
  }), { headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
}
