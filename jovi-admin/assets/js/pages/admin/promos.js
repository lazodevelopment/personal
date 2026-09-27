import { h, pageHeader, card, table, badge, btn, field, input, select, checkbox, drawer, closeDrawer, toast, errorToast, fmtDate, money } from '../../ui.js';
import { promoCodes, savePromo, cachedMembers } from '../../data.js';
import { can } from '../../auth.js';

// The app currently hard-codes WELCOME10!, SAVE25!, FIRSTMONTH!, FAMILY20! in Onboarding.
// This collection is the intended replacement; until Onboarding reads it, treat it as the source of truth for marketing.
export async function render() {
  const wrap = h('div'); const list = h('div');
  const members = await cachedMembers();
  wrap.append(pageHeader('Promo codes', 'Codes and their usage. The app validates codes in Onboarding; see the note below.', can('writeBusiness') ? [btn('New code', () => edit(null), { variant: 'btn-primary' })] : []),
    h('div', { class: 'callout mb' }, h('div', null, h('b', null, 'App note: '), 'Onboarding still validates four hard-coded codes (WELCOME10!, SAVE25!, FIRSTMONTH!, FAMILY20!). Codes created here take effect once Onboarding is switched to read promo_codes. Usage counts below come from members\' promoCodeApplied field either way.')), list);
  async function load() {
    const rows = await promoCodes();
    const seed = [['WELCOME10!', 'percent', 10], ['SAVE25!', 'amount', 25], ['FIRSTMONTH!', 'first_month', 100], ['FAMILY20!', 'percent', 20]].filter(([c]) => !rows.find(r => r.code === c)).map(([code, kind, value]) => ({ id: code, code, kind, value, active: true, hardcoded: true }));
    const all = [...rows, ...seed].map(r => ({ ...r, uses: members.filter(m => (m.promoCodeApplied || '').toUpperCase() === r.code).length }));
    list.replaceChildren(card(table([{ label: 'Code', render: r => h('b', { class: 'mono' }, r.code) }, { label: 'Discount', render: r => r.kind === 'percent' ? `${r.value}% off` : r.kind === 'amount' ? `${money(r.value)} off` : 'First month free' }, { label: 'Applies to', render: r => r.familyOnly ? 'Family plans' : 'All plans' }, { label: 'Uses', key: 'uses' }, { label: 'Expires', render: r => r.expiresAt ? fmtDate(r.expiresAt) : '—' }, { label: 'Status', render: r => badge(r.active === false ? 'suspended' : 'active', r.hardcoded ? 'In app' : r.active === false ? 'Off' : 'Active') }, { label: '', render: r => can('writeBusiness') ? btn('Edit', () => edit(r), { size: 'btn-sm' }) : null }], all, { empty: 'No codes' })));
  }
  function edit(r) {
    const f = { code: input({ value: r?.code || '', placeholder: 'e.g. SPRING15', disabled: !!r }), kind: select([['percent', 'Percent off'], ['amount', 'Dollar amount off'], ['first_month', 'First month free']], r?.kind || 'percent'), value: input({ type: 'number', value: r?.value ?? 10 }), expires: input({ type: 'date', value: r?.expiresAt ? new Date(r.expiresAt.toDate ? r.expiresAt.toDate() : r.expiresAt).toISOString().slice(0, 10) : '' }), family: checkbox('Family plans only', !!r?.familyOnly), active: checkbox('Active', r ? r.active !== false : true), notes: input({ value: r?.notes || '', placeholder: 'Campaign / channel' }) };
    drawer(r ? `Edit ${r.code}` : 'New promo code', h('div', { class: 'col' }, field('Code', f.code), field('Type', f.kind), field('Value', f.value), field('Expires', f.expires), f.family, f.active, field('Notes', f.notes), h('div', { class: 'row', style: { justifyContent: 'flex-end' } }, btn('Cancel', closeDrawer), btn('Save', async () => { try { await savePromo(f.code.value.trim(), { kind: f.kind.value, value: Number(f.value.value), expiresAt: f.expires.value ? new Date(f.expires.value) : null, familyOnly: f.family.querySelector('input').checked, active: f.active.querySelector('input').checked, notes: f.notes.value.trim() }); toast('Saved', 'success'); closeDrawer(); load(); } catch (e) { errorToast(e); } }, { variant: 'btn-primary' }))));
  }
  await load();
  return wrap;
}
