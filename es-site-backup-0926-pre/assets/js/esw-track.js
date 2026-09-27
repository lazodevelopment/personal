/* esw-track.js — visitor + session tracking for elizabethscottweddings.com
 * Writes directly to Firestore over REST (no SDK). Include after site.js:
 *   <script src="/js/esw-track.js" defer></script>
 * Uses the atv_* sessionStorage keys that site.js already sets.
 */
(function () {
  var PROJECT = 'elizabeth-scott-738e5';      // same as admin's firebaseConfig.projectId
  var API_KEY = 'AIzaSyCGLuSg0vXbqKhzJwvbAYzTD7Lo17FbJ28';     // firebaseConfig.apiKey (public web key)
  var BASE = 'https://firestore.googleapis.com/v1/projects/' + PROJECT + '/databases/(default)/documents';
  var HEARTBEAT_MS = 30000;
  var MAX_HITS = 200;

  // Bots, link-preview fetchers (Facebook/Instagram/iMessage/Slack…), headless browsers and prerenders are not visitors.
  var BOT = /bot|crawl|spider|slurp|lighthouse|facebookexternalhit|facebot|whatsapp|twitterbot|linkedinbot|pinterest|slackbot|discordbot|telegrambot|applebot|bingpreview|headlesschrome|phantomjs|petalbot|ahrefs|semrush|mj12|dataprovider|screaming frog|gtmetrix|pingdom|uptimerobot|preview|snapchat|skypeuripreview|embedly|quora link preview|outbrain|vkshare|w3c_validator|google-inspectiontool|chrome-lighthouse|yandex|baidu|duckduckbot|sogou|exabot|ia_archiver|archive\.org/i;
  if (navigator.doNotTrack === '1' || BOT.test(navigator.userAgent) || navigator.webdriver) return;
  if (document.prerendering || document.visibilityState === 'prerender') return;
  var stripQ = function (u) { return String(u || '').split('?')[0].split('#')[0]; };

  // ---- session id (lives for the tab's lifetime, matches site.js sessionStorage scope)
  var sid = sessionStorage.getItem('atv_sid');
  if (!sid) {
    var a = new Uint8Array(12); crypto.getRandomValues(a);
    sid = Array.prototype.map.call(a, function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
    sessionStorage.setItem('atv_sid', sid);
  }
  window.atvSid = sid;
  var hitCount = parseInt(sessionStorage.getItem('atv_hits') || '0', 10);

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

  // ---- geo (one call per session) via Pages Function /api/geo
  function withGeo(cb) {
    var g = sessionStorage.getItem('atv_geo');
    if (g) return cb(JSON.parse(g));
    fetch('/api/geo').then(function (r) { return r.json(); }).then(function (j) {
      sessionStorage.setItem('atv_geo', JSON.stringify(j)); cb(j);
    }).catch(function () { cb({}); });
  }

  // ---- session upsert (commit with server timestamps + increment)
  function upsertSession(geo, isNew) {
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
      utm_source: S(new URLSearchParams(location.search).get('utm_source') || (new URLSearchParams(location.search).get('fbclid') ? 'facebook/instagram' : '') || (/instagram/i.test(navigator.userAgent) ? 'instagram' : '') || '')
    });
    var mask = Object.keys(fields);
    var writes = [{
      update: { name: BASE.replace(/^https:\/\/firestore\.googleapis\.com\/v1\//, '') + '/sessions/' + sid, fields: fields },
      updateMask: { fieldPaths: mask }
    }, {
      transform: {
        document: BASE.replace(/^https:\/\/firestore\.googleapis\.com\/v1\//, '') + '/sessions/' + sid,
        fieldTransforms: [
          { fieldPath: 'last_seen', setToServerValue: 'REQUEST_TIME' },
          { fieldPath: 'page_count', increment: { integerValue: '1' } }
        ].concat(isNew ? [{ fieldPath: 'first_seen', setToServerValue: 'REQUEST_TIME' }] : [])
      }
    }];
    send(':commit', { writes: writes });
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

  // ---- go
  withGeo(function (geo) {
    upsertSession(geo, hitCount === 0);
    hit();
  });

  setInterval(function () { if (document.visibilityState === 'visible') heartbeat(false); }, HEARTBEAT_MS);
  document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden') heartbeat(true); });
  window.addEventListener('pagehide', function () { heartbeat(true); });
})();
