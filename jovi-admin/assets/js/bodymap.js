// Body map: front/back human avatar with clickable markers.
// marks: [{ id, view: 'front'|'back', x, y (0..1 of the figure box), type, label, note, at, by }]
import { h, btn, input, select, textarea, field, modal, toast, uid } from './ui.js';

export const MARK_TYPES = [['pain', 'Pain', '#FF6B4A'], ['wound', 'Wound', '#D64545'], ['rash', 'Rash / skin', '#D99A1B'], ['lesion', 'Lesion', '#8A5D00'], ['injury', 'Injury', '#3B6FE0'], ['line', 'IV / line', '#00B894'], ['procedure', 'Procedure site', '#7C3AED'], ['other', 'Other', '#6B7590']];
const color = t => (MARK_TYPES.find(x => x[0] === t) || MARK_TYPES[7])[2];

// Simplified anatomical silhouette in a 200x460 box. Same outline for both views; the back adds a spine and scapula cue.
const FIGURE = `
<path d="M100 14c-14 0-24 11-24 26 0 12 5 22 12 27v9c-10 3-24 8-33 14-11 7-16 15-18 30l-9 70c-1 8 5 12 10 12s9-4 10-10l9-62 4 1-4 62c-1 10 0 20 2 28l3 20v90c0 12 1 22 3 32l6 58c1 9 5 13 12 13s12-4 12-12v-58l4-30 4 30v58c0 8 5 12 12 12s11-4 12-13l6-58c2-10 3-20 3-32v-90l3-20c2-8 3-18 2-28l-4-62 4-1 9 62c1 6 5 10 10 10s11-4 10-12l-9-70c-2-15-7-23-18-30-9-6-23-11-33-14v-9c7-5 12-15 12-27 0-15-10-26-24-26z" fill="#F4F0EA" stroke="#9AA3BA" stroke-width="1.5" stroke-linejoin="round"/>
<path d="M76 40c0-13 10-24 24-24s24 11 24 24" fill="none" stroke="#9AA3BA" stroke-width="1" opacity=".5"/>`;
const FRONT_DETAIL = `<path d="M84 118c8 6 24 6 32 0M100 130v70M86 214c8 4 20 4 28 0" fill="none" stroke="#9AA3BA" stroke-width="1" opacity=".6"/><ellipse cx="100" cy="176" rx="3" ry="4" fill="#9AA3BA" opacity=".4"/>`;
const BACK_DETAIL = `<path d="M100 92v128M74 120c6 12 12 20 22 22M126 120c-6 12-12 20-22 22M84 232c8 6 24 6 32 0" fill="none" stroke="#9AA3BA" stroke-width="1" opacity=".6"/>`;
const REGIONS = [[100, 40, 'head'], [100, 88, 'neck'], [70, 130, 'right shoulder'], [130, 130, 'left shoulder'], [100, 140, 'chest'], [100, 190, 'abdomen'], [40, 200, 'right arm'], [160, 200, 'left arm'], [30, 262, 'right hand'], [170, 262, 'left hand'], [100, 230, 'pelvis'], [82, 300, 'right thigh'], [118, 300, 'left thigh'], [82, 360, 'right knee'], [118, 360, 'left knee'], [82, 410, 'right lower leg'], [118, 410, 'left lower leg'], [82, 450, 'right foot'], [118, 450, 'left foot']];
export function regionFor(view, x, y) {
  let best = 'body', d = 1e9; for (const [rx, ry, name] of REGIONS) { const dx = rx - x * 200, dy = ry - y * 460; const dd = dx * dx + dy * dy; if (dd < d) { d = dd; best = name; } }
  // Mirror left/right on the back view (the figure faces away from the viewer).
  if (view === 'back') best = best.replace(/^left /, 'TMP ').replace(/^right /, 'left ').replace(/^TMP /, 'right ');
  return (view === 'back' ? 'posterior ' : '') + best;
}

/** Renders the body map. Returns an element with .getMarks(). */
export function bodyMap({ marks = [], readOnly = false, onChange = () => {}, height = 420 } = {}) {
  let view = 'front'; let list = marks.map(m => ({ ...m }));
  const wrap = h('div', { class: 'bodymap' });
  const legend = h('div', { class: 'chips' }, MARK_TYPES.map(([k, l, c]) => h('span', { class: 'chip', style: { borderColor: c, color: c, background: '#fff' } }, l)));
  const flip = h('div', { class: 'row' }, btn('Front', () => { view = 'front'; draw(); }, { size: 'btn-sm' }), btn('Back', () => { view = 'back'; draw(); }, { size: 'btn-sm' }), h('span', { class: 'muted small' }, readOnly ? 'Hover a marker for details' : 'Click the figure to add a marker'));
  const stage = h('div', { class: 'bodymap-stage', style: { height: height + 'px' } });
  const listEl = h('div', { class: 'list' });
  wrap.append(flip, stage, listEl, legend);
  function draw() {
    flip.querySelectorAll('.btn').forEach((b, i) => b.classList.toggle('btn-primary', (i === 0 ? 'front' : 'back') === view));
    stage.replaceChildren();
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 200 460'); svg.setAttribute('class', 'bodymap-svg');
    svg.innerHTML = FIGURE + (view === 'front' ? FRONT_DETAIL : BACK_DETAIL);
    for (const m of list.filter(x => x.view === view)) {
      const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      g.innerHTML = `<circle cx="${m.x * 200}" cy="${m.y * 460}" r="8" fill="${color(m.type)}" fill-opacity=".85" stroke="#fff" stroke-width="2"/><text x="${m.x * 200}" y="${m.y * 460 + 3.5}" text-anchor="middle" font-size="9" font-weight="700" fill="#fff">${list.indexOf(m) + 1}</text>`;
      g.style.cursor = 'pointer'; g.setAttribute('data-title', `${m.label || m.type} · ${m.region || ''}${m.note ? ' · ' + m.note : ''}`);
      g.addEventListener('click', e => { e.stopPropagation(); if (!readOnly) edit(m); else toast(g.getAttribute('data-title')); });
      const t = document.createElementNS('http://www.w3.org/2000/svg', 'title'); t.textContent = g.getAttribute('data-title'); g.append(t);
      svg.append(g);
    }
    if (!readOnly) svg.addEventListener('click', e => { const r = svg.getBoundingClientRect(); const box = fitBox(r); const x = (e.clientX - box.x) / box.w, y = (e.clientY - box.y) / box.h; if (x < 0 || x > 1 || y < 0 || y > 1) return; edit({ id: uid(), view, x, y, type: 'pain', label: '', note: '', region: regionFor(view, x, y) }, true); });
    stage.append(svg);
    listEl.replaceChildren(...list.map((m, i) => h('div', { class: 'list-item', style: { padding: '6px 10px' } }, h('span', { class: 'badge', style: { background: color(m.type), color: '#fff' } }, i + 1), h('div', { class: 'grow' }, h('b', null, `${m.label || (MARK_TYPES.find(x => x[0] === m.type) || [])[1] || m.type}`), h('span', null, `${m.region || m.view}${m.note ? ' · ' + m.note : ''}`)), !readOnly ? btn('✕', () => { list = list.filter(x => x !== m); draw(); onChange(list); }, { size: 'btn-sm', variant: 'btn-ghost' }) : null)));
  }
  // The SVG preserves aspect ratio; compute the drawn box inside the element.
  function fitBox(r) { const ar = 200 / 460; let w = r.width, hh = r.height; if (w / hh > ar) { w = hh * ar; } else { hh = w / ar; } return { x: r.x + (r.width - w) / 2, y: r.y + (r.height - hh) / 2, w, h: hh }; }
  function edit(m, isNew = false) {
    const type = select(MARK_TYPES.map(([k, l]) => [k, l]), m.type); const label = input({ value: m.label || '', placeholder: 'Short label, e.g. "Sharp pain 7/10"' }); const note = textarea({ value: m.note || '', rows: 2, placeholder: 'Details' });
    const md = modal(`${isNew ? 'Add' : 'Edit'} marker · ${m.region || ''}`, h('div', { class: 'col' }, field('Type', type), field('Label', label), field('Note', note)), [
      btn('Cancel', () => md.close()),
      !isNew ? btn('Remove', () => { list = list.filter(x => x.id !== m.id); md.close(); draw(); onChange(list); }, { variant: 'btn-danger' }) : null,
      btn('Save', () => { Object.assign(m, { type: type.value, label: label.value.trim(), note: note.value.trim(), at: m.at || new Date().toISOString() }); if (isNew) list.push(m); md.close(); draw(); onChange(list); }, { variant: 'btn-primary' }),
    ].filter(Boolean));
  }
  draw();
  wrap.getMarks = () => list;
  return wrap;
}
