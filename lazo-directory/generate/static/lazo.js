/* lazo.js - JC-LAZO-JS-0915-004
   The site's only script. It does ten small things and nothing else:
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
     8. scroll motion - hero parallax and ease-away, count-ups, gliding rails, the
                       app hero phones. See the block at the end.
     9. cookie notice - the Meta pixel waits for consent in the EU/EEA, UK and
                       California, runs opt-out elsewhere; "Cookie choices" in the footer
                       opens the notice for everyone.
    10. night switch - the sun/moon pill in the header flips html[data-theme]
                       and remembers the choice (localStorage 'lazo-theme'). Light is
                       the default; base.html applies a stored choice in <head>.
   (0915-002 replaces a file that had been overwritten with a Python patch
   script, so none of this had been running.) */
(function () {
  var d = document, html = d.documentElement;
  var reduce = false;
  try { reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) {}
  if (!reduce) html.classList.add('motion');

  d.addEventListener('touchstart', function () {}, { passive: true });

  /* night switch  JC-LAZO-NIGHT-1014-002 */
  (function () {
    var sws = d.querySelectorAll('.theme-sw'); if (!sws.length) return;
    var meta = d.querySelector('meta[name=theme-color]'), fade;
    function sync() {
      var night = html.getAttribute('data-theme') === 'dark';
      for (var i = 0; i < sws.length; i++) sws[i].setAttribute('aria-checked', night ? 'true' : 'false');
      if (meta) meta.setAttribute('content', night ? '#1C0E1E' : '#FAF6F0');
    }
    function flip() {
      var next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      html.classList.add('theme-anim'); clearTimeout(fade);
      html.setAttribute('data-theme', next);
      try { if (next === 'dark') localStorage.setItem('lazo-theme', 'dark'); else localStorage.removeItem('lazo-theme'); } catch (e) {}
      sync();
      fade = setTimeout(function () { html.classList.remove('theme-anim'); }, 600);
    }
    for (var i = 0; i < sws.length; i++) sws[i].addEventListener('click', flip);
    /* another tab flipped it: follow along */
    window.addEventListener('storage', function (e) {
      if (e.key !== 'lazo-theme') return;
      html.setAttribute('data-theme', e.newValue === 'dark' ? 'dark' : 'light'); sync();
    });
    sync();
  })();

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

  /* ---- footer city list: a few rows + "Show all" on desktop (JC-LAZO-AUDIT-1016) ---- */
  (function () {
    var box = d.querySelector('.foot-cities'), btn = box && box.querySelector('.foot-more');
    if (!btn) return;
    var label = btn.textContent, mq = window.matchMedia('(max-width:760px)');
    function sync() {
      var phone = mq.matches;
      box.classList.toggle('clamp', !phone);
      btn.hidden = phone;
      if (phone) box.classList.remove('all');
    }
    btn.addEventListener('click', function () {
      var all = box.classList.toggle('all');
      btn.textContent = all ? 'Show fewer cities' : label;
      btn.setAttribute('aria-expanded', all ? 'true' : 'false');
    });
    btn.setAttribute('aria-expanded', 'false');
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

  /* ---- 9. cookie notice (JC-LAZO-CONSENT-1003 / -1004) ----
     base.html defines window.lzPixel.load() and window.lzConsentState ('', 'yes', 'no',
     'gpc' or 'optout'). '' means an opt-in region with no decision stored: a small notice
     asks; Allow loads the pixel now and for a year, Decline is remembered too. 'optout'
     means the pixel is already running (disclosed in the privacy policy) and the notice
     only appears from "Cookie choices" in the footer (data-lz-consent), where Decline
     stops it from the next page. Never inside an iframe. */
  (function () {
    if (window.top !== window.self) return;
    var box = null;
    function save(v) { try { localStorage.setItem('lz_consent', v + ':' + Date.now()); } catch (e) {} window.lzConsentState = v; }
    function close() {
      if (!box) return;
      var b = box; box = null;
      b.classList.remove('show');
      setTimeout(function () { if (b.parentNode) b.parentNode.removeChild(b); }, 450);
    }
    function open() {
      if (box) return;
      box = d.createElement('aside');
      box.className = 'lz-consent';
      box.setAttribute('role', 'dialog');
      box.setAttribute('aria-label', 'Cookie choices');
      var on = !!window.fbq;
      box.innerHTML = '<p><b>One pixel, your call.</b> We use a Meta pixel on our marketing pages to learn which ads bring couples to Lazo. It never runs on a couple\u2019s wedding website' + (on ? ', and you can turn it off here; your choice is kept for a year and applies from the next page.' : ', and nothing loads until you allow it.') + ' <a href="/privacy/#cookies">Privacy policy</a></p>' +
        '<div class="b"><button type="button" class="yes">' + (on ? 'Keep it on' : 'Allow') + '</button><button type="button" class="no">' + (on ? 'Turn it off' : 'Decline') + '</button></div>';
      d.body.appendChild(box);
      void box.offsetWidth; /* commit the start state so the transition runs, even in a hidden tab */
      box.classList.add('show');
      box.querySelector('.yes').addEventListener('click', function () {
        save('yes');
        try { if (window.lzPixel) window.lzPixel.load(); } catch (e) {}
        close();
      });
      box.querySelector('.no').addEventListener('click', function () { save('no'); close(); });
    }
    if (window.lzConsentState === '') open();
    [].slice.call(d.querySelectorAll('[data-lz-consent]')).forEach(function (a) {
      a.addEventListener('click', function (e) { e.preventDefault(); open(); try { box.scrollIntoView({ block: 'end' }); } catch (_) {} });
    });
    window.lzConsentOpen = open;
  })();

  /* ---- app install bar (phones) - JC-LAZO-APPBAR-1003 ----
     iOS Safari already shows Apple's smart banner (meta apple-itunes-app), so this
     only appears where that banner can't: Android, and iOS browsers that aren't
     Safari. Dismissed = quiet for 30 days. Never on /app/ (that page IS the pitch),
     never inside an iframe (the wedding-website hub previews), never on a desktop. */
  (function () {
    try {
      if (window.top !== window.self) return;
      if (d.querySelector('.lz-consent')) return;
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
      void bar.offsetWidth;
      bar.classList.add('show');
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
    '.vp-h2', '.vp-price', '.vp-about > *', '.v-review', '.v-peer', '.v-cal-month', '.ww-strip', '.vp-card',
    '.apphome .ag > *', '.vf3 > *', '.pz > *', '.fc', '.phones > *', '.pcap', '.all', '.hdr',
    '.ap-strip .head > *', '.ap-rail figure', '.ap-feats .ap-f', '.ap-vs > div', '.ap-faq-h', '.ap-cta > *', '.why-cols > *', '.score'
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

  /* ---- 8. scroll motion (JC-LAZO-MOTION-1003) ----
     The same hand everywhere: photo heroes carry a background layer that scrolls
     slower than the page while the headline eases away; the home and app counts
     count up the first time they are seen; horizontal rails (the app screens, a
     vendor's sheet pages) glide sideways while the reader scrolls past them, and
     stop the moment the reader steers one; the app hero phones drift at three
     speeds. Transforms and opacity only, one rAF per scroll, and none of it
     without html.motion. */
  (function () {
    var q = function (s) { return d.querySelector(s); }, qa = function (s) { return [].slice.call(d.querySelectorAll(s)); };
    var wide = window.matchMedia('(min-width:900px)');

    function countUp(b) {
      var m = /^([^\d]*)([\d,]+)(.*)$/.exec(b.textContent.trim()); if (!m) return;
      var end = parseInt(m[2].replace(/,/g, ''), 10); if (!end) return;
      var t0 = null, dur = 1400;
      function step(t) {
        if (t0 === null) t0 = t;
        var p = Math.min((t - t0) / dur, 1), e = 1 - Math.pow(1 - p, 3);
        b.textContent = m[1] + Math.round(end * e).toLocaleString('en-US') + m[3];
        if (p < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    }
    qa('.hm-facts b, .ap-proof b, .fv-stat b').forEach(function (b) {
      var o = new IntersectionObserver(function (es) { if (!es[0].isIntersecting) return; o.disconnect(); countUp(b); }, { threshold: 0.6 });
      o.observe(b);
    });

    var heroes = qa('.hero').map(function (h) {
      var bg = null;
      if (h.classList.contains('hero-photo') && h.style.backgroundImage) {
        bg = d.createElement('div'); bg.className = 'hero-bg';
        bg.style.backgroundImage = h.style.backgroundImage;
        h.insertBefore(bg, h.firstChild);
        h.style.backgroundImage = 'none';
      }
      return { el: h, bg: bg, inner: h.querySelector('.hero-inner') };
    });
    var shots = qa('.ap-shots img'), speeds = [0.10, 0.18, 0.06];
    var apHero = q('.ap-hero'), apText = q('.ap-wrap > div:first-child');
    var rails = qa('.ap-rail, .v-sheet-pages').map(function (r) {
      var m = { el: r, manual: false }, tx = 0, ty = 0;
      r.addEventListener('wheel', function (e) { if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) m.manual = true; }, { passive: true });
      r.addEventListener('touchstart', function (e) { tx = e.touches[0].clientX; ty = e.touches[0].clientY; }, { passive: true });
      r.addEventListener('touchmove', function (e) { if (Math.abs(e.touches[0].clientX - tx) > Math.abs(e.touches[0].clientY - ty) + 4) m.manual = true; }, { passive: true });
      r.addEventListener('pointerdown', function (e) { if (e.pointerType === 'mouse') m.manual = true; });
      r.addEventListener('keydown', function () { m.manual = true; });
      return m;
    });
    if (!heroes.length && !shots.length && !rails.length) return;

    var busy = false;
    function frame() {
      busy = false;
      var y = window.scrollY || window.pageYOffset || 0, vh = window.innerHeight || 1;
      heroes.forEach(function (h) {
        var r = h.el.getBoundingClientRect(); if (r.bottom < 0) return;
        var into = Math.max(0, -r.top);
        if (h.bg) h.bg.style.setProperty('--hy', (into * 0.25).toFixed(1) + 'px');
        if (h.inner) {
          if (wide.matches) {
            var p = Math.min(into / (r.height * 0.9), 1);
            h.inner.style.opacity = String(1 - p * 0.55);
            h.inner.style.transform = 'translateY(' + (into * 0.12).toFixed(1) + 'px)';
          } else { h.inner.style.opacity = ''; h.inner.style.transform = ''; }
        }
      });
      if (apHero) {
        var rh = apHero.getBoundingClientRect();
        if (rh.bottom > 0) {
          var k = wide.matches ? 1 : 0.45;
          shots.forEach(function (im, i) { im.style.setProperty('--py', (-y * speeds[i] * k).toFixed(1) + 'px'); });
          if (apText) {
            if (wide.matches) {
              var p2 = Math.min(y / (rh.height * 0.9), 1);
              apText.style.opacity = String(1 - p2 * 0.55);
              apText.style.transform = 'translateY(' + (y * 0.12).toFixed(1) + 'px)';
            } else { apText.style.opacity = ''; apText.style.transform = ''; }
          }
          apHero.style.setProperty('--gy', (y * 0.25).toFixed(1) + 'px');
        }
      }
      rails.forEach(function (m) {
        if (m.manual) return;
        var r = m.el.getBoundingClientRect(); if (r.bottom <= 0 || r.top >= vh) return;
        var prog = Math.max(0, Math.min(1, (vh - r.top) / (vh + r.height)));
        var e = prog * prog * (3 - 2 * prog);
        m.el.scrollLeft = e * (m.el.scrollWidth - m.el.clientWidth) * 0.85;
      });
    }
    function tick() { if (busy) return; busy = true; requestAnimationFrame(frame); }
    window.addEventListener('scroll', tick, { passive: true });
    window.addEventListener('resize', tick);
    frame();
  })();

  /* ---- 11. home scroll motion (JC-LAZO-MOTION-1016) ----
     a. the three app phones on the home page float up at three speeds as the section passes;
     b. June listens: scroll speed is published as window.LZ_SCROLLV (0..1, decaying) and
        lazo.june.js lets the idle core swell with it;
     c. the category tiles tilt in one after another (CSS, keyed off .reveal/.in-view);
     d. the couple feature cards stack: each card is sticky, and as the card below slides over
        it, it settles back (scale and shade by how much of it is covered).
     Transforms only, one rAF per scroll, none of it without html.motion (we only get here
     when motion is allowed). */
  (function () {
    var hh = function () { var h = d.querySelector('.site-head'); html.style.setProperty('--hh', (h ? h.offsetHeight : 64) + 'px'); };
    hh(); window.addEventListener('resize', hh);
    var shots = [].slice.call(d.querySelectorAll('.apphome .shots img')), sp = [0.07, -0.05, 0.12];
    var box = d.querySelector('.apphome .shots');
    var cards = [].slice.call(d.querySelectorAll('#features .ftg > .fc'));
    var grid = d.querySelector('#features .ftg');
    if (grid) grid.classList.add('stack');
    var lastY = window.scrollY || 0, lastT = 0, v = 0, busy = false;
    window.LZ_SCROLLV = 0;
    function cols() { if (!grid) return 1; var t = getComputedStyle(grid).gridTemplateColumns; return t ? t.split(' ').filter(Boolean).length : 1; }
    function frame(now) {
      busy = false;
      var y = window.scrollY || 0, vh = window.innerHeight || 1;
      var dt = Math.max(16, (now || 0) - lastT); lastT = now || 0;
      v = Math.min(1, v * 0.6 + Math.abs(y - lastY) / dt * 0.35); lastY = y; window.LZ_SCROLLV = v;
      if (box) {
        var r = box.getBoundingClientRect();
        if (r.bottom > -200 && r.top < vh + 200) {
          var c = (r.top + r.height / 2 - vh / 2);
          shots.forEach(function (im, i) { im.style.setProperty('--sy', (c * sp[i]).toFixed(1) + 'px'); });
        }
      }
      if (cards.length) {
        var n = cols();
        cards.forEach(function (cd, i) {
          var nx = cards[i + n]; if (!nx) { cd.style.removeProperty('--cov'); return; }
          var a = cd.getBoundingClientRect(), b = nx.getBoundingClientRect();
          var cov = Math.max(0, Math.min(1, (a.bottom - b.top) / (a.height || 1)));
          cd.style.setProperty('--cov', cov.toFixed(3));
        });
      }
    }
    function tick() { if (busy) return; busy = true; requestAnimationFrame(frame); }
    window.addEventListener('scroll', tick, { passive: true });
    window.addEventListener('resize', tick);
    // let the June core feel the scroll decay back to rest
    setInterval(function () { if (window.LZ_SCROLLV > 0.001) { window.LZ_SCROLLV *= 0.85; v = window.LZ_SCROLLV; } }, 60);
    frame(0);
  })();
})();

/* JC-LAZO-VSONG-1020-002: the vendor's storefront song. Vendor pages only; the
   worker answers /music/song?v= with a live clip when the vendor picked one in
   the app (vendors.song), else null and nothing is mounted. Same pill as the
   couple sites: a record that turns while it plays, one tap pauses, and when
   the browser refuses autoplay the first tap anywhere starts it. */
(function () {
  if (window.top !== window) return;
  var vp = document.querySelector('.vp[data-vendor-id]');
  var id = vp && vp.getAttribute('data-vendor-id');
  if (!id) return;
  fetch('https://meetlazo.com/music/song?v=' + encodeURIComponent(id))
    .then(function (r) { return r.json(); })
    .then(function (j) { var S = j && j.song; if (S && S.src) mount(S); })
    .catch(function () {});
  function mount(S) {
    var reduce = false; try { reduce = matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) {}
    var a = new Audio(); a.preload = 'auto'; a.src = S.src; a.loop = !!S.loop; a.volume = 0;
    var el = document.createElement('button'); el.type = 'button'; el.className = 'oursong'; el.setAttribute('aria-label', 'Play their song');
    var esc = function (t) { return String(t || '').replace(/[<>&"]/g, function (c) { return { '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]; }); };
    el.innerHTML = '<span class="disc"' + (S.art ? ' style="background-image:url(&quot;' + esc(S.art) + '&quot;)"' : '') + '></span>'
      + '<span class="tx"><span class="t">' + esc(S.title || 'Their song') + '</span><span class="a">' + esc(S.artist || '') + '</span><span class="h" data-h>Tap to play</span></span>'
      + '<span class="pp" aria-hidden="true"></span>';
    document.body.appendChild(el);
    var hint = el.querySelector('[data-h]'), fade = null, armed = false;
    function setHint(t) { if (hint) hint.textContent = t; }
    function fadeTo(v, ms) { clearInterval(fade); var steps = Math.max(1, Math.round(ms / 40)), i = 0, from = a.volume; fade = setInterval(function () { i++; a.volume = Math.max(0, Math.min(1, from + (v - from) * (i / steps))); if (i >= steps) clearInterval(fade); }, 40); }
    function play() { var p = a.play(); if (p && p.then) p.then(function () { el.classList.add('playing'); setHint('Now playing'); fadeTo(.9, reduce ? 0 : 1400); try { sessionStorage.removeItem('lzvsongoff'); } catch (e) {} }).catch(function () { arm(); }); }
    function pause() { fadeTo(0, reduce ? 0 : 500); setTimeout(function () { a.pause(); }, reduce ? 0 : 520); el.classList.remove('playing'); el.classList.add('off'); setHint('Paused · tap to play'); try { sessionStorage.setItem('lzvsongoff', '1'); } catch (e) {} }
    function arm() {
      if (armed) return; armed = true; setHint('Tap anywhere to play');
      var go = function () { document.removeEventListener('pointerdown', go, true); document.removeEventListener('keydown', go, true); if (!el.classList.contains('playing') && !el.classList.contains('off')) play(); };
      document.addEventListener('pointerdown', go, true); document.addEventListener('keydown', go, true);
    }
    el.addEventListener('click', function (e) { e.stopPropagation(); if (el.classList.contains('playing')) pause(); else { el.classList.remove('off'); play(); } });
    a.addEventListener('ended', function () { el.classList.remove('playing'); setHint('Play it again'); });
    a.addEventListener('error', function () { el.remove(); });
    var off = false; try { off = sessionStorage.getItem('lzvsongoff') === '1'; } catch (e) {}
    if (off) { el.classList.add('off'); setHint('Tap to play'); }
    else if (S.autoplay !== false) { play(); }
    else { setHint('Tap to play'); }
  }
})();
