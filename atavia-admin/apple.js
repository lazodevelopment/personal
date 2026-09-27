/* ============================================================================
   apple.js — fluid-interface behaviour for the Atavia admin
   Shared by index.html, leads.html and visitors.html. No dependencies, no build.

   The whole file is driven by one idea: motion starts from the value that is
   currently on screen, inherits the pointer's velocity, projects that momentum
   forward, and can be grabbed and reversed at any instant. Springs are what
   make that natural — they are interruptible and velocity-aware by definition,
   which CSS transitions and keyframes are not.

   It attaches itself by observing the DOM (classes, scroll, pointer events), so
   none of the page modules had to change to get any of this.
   ============================================================================ */

const RM = matchMedia('(prefers-reduced-motion: reduce)');
const reduced = () => RM.matches;
const clamp = (v, lo, hi) => v < lo ? lo : v > hi ? hi : v;

/* ---------------------------------------------------------------------------
   1. Spring
   Apple's two designer-facing parameters rather than mass/stiffness/damping:

     damping  — 1.0 is critically damped (no overshoot). Below 1.0 overshoots.
     response — how fast it reaches the target, in seconds. Not a duration: a
                spring has no fixed duration, the settle time falls out of the
                parameters.

   Re-targeting mid-flight keeps the current value AND the current velocity, so
   a reversal blends instead of hitting a brick wall.
--------------------------------------------------------------------------- */
class Spring {
  constructor(value, { damping = 1, response = 0.4, onUpdate, onRest, epsilon = 0.0015 } = {}) {
    this.value = value; this.target = value; this.velocity = 0;
    this.damping = damping; this.response = response;
    this.onUpdate = onUpdate; this.onRest = onRest; this.epsilon = epsilon;
  }
  /* Jump straight to a value (used to seed from the presentation value). */
  set(value, velocity = 0) {
    halt(this);
    this.value = this.target = value; this.velocity = velocity;
    this.onUpdate?.(this.value);
  }
  /* Re-target. Velocity carries over unless handed a new one (§ velocity
     handoff: the release velocity of the gesture). */
  to(target, { velocity, damping, response } = {}) {
    this.target = target;
    if (velocity !== undefined) this.velocity = velocity;
    if (damping !== undefined) this.damping = damping;
    if (response !== undefined) this.response = response;
    if (reduced()) {                       // non-vestibular equivalent: no travel
      this.value = target; this.velocity = 0;
      halt(this); this.onUpdate?.(this.value); this.onRest?.(this.value);
      return;
    }
    run(this);
  }
  stop() { this.velocity = 0; halt(this); }
  advance(dt) {
    const w = 2 * Math.PI / this.response, z = this.damping;
    /* Sub-step so one long frame can't blow the integrator up. */
    let left = dt;
    while (left > 0) {
      const h = Math.min(left, 1 / 240); left -= h;
      const a = -w * w * (this.value - this.target) - 2 * z * w * this.velocity;
      this.velocity += a * h;
      this.value += this.velocity * h;
    }
    const scale = Math.max(1, Math.abs(this.target));
    if (Math.abs(this.value - this.target) < this.epsilon * scale &&
        Math.abs(this.velocity) < this.epsilon * scale * 8) {
      this.value = this.target; this.velocity = 0;
      halt(this); this.onUpdate?.(this.value); this.onRest?.(this.value);
      return;
    }
    this.onUpdate?.(this.value);
  }
}

/* One display-synced clock for every spring on the page. */
const living = new Set();
let rafId = 0, lastT = 0;
function run(s) {
  if (living.has(s)) return;
  living.add(s);
  if (!rafId) { lastT = performance.now(); rafId = requestAnimationFrame(tick); }
}
function halt(s) {
  living.delete(s);
  if (!living.size && rafId) { cancelAnimationFrame(rafId); rafId = 0; }
}
function tick(now) {
  const dt = Math.min((now - lastT) / 1000, 1 / 30);
  lastT = now;
  for (const s of [...living]) s.advance(dt);
  rafId = living.size ? requestAnimationFrame(tick) : 0;
}

/* ---------------------------------------------------------------------------
   2. Momentum projection — where is this flick actually going?
   The exponential-decay form Apple ships, not the v^2/(2a) from physics class.
   Same curve as scroll deceleration, which is why it feels native.
--------------------------------------------------------------------------- */
const project = (velocity, decelerationRate = 0.998) =>
  (velocity / 1000) * decelerationRate / (1 - decelerationRate);

/* Soft boundary: the further past the edge, the less it follows. Real things
   slow down before they stop; they don't hit a wall. */
const rubberband = (overshoot, dimension, constant = 0.55) =>
  (overshoot * dimension * constant) / (dimension + constant * Math.abs(overshoot));

/* A short position history is what velocity at release is read from — the last
   single pointermove is far too noisy. */
class Tracker {
  constructor() { this.points = []; }
  push(v) {
    const t = performance.now();
    this.points.push({ t, v });
    while (this.points.length > 6 || (this.points.length > 2 && t - this.points[0].t > 110))
      this.points.shift();
  }
  velocity() {                                   // px/s
    const p = this.points;
    if (p.length < 2) return 0;
    const a = p[0], b = p[p.length - 1], dt = (b.t - a.t) / 1000;
    return dt > 0.004 ? (b.v - a.v) / dt : 0;
  }
  reset() { this.points.length = 0; }
}

/* ---------------------------------------------------------------------------
   3. Response — feedback on pointer-down, never on click
   The moment feedback waits for touch-up, directness falls off a cliff. Includes
   ~10px of hysteresis so a press can be cancelled by dragging away, and
   restored by coming back.
--------------------------------------------------------------------------- */
const PRESSABLE = '.btn,.chip,.nav a,.stat,.nx,.cev,.cal .nav2 button,.zoomctl button,' +
                  '.note .x,.link,tbody tr.row,.modal .macts .btn';
{
  let el = null, ox = 0, oy = 0, pid = null;
  const SLOP = 10;
  const release = () => { el?.classList.remove('is-pressed'); el = null; pid = null; };

  document.addEventListener('pointerdown', e => {
    if (e.button && e.button !== 0) return;
    const t = e.target.closest(PRESSABLE);
    if (!t) return;
    el = t; pid = e.pointerId; ox = e.clientX; oy = e.clientY;
    el.classList.add('is-pressed');
  }, true);

  document.addEventListener('pointermove', e => {
    if (!el || e.pointerId !== pid) return;
    const away = Math.hypot(e.clientX - ox, e.clientY - oy) > SLOP;
    el.classList.toggle('is-pressed', !away);
  }, true);

  for (const ev of ['pointerup', 'pointercancel', 'blur'])
    document.addEventListener(ev, release, true);
}

/* ---------------------------------------------------------------------------
   4. Scroll edge effects
   Floating chrome separates from content with a soft fading edge, and only once
   there is something behind it to separate from.
--------------------------------------------------------------------------- */
{
  let queued = false;
  const sync = () => {
    queued = false;
    document.body.classList.toggle('at-edge', window.scrollY > 6);
  };
  addEventListener('scroll', () => { if (!queued) { queued = true; requestAnimationFrame(sync); } },
                   { passive: true });
  sync();
}

/* Horizontal scrollers: mask only the edge that actually has more beyond it. */
function watchEdges(el) {
  const sync = () => {
    const max = el.scrollWidth - el.clientWidth;
    el.classList.toggle('edge-start', el.scrollLeft <= 1);
    el.classList.toggle('edge-end', el.scrollLeft >= max - 1 || max <= 1);
  };
  el.addEventListener('scroll', sync, { passive: true });
  new ResizeObserver(sync).observe(el);
  new MutationObserver(sync).observe(el, { childList: true });
  sync();
}

/* ---------------------------------------------------------------------------
   5. Drag-to-scroll with momentum (mouse only — touch already has its own)
   1:1 while the pointer is down, then a flick projects forward and snaps to the
   card nearest where the momentum was actually headed.
--------------------------------------------------------------------------- */
function dragScroll(el, snapSelector) {
  const track = new Tracker();
  const spring = new Spring(0, {
    damping: 1, response: 0.45, epsilon: 0.02,
    onUpdate: v => { el.scrollLeft = v; },
  });
  let id = null, x0 = 0, sl0 = 0, moved = false;

  el.addEventListener('pointerdown', e => {
    if (e.pointerType !== 'mouse' || e.button !== 0 || reduced()) return;
    spring.stop();                       // interruptible: grab it mid-flight
    id = e.pointerId; x0 = e.clientX; sl0 = el.scrollLeft; moved = false;
    track.reset(); track.push(el.scrollLeft);
  });

  el.addEventListener('pointermove', e => {
    if (e.pointerId !== id) return;
    const dx = e.clientX - x0;
    if (!moved) {
      if (Math.abs(dx) < 10) return;     // hysteresis before committing to a drag
      moved = true;
      el.classList.add('dragging');
      el.setPointerCapture(id);          // keep tracking outside the bounds
    }
    el.scrollLeft = sl0 - dx;            // content stays glued to the pointer
    track.push(el.scrollLeft);
    e.preventDefault();
  });

  const end = e => {
    if (e.pointerId !== id) return;
    id = null;
    if (!moved) return;
    el.classList.remove('dragging');
    const v = track.velocity();
    const max = el.scrollWidth - el.clientWidth;
    let dest = clamp(el.scrollLeft + project(v), 0, max);

    if (snapSelector) {                  // snap to whatever the flick was aimed at
      let best = null, bestD = Infinity;
      for (const card of el.querySelectorAll(snapSelector)) {
        const d = Math.abs(card.offsetLeft - el.offsetLeft - dest);
        if (d < bestD) { bestD = d; best = card; }
      }
      if (best) dest = clamp(best.offsetLeft - el.offsetLeft, 0, max);
    }
    spring.set(el.scrollLeft);
    spring.to(dest, { velocity: v, damping: 0.85, response: 0.4 }); // flick → a little bounce

    /* A drag must not also open the card underneath it. Swallow only the click
       that this gesture itself produces — disarm on the next tick so a genuine
       click later on isn't eaten. */
    const swallow = ev => { ev.stopPropagation(); ev.preventDefault(); disarm(); };
    const disarm = () => el.removeEventListener('click', swallow, true);
    el.addEventListener('click', swallow, true);
    setTimeout(disarm, 0);
  };
  el.addEventListener('pointerup', end);
  el.addEventListener('pointercancel', end);
}

/* ---------------------------------------------------------------------------
   6. The questionnaire sheet
   Materialises out of the control that opened it, dismisses back along the same
   path, and can be grabbed and thrown away at any point — including while it is
   still arriving.
--------------------------------------------------------------------------- */
function wireSheet(modal) {
  const sheet = modal.querySelector('.sheet');
  if (!sheet) return;

  const setM = v => modal.style.setProperty('--m', v.toFixed(4));
  const setDrag = v => modal.style.setProperty('--drag', v.toFixed(2) + 'px');

  const m = new Spring(0, { onUpdate: setM, onRest: v => { if (v === 0) finishExit(); } });
  const drag = new Spring(0, { onUpdate: setDrag });

  let open = false, dismissing = false;

  /* Anchor the sheet to whatever was last pressed, so the spatial relationship
     between the control and the content it opened is obvious. */
  let origin = null;
  document.addEventListener('pointerdown', e => { origin = { x: e.clientX, y: e.clientY }; }, true);

  function anchor() {
    if (!origin) { sheet.style.transformOrigin = '50% 0'; return; }
    const r = sheet.getBoundingClientRect();
    if (!r.width) { sheet.style.transformOrigin = '50% 0'; return; }
    sheet.style.transformOrigin =
      `${clamp(origin.x - r.left, 0, r.width).toFixed(1)}px ${clamp(origin.y - r.top, 0, r.height).toFixed(1)}px`;
  }

  function enter() {
    open = true; dismissing = false;
    modal.classList.remove('a-exit');
    document.body.classList.add('modal-open');
    drag.set(0); m.set(0);
    anchor();
    m.to(1, { damping: 1, response: 0.42 });     // arriving unprompted: no overshoot
  }

  function exit() {
    open = false;
    modal.classList.add('a-exit');               // keep it painted while it leaves
    m.to(0, { damping: 1, response: 0.3 });      // mirrors the way it came in
  }

  function finishExit() {
    modal.classList.remove('a-exit', 'grabbing');
    document.body.classList.remove('modal-open');
    drag.set(0); dismissing = false;
  }

  /* The page's own module owns open/close; we just watch the class it toggles. */
  new MutationObserver(() => {
    const showing = modal.classList.contains('show');
    if (showing && !open) enter();
    else if (!showing && open) exit();
  }).observe(modal, { attributes: true, attributeFilter: ['class'] });

  /* --- drag to dismiss ---------------------------------------------------- */
  const track = new Tracker();
  let id = null, y0 = 0, base = 0, committed = false;

  sheet.addEventListener('pointerdown', e => {
    if (reduced() || dismissing) return;
    if (e.button && e.button !== 0) return;
    if (e.target.closest('button,a,input,textarea,select')) return;
    const r = sheet.getBoundingClientRect();
    /* The header is the grab area, plus the handle strip above it with ~10px of
       hit padding — the handle is only 4px tall but nobody aims that precisely. */
    const grabbable = e.target.closest('.mhead') || (e.clientY - r.top) <= 44;
    if (!grabbable) return;
    drag.stop();
    id = e.pointerId; y0 = e.clientY; base = drag.value; committed = false;
    track.reset(); track.push(base);
  });

  sheet.addEventListener('pointermove', e => {
    if (e.pointerId !== id) return;
    let dy = base + (e.clientY - y0);
    if (!committed) {
      if (Math.abs(dy - base) < 8) return;
      committed = true;
      sheet.setPointerCapture(id);
      modal.classList.add('grabbing');
    }
    /* Down is the dismiss direction and tracks 1:1. Up has nowhere to go, so it
       resists progressively rather than stopping dead. */
    if (dy < 0) dy = -rubberband(-dy, window.innerHeight);
    drag.set(dy);
    track.push(dy);
    e.preventDefault();
  });

  const release = e => {
    if (e.pointerId !== id) return;
    id = null;
    if (!committed) return;
    committed = false;
    modal.classList.remove('grabbing');

    const v = track.velocity();
    const height = sheet.getBoundingClientRect().height || window.innerHeight;
    /* Decide on where the gesture was going, not on where the finger stopped. */
    const landing = drag.value + project(v);
    const commit = landing > Math.min(height * 0.28, 190) || v > 650;

    if (commit) {
      dismissing = true;
      /* Keep going at the finger's speed — no seam between drag and animation. */
      drag.to(height + 120, { velocity: v, damping: 1, response: 0.32 });
      /* Hand the actual close back to the page's own handler. */
      modal.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    } else {
      drag.to(0, { velocity: v, damping: 0.8, response: 0.35 }); // a flick preceded it
    }
  };
  sheet.addEventListener('pointerup', release);
  sheet.addEventListener('pointercancel', release);

  /* A grab mid-drag must never be eaten by a text selection. */
  sheet.addEventListener('dragstart', e => { if (committed) e.preventDefault(); });
}

/* ---------------------------------------------------------------------------
   7. Toast & map tooltip — same path in, same path out
--------------------------------------------------------------------------- */
function wireFader(el, opts = {}) {
  const spring = new Spring(0, {
    onUpdate: v => el.style.setProperty('--t', v.toFixed(4)),
    onRest: v => { if (v === 0 && opts.hideOnRest) el.style.visibility = 'hidden'; },
  });
  let shown = false;
  new MutationObserver(() => {
    const showing = el.classList.contains('show');
    if (showing === shown) return;
    shown = showing;
    if (showing) {
      el.style.visibility = '';
      spring.to(1, { damping: 1, response: opts.inResponse ?? 0.34 });
    } else {
      spring.to(0, { damping: 1, response: opts.outResponse ?? 0.26 });
    }
  }).observe(el, { attributes: true, attributeFilter: ['class'] });
}

/* ---------------------------------------------------------------------------
   Wire up whatever this page happens to have.
--------------------------------------------------------------------------- */
const $ = s => document.querySelector(s);

for (const el of document.querySelectorAll('.rail,.chips')) watchEdges(el);
const rail = $('.rail');
if (rail) dragScroll(rail, '.nx');

const modal = $('.modal');
if (modal) wireSheet(modal);

const toast = $('.toast');
if (toast) wireFader(toast);

/* The tooltip is repositioned every mousemove, so it must not be display:none
   while it settles — swap the page's display toggle for visibility. */
const tip = $('.tip');
if (tip) {
  tip.style.display = 'block';
  tip.style.visibility = 'hidden';
  wireFader(tip, { hideOnRest: true, inResponse: 0.22, outResponse: 0.18 });
}

/* Reduced motion can be toggled while the page is open; settle everything
   in flight immediately rather than letting it keep swinging. */
RM.addEventListener?.('change', () => {
  if (!reduced()) return;
  for (const s of [...living]) s.to(s.target);
});
