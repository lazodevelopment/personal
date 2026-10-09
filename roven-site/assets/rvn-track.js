/* rvn-track.js — visitor + session tracking for rovenhr.com (JC-RVN-TRACK-1005-001)
 * Same tracker as meetlazo.com / elizabethscottweddings.com, so JARVIS reads all sites the same way.
 * Writes to Firestore over REST (sessions/{sid} + hits). A visit is only recorded once a person shows
 * up: visible page AND a touch, scroll, mouse move or key, or (ordinary residential network with a known
 * location) simply staying DWELL_MS. Prerenders, prefetches and bots never get that far; Meta's ad-link
 * checks are flagged by /api/geo and written once with bot:true and no trail.
 * Served as a static file from roven-site/assets/; injected into every page by functions/_middleware.js.
 */
(function () {
  var PROJECT = 'roven-7efea';
  var API_KEY = 'AIzaSyCO31iGs8W7R-vCZuHS2PhrFyjUhYxyehs';   // public web key (Firebase web app config)
  var BASE = 'https://firestore.googleapis.com/v1/projects/' + PROJECT + '/databases/(default)/documents';
  var DOC_BASE = 'projects/' + PROJECT + '/databases/(default)/documents';
  var HEARTBEAT_MS = 30000;
  var IDLE_MS = 15 * 60 * 1000;   // stop extending the visit after this long idle (tab left open)
  var DWELL_MS = 8000;            // visible this long with no interaction still counts, if the network looks human
  var MAX_HITS = 200;

  var BOT = /bot|crawl|spider|slurp|lighthouse|facebookexternalhit|facebot|meta-externalagent|whatsapp|twitterbot|linkedinbot|pinterest|slackbot|discordbot|telegrambot|applebot|bingpreview|headlesschrome|phantomjs|petalbot|ahrefs|semrush|mj12|dataprovider|screaming frog|gtmetrix|pingdom|uptimerobot|preview|snapchat|skypeuripreview|embedly|quora link preview|outbrain|vkshare|w3c_validator|google-inspectiontool|chrome-lighthouse|yandex|baidu|duckduckbot|sogou|exabot|ia_archiver|archive\.org/i;
  if (navigator.doNotTrack === '1' || BOT.test(navigator.userAgent) || navigator.webdriver) return;

  var stripQ = function (u) { return String(u || '').split('?')[0].split('#')[0]; };
  var qs = new URLSearchParams(location.search);

  // ---- session id (lives for the tab's lifetime)
  var sid = sessionStorage.getItem('rv_sid');
  if (!sid) {
    var a = new Uint8Array(12); crypto.getRandomValues(a);
    sid = Array.prototype.map.call(a, function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
    sessionStorage.setItem('rv_sid', sid);
  }
  window.rovenSid = sid;

  // Landing page + referrer are whatever the FIRST page of the visit saw.
  if (!sessionStorage.getItem('rv_landing')) {
    sessionStorage.setItem('rv_landing', stripQ(location.pathname));
    sessionStorage.setItem('rv_referrer', document.referrer || 'direct');
  }

  var hitCount = parseInt(sessionStorage.getItem('rv_hits') || '0', 10);
  var engaged = sessionStorage.getItem('rv_engaged') || '';    // how the visit first proved itself
  var docExists = sessionStorage.getItem('rv_started') === '1';

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
    var g = sessionStorage.getItem('rv_geo');
    if (g) { try { return cb(JSON.parse(g)); } catch (e) { /* refetch */ } }
    fetch('/api/geo').then(function (r) { return r.json(); }).then(function (j) {
      try { sessionStorage.setItem('rv_geo', JSON.stringify(j)); } catch (e) {}
      cb(j);
    }).catch(function () { cb({}); });
  }

  function upsertSession(geo, isNew, how, why) {
    var fields = clean({
      sid: S(sid),
      page: S(location.pathname),
      title: S(document.title),
      device: S(device()),
      ua: S(navigator.userAgent),
      screen: S(screen.width + 'x' + screen.height),
      lang: S(navigator.language),
      landing: S(sessionStorage.getItem('rv_landing') || stripQ(location.pathname)),
      referrer: S(sessionStorage.getItem('rv_referrer') || document.referrer || 'direct'),
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
    try { sessionStorage.setItem('rv_started', '1'); } catch (e) {}
    docExists = true;
  }

  function hit() {
    if (hitCount >= MAX_HITS) return;
    hitCount++;
    try { sessionStorage.setItem('rv_hits', String(hitCount)); } catch (e) {}
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
      if (!engaged) { engaged = how; try { sessionStorage.setItem('rv_engaged', engaged); } catch (e) {} }
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