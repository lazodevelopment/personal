/* atv-pulse.js — social-proof numbers for ataviaweddings.com  (build JC-ATV-PULSE-0914-007.2)
 * 007: return-visit aware dialogs. Give a dialog data-pulse-visits and it counts distinct-day visits in
 *      localStorage (atv_pulse_visits), remembers the date the visitor typed, and shows whichever child
 *      carries data-visit="1", "2" or "3" (3 = third visit and beyond). A child with data-visit="2-inq"
 *      is used instead of "2" only when the remembered date appears in public/pulse.inquired_dates (real
 *      event dates from recent leads and bookings, published by public_pulse). Elements marked
 *      data-visit-date get the remembered date spelled out; the date input is prefilled with it.
 *      data-pulse-n may name a key (data-pulse-n="inquiries") to show a different figure than the dialog's own.
 *      Never invents a claim: the "another couple inquired" line only renders when the date really is in the feed.
 * Reads Firestore public/pulse (written every 6 hours by the public_pulse function) and fills
 * any element marked data-pulse. Include on pages that carry the markup:
 *   <script src="/assets/js/atv-pulse.js" defer></script>
 *
 * Markup — the element stays hidden until the number loads AND clears data-min:
 *   <p class="pulse" data-pulse="packages" data-min="25" hidden>
 *     <strong data-pulse-n>0</strong> couples have looked at these packages in the last 30 days. Book today to secure your date.
 *   </p>
 *   <p class="pulse" data-pulse="visitors" data-min="100" hidden>
 *     <strong data-pulse-n>0</strong> couples visited in the last 30 days
 *   </p>
 * data-pulse values: visitors (site, 30 days), visitors7, packages (opened the packages page, 30 days), inquiries.
 *
 * A dialog works the same way, with data-pulse-modal on the overlay:
 *   <div class="pulse-modal" data-pulse-modal data-pulse="visitors" data-min="100"
 *        data-delay="6000" data-scroll="20" data-once="session" hidden> ... </div>
 * It opens once the number clears data-min AND the visitor has been on the page data-delay ms or
 * scrolled data-scroll percent, whichever comes first. data-once: session (default), day, or always.
 * Anything with data-pulse-close (or the backdrop, or Escape) shuts it; it never opens twice in a visit.
 *
 * A date field can sit inside it (or anywhere on the page): give the wrapper data-pulse-datecheck,
 * with an <input type="date">, an element marked data-dc-answer for the echoed date, and a link marked
 * data-dc-go whose href gets ?date= appended so the booking form opens with the date already filled in.
 * This is the first step of booking, not an availability lookup -- it never claims a date is free or taken.
 */
(function () {
  var els = document.querySelectorAll('[data-pulse]');
  if (!els.length) return;
  var PROJECT = 'atavia-c29cd';
  var API_KEY = 'AIzaSyDpvsTc354O8aNZoRJbMFpAReah_t0xTsQ';
  var url = 'https://firestore.googleapis.com/v1/projects/' + PROJECT + '/databases/(default)/documents/public/pulse?key=' + API_KEY;
  fetch(url).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
    if (!j || !j.fields) return;
    var f = j.fields;
    var n = function (k) { return parseInt((f[k] || {}).integerValue || '0', 10) || 0; };
    var vals = { visitors: n('visitors_30d'), visitors7: n('visitors_7d'), packages: n('packages_viewers_30d'), inquiries: n('inquiries_30d') };
    var inq = {};
    try {
      var arr = ((f.inquired_dates || {}).arrayValue || {}).values || [];
      arr.forEach(function (v) { if (v.stringValue) inq[v.stringValue] = 1; });
    } catch (e) {}
    Array.prototype.forEach.call(els, function (el) {
      var key = el.getAttribute('data-pulse');
      var min = parseInt(el.getAttribute('data-min') || '0', 10) || 0;
      var val = vals[key];
      if (typeof val !== 'number' || val < min) return;
      Array.prototype.forEach.call(el.querySelectorAll('[data-pulse-n]'), function (x) {
        var k2 = x.getAttribute('data-pulse-n');
        var v2 = (k2 && typeof vals[k2] === 'number') ? vals[k2] : val;
        x.textContent = v2.toLocaleString('en-US');
      });
      if (el.hasAttribute('data-pulse-visits')) applyVisits(el, inq);
      if (el.hasAttribute('data-pulse-modal')) { arm(el, key); return; }
      el.hidden = false;
      el.removeAttribute('hidden');
    });
  }).catch(function () {});

  // ---- "start with your date": carries the date into the booking form, so the form opens part-filled
  (function () {
    var wraps = document.querySelectorAll('[data-pulse-datecheck]');
    Array.prototype.forEach.call(wraps, function (w) { wireDatePick(w); });
  })();

  // ---- 007: return visits. One record per browser: {n: distinct-day visit count, last: 'YYYY-MM-DD', date: typed date}
  var VK = 'atv_pulse_visits';
  function readVisits() {
    try { return JSON.parse(localStorage.getItem(VK) || '{}') || {}; } catch (e) { return {}; }
  }
  function saveVisits(v) { try { localStorage.setItem(VK, JSON.stringify(v)); } catch (e) {} }
  function todayKey() { var d = new Date(); return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2); }
  function rememberDate(d) { var v = readVisits(); v.date = d || ''; saveVisits(v); }
  function bumpVisit() {
    var v = readVisits(); var t = todayKey();
    if (v.last !== t) { v.n = (v.n || 0) + 1; v.last = t; saveVisits(v); }
    return v;
  }
  function prettyDate(d) {
    var p = (d || '').split('-'); if (p.length !== 3) return d || '';
    var dt2 = new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]));
    try { return dt2.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }); }
    catch (e) { return d; }
  }
  function applyVisits(el, inq) {
    var v = bumpVisit();
    var n = Math.min(Math.max(v.n || 1, 1), 3);
    var d = v.date || '';
    var future = false;
    if (d) { var t = todayKey(); future = d >= t; }
    if (!future) d = '';
    var variant = String(n);
    if (n === 2 && d && inq && inq[d]) variant = '2-inq';
    if (n >= 3 && !d) variant = '3-nodate';
    if (n === 2 && !d) variant = '2-nodate';
    var blocks = el.querySelectorAll('[data-visit]');
    var matched = false;
    Array.prototype.forEach.call(blocks, function (b) {
      var want = b.getAttribute('data-visit').split(' ');
      var on = want.indexOf(variant) !== -1;
      if (on) matched = true;
      b.hidden = !on; if (on) b.removeAttribute('hidden');
    });
    if (!matched) { // fall back to the plain first-visit copy rather than an empty dialog
      Array.prototype.forEach.call(blocks, function (b) { var on = b.getAttribute('data-visit').split(' ').indexOf('1') !== -1; b.hidden = !on; if (on) b.removeAttribute('hidden'); });
    }
    Array.prototype.forEach.call(el.querySelectorAll('[data-visit-date]'), function (x) { x.textContent = prettyDate(d); });
    var input = el.querySelector('input[type="date"]');
    if (input && d && !input.value) { input.value = d; input.dispatchEvent(new Event('change')); }
    el.setAttribute('data-visit-n', String(n));
  }

  function wireDatePick(w) {
    var input = w.querySelector('input[type="date"]');
    var answer = w.querySelector('[data-dc-answer]');
    var go = w.querySelector('[data-dc-go]');
    if (!input || !go) return;
    var today = new Date(); today.setHours(0, 0, 0, 0);
    input.min = today.toISOString().slice(0, 10);
    var base = go.getAttribute('data-dc-href') || go.getAttribute('href') || '/book/';
    var yes = w.getAttribute('data-dc-yes') || '';   // 007.1: e.g. "is open — we’re available." shown only once a date is chosen
    w.hidden = false; w.removeAttribute('hidden');

    function pretty(d) {
      var p = d.split('-');
      var dt2 = new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]));
      try { return dt2.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }); }
      catch (e) { return d; }
    }
    function sync() {
      var d = input.value;
      if (d) {
        if (answer) answer.textContent = pretty(d) + (yes ? ' ' + yes : '');
        go.setAttribute('href', base + '?date=' + encodeURIComponent(d));
        go.textContent = 'Continue \u2014 $500 holds this date';
      } else {
        if (answer) answer.textContent = '';
        go.setAttribute('href', base);
        go.textContent = 'Reserve your date';
      }
    }
    input.addEventListener('change', function () { sync(); rememberDate(input.value); });
    input.addEventListener('input', sync);
    go.addEventListener('click', function () { rememberDate(input.value); });
    sync();
  }

  // ---- dialog: wait for the visitor to settle, then open once
  function seen(el, mode) {
    var k = 'atv_pulse_seen_' + (el.id || el.getAttribute('data-pulse') || 'x');
    try {
      if (mode === 'always') return { get: function () { return false; }, set: function () {} };
      if (mode === 'day') {
        return { get: function () { return localStorage.getItem(k) === new Date().toDateString(); },
                 set: function () { localStorage.setItem(k, new Date().toDateString()); } };
      }
      return { get: function () { return sessionStorage.getItem(k) === '1'; },
               set: function () { sessionStorage.setItem(k, '1'); } };
    } catch (e) { return { get: function () { return false; }, set: function () {} }; }
  }

  // 007.2: at most one pulse dialog per day across the whole site (home + packages), unless the
  // dialog opts out with data-daily-cap="off".
  var CAPK = 'atv_pulse_day';
  function dayCapHit() { try { return localStorage.getItem(CAPK) === new Date().toDateString(); } catch (e) { return false; } }
  function dayCapSet() { try { localStorage.setItem(CAPK, new Date().toDateString()); } catch (e) {} }

  function arm(el, key) {
    var mode = el.getAttribute('data-once') || 'session';
    var store = seen(el, mode);
    if (store.get()) return;
    if (el.getAttribute('data-daily-cap') !== 'off' && dayCapHit()) return;
    var delay = parseInt(el.getAttribute('data-delay') || '6000', 10);
    var pct = parseInt(el.getAttribute('data-scroll') || '20', 10);
    var opened = false, timer = null, lastFocus = null;

    function onScroll() {
      var h = document.documentElement.scrollHeight - window.innerHeight;
      if (h > 0 && (window.pageYOffset / h) * 100 >= pct) open();
    }
    function open() {
      if (opened) return; opened = true;
      clearTimeout(timer);
      window.removeEventListener('scroll', onScroll);
      store.set();
      if (el.getAttribute('data-daily-cap') !== 'off') dayCapSet();
      lastFocus = document.activeElement;
      el.hidden = false; el.removeAttribute('hidden');
      el.setAttribute('aria-hidden', 'false');
      document.documentElement.style.overflow = 'hidden';
      requestAnimationFrame(function () { el.classList.add('is-open'); });
      var first = el.querySelector('[data-pulse-close], a, button');
      if (first && first.focus) { try { first.focus({ preventScroll: true }); } catch (e) { first.focus(); } }
      document.addEventListener('keydown', onKey);
    }
    function close() {
      document.removeEventListener('keydown', onKey);
      el.classList.remove('is-open');
      el.setAttribute('aria-hidden', 'true');
      document.documentElement.style.overflow = '';
      setTimeout(function () { el.hidden = true; }, 260);
      if (lastFocus && lastFocus.focus) { try { lastFocus.focus({ preventScroll: true }); } catch (e) {} }
    }
    function onKey(e) {
      if (e.key === 'Escape' || e.keyCode === 27) { close(); return; }
      if (e.key !== 'Tab') return;                       // keep focus inside while it is open
      var f = el.querySelectorAll('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])');
      if (!f.length) return;
      var a = f[0], b = f[f.length - 1];
      if (e.shiftKey && document.activeElement === a) { e.preventDefault(); b.focus(); }
      else if (!e.shiftKey && document.activeElement === b) { e.preventDefault(); a.focus(); }
    }

    el.addEventListener('click', function (e) {
      if (e.target === el || (e.target.closest && e.target.closest('[data-pulse-close]'))) { e.preventDefault(); close(); }
    });
    if (delay > 0) timer = setTimeout(open, delay);
    if (pct > 0) { window.addEventListener('scroll', onScroll, { passive: true }); onScroll(); }
  }
})();
