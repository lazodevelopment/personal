/* lazo.js - JC-LAZO-JS-0915-004
   The site's only script. It does seven small things and nothing else:
     1. html.motion  - set unless the visitor asked for reduced motion; every
                       CSS animation and reveal keys off it, so with it absent
                       the page simply appears.
     2. .site-head.scrolled - the header tightens once the page has moved.
     3. .reveal / .in-view  - sections rise into place as they enter the
                       viewport, siblings a beat apart (--i sets the stagger).
     4. a no-op touchstart listener so iOS honours :active, which is how every
                       button and card answers the finger on pointer-down.
     5. contact forms - every form.cform (the /contact/, /delete-account/,
                       /privacy/ and /terms/ form) posts with fetch() and
                       answers in place. The markup is a real <form method=post>,
                       so with this script blocked it still submits.
     6. footer accordions on phones - the footer carries ~75 links, which is
                       right for a browser and wrong for a thumb. The markup
                       ships open, so with this script off (or on a desktop)
                       every link is visible and crawlable; here the headings
                       become toggles and the closed columns go `inert` so
                       they are out of the tab order too.
     7. app install bar - on Android phones (and iOS browsers without Apple's own
                       smart banner) a dismissible bar offers the store listing.
   (0915-002 replaces a file that had been overwritten with a Python patch
   script, so none of this had been running.) */
(function () {
  var d = document, html = d.documentElement;
  var reduce = false;
  try { reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) {}
  if (!reduce) html.classList.add('motion');

  d.addEventListener('touchstart', function () {}, { passive: true });

  /* header */
  var head = d.querySelector('.site-head'), ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      if (head) head.classList.toggle('scrolled', (window.scrollY || window.pageYOffset || 0) > 12);
      ticking = false;
    });
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ---- footer accordions (phones only) ---- */
  (function () {
    var foot = d.querySelector('.site-foot');
    if (!foot) return;
    var cols = [].slice.call(foot.querySelectorAll('.foot-col'));
    if (!cols.length) return;

    var parts = cols.map(function (col, i) {
      var h = col.querySelector('h4'), stack = col.querySelector('.foot-stack');
      if (!h || !stack) return null;
      var id = 'footc' + i;
      stack.id = id;
      h.setAttribute('role', 'button');
      h.setAttribute('tabindex', '0');
      h.setAttribute('aria-controls', id);
      function set(open) {
        col.classList.toggle('open', open);
        h.setAttribute('aria-expanded', open ? 'true' : 'false');
        /* a link you cannot see is a link you should not be able to tab to */
        if (open) stack.removeAttribute('inert'); else stack.setAttribute('inert', '');
      }
      function toggle() { set(!col.classList.contains('open')); }
      h.addEventListener('click', toggle);
      h.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); toggle(); }
      });
      return { col: col, h: h, stack: stack, set: set };
    }).filter(Boolean);

    var mq = window.matchMedia('(max-width:760px)');
    function sync() {
      var phone = mq.matches;
      foot.classList.toggle('foot-acc', phone);
      parts.forEach(function (p) {
        if (phone) {
          p.set(p.col.classList.contains('open'));      /* keep what the reader opened */
        } else {
          p.col.classList.remove('open');
          p.h.removeAttribute('aria-expanded');
          p.stack.removeAttribute('inert');
        }
      });
    }
    if (mq.addEventListener) mq.addEventListener('change', sync);
    else if (mq.addListener) mq.addListener(sync);
    sync();
  })();

  /* ---- contact form (JC-LAZO-CFORM-0916-001) ----
     Progressive enhancement, in that order: the form in _contact_form.html is a
     real <form method=post> and works with this script blocked. Here we keep the
     reader on the page - post it with fetch(), answer in place, and leave what
     they typed alone if it fails so nobody retypes a paragraph. */
  [].slice.call(d.querySelectorAll('form.cform')).forEach(function (f) {
    var btn = f.querySelector('button[type=submit]');
    var msg = f.querySelector('.cf-msg');
    var label = btn ? btn.textContent : 'Send message';
    var sent = false;

    function say(kind, text) {
      if (!msg) return;
      msg.className = 'cf-msg show ' + kind;
      msg.textContent = text;
    }

    /* a field the reader has already failed once is allowed to look failed */
    f.addEventListener('invalid', function () { f.classList.add('tried'); }, true);

    f.addEventListener('submit', function (e) {
      /* preventDefault FIRST. Anything below that returns early - an invalid field,
         a double-click - must not fall through to a native POST that throws the
         reader onto a bare response page and loses what they typed. */
      e.preventDefault();
      f.classList.add('tried');                 /* :invalid styling starts only now */
      if (f.checkValidity && !f.checkValidity()) {
        if (f.reportValidity) f.reportValidity();   /* say which field, and focus it */
        return;
      }
      if (sent) return;

      var data = {}, fd = new FormData(f);
      fd.forEach(function (v, k) { data[k] = typeof v === 'string' ? v : ''; });
      data.page = location.pathname;
      data.referrer = d.referrer || '';

      sent = true;
      if (btn) { btn.disabled = true; btn.textContent = 'Sending\u2026'; }
      if (msg) msg.className = 'cf-msg';

      fetch(f.action, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(data)
      })
        .then(function (r) { return r.json().catch(function () { return { ok: r.ok }; }); })
        .then(function (j) {
          if (!j || !j.ok) throw new Error((j && j.error) || 'failed');
          [].slice.call(f.querySelectorAll('input:not([type=hidden]),textarea')).forEach(function (i) { i.value = ''; });
          f.classList.remove('tried');
          if (btn) { btn.disabled = true; btn.textContent = 'Sent'; }
          say('ok', "Got it \u2014 thank you. A person reads every one of these; you'll hear back at the address you gave us, usually the same business day and always within two.");
          try { if (window.fbq) fbq('trackCustom', 'ContactSubmit', { topic: data.topic || '' }); } catch (_) {}
        })
        .catch(function () {
          sent = false;
          if (btn) { btn.disabled = false; btn.textContent = label; }
          say('err', "That didn't send \u2014 and your message is still in the box, so nothing is lost. Give it another try in a moment; if it keeps refusing, message us from inside Lazo at app.meetlazo.com and we'll pick it up there.");
        });
    });
  });

  /* ---- app install bar (phones) - JC-LAZO-APPBAR-1003 ----
     iOS Safari already shows Apple's smart banner (meta apple-itunes-app), so this
     only appears where that banner can't: Android, and iOS browsers that aren't
     Safari. Dismissed = quiet for 30 days. Never on /app/ (that page IS the pitch),
     never inside an iframe (the wedding-website hub previews), never on a desktop. */
  (function () {
    try {
      if (window.top !== window.self) return;
      if (/^\/app\/?$/.test(location.pathname)) return;
      if (!window.matchMedia('(max-width:760px)').matches) return;
      var ua = navigator.userAgent || '';
      var android = /Android/i.test(ua);
      var ios = /iPhone|iPad|iPod/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
      if (!android && !ios) return;
      if (ios && /Safari/i.test(ua) && !/CriOS|FxiOS|EdgiOS|OPiOS|DuckDuckGo|GSA/i.test(ua)) return;
      var off = +(localStorage.getItem('lz_appbar_off') || 0);
      if (off && Date.now() - off < 30 * 864e5) return;
      var store = android ? 'play' : 'apple';
      var href = android ? 'https://play.google.com/store/apps/details?id=com.meetlazo.app'
                         : 'https://apps.apple.com/us/app/lazo-wedding-planner/id6812863675';
      var bar = d.createElement('aside');
      bar.className = 'lz-appbar';
      bar.setAttribute('aria-label', 'Get the Lazo app');
      bar.innerHTML = '<button type="button" class="x" aria-label="Not now">&times;</button>' +
        '<img src="/assets/appicon.png" alt="" width="44" height="44">' +
        '<div class="t"><b>Lazo: Wedding Planner</b><span>Free on ' + (android ? 'Google Play' : 'the App Store') + '. Vendors, June, your website.</span></div>' +
        '<a class="go" href="' + href + '" rel="noopener">Get</a>';
      d.body.appendChild(bar);
      html.classList.add('has-appbar');
      function remember() { try { localStorage.setItem('lz_appbar_off', String(Date.now())); } catch (e) {} }
      requestAnimationFrame(function () { requestAnimationFrame(function () { bar.classList.add('show'); }); });
      bar.querySelector('.x').addEventListener('click', function () {
        remember();
        bar.classList.remove('show'); html.classList.remove('has-appbar');
        setTimeout(function () { if (bar.parentNode) bar.parentNode.removeChild(bar); }, 400);
      });
      bar.querySelector('.go').addEventListener('click', function () {
        remember();
        try { if (window.fbq) fbq('trackCustom', 'AppStoreClick', { store: store, from: 'bar' }); } catch (e) {}
      });
    } catch (e) {}
  })();

  /* reveal */
  if (reduce || !('IntersectionObserver' in window)) return;
  var SEL = [
    '.band > .rowhead', '.band > .band-title', '.band > .band-sub', '.band > .eyebrow',
    '.band-plum > .band-title', '.band-plum > .band-sub',
    '.split > :not(.chat)', '.chat > .msg', '.vgrid > *', '.tile-grid > *', '.steps > *',
    '.promises > *', '.claims > li', '.stance .cols > *', '.ww', '.claim-strip',
    '.cat-grid > *', '.metro-grid > *', '.vendor-list > *', '.why-list > *', '.faq',
    '.founder-grid > *', '.june-inner > *', '.fv-card', '.fv-step', '.fv-tier', '.fv-stat',
    '.vp-h2', '.vp-price', '.vp-about > *', '.v-review', '.v-peer', '.v-cal-month', '.ww-strip', '.vp-card'
  ].join(',');
  var els = [].slice.call(d.querySelectorAll(SEL)).filter(function (e) {
    return !e.closest('.hero') && !e.closest('.site-head') && !e.closest('.site-foot');
  });
  var counts = [];
  function nth(parent) {
    for (var i = 0; i < counts.length; i++) if (counts[i].p === parent) return counts[i].n++;
    counts.push({ p: parent, n: 1 });
    return 0;
  }
  var tagged = [];
  els.forEach(function (e) {
    if (e.parentElement && e.parentElement.closest('.reveal')) return; /* never nest */
    e.style.setProperty('--i', Math.min(nth(e.parentNode), 8));
    e.classList.add('reveal');
    tagged.push(e);
  });
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (!en.isIntersecting) return;
      en.target.classList.add('in-view');
      io.unobserve(en.target);
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.06 });
  tagged.forEach(function (e) { io.observe(e); });
})();
