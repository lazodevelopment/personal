// worker/src/track.js — JC-LAZO-TRACK-0916-001
//
// First-party visitor analytics for meetlazo.com, mirroring what
// admin.ataviaweddings.com runs (atv-track.js + /api/geo).
//
// Atavia ships its tracker from the page templates. Lazo can't: a <script> tag
// in base.html changes all ~72k built pages and forces a full rebuild + R2
// re-upload for every tweak. The Worker already rewrites HTML on the way out
// (that's how withGeo injects window.LAZO_GEO), so the tracker is injected
// there instead — one `wrangler deploy` to roll out, one to roll back, and the
// built site never has to know it exists.
//
// Three exports, wired in index.js:
//   geoResponse(req)          -> GET /api/geo          (location + bot verdict)
//   trackerResponse(req)      -> GET /assets/lazo-track.js
//   withTracker(req, resp)    -> appends the <script> tag to any HTML response
//
// Nothing here blocks anything. Visits that look like bots are still written
// (bot:true, one doc, no page trail) so God Mode can count what it hid.

import { METROS } from "./geo.js";

/* ============================================================
   /api/geo — where the visitor is, what network they came from,
   and whether they look like a person. Same shape as Atavia's
   Pages Function so the two trackers stay interchangeable.
   ============================================================ */

// Meta's own servers — ad review, link-safety checks, in-app prefetch — all
// arrive as AS32934. None of it is a couple browsing.
const BOT_ASN = new Set([32934]);

// Cloud / hosting networks. Not a verdict on their own (a planner at a big
// company can sit behind one); the tracker only uses `dc` to refuse the
// "sat still for 8s" fallback, so a real visitor still counts the moment
// they scroll or tap.
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

// Fetchers that execute JavaScript. The tracker already skips these client-side;
// this is belt-and-braces for anything reaching /api/geo another way.
const BOT_UA = /bot|crawl|spider|slurp|facebookexternalhit|facebot|meta-externalagent|headlesschrome|phantomjs|lighthouse|preview|python-requests|curl\/|wget\//i;

export function geoResponse(request) {
  const cf = request.cf || {};
  const ua = request.headers.get("user-agent") || "";
  const asn = Number(cf.asn) || null;
  const org = cf.asOrganization || null;

  let why = null;
  if (asn && BOT_ASN.has(asn)) why = "meta network";
  else if (cf.verifiedBotCategory) why = "verified bot: " + cf.verifiedBotCategory;
  else if (BOT_UA.test(ua)) why = "crawler user-agent";

  const dc = !why && ((asn && HOSTING_ASN.has(asn)) || (org ? HOSTING_RE.test(org) : false));

  return new Response(JSON.stringify({
    city: cf.city || null,
    region: cf.regionCode || cf.region || null,
    country: cf.country || null,
    lat: cf.latitude ? Number(cf.latitude) : null,
    lng: cf.longitude ? Number(cf.longitude) : null,
    asn,
    org,
    dc: !!dc,
    bot: !!why,
    why,
  }), { headers: { "content-type": "application/json", "cache-control": "no-store" } });
}

/* ============================================================
   The tracker itself, served from the Worker.
   ============================================================ */

// Bumping this busts the browser + edge cache for the script.
export const TRACK_V = "0916-001";

const METRO_SLUGS = JSON.stringify(METROS.map(m => m[0]));

// ES5 on purpose: no build step, no template literals (this whole thing lives
// inside a template literal), and it has to run on whatever a guest is using.
const TRACKER = `/* lazo-track.js — visitor + session tracking for meetlazo.com (JC-LAZO-TRACK-${TRACK_V})
 * Injected by the Worker on every HTML response. Writes to Firestore over REST.
 *
 * A visit is only recorded once a person shows up. On the first page nothing is
 * written until the page is visible AND the visitor touches, scrolls, moves the
 * mouse or types — or, from an ordinary residential network with a known
 * location, simply stays for DWELL_MS. Prerenders, prefetches and open-and-close
 * loads never get that far. Meta's ad-link checks come back from /api/geo
 * flagged and are written once with bot:true and no trail, so God Mode can count
 * them as hidden. Later pages of a visit that already proved itself write
 * immediately — the navigation was the interaction.
 */
(function () {
  var PROJECT = 'lazo-513ec';
  var API_KEY = 'AIzaSyD2EdP1wD-DaaZdS9Cdc4rXv_QeL3XdxbU';   // public web key, same as God Mode's
  var BASE = 'https://firestore.googleapis.com/v1/projects/' + PROJECT + '/databases/(default)/documents';
  var DOC_BASE = 'projects/' + PROJECT + '/databases/(default)/documents';
  var HEARTBEAT_MS = 30000;
  var IDLE_MS = 15 * 60 * 1000;   // stop extending the visit after this long idle (tab left open)
  var DWELL_MS = 8000;            // visible this long with no interaction still counts, if the network looks human
  var MAX_HITS = 200;
  var METROS = ${METRO_SLUGS};

  var BOT = /bot|crawl|spider|slurp|lighthouse|facebookexternalhit|facebot|meta-externalagent|whatsapp|twitterbot|linkedinbot|pinterest|slackbot|discordbot|telegrambot|applebot|bingpreview|headlesschrome|phantomjs|petalbot|ahrefs|semrush|mj12|dataprovider|screaming frog|gtmetrix|pingdom|uptimerobot|preview|snapchat|skypeuripreview|embedly|quora link preview|outbrain|vkshare|w3c_validator|google-inspectiontool|chrome-lighthouse|yandex|baidu|duckduckbot|sogou|exabot|ia_archiver|archive\\.org/i;
  if (navigator.doNotTrack === '1' || BOT.test(navigator.userAgent) || navigator.webdriver) return;

  var stripQ = function (u) { return String(u || '').split('?')[0].split('#')[0]; };
  var qs = new URLSearchParams(location.search);

  // ---- which metro / vendor page this is, from the URL alone
  // /phoenix/                        -> metro: phoenix
  // /phoenix/photographers/          -> metro: phoenix
  // /phoenix/photographers/jane-doe/ -> metro: phoenix, vendor: jane-doe
  function parts() {
    var seg = location.pathname.split('/').filter(Boolean);
    var out = { metro: null, vendor: null };
    if (!seg.length) return out;
    if (METROS.indexOf(seg[0]) === -1) return out;
    out.metro = seg[0];
    if (seg.length >= 3) out.vendor = seg[2];
    return out;
  }

  // ---- session id (lives for the tab's lifetime)
  var sid = sessionStorage.getItem('lz_sid');
  if (!sid) {
    var a = new Uint8Array(12); crypto.getRandomValues(a);
    sid = Array.prototype.map.call(a, function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
    sessionStorage.setItem('lz_sid', sid);
  }
  window.lazoSid = sid;   // so the inquiry flow can stamp the visit that produced it

  // Landing page + referrer are whatever the FIRST page of the visit saw.
  if (!sessionStorage.getItem('lz_landing')) {
    sessionStorage.setItem('lz_landing', stripQ(location.pathname));
    sessionStorage.setItem('lz_referrer', document.referrer || 'direct');
  }

  var hitCount = parseInt(sessionStorage.getItem('lz_hits') || '0', 10);
  var engaged = sessionStorage.getItem('lz_engaged') || '';    // how the visit first proved itself
  var docExists = sessionStorage.getItem('lz_started') === '1';

  function S(v) { return { stringValue: String(v).slice(0, 500) }; }
  function I(v) { return { integerValue: String(v) }; }
  function clean(o) { var r = {}; for (var k in o) if (o[k] != null && o[k] !== '') r[k] = o[k]; return r; }

  function device() {
    var ua = navigator.userAgent;
    if (/iPad|Tablet/i.test(ua)) return 'tablet';
    if (/Mobi|Android|iPhone/i.test(ua)) return 'mobile';
    return 'desktop';
  }

  function send(path, body, beacon) {
    var url = BASE + path + (path.indexOf('?') > -1 ? '&' : '?') + 'key=' + API_KEY;
    var json = JSON.stringify(body);
    if (beacon && navigator.sendBeacon) {
      navigator.sendBeacon(url, new Blob([json], { type: 'application/json' }));
      return;
    }
    fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: json, keepalive: true }).catch(function () {});
  }

  // ---- geo + network + bot verdict (one call per session)
  function withGeo(cb) {
    var g = sessionStorage.getItem('lz_geo');
    if (g) { try { return cb(JSON.parse(g)); } catch (e) { /* refetch */ } }
    fetch('/api/geo').then(function (r) { return r.json(); }).then(function (j) {
      try { sessionStorage.setItem('lz_geo', JSON.stringify(j)); } catch (e) {}
      cb(j);
    }).catch(function () { cb({}); });
  }

  function upsertSession(geo, isNew, how, why) {
    var p = parts();
    var fields = clean({
      sid: S(sid),
      page: S(location.pathname),
      title: S(document.title),
      device: S(device()),
      ua: S(navigator.userAgent),
      screen: S(screen.width + 'x' + screen.height),
      lang: S(navigator.language),
      landing: S(sessionStorage.getItem('lz_landing') || stripQ(location.pathname)),
      referrer: S(sessionStorage.getItem('lz_referrer') || document.referrer || 'direct'),
      metro: p.metro ? S(p.metro) : null,
      vendor: p.vendor ? S(p.vendor) : null,
      city: geo.city ? S(geo.city) : null,
      region: geo.region ? S(geo.region) : null,
      country: geo.country ? S(geo.country) : null,
      lat: typeof geo.lat === 'number' ? { doubleValue: geo.lat } : null,
      lng: typeof geo.lng === 'number' ? { doubleValue: geo.lng } : null,
      asn: geo.asn ? I(geo.asn) : null,
      org: geo.org ? S(geo.org) : null,
      bot: { booleanValue: !!why },
      bot_why: why ? S(why) : null,
      engaged: S(how),
      utm_source: S(qs.get('utm_source') || (qs.get('fbclid') ? 'facebook/instagram' : '') || (/instagram/i.test(navigator.userAgent) ? 'instagram' : '') || ''),
      utm_campaign: qs.get('utm_campaign') ? S(qs.get('utm_campaign')) : null
    });
    // A field path in the mask with no value clears it — so a visit flagged on
    // one page and cleared on the next would lose its reason without this.
    var mask = Object.keys(fields).concat(why ? [] : ['bot_why']);
    var doc = DOC_BASE + '/sessions/' + sid;
    send(':commit', { writes: [
      { update: { name: doc, fields: fields }, updateMask: { fieldPaths: mask } },
      { transform: { document: doc, fieldTransforms: [
          { fieldPath: 'last_seen', setToServerValue: 'REQUEST_TIME' },
          { fieldPath: 'page_count', increment: { integerValue: '1' } }
        ].concat(isNew ? [{ fieldPath: 'first_seen', setToServerValue: 'REQUEST_TIME' }] : []) } }
    ] });
    try { sessionStorage.setItem('lz_started', '1'); } catch (e) {}
    docExists = true;
  }

  function hit() {
    if (hitCount >= MAX_HITS) return;
    hitCount++;
    try { sessionStorage.setItem('lz_hits', String(hitCount)); } catch (e) {}
    send('/sessions/' + sid + '/hits', {
      fields: { path: S(location.pathname), title: S(document.title), t: { timestampValue: new Date().toISOString() } }
    });
  }

  function heartbeat(beacon) {
    var doc = DOC_BASE + '/sessions/' + sid;
    send(':commit', { writes: [
      { update: { name: doc, fields: { page: S(location.pathname) } }, updateMask: { fieldPaths: ['page'] } },
      { transform: { document: doc, fieldTransforms: [{ fieldPath: 'last_seen', setToServerValue: 'REQUEST_TIME' }] } }
    ] }, beacon);
  }

  // ---- activity clock for the idle guard
  var lastActive = Date.now();
  var ACTIVITY = ['pointerdown', 'touchstart', 'keydown', 'wheel', 'scroll', 'pointermove'];
  ACTIVITY.forEach(function (t) { window.addEventListener(t, function () { lastActive = Date.now(); }, { capture: true, passive: true }); });

  var started = false;
  function start(how) {
    if (started) return; started = true;
    withGeo(function (geo) {
      var why = geo.bot ? (geo.why || 'bot')
              : (how === 'dwell' && geo.dc) ? 'no interaction, hosting network'
              : (how === 'dwell' && !geo.city) ? 'no interaction, no location'
              : null;
      upsertSession(geo, !docExists, how, why);
      if (why) return;   // flagged: one doc for the hidden count, no trail, gate again next page
      if (!engaged) { engaged = how; try { sessionStorage.setItem('lz_engaged', engaged); } catch (e) {} }
      hit();
      setInterval(function () {
        if (document.visibilityState === 'visible' && Date.now() - lastActive < IDLE_MS) heartbeat(false);
      }, HEARTBEAT_MS);
      document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden') heartbeat(true); });
      window.addEventListener('pagehide', function () { heartbeat(true); });
    });
  }

  // ---- gate: the first page of a visit has to show a person first
  function gate() {
    if (engaged) return start(engaged);
    var timer = null;
    var KIND = { pointerdown: 'tap', touchstart: 'touch', keydown: 'key', wheel: 'scroll', scroll: 'scroll', pointermove: 'mouse' };
    function onEvt(e) {
      if (e.type === 'pointermove' && e.pointerType !== 'mouse') return;  // touch "moves" are noise
      done(KIND[e.type] || 'touch');
    }
    function done(how) {
      clearTimeout(timer);
      ACTIVITY.forEach(function (t) { window.removeEventListener(t, onEvt, true); });
      document.removeEventListener('visibilitychange', arm);
      start(how);
    }
    function arm() {   // the dwell clock only runs while the page is on screen
      clearTimeout(timer);
      if (document.visibilityState === 'visible') timer = setTimeout(function () { done('dwell'); }, DWELL_MS);
    }
    ACTIVITY.forEach(function (t) { window.addEventListener(t, onEvt, { capture: true, passive: true }); });
    document.addEventListener('visibilitychange', arm);
    arm();
  }

  if (document.prerendering) document.addEventListener('prerenderingchange', gate, { once: true });
  else gate();
})();
`;

export function trackerResponse() {
  return new Response(TRACKER, {
    headers: {
      "content-type": "application/javascript; charset=utf-8",
      // Versioned via ?v= in the injected tag, so this can cache hard.
      "cache-control": "public, max-age=86400, s-maxage=604800",
      "access-control-allow-origin": "*",
    },
  });
}

/* ============================================================
   Injection — the same HTMLRewriter trick withGeo uses.
   ============================================================ */

const TAG = `<script defer src="/assets/lazo-track.js?v=${TRACK_V}"></script>`;

// Pages that must never phone home: the gallery passcode wall and anything
// under /w/ (a couple's own wedding site — their guests are not Lazo traffic).
const NO_TRACK = /^\/(w|gallery|galleries)\//;

export function withTracker(request, response) {
  try {
    const ct = response.headers.get("content-type") || "";
    if (!ct.includes("text/html")) return response;
    if (NO_TRACK.test(new URL(request.url).pathname)) return response;
    return new HTMLRewriter()
      .on("head", { element(el) { el.append(TAG, { html: true }); } })
      .transform(response);
  } catch (e) {
    return response;
  }
}
