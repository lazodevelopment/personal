/* atv-track.js — visitor + session tracking for ataviaweddings.com  (build JC-ATV-BOTGATE-0909-001)
 * Writes directly to Firestore over REST (no SDK). Include after site.js:
 *   <script src="/assets/js/atv-track.js" defer></script>
 * Uses the atv_* sessionStorage keys that site.js already sets.
 *
 * A visit is only recorded once a person shows up. On the first page of a visit nothing is
 * written until the page is visible AND the visitor touches, scrolls, moves the mouse or
 * types — or, from an ordinary residential network with a known location, simply stays on
 * the page for DWELL_MS. Prerenders, prefetches and open-and-close loads never get that far.
 * Meta's ad-link checks (its servers open the landing URL, run the JavaScript and close
 * within seconds) come back from /api/geo flagged, and are written once with bot:true and
 * no trail so the admin page can count them as hidden. Later pages of a visit that has
 * already proved itself are written immediately.
 */
(function () {
  var PROJECT = 'atavia-c29cd';      // same as admin's firebaseConfig.projectId
  var API_KEY = 'AIzaSyDpvsTc354O8aNZoRJbMFpAReah_t0xTsQ';     // firebaseConfig.apiKey (public web key)
  var BASE = 'https://firestore.googleapis.com/v1/projects/' + PROJECT + '/databases/(default)/documents';
  var HEARTBEAT_MS = 30000;
  var IDLE_MS = 15 * 60 * 1000;      // stop extending the visit after this long with no activity (tab left open)
  var DWELL_MS = 8000;               // visible this long with no interaction still counts — if the network looks like a person's
  var MAX_HITS = 200;

  // Bots, link-preview fetchers (Facebook/Instagram/iMessage/Slack…), headless browsers and automation are not visitors.
  var BOT = /bot|crawl|spider|slurp|lighthouse|facebookexternalhit|facebot|meta-externalagent|whatsapp|twitterbot|linkedinbot|pinterest|slackbot|discordbot|telegrambot|applebot|bingpreview|headlesschrome|phantomjs|petalbot|ahrefs|semrush|mj12|dataprovider|screaming frog|gtmetrix|pingdom|uptimerobot|preview|snapchat|skypeuripreview|embedly|quora link preview|outbrain|vkshare|w3c_validator|google-inspectiontool|chrome-lighthouse|yandex|baidu|duckduckbot|sogou|exabot|ia_archiver|archive\.org/i;
  if (navigator.doNotTrack === '1' || BOT.test(navigator.userAgent) || navigator.webdriver) return;
  var stripQ = function (u) { return String(u || '').split('?')[0].split('#')[0]; };
  var qs = new URLSearchParams(location.search);

  // ---- session id (lives for the tab's lifetime, matches site.js sessionStorage scope)
  var sid = sessionStorage.getItem('atv_sid');
  if (!sid) {
    var a = new Uint8Array(12); crypto.getRandomValues(a);
    sid = Array.prototype.map.call(a, function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
    sessionStorage.setItem('atv_sid', sid);
  }
  window.atvSid = sid;
  var hitCount = parseInt(sessionStorage.getItem('atv_hits') || '0', 10);
  var engaged = sessionStorage.getItem('atv_engaged') || '';   // how this visit first proved itself ('' until it has)
  var docExists = sessionStorage.getItem('atv_started') === '1';

  // ---- helpers to build Firestore typed values
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

  // ---- geo + network + bot verdict (one call per session) via Pages Function /api/geo
  function withGeo(cb) {
    var g = sessionStorage.getItem('atv_geo');
    if (g) return cb(JSON.parse(g));
    fetch('/api/geo').then(function (r) { return r.json(); }).then(function (j) {
      sessionStorage.setItem('atv_geo', JSON.stringify(j)); cb(j);
    }).catch(function () { cb({}); });
  }

  // ---- session upsert (commit with server timestamps + increment)
  function upsertSession(geo, isNew, how, why) {
    var fields = clean({
      sid: S(sid),
      page: S(location.pathname),
      title: S(document.title),
      device: S(device()),
      ua: S(navigator.userAgent),
      screen: S(screen.width + 'x' + screen.height),
      lang: S(navigator.language),
      landing: S(stripQ(sessionStorage.getItem('atv_landing') || location.pathname)),
      referrer: S(sessionStorage.getItem('atv_referrer') || document.referrer || 'direct'),
      venue: sessionStorage.getItem('atv_venue') ? S(sessionStorage.getItem('atv_venue')) : null,
      venue_url: sessionStorage.getItem('atv_venue_url') ? S(sessionStorage.getItem('atv_venue_url')) : null,
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
    // A field path in the mask with no value clears it — so a visit flagged on one page and cleared on the next loses its reason.
    var mask = Object.keys(fields).concat(why ? [] : ['bot_why']);
    var doc = BASE.replace(/^https:\/\/firestore\.googleapis\.com\/v1\//, '') + '/sessions/' + sid;
    var writes = [{
      update: { name: doc, fields: fields },
      updateMask: { fieldPaths: mask }
    }, {
      transform: {
        document: doc,
        fieldTransforms: [
          { fieldPath: 'last_seen', setToServerValue: 'REQUEST_TIME' },
          { fieldPath: 'page_count', increment: { integerValue: '1' } }
        ].concat(isNew ? [{ fieldPath: 'first_seen', setToServerValue: 'REQUEST_TIME' }] : [])
      }
    }];
    send(':commit', { writes: writes });
    sessionStorage.setItem('atv_started', '1'); docExists = true;
  }

  function hit() {
    if (hitCount >= MAX_HITS) return;
    hitCount++; sessionStorage.setItem('atv_hits', String(hitCount));
    send('/sessions/' + sid + '/hits', {
      fields: { path: S(location.pathname), title: S(document.title), t: { timestampValue: new Date().toISOString() } }
    });
  }

  function heartbeat(beacon) {
    var doc = BASE.replace(/^https:\/\/firestore\.googleapis\.com\/v1\//, '') + '/sessions/' + sid;
    send(':commit', { writes: [
      { update: { name: doc, fields: { page: S(location.pathname) } }, updateMask: { fieldPaths: ['page'] } },
      { transform: { document: doc, fieldTransforms: [{ fieldPath: 'last_seen', setToServerValue: 'REQUEST_TIME' }] } }
    ] }, beacon);
  }

  // ---- activity clock for the idle guard (kept for the life of the page)
  var lastActive = Date.now();
  var ACTIVITY = ['pointerdown', 'touchstart', 'keydown', 'wheel', 'scroll', 'pointermove'];
  ACTIVITY.forEach(function (t) { window.addEventListener(t, function () { lastActive = Date.now(); }, { capture: true, passive: true }); });

  // ---- start: runs once per page, after the gate has passed
  var started = false;
  function start(how) {
    if (started) return; started = true;
    withGeo(function (geo) {
      var why = geo.bot ? (geo.why || 'bot')
              : (how === 'dwell' && geo.dc) ? 'no interaction, hosting network'
              : (how === 'dwell' && !geo.city) ? 'no interaction, no location'
              : null;
      upsertSession(geo, !docExists, how, why);
      if (why) return;                     // flagged: one doc for the admin's "hidden" count — no trail, no heartbeat, gate again next page
      if (!engaged) { engaged = how; sessionStorage.setItem('atv_engaged', engaged); }
      hit();
      setInterval(function () { if (document.visibilityState === 'visible' && Date.now() - lastActive < IDLE_MS) heartbeat(false); }, HEARTBEAT_MS);
      document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden') heartbeat(true); });
      window.addEventListener('pagehide', function () { heartbeat(true); });
    });
  }

  // ---- gate: the first page of a visit has to show a person before anything is written
  function gate() {
    if (engaged) return start(engaged);  // a later page of a visit that already proved itself — the navigation was the interaction
    var timer = null;
    var KIND = { pointerdown: 'tap', touchstart: 'touch', keydown: 'key', wheel: 'scroll', scroll: 'scroll', pointermove: 'mouse' };
    function onEvt(e) {
      if (e.type === 'pointermove' && e.pointerType !== 'mouse') return;   // touch "moves" are noise; touchstart covers phones
      done(KIND[e.type] || 'touch');
    }
    function done(how) {
      clearTimeout(timer);
      ACTIVITY.forEach(function (t) { window.removeEventListener(t, onEvt, true); });
      document.removeEventListener('visibilitychange', arm);
      start(how);
    }
    function arm() {                     // the dwell clock only runs while the page is actually on screen
      clearTimeout(timer);
      if (document.visibilityState === 'visible') timer = setTimeout(function () { done('dwell'); }, DWELL_MS);
    }
    ACTIVITY.forEach(function (t) { window.addEventListener(t, onEvt, { capture: true, passive: true }); });
    document.addEventListener('visibilitychange', arm);
    arm();
  }

  // Chrome prerenders (speculation rules / address-bar prerender) become real visits only when activated.
  if (document.prerendering) document.addEventListener('prerenderingchange', gate, { once: true });
  else gate();
})();
