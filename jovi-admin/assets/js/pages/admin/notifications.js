import { h, pageHeader, card, cardHead, table, btn, field, input, textarea, select, toast, errorToast, fmtDateTime, confirm } from '../../ui.js';
import { cachedMembers, broadcasts, sendBroadcast } from '../../data.js';
import { can } from '../../auth.js';

export async function render() {
  const wrap = h('div'); const hist = h('div');
  const members = await cachedMembers();
  const seg = { all: m => true, active: m => ['active', 'past_due', 'canceling'].includes(m.status), pets: m => !!m.hasPetInsurance, family: m => (m.planType || m.planTier) === 'Family', past_due: m => ['past_due', 'suspended'].includes(m.status), AZ: m => m.state === 'AZ', FL: m => m.state === 'FL', TX: m => m.state === 'TX', CO: m => m.state === 'CO' };
  const f = { title: input({ placeholder: 'Title (push + inbox)', maxlength: 80 }), body: textarea({ placeholder: 'Message. Keep it under 240 characters for push.', maxlength: 500 }), aud: select([['active', 'Active members'], ['all', 'Everyone'], ['pets', 'Pet owners'], ['family', 'Family plans'], ['past_due', 'Past due / suspended'], ['AZ', 'Arizona'], ['FL', 'Florida'], ['TX', 'Texas'], ['CO', 'Colorado']], 'active'), route: select([['', 'No link'], ['billing', 'Billing'], ['planDetails', 'Plan details'], ['appointments', 'Appointments'], ['scriptRefill', 'Prescription refills'], ['pharmacies', 'Pharmacies'], ['ChatLanding', 'Help center'], ['notifications', 'Inbox']], '') };
  const count = h('span', { class: 'muted small' });
  const upd = () => { count.textContent = `${members.filter(seg[f.aud.value]).length} recipients`; }; f.aud.addEventListener('change', upd); upd();
  const send = btn('Send broadcast', async () => {
    const uids = members.filter(seg[f.aud.value]).map(m => m.id); if (!f.title.value.trim() || !f.body.value.trim()) return toast('Title and message are required', 'error');
    if (!(await confirm(`Send to ${uids.length} members?`, 'This writes an inbox item for each member and queues a push through the app\'s notification trigger. It cannot be recalled.', { okLabel: 'Send' }))) return;
    send.disabled = true; try { await sendBroadcast({ title: f.title.value.trim(), body: f.body.value.trim(), route: f.route.value || null, audience: f.aud.value, uids }); toast('Broadcast sent', 'success'); f.title.value = ''; f.body.value = ''; loadHist(); } catch (e) { errorToast(e); } finally { send.disabled = false; }
  }, { variant: 'btn-accent', disabled: !can('writeBusiness') });
  async function loadHist() { const rows = await broadcasts().catch(() => []); hist.replaceChildren(card(cardHead('Sent broadcasts'), table([{ label: 'When', render: r => fmtDateTime(r.createdAt) }, { label: 'Title', key: 'title' }, { label: 'Audience', key: 'audience' }, { label: 'Recipients', key: 'count' }, { label: 'By', key: 'by' }], rows, { empty: 'Nothing sent yet' }))); }
  wrap.append(pageHeader('Broadcasts', 'Send an in-app inbox message plus push notification to a segment of members.'),
    h('div', { class: 'grid grid-2' }, card(cardHead('Compose'), field('Audience', f.aud), count, field('Title', f.title), field('Message', f.body), field('Opens page', f.route), h('div', { class: 'row', style: { justifyContent: 'flex-end' } }, send)), hist));
  await loadHist();
  return wrap;
}
