// ============================================================
// ROVEN — motion.js
// All interaction + animation. Everything respects
// prefers-reduced-motion and pointer capability.
// ============================================================

const noMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const finePointer = window.matchMedia('(pointer: fine)').matches;

// ---------- mobile nav ----------
const navToggle = document.querySelector('.nav-toggle');
const navLinks = document.getElementById('navlinks');
if (navToggle && navLinks) {
  navToggle.addEventListener('click', () => {
    const open = navLinks.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', open);
  });
}

// ---------- scroll reveal ----------
const revealIO = new IntersectionObserver(entries => entries.forEach(e => {
  if (e.isIntersecting) { e.target.classList.add('in'); revealIO.unobserve(e.target); }
}), { threshold: .12 });
document.querySelectorAll('.reveal, .problem').forEach(el => revealIO.observe(el));

// ---------- easing ----------
const easeOut = t => 1 - Math.pow(1 - t, 3);

// ---------- animated number ----------
function countUp(el, target, { decimals = 0, suffix = '', duration = 1100, delay = 0 } = {}) {
  if (noMotion) { el.textContent = target.toFixed(decimals) + suffix; return; }
  const start = performance.now() + delay;
  function frame(now) {
    if (now < start) { requestAnimationFrame(frame); return; }
    const t = Math.min((now - start) / duration, 1);
    el.textContent = (target * easeOut(t)).toFixed(decimals) + suffix;
    if (t < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

// ---------- accountability card: ring + counters, on view ----------
const CIRC = 264; // 2πr, r=42
function playCard(card) {
  card.classList.add('play');
  const ring = card.querySelector('.ring');
  const meter = card.querySelector('.ring .meter');
  const label = card.querySelector('.ring text');
  const score = parseFloat(ring?.dataset.score || '0');
  const finalOffset = CIRC * (1 - score / 100);

  if (meter && label) {
    if (noMotion) {
      meter.style.strokeDashoffset = finalOffset;
      label.textContent = Math.round(score);
    } else {
      meter.style.strokeDashoffset = CIRC;
      label.textContent = '0';
      const start = performance.now() + 200;
      const duration = 1300;
      function frame(now) {
        if (now < start) { requestAnimationFrame(frame); return; }
        const t = Math.min((now - start) / duration, 1);
        const v = score * easeOut(t);
        meter.style.strokeDashoffset = CIRC - (CIRC - finalOffset) * easeOut(t);
        label.textContent = Math.round(v);
        if (t < 1) requestAnimationFrame(frame);
      }
      requestAnimationFrame(frame);
    }
  }

  // metric value counters
  card.querySelectorAll('[data-count]').forEach((el, i) => {
    countUp(el, parseFloat(el.dataset.count), {
      decimals: parseInt(el.dataset.decimals || '0', 10),
      suffix: el.dataset.suffix || '',
      duration: 900,
      delay: 250 + i * 150
    });
  });
}

const cardIO = new IntersectionObserver(entries => entries.forEach(e => {
  if (e.isIntersecting) { playCard(e.target); cardIO.unobserve(e.target); }
}), { threshold: .35 });
document.querySelectorAll('.score-card').forEach(c => cardIO.observe(c));

// ---------- live activity feed ----------
const FEED = [
  'APPLICATION ANSWERED · 14 MIN AGO',
  'INTERVIEW SCHEDULED · 1 HR AGO',
  'NEW ROLE CONFIRMED OPEN · 2 HRS AGO',
  'HIRE CONFIRMED · YESTERDAY',
  'APPLICATION ANSWERED · 3 HRS AGO'
];
document.querySelectorAll('.sc-live-text').forEach((el, cardIdx) => {
  let i = cardIdx % FEED.length;
  el.textContent = FEED[i];
  if (noMotion) return;
  setInterval(() => {
    el.classList.add('swap');
    setTimeout(() => {
      i = (i + 1) % FEED.length;
      el.textContent = FEED[i];
      el.classList.remove('swap');
    }, 300);
  }, 3800);
});

// ---------- hero card parallax tilt ----------
if (finePointer && !noMotion) {
  document.querySelectorAll('.hero').forEach(hero => {
    const card = hero.querySelector('.tilt-target');
    if (!card) return;
    hero.addEventListener('mousemove', e => {
      const r = hero.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - .5;
      const y = (e.clientY - r.top) / r.height - .5;
      card.style.transform = `rotateY(${x * 7}deg) rotateX(${y * -7}deg)`;
    });
    hero.addEventListener('mouseleave', () => { card.style.transform = ''; });
  });

  // tilt cards
  document.querySelectorAll('.tilt').forEach(el => {
    el.addEventListener('mousemove', e => {
      const r = el.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - .5;
      const y = (e.clientY - r.top) / r.height - .5;
      el.style.transform = `perspective(700px) rotateY(${x * 5}deg) rotateX(${y * -5}deg) translateY(-3px)`;
    });
    el.addEventListener('mouseleave', () => { el.style.transform = ''; });
  });

  // magnetic buttons
  document.querySelectorAll('.magnet').forEach(btn => {
    btn.addEventListener('mousemove', e => {
      const r = btn.getBoundingClientRect();
      const x = e.clientX - r.left - r.width / 2;
      const y = e.clientY - r.top - r.height / 2;
      btn.style.transform = `translate(${x * .18}px, ${y * .3}px)`;
    });
    btn.addEventListener('mouseleave', () => { btn.style.transform = ''; });
  });
}

// ---------- orb scroll parallax ----------
if (!noMotion) {
  const orbs = document.querySelectorAll('.orb');
  if (orbs.length) {
    let ticking = false;
    window.addEventListener('scroll', () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const y = window.scrollY;
        orbs.forEach((o, i) => {
          o.style.marginTop = (y * (i % 2 ? .05 : -.04)) + 'px';
        });
        ticking = false;
      });
    }, { passive: true });
  }
}

// ---------- scroll progress bar ----------
const progressBar = document.querySelector('.scroll-progress .bar');
if (progressBar) {
  let pTick = false;
  function setProgress() {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    progressBar.style.transform = `scaleX(${max > 0 ? window.scrollY / max : 0})`;
    pTick = false;
  }
  window.addEventListener('scroll', () => {
    if (!pTick) { pTick = true; requestAnimationFrame(setProgress); }
  }, { passive: true });
  window.addEventListener('resize', setProgress, { passive: true });
  setProgress();
}

// ---------- AJAX form submit (Formspree) ----------
document.querySelectorAll('form[action*="formspree"]').forEach(form => {
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    const orig = btn.textContent;
    btn.disabled = true; btn.textContent = 'Sending…';
    try {
      const res = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { 'Accept': 'application/json' }
      });
      if (res.ok) {
        form.innerHTML = '<p class="form-success"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 9 L8 15 L17 4"/></svg>You\'re on the list. We\'ll be in touch.</p>';
      } else { throw new Error(); }
    } catch {
      btn.disabled = false; btn.textContent = orig;
      let err = form.querySelector('.form-error');
      if (!err) {
        err = document.createElement('p');
        err.className = 'form-error';
        err.textContent = "That didn't go through. Try again, or email us directly.";
        form.appendChild(err);
      }
    }
  });
});
