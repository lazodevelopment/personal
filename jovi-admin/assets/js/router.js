// Hash router: #/side/page/param. Each page module exports render(ctx) -> Node | Promise<Node>.
import { h, clear, spinner, errorToast, empty } from './ui.js';
import { session, canSide } from './auth.js';

const routes = new Map();
export function register(path, loader, meta = {}) { routes.set(path, { loader, meta }); }
export function navigate(path) { location.hash = '#' + path; }
export function current() { const p = location.hash.replace(/^#\/?/, ''); const parts = p.split('/').filter(Boolean); return { side: parts[0] || '', page: parts[1] || '', param: parts.slice(2).join('/'), parts }; }

let outlet, onRouteChange = () => {}, teardown = null;
export function mount(el, onChange) { outlet = el; onRouteChange = onChange; window.addEventListener('hashchange', run); run(); }

export async function run() {
  if (!outlet) return;
  if (teardown) { try { teardown(); } catch {} teardown = null; }
  const r = current();
  if (!session.role) return; // app.js shows login
  if (!r.side) { navigate(canSide('ehr') && session.role === 'clinician' ? '/ehr/schedule' : '/admin/dashboard'); return; }
  if (!canSide(r.side)) { navigate(canSide('ehr') ? '/ehr/schedule' : '/admin/dashboard'); return; }
  const key = `${r.side}/${r.page}`;
  const route = routes.get(key) || routes.get(`${r.side}/`);
  onRouteChange(r, route?.meta || {});
  clear(outlet).append(spinner());
  try {
    const mod = await route.loader();
    const ctx = { ...r, outlet, setTeardown: fn => { teardown = fn; } };
    const node = await mod.render(ctx);
    clear(outlet).append(node);
    outlet.scrollTop = 0;
  } catch (e) {
    console.error(e);
    clear(outlet).append(empty('This page failed to load', (e && e.message) || ''));
    errorToast(e);
  }
}
