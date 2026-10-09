// Shell: login, sidebar per side/role, topbar, global member search, route mounting.
import { h, clear, btn, input, field, toast, errorToast, avatar, searchBox } from './ui.js';
import { session, onSession, signIn, logOut, canSide, can, resetPassword } from './auth.js';
import { register, mount, navigate, current } from './router.js';
import { db, collection, query, where, orderBy, limit, getDocs } from './firebase.js';
import { watchCounts } from './data.js';
const COUNT_KEYS = { '/ehr/schedule': 'pending', '/ehr/inbox': 'pending', '/ehr/refills': 'refills', '/ehr/messages': 'tickets', '/admin/support': 'tickets', '/admin/appointments': 'pending' };
let counts = {}, stopCounts = null;

const I = {
  dash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="5" rx="2"/><rect x="13" y="11" width="8" height="10" rx="2"/><rect x="3" y="14" width="8" height="7" rx="2"/></svg>',
  people: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0"/><path d="M17 4a4 4 0 0 1 0 8M22 21a7 7 0 0 0-5-6.7"/></svg>',
  card: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="5" width="20" height="14" rx="3"/><path d="M2 10h20"/></svg>',
  receipt: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M5 3h14v18l-2.5-1.5L14 21l-2-1.5L10 21l-2.5-1.5L5 21z"/><path d="M9 8h6M9 12h6"/></svg>',
  cal: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>',
  chat: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M21 14a3 3 0 0 1-3 3H8l-5 4V6a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3z"/></svg>',
  pill: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7z"/><path d="m8.5 8.5 7 7"/></svg>',
  clinic: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M3 21V8l9-5 9 5v13"/><path d="M9 21v-6h6v6M12 10v4M10 12h4"/></svg>',
  shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
  chart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 20V10M10 20V4M16 20v-8M22 20H2"/></svg>',
  tag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><circle cx="7.5" cy="7.5" r="1.5"/></svg>',
  log: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 6h16M4 12h10M4 18h7"/></svg>',
  inbox: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M3 13h5l2 3h4l2-3h5"/><path d="M5 4h14l2 9v7H3v-7z"/></svg>',
  folder: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>',
  paw: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><circle cx="11" cy="4" r="2"/><circle cx="18" cy="8" r="2"/><circle cx="20" cy="16" r="2"/><path d="M9 10a5 5 0 0 1 5 5v3.5a3.5 3.5 0 0 1-6.84 1.045Q6.52 17.48 4.46 16.84A3.5 3.5 0 0 1 5.5 10z"/></svg>',
  lab: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M9 3h6M10 3v6l-6 10a2 2 0 0 0 2 3h12a2 2 0 0 0 2-3l-6-10V3"/></svg>',
  vax: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="m18 2 4 4M14 4l6 6M12 6l6 6-8 8H5v-5z"/></svg>',
  bell: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>',
  menu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
};

// Navigation: [side, group, [path, label, icon, roles?]]
const NAV = {
  admin: [
    ['Overview', [
      ['/admin/dashboard', 'Dashboard', I.dash],
      ['/admin/analytics', 'Analytics', I.chart],
    ]],
    ['Business', [
      ['/admin/members', 'Members', I.people],
      ['/admin/billing', 'Billing & revenue', I.card],
      ['/admin/invoices', 'Invoices & receipts', I.receipt],
      ['/admin/claims', 'Claims (financial)', I.receipt],
      ['/admin/appointments', 'Appointment volume', I.cal],
      ['/admin/support', 'Support inbox', I.chat],
    ]],
    ['Operations', [
      ['/admin/pharmacies', 'Partner pharmacies', I.pill],
      ['/admin/clinics', 'Clinics', I.clinic],
      ['/admin/promos', 'Promo codes', I.tag],
      ['/admin/notifications', 'Broadcasts', I.bell],
    ]],
    ['Governance', [
      ['/admin/staff', 'Staff & roles', I.shield, ['superadmin']],
      ['/admin/audit', 'Audit log', I.log, ['superadmin', 'admin']],
    ]],
  ],
  ehr: [
    ['Today', [
      ['/ehr/schedule', 'Schedule', I.cal],
      ['/ehr/inbox', 'Clinical inbox', I.inbox],
      ['/ehr/tasks', 'Tasks', I.log],
      ['/ehr/caregaps', 'Care gaps', I.shield],
    ]],
    ['Patients', [
      ['/ehr/patients', 'Patients', I.people],
      ['/ehr/pets', 'Pets', I.paw],
    ]],
    ['Queues', [
      ['/ehr/refills', 'Refill requests', I.pill],
      ['/ehr/claims', 'Claims review', I.receipt],
      ['/ehr/vaccinations', 'Vaccinations due', I.vax],
      ['/ehr/messages', 'Messages', I.chat],
      ['/ehr/orders', 'Orders & results', I.lab],
      ['/ehr/fax', 'Fax', I.folder],
    ]],
    ['Reference', [
      ['/ehr/records', 'Care records', I.folder],
      ['/ehr/templates', 'Templates & phrases', I.log],
    ]],
  ],
};

// Lazy page registry
const P = (side, page) => () => import(`./pages/${side}/${page}.js`);
for (const side of ['admin', 'ehr']) for (const [, items] of NAV[side]) for (const [path] of items) register(path.slice(1), P(side, path.split('/')[2]));
register('ehr/chart', P('ehr', 'chart'));
register('ehr/pet', P('ehr', 'pet'));
register('admin/member', P('admin', 'member'));

const root = document.getElementById('app');
window.addEventListener('error', e => { console.error(e.error || e.message); toast('Error: ' + (e.error?.message || e.message), 'error', 8000); });
window.addEventListener('unhandledrejection', e => { console.error(e.reason); toast('Error: ' + (e.reason?.message || e.reason), 'error', 8000); });
let shell, outlet, sidebar, crumb;

function renderLogin(err) {
  const email = input({ type: 'email', name: 'email', placeholder: 'you@jovihealth.com', autocomplete: 'username', required: true });
  const pass = input({ type: 'password', name: 'password', placeholder: '••••••••', autocomplete: 'current-password', required: true });
  const submit = btn('Sign in', null, { variant: 'btn-primary', type: 'submit' });
  const form = h('form', { onSubmit: async e => { e.preventDefault(); submit.disabled = true; try { await signIn(email.value.trim(), pass.value); } catch (ex) { errorToast(ex, 'Sign in failed'); submit.disabled = false; } } },
    field('Email', email), field('Password', pass), submit,
    h('button', { type: 'button', class: 'btn btn-ghost btn-sm', onClick: async () => { if (!email.value.trim()) return toast('Enter your email first', 'error'); try { await resetPassword(email.value.trim()); toast('Password reset email sent', 'success'); } catch (ex) { errorToast(ex); } } }, 'Set or reset password'));
  clear(root).append(h('div', { class: 'login' }, h('div', { class: 'login-card' },
    h('img', { src: '/assets/img/jovi-logo-navy.png', alt: 'Jovi' }),
    h('h1', null, 'Staff sign in'),
    h('p', null, 'Business admin and clinical workspace. Authorized personnel only.'),
    err ? h('div', { class: 'phi-banner' }, err) : null,
    form,
    h('div', { class: 'login-foot' }, 'Access is logged. Protected health information is visible only to clinical roles. If you need access, ask a Jovi superadmin to add you under Staff & roles.'))));
}

function renderShell() {
  outlet = h('div', { class: 'content' });
  crumb = h('div', { class: 'crumb' });
  sidebar = h('aside', { class: 'sidebar' });
  const gsearch = searchBox(can('viewPhi') ? 'Find a member or patient…' : 'Find a member…', v => globalSearch(v));
  gsearch.classList.add('gsearch');
  gsearch.addEventListener('keydown', e => { if (e.key === 'Enter') globalSearch(gsearch.value.trim(), true); });
  const menuBtn = h('button', { class: 'icon-btn menu-btn', 'aria-label': 'Menu', html: I.menu, onClick: () => sidebar.classList.toggle('open') });
  shell = h('div', { class: 'shell' }, sidebar, h('div', { class: 'main', onClick: () => sidebar.classList.remove('open') }, h('div', { class: 'topbar' }, menuBtn, crumb, gsearch), outlet));
  menuBtn.addEventListener('click', e => e.stopPropagation());
  clear(root).append(shell);
  renderSidebar();
  if (!stopCounts) stopCounts = watchCounts(c => { counts = c; renderSidebar(); });
  startIdleTimer();
  document.addEventListener('keydown', e => { if (e.key === 'F11' || (e.altKey && e.key.toLowerCase() === 'k')) { e.preventDefault(); toggleKiosk(); } });
  document.addEventListener('keydown', e => { if (e.key === '/' && !/input|textarea|select/i.test(e.target.tagName)) { e.preventDefault(); gsearch.focus(); } if (e.key === 'Escape' && searchPop) { searchPop.remove(); searchPop = null; } });
  mount(outlet, (r, meta) => { renderSidebar(); crumb.innerHTML = `${r.side === 'ehr' ? 'Clinical' : 'Business'} <span class="muted">/</span> <b>${labelFor(r)}</b>`; sidebar.classList.remove('open'); });
}
function labelFor(r) { for (const [, items] of NAV[r.side] || []) for (const [p, l] of items) if (p === `/${r.side}/${r.page}`) return l; return r.page === 'chart' ? 'Patient chart' : r.page === 'pet' ? 'Pet chart' : r.page === 'member' ? 'Member' : r.page; }

function renderSidebar() {
  const r = current();
  const side = r.side && canSide(r.side) ? r.side : (canSide('admin') ? 'admin' : 'ehr');
  clear(sidebar);
  sidebar.append(h('a', { class: 'brand', href: '#/' }, h('img', { src: '/assets/img/jovi-logo-white.png', alt: 'Jovi' }), h('span', null, 'staff')));
  if (canSide('admin') && canSide('ehr')) {
    sidebar.append(h('div', { class: 'side-switch' },
      h('button', { class: side === 'admin' ? 'on' : '', onClick: () => navigate('/admin/dashboard') }, 'Business'),
      h('button', { class: side === 'ehr' ? 'on' : '', onClick: () => navigate('/ehr/schedule') }, 'Clinical')));
  }
  for (const [group, items] of NAV[side]) {
    const g = h('div', { class: 'nav-group' }, h('h6', null, group));
    let any = false;
    for (const [path, label, icon, roles] of items) {
      if (roles && !roles.includes(session.role)) continue;
      any = true;
      const n = counts[COUNT_KEYS[path]];
      g.append(h('a', { class: `nav-item ${location.hash === '#' + path ? 'on' : ''}`, href: '#' + path }, h('span', { class: 'ico', html: icon }), label, n ? h('span', { class: 'count' }, n) : null));
    }
    if (any) sidebar.append(g);
  }
  sidebar.append(h('div', { class: 'me' }, avatar(session.staff?.name || session.user.email, null, 32),
    h('div', null, h('b', null, session.staff?.name || session.user.email.split('@')[0]), h('span', null, session.role)),
    h('button', { onClick: () => logOut() }, 'Sign out')));
}

// Global search: members by name/email prefix (Firestore prefix range on onboard_fullName + email).
let searchPop;
async function globalSearch(q, go = false) {
  if (searchPop) { searchPop.remove(); searchPop = null; }
  if (!q || q.length < 2) return;
  try {
    const { findMembers } = await import('./data.js');
    const rows = await findMembers(q, 8);
    if (go && rows.length === 1) return openMember(rows[0].id);
    searchPop = h('div', { class: 'card', style: { position: 'fixed', top: '62px', right: '24px', width: 'min(420px,90vw)', zIndex: 30, padding: '6px' } },
      rows.length ? rows.map(m => h('div', { class: 'list-item', style: { border: 0, cursor: 'pointer' }, onClick: () => { searchPop.remove(); searchPop = null; openMember(m.id); } },
        avatar(m.name, m.photo, 30), h('div', { class: 'grow' }, h('b', null, m.name), h('span', null, m.email || '')))) : h('div', { class: 'empty' }, h('b', null, 'No matches')));
    document.body.append(searchPop);
    const off = e => { if (searchPop && !searchPop.contains(e.target)) { searchPop.remove(); searchPop = null; document.removeEventListener('click', off); } };
    setTimeout(() => document.addEventListener('click', off), 0);
  } catch (e) { errorToast(e); }
}
function openMember(id) { navigate(current().side === 'ehr' && canSide('ehr') ? `/ehr/chart/${id}` : `/admin/member/${id}`); }

// ── Idle timeout & exam-room mode ──────────────────────────────────────
const IDLE_MS = 15 * 60 * 1000; let idleT = null, warnT = null, warned = null;
function startIdleTimer() {
  const reset = () => { clearTimeout(idleT); clearTimeout(warnT); if (warned) { warned.remove(); warned = null; }
    warnT = setTimeout(() => { warned = h('div', { class: 'toast toast-error in', style: { position: 'fixed', left: '50%', bottom: '22px', transform: 'translateX(-50%)', zIndex: 95 } }, 'Signing out in 60 seconds due to inactivity. Move the mouse to stay signed in.'); document.body.append(warned); }, IDLE_MS - 60000);
    idleT = setTimeout(() => { logOut(); toast('Signed out after 15 minutes of inactivity', 'info', 8000); }, IDLE_MS); };
  ['pointerdown', 'keydown', 'scroll', 'touchstart'].forEach(ev => document.addEventListener(ev, reset, { passive: true })); reset();
}
export function toggleKiosk(on) { const k = on == null ? !document.body.classList.contains('kiosk') : on; document.body.classList.toggle('kiosk', k); toast(k ? 'Exam room mode on (Alt+K to exit)' : 'Exam room mode off', 'info'); }
window.joviKiosk = toggleKiosk;

onSession(s => {
  if (!s.user) return renderLogin();
  if (!s.role) return renderLogin(s.error ? 'Could not read your staff record: ' + (s.error.message || '') : `${s.user.email} is signed in but has no active staff record. Ask a superadmin to add you.`);
  if (!shell || !document.body.contains(shell)) renderShell();
});
