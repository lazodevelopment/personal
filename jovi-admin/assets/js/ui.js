// Tiny UI kit: DOM builder, formatters, tables, drawers, modals, toasts.
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === 'html') el.innerHTML = v;
    else if (k === 'dataset') Object.assign(el.dataset, v);
    else if (v === true) el.setAttribute(k, '');
    else el.setAttribute(k, v);
  }
  for (const c of children.flat(Infinity)) {
    if (c == null || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}
export const frag = (...kids) => { const f = document.createDocumentFragment(); kids.flat(Infinity).forEach(k => k != null && k !== false && f.append(k instanceof Node ? k : document.createTextNode(String(k)))); return f; };
export function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }
export function esc(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }

// ── Formatters ──────────────────────────────────────────────────────────
export const money = (n, opts = {}) => {
  const v = Number(n);
  if (!isFinite(v)) return '—';
  return v.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: opts.cents === false ? 0 : 2, maximumFractionDigits: 2 });
};
export function toDate(v) {
  if (!v) return null;
  if (v instanceof Date) return v;
  if (typeof v.toDate === 'function') return v.toDate();
  if (typeof v === 'object' && 'seconds' in v) return new Date(v.seconds * 1000);
  if (typeof v === 'number') return new Date(v);
  if (typeof v === 'string') { const d = new Date(v); return isNaN(d) ? null : d; }
  return null;
}
export const fmtDate = (v, o = {}) => { const d = toDate(v); return d ? d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', ...o }) : '—'; };
export const fmtDateTime = v => { const d = toDate(v); return d ? d.toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' }) : '—'; };
export const fmtTime = v => { const d = toDate(v); return d ? d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : '—'; };
export function ago(v) {
  const d = toDate(v); if (!d) return '—';
  const s = (Date.now() - d.getTime()) / 1000; const a = Math.abs(s); const f = s < 0 ? 'in ' : ''; const suf = s < 0 ? '' : ' ago';
  if (a < 60) return 'just now';
  if (a < 3600) return `${f}${Math.round(a / 60)} min${suf}`;
  if (a < 86400) return `${f}${Math.round(a / 3600)} h${suf}`;
  if (a < 86400 * 14) return `${f}${Math.round(a / 86400)} d${suf}`;
  return fmtDate(d);
}
export function age(dob) { const d = toDate(dob); if (!d) return null; const n = new Date(); let a = n.getFullYear() - d.getFullYear(); const m = n.getMonth() - d.getMonth(); if (m < 0 || (m === 0 && n.getDate() < d.getDate())) a--; return a; }
// App stores appointmentDate as "yyyy-MM-ddT00:00:00" + appointmentTime "HH:mm" (local wall clock).
export function apptWhen(dateStr, timeStr) {
  if (!dateStr) return null;
  const day = String(dateStr).slice(0, 10);
  const t = (timeStr && /^\d{1,2}:\d{2}/.test(timeStr)) ? timeStr.slice(0, 5) : '00:00';
  const d = new Date(`${day}T${t}:00`);
  return isNaN(d) ? null : d;
}
export const todayStr = (d = new Date()) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
export const initials = name => String(name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join('') || '?';
export const title = s => String(s || '').replace(/[_-]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
export const phone = p => { const d = String(p || '').replace(/\D/g, ''); return d.length === 10 ? `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}` : (p || '—'); };
export const pct = (a, b) => (b ? Math.round((a / b) * 100) : 0);

// ── Status badges ───────────────────────────────────────────────────────
const TONES = {
  green: ['active', 'confirmed', 'completed', 'approved', 'paid', 'ready', 'filled', 'success', 'resolved', 'closed', 'available'],
  amber: ['pending', 'requested', 'processing', 'in_progress', 'under_review', 'review', 'past_due', 'canceling', 'submitted', 'open', 'scheduled'],
  red: ['denied', 'rejected', 'cancelled', 'canceled', 'failed', 'suspended', 'overdue', 'error', 'no_show'],
  blue: ['new', 'info', 'telehealth', 'clinic'],
};
export function tone(status) { const s = String(status || '').toLowerCase(); for (const [t, list] of Object.entries(TONES)) if (list.includes(s)) return t; return 'gray'; }
export const badge = (status, label) => h('span', { class: `badge badge-${tone(status)}` }, label ?? title(status || 'unknown'));
export const pill = (text, cls = '') => h('span', { class: `pill ${cls}` }, text);
export const avatar = (name, url, size = 34) => url
  ? h('img', { class: 'avatar', src: url, alt: '', style: { width: size + 'px', height: size + 'px' } })
  : h('span', { class: 'avatar avatar-txt', style: { width: size + 'px', height: size + 'px', fontSize: Math.round(size * .38) + 'px' } }, initials(name));

// ── Layout pieces ───────────────────────────────────────────────────────
export function pageHeader(titleText, subtitle, actions = []) {
  return h('div', { class: 'page-head' },
    h('div', null, h('h1', null, titleText), subtitle ? h('p', { class: 'muted' }, subtitle) : null),
    actions.length ? h('div', { class: 'page-actions' }, actions) : null);
}
export const card = (...kids) => h('section', { class: 'card' }, kids);
export const cardHead = (t, right) => h('div', { class: 'card-head' }, h('h3', null, t), right || null);
export const stat = (label, value, sub, tone = '') => h('div', { class: `stat ${tone}` }, h('span', { class: 'stat-label' }, label), h('b', { class: 'stat-value' }, value), sub ? h('span', { class: 'stat-sub' }, sub) : null);
export const empty = (msg, sub) => h('div', { class: 'empty' }, h('div', { class: 'empty-ico' }, '◌'), h('b', null, msg), sub ? h('span', null, sub) : null);
export const spinner = (label = 'Loading…') => h('div', { class: 'spinner-wrap' }, h('span', { class: 'spinner' }), h('span', { class: 'muted' }, label));
export const kv = (k, v) => h('div', { class: 'kv' }, h('span', { class: 'k' }, k), h('span', { class: 'v' }, v ?? '—'));
export const btn = (label, onClick, opts = {}) => h('button', { class: `btn ${opts.variant || 'btn-secondary'} ${opts.size || ''} ${opts.class || ''}`, type: opts.type || 'button', disabled: opts.disabled, title: opts.title, onClick }, opts.icon ? h('span', { class: 'ico', html: opts.icon }) : null, label);
export const tabs = (items, active, onPick) => h('div', { class: 'tabs', role: 'tablist' }, items.map(([key, label, count]) => h('button', { class: `tab ${key === active ? 'on' : ''}`, role: 'tab', 'aria-selected': key === active ? 'true' : 'false', onClick: () => onPick(key) }, label, count != null ? h('span', { class: 'tab-count' }, count) : null)));

// ── Forms ───────────────────────────────────────────────────────────────
export function field(label, input, hint) { return h('label', { class: 'field' }, h('span', { class: 'field-label' }, label), input, hint ? h('span', { class: 'field-hint' }, hint) : null); }
export const input = (attrs = {}) => h('input', { class: 'input', ...attrs });
export const textarea = (attrs = {}) => h('textarea', { class: 'input textarea', rows: 4, ...attrs });
export function select(options, value, attrs = {}) {
  const s = h('select', { class: 'input', ...attrs });
  for (const o of options) { const [v, l] = Array.isArray(o) ? o : [o, title(o)]; s.append(h('option', { value: v, selected: v === value ? true : null }, l)); }
  return s;
}
export const checkbox = (label, checked, attrs = {}) => h('label', { class: 'check' }, h('input', { type: 'checkbox', checked: checked ? true : null, ...attrs }), h('span', null, label));
export function formValues(root) { const o = {}; root.querySelectorAll('[name]').forEach(el => { o[el.name] = el.type === 'checkbox' ? el.checked : el.type === 'number' ? (el.value === '' ? null : Number(el.value)) : el.value; }); return o; }

// ── Table ───────────────────────────────────────────────────────────────
/** columns: [{key,label,render?(row),width?,align?,sort?}], rows: array, opts: {onRow, empty, rowClass} */
export function table(columns, rows, opts = {}) {
  const t = h('table', { class: 'table' });
  t.append(h('thead', null, h('tr', null, columns.map(c => h('th', { style: c.width ? { width: c.width } : null, class: c.align ? `al-${c.align}` : '' }, c.label)))));
  const tb = h('tbody');
  if (!rows.length) tb.append(h('tr', null, h('td', { colspan: columns.length }, empty(opts.empty || 'Nothing here yet', opts.emptySub))));
  for (const r of rows) {
    const tr = h('tr', { class: `${opts.onRow ? 'clickable' : ''} ${opts.rowClass ? opts.rowClass(r) : ''}`, onClick: opts.onRow ? (e) => { if (e.target.closest('button,a,input,select')) return; opts.onRow(r); } : null });
    for (const c of columns) { const v = c.render ? c.render(r) : r[c.key]; tr.append(h('td', { class: c.align ? `al-${c.align}` : '' }, v instanceof Node ? v : (v ?? '—'))); }
    tb.append(tr);
  }
  t.append(tb);
  return h('div', { class: 'table-wrap' }, t);
}
export function searchBox(placeholder, onChange, value = '') {
  const i = input({ type: 'search', placeholder, value, class: 'input search' });
  let tm; i.addEventListener('input', () => { clearTimeout(tm); tm = setTimeout(() => onChange(i.value.trim()), 180); });
  return i;
}

// ── Drawer / modal / toast / confirm ────────────────────────────────────
export function drawer(titleText, body, opts = {}) {
  closeDrawer();
  const root = h('div', { class: `drawer-root ${opts.wide ? 'wide' : ''}` },
    h('div', { class: 'drawer-scrim', onClick: closeDrawer }),
    h('aside', { class: 'drawer', role: 'dialog', 'aria-label': titleText },
      h('div', { class: 'drawer-head' }, h('h2', null, titleText), opts.actions ? h('div', { class: 'drawer-actions' }, opts.actions) : null, h('button', { class: 'icon-btn', 'aria-label': 'Close', onClick: closeDrawer }, '✕')),
      h('div', { class: 'drawer-body' }, body)));
  document.body.append(root);
  document.body.classList.add('drawer-open');
  requestAnimationFrame(() => root.classList.add('in'));
  const onKey = e => { if (e.key === 'Escape') closeDrawer(); };
  document.addEventListener('keydown', onKey);
  root._onKey = onKey;
  return root;
}
export function closeDrawer() {
  const r = document.querySelector('.drawer-root'); if (!r) return;
  document.removeEventListener('keydown', r._onKey);
  r.classList.remove('in'); document.body.classList.remove('drawer-open');
  setTimeout(() => r.remove(), 220);
}
export function modal(titleText, body, actions = []) {
  const root = h('div', { class: 'modal-root' },
    h('div', { class: 'modal-scrim' }),
    h('div', { class: 'modal', role: 'dialog', 'aria-modal': 'true', 'aria-label': titleText },
      h('h2', null, titleText), h('div', { class: 'modal-body' }, body),
      h('div', { class: 'modal-actions' }, actions)));
  document.body.append(root); requestAnimationFrame(() => root.classList.add('in'));
  root.close = () => { root.classList.remove('in'); setTimeout(() => root.remove(), 180); };
  return root;
}
export function confirm(titleText, message, { okLabel = 'Confirm', danger = false } = {}) {
  return new Promise(res => {
    const m = modal(titleText, h('p', null, message), [
      btn('Cancel', () => { m.close(); res(false); }),
      btn(okLabel, () => { m.close(); res(true); }, { variant: danger ? 'btn-danger' : 'btn-primary' }),
    ]);
  });
}
export function prompt(titleText, label, { placeholder = '', multiline = false, okLabel = 'Save', value = '' } = {}) {
  return new Promise(res => {
    const inp = multiline ? textarea({ placeholder, value }) : input({ placeholder, value });
    const m = modal(titleText, field(label, inp), [btn('Cancel', () => { m.close(); res(null); }), btn(okLabel, () => { m.close(); res(inp.value.trim()); }, { variant: 'btn-primary' })]);
    setTimeout(() => inp.focus(), 50);
  });
}
export function toast(msg, kind = 'info', ms = 3400) {
  let host = document.querySelector('.toasts'); if (!host) { host = h('div', { class: 'toasts' }); document.body.append(host); }
  const t = h('div', { class: `toast toast-${kind}` }, msg); host.append(t);
  requestAnimationFrame(() => t.classList.add('in'));
  setTimeout(() => { t.classList.remove('in'); setTimeout(() => t.remove(), 250); }, ms);
}
export const errorToast = (e, fallback = 'Something went wrong') => { console.error(e); toast(friendlyError(e) || fallback, 'error', 5000); };
export function friendlyError(e) {
  const c = e && (e.code || '');
  if (c.includes('permission-denied')) return 'Permission denied by Firestore rules. Your staff role may not allow this, or the rules have not been deployed yet.';
  if (c.includes('failed-precondition') && /index/i.test(e.message || '')) return 'This query needs a Firestore index. Open the browser console for the create-index link.';
  if (c.includes('unauthenticated')) return 'You are signed out.';
  return e && e.message ? e.message.replace(/^Firebase: /, '').replace(/\(auth\/.*\)\.?$/, '').trim() : '';
}

// ── CSV export ──────────────────────────────────────────────────────────
export function downloadCsv(filename, columns, rows) {
  const q = v => { const s = v == null ? '' : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  const lines = [columns.map(c => q(c.label)).join(',')];
  for (const r of rows) lines.push(columns.map(c => q(typeof c.csv === 'function' ? c.csv(r) : (c.csv ? r[c.csv] : r[c.key]))).join(','));
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
  const a = h('a', { href: URL.createObjectURL(blob), download: filename }); document.body.append(a); a.click(); a.remove();
}

// ── Misc ────────────────────────────────────────────────────────────────
export const sum = (arr, f) => arr.reduce((a, x) => a + (Number(typeof f === 'function' ? f(x) : x[f]) || 0), 0);
export const groupBy = (arr, f) => arr.reduce((m, x) => { const k = typeof f === 'function' ? f(x) : x[f]; (m[k] ||= []).push(x); return m; }, {});
export const sortBy = (arr, f, desc = false) => [...arr].sort((a, b) => { const va = typeof f === 'function' ? f(a) : a[f], vb = typeof f === 'function' ? f(b) : b[f]; return (va > vb ? 1 : va < vb ? -1 : 0) * (desc ? -1 : 1); });
export const debounce = (fn, ms = 200) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
export const uid = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
