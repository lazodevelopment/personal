import { h, pageHeader, card, cardHead, table, badge, btn, tabs, ago, fmtDateTime, toast, errorToast, prompt, avatar, kv, drawer, closeDrawer } from '../../ui.js';
import { refillQueue, updateRefill, careRefillQueue, updateCareRefill, cachedMembers, getMember, prescriptionsFor, pharmacies, addPrescription } from '../../data.js';
import { navigate } from '../../router.js';
import { can } from '../../auth.js';
import { db, doc, updateDoc, increment, Timestamp } from '../../firebase.js';

export async function render() {
  const wrap = h('div'); const body = h('div'); let tab = 'requested';
  const [members, phs] = await Promise.all([cachedMembers(), pharmacies().catch(() => [])]);
  const nm = uid => members.find(m => m.id === uid)?.name || uid;
  const phName = r => r.pharmacyName || phs.find(p => p.id === r.pharmacyId)?.name || (String(r.pharmacyId || '').startsWith('place:') ? 'Nearby pharmacy (Google)' : '—');
  const TABS = [['requested', 'New'], ['approved', 'Approved / processing'], ['ready', 'Ready for pickup'], ['care', 'Via Request Care'], ['done', 'Recent decisions']];
  async function draw() {
    body.replaceChildren(tabs(TABS, tab, t => { tab = t; draw(); }), h('div', { class: 'spinner-wrap' }, h('span', { class: 'spinner' })));
    let content;
    if (tab === 'care') {
      const rows = await careRefillQueue();
      content = card(h('p', { class: 'muted small mb' }, 'Refills submitted through Request Care (no prescription on file). Approving here creates a prescription record so the member can refill from the app next time.'), table([
        { label: 'Requested', render: r => ago(r.createdAt) }, { label: 'Member', render: r => h('a', { href: `#/ehr/chart/${r.userId}`, class: 'lnk' }, nm(r.userId)) }, { label: 'Patient', key: 'patientName' }, { label: 'Medication', render: r => h('div', null, h('b', null, r.medicationName || '—'), h('div', { class: 'small muted' }, r.medicationType)) }, { label: 'Current meds / allergies', render: r => h('div', { class: 'small' }, `${r.currentMedications || '—'}`, h('div', { class: 'muted' }, `Allergies: ${r.allergies || 'none listed'}`)) }, { label: 'Physician', key: 'primaryPhysician' },
        { label: '', render: r => can('refills') ? h('div', { class: 'row' }, btn('Approve + create Rx', () => approveCare(r), { variant: 'btn-success', size: 'btn-sm' }), btn('Deny', async () => { const why = await prompt('Deny refill', 'Reason (sent to member)'); if (why == null) return; try { await updateCareRefill(r.id, 'denied', { denialReason: why }); toast('Denied', 'success'); draw(); } catch (e) { errorToast(e); } }, { variant: 'btn-danger', size: 'btn-sm' })) : null },
      ], rows, { empty: 'No Request Care refills pending' }));
    } else {
      const statuses = tab === 'requested' ? ['requested'] : tab === 'approved' ? ['approved', 'processing', 'in_progress'] : tab === 'ready' ? ['ready'] : ['filled', 'completed', 'denied', 'rejected', 'cancelled'];
      const rows = await refillQueue(statuses);
      const act = r => !can('refills') ? null : h('div', { class: 'row' },
        r.status === 'requested' ? btn('Approve', () => move(r, 'approved'), { variant: 'btn-success', size: 'btn-sm' }) : null,
        ['requested', 'approved', 'processing', 'in_progress'].includes(r.status) ? btn('Ready', () => move(r, 'ready'), { variant: 'btn-primary', size: 'btn-sm' }) : null,
        r.status === 'ready' ? btn('Picked up', () => move(r, 'filled'), { variant: 'btn-success', size: 'btn-sm' }) : null,
        !['filled', 'completed', 'denied', 'rejected', 'cancelled'].includes(r.status) ? btn('Deny', async () => { const why = await prompt('Deny refill', 'Reason (sent to member)'); if (why == null) return; move(r, 'denied', { denialReason: why }); }, { variant: 'btn-danger', size: 'btn-sm' }) : null);
      content = card(table([
        { label: 'Requested', render: r => fmtDateTime(r.requestedDate || r.createdAt) }, { label: 'Member', render: r => h('a', { href: `#/ehr/chart/${r.userId}`, class: 'lnk' }, nm(r.userId)) }, { label: 'Medication', render: r => h('div', null, h('b', null, r.medicationName), h('div', { class: 'small muted' }, `Rx ${r.rxNumber || '—'} · refill #${r.refillNumber || '—'}`)) }, { label: 'Pharmacy', render: r => h('div', null, phName(r), r.payWithGoodRx ? h('div', null, badge('pending', 'GoodRx coupon · cash price')) : null) }, { label: 'Status', render: r => badge(r.status) }, { label: 'Handled by', render: r => r.handledByName || '—' }, { label: '', render: act },
      ], rows, { empty: 'Nothing here' }));
    }
    body.replaceChildren(tabs(TABS, tab, t => { tab = t; draw(); }), content);
  }
  async function move(r, status, extra = {}) { try { await updateRefill(r.id, status, extra); toast(`Marked ${status}. Member notified.`, 'success'); draw(); } catch (e) { errorToast(e); } }
  async function approveCare(r) {
    const { input, select, field, textarea } = await import('../../ui.js');
    const f = { name: input({ value: r.medicationName || '' }), dosage: input({ placeholder: 'e.g. 10 mg' }), frequency: input({ placeholder: 'e.g. once daily' }), refills: input({ type: 'number', value: 3 }), days: input({ type: 'number', value: 30 }), instructions: textarea({ rows: 2 }) };
    drawer(`Approve refill for ${nm(r.userId)}`, h('div', { class: 'col' }, field('Medication', f.name), h('div', { class: 'form-grid' }, field('Dosage', f.dosage), field('Frequency', f.frequency), field('Total refills', f.refills), field('Days supply', f.days)), field('Instructions', f.instructions), h('div', { class: 'row', style: { justifyContent: 'flex-end' } }, btn('Cancel', closeDrawer), btn('Approve & create Rx', async () => {
      try { await addPrescription(r.userId, { medicationName: f.name.value.trim(), dosage: f.dosage.value.trim(), frequency: f.frequency.value.trim(), totalRefills: Number(f.refills.value) || 0, refillsRemaining: Number(f.refills.value) || 0, daysSupply: Number(f.days.value) || 30, instructions: f.instructions.value.trim(), rxNumber: 'RX' + Date.now().toString(36).toUpperCase(), lastRefilled: Timestamp.now(), originalPharmacy: '' }); await updateCareRefill(r.id, 'approved'); toast('Approved. Prescription created.', 'success'); closeDrawer(); draw(); } catch (e) { errorToast(e); }
    }, { variant: 'btn-success' }))));
  }
  wrap.append(pageHeader('Refill requests', 'Each status change notifies the member through the app. Ready means the pharmacy has it waiting.'), body);
  await draw();
  return wrap;
}
