/* ============================================================
   ATAVIA WEDDINGS — shared site scripts
   ============================================================ */
(function () {
  "use strict";

  /* ---- nav: scroll state + mobile toggle ---- */
  var nav = document.querySelector(".nav");
  var toggle = document.querySelector(".nav__toggle");
  var menu = document.querySelector(".mobile-menu");

  if (nav) {
    var onScroll = function () { nav.classList.toggle("is-scrolled", window.pageYOffset > 12); };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }
  if (toggle && menu) {
    var closeMenu = function () { toggle.classList.remove("is-open"); menu.classList.remove("is-open"); document.body.style.overflow = ""; };
    toggle.addEventListener("click", function () {
      var open = menu.classList.toggle("is-open");
      toggle.classList.toggle("is-open", open);
      document.body.style.overflow = open ? "hidden" : "";
    });
    menu.querySelectorAll("a").forEach(function (a) { a.addEventListener("click", closeMenu); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeMenu(); });
  }

  /* ---- reveal on scroll ---- */
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    document.querySelectorAll(".reveal").forEach(function (el) { io.observe(el); });
  } else {
    document.querySelectorAll(".reveal").forEach(function (el) { el.classList.add("in"); });
  }

  /* ---- animated counters ---- */
  if ("IntersectionObserver" in window) {
    var cio = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        var el = e.target, target = +el.dataset.count, sfx = el.dataset.suffix || "", dur = 1600, start = performance.now();
        var step = function (now) {
          var p = Math.min((now - start) / dur, 1), ease = 1 - Math.pow(1 - p, 3);
          el.textContent = Math.round(target * ease).toLocaleString() + sfx;
          if (p < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step); cio.unobserve(el);
      });
    }, { threshold: 0.6 });
    document.querySelectorAll("[data-count]").forEach(function (el) { cio.observe(el); });
  }

  /* ---- video lightbox ---- */
  var vlb = document.getElementById("videoLightbox");
  if (vlb) {
    var vFrame = vlb.querySelector(".lb__frame");
    var openVideo = function (id) {
      vFrame.innerHTML = '<iframe src="https://www.youtube.com/embed/' + id + '?autoplay=1&rel=0" title="Atavia wedding film" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>';
      vlb.classList.add("open"); document.body.style.overflow = "hidden";
    };
    var closeVideo = function () { vlb.classList.remove("open"); vFrame.innerHTML = ""; document.body.style.overflow = ""; };
    document.querySelectorAll("[data-video]").forEach(function (el) {
      el.addEventListener("click", function () { openVideo(el.getAttribute("data-video")); });
    });
    vlb.addEventListener("click", function (e) { if (e.target === vlb || e.target.closest(".lb__close")) closeVideo(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeVideo(); });
  }

  /* ---- gallery lightbox ---- */
  var glb = document.getElementById("galleryLightbox");
  if (glb) {
    var gImg = glb.querySelector(".glb__img");
    var gCount = glb.querySelector(".glb__count");
    var items = [].slice.call(document.querySelectorAll("[data-glb]"));
    var sources = items.map(function (el) { return el.getAttribute("data-glb-full") || el.getAttribute("data-glb"); });
    var gi = 0;
    var update = function () { gImg.src = sources[gi]; if (gCount) gCount.textContent = (gi + 1) + " / " + sources.length; };
    var openG = function (i) { gi = i; update(); glb.classList.add("open"); document.body.style.overflow = "hidden"; };
    var closeG = function () { glb.classList.remove("open"); document.body.style.overflow = ""; };
    var stepG = function (d) { gi = (gi + d + sources.length) % sources.length; update(); };
    items.forEach(function (el, i) { el.addEventListener("click", function () { openG(i); }); });
    glb.addEventListener("click", function (e) {
      if (e.target === glb || e.target.closest(".glb__close")) return closeG();
      if (e.target.closest(".glb__prev")) return stepG(-1);
      if (e.target.closest(".glb__next")) return stepG(1);
    });
    document.addEventListener("keydown", function (e) {
      if (!glb.classList.contains("open")) return;
      if (e.key === "Escape") closeG();
      if (e.key === "ArrowRight") stepG(1);
      if (e.key === "ArrowLeft") stepG(-1);
    });
  }

  /* ---- FAQ single-open accordion ---- */
  var faqItems = document.querySelectorAll(".faq__item");
  faqItems.forEach(function (item) {
    item.addEventListener("toggle", function () {
      if (item.open) faqItems.forEach(function (o) { if (o !== item) o.open = false; });
    });
  });

  /* ---- footer year ---- */
  var yr = document.getElementById("year");
  if (yr) yr.textContent = new Date().getFullYear();
})();

/* ---------- Lead attribution -------------------------------------------
   Records, for this browser session: the first page the visitor landed on,
   where they came from, and the most recent VENUE page they viewed.
   The contact form reads these and sends them with the booking request,
   so every lead tells you which venue page produced it. */
(function(){
  try{
    var ss = window.sessionStorage;
    if(!ss.getItem('atv_landing')){
      ss.setItem('atv_landing', location.pathname + location.search);
      ss.setItem('atv_referrer', document.referrer || 'direct');
    }
    var m = document.querySelector('meta[name="atv-venue"]');
    if(m && m.content){
      ss.setItem('atv_venue', m.content);
      ss.setItem('atv_venue_url', location.pathname);
    }
  }catch(e){ /* private mode — attribution just won't record */ }
})();

/* ---------- attribution v2: URL params win, visible venue chip ---------- */
(function(){
  try{
    var q = new URLSearchParams(location.search);
    var pVenue = q.get('venue'), pFrom = q.get('from');
    var ss = null; try{ ss = window.sessionStorage; }catch(e){}
    if(pVenue && ss){ try{ ss.setItem('atv_venue', pVenue); ss.setItem('atv_venue_url', pFrom || ''); }catch(e){} }
    var venue = pVenue || (ss && ss.getItem('atv_venue')) || '';
    var vurl  = pFrom  || (ss && ss.getItem('atv_venue_url')) || '';
    var form = document.querySelector('form[action*="formspree"]');
    if(!form) return;
    function setF(n, v){ var el = form.querySelector('[name="'+n+'"]'); if(el && v) el.value = v; }
    setF('Venue', venue);
    setF('Venue Page', vurl);
    if(ss){ setF('Landing Page', ss.getItem('atv_landing') || ''); setF('Referrer', ss.getItem('atv_referrer') || ''); }
    if(venue){
      var chip = document.getElementById('venueContext'),
          name = document.getElementById('venueContextName');
      if(chip && name){ name.textContent = venue; chip.style.display = 'block'; }
    }
  }catch(e){}
})();
