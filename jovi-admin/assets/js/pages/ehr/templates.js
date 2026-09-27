import { h, pageHeader, card, cardHead, table, badge, btn, tabs, input, textarea, field, select, drawer, closeDrawer, toast, errorToast } from '../../ui.js';
import { noteTemplates, saveTemplate, smartPhrases, savePhrase } from '../../data.js';
import { can } from '../../auth.js';

export async function render() {
  const wrap = h('div'); const body = h('div'); let tab = 'templates';
  const TABS = [['templates', 'Note templates'], ['phrases', 'Smart phrases']];
  async function draw() {
    body.replaceChildren(tabs(TABS, tab, t => { tab = t; draw(); }));
    if (tab === 'templates') {
      const rows = await noteTemplates();
      body.append(card(cardHead('Templates by visit type', can('chart') ? btn('New template', () => editT(null), { size: 'btn-sm', variant: 'btn-primary' }) : null), h('p', { class: 'muted small mb' }, 'Templates pre-fill HPI, exam, plan, and education in the note editor. Use {reason} to insert the chief complaint.'),
        table([{ label: 'Name', render: t => h('b', null, t.name) }, { label: 'Visit type', key: 'visitType' }, { label: 'HPI starts', render: t => h('span', { class: 'small muted' }, (t.hpi || '').slice(0, 80)) }, { label: 'Source', render: t => badge(t.builtin ? 'info' : 'active', t.builtin ? 'Built-in' : 'Custom') }, { label: '', render: t => can('chart') ? btn(t.builtin ? 'Customize' : 'Edit', () => editT(t), { size: 'btn-sm' }) : null }], rows)));
    } else {
      const rows = await smartPhrases();
      body.append(card(cardHead('Smart phrases', can('chart') ? btn('New phrase', () => editP(null), { size: 'btn-sm', variant: 'btn-primary' }) : null), h('p', { class: 'muted small mb' }, 'Type the key at the end of any note field, for example ".rtc", and it expands in place.'),
        table([{ label: 'Key', render: p => h('b', { class: 'mono' }, p.key) }, { label: 'Expands to', render: p => h('span', { class: 'small' }, p.text) }, { label: 'Source', render: p => badge(p.builtin ? 'info' : 'active', p.builtin ? 'Built-in' : 'Custom') }, { label: '', render: p => can('chart') ? btn('Edit', () => editP(p), { size: 'btn-sm' }) : null }], rows)));
    }
  }
  function editT(t) {
    const f = { name: input({ value: t?.name || '' }), vt: select(['Primary Care', 'Urgent Care', 'Wellness', 'Telehealth', 'Follow-up', 'Procedure', 'Sick or Injured'].map(x => [x, x]), t?.visitType || 'Primary Care'), hpi: textarea({ value: t?.hpi || '', rows: 5 }), exam: textarea({ value: t?.exam || '', rows: 7 }), plan: textarea({ value: t?.plan || '', rows: 3 }), edu: textarea({ value: t?.edu || '', rows: 2 }) };
    drawer(t ? `Edit ${t.name}` : 'New template', h('div', { class: 'col' }, h('div', { class: 'form-grid' }, field('Name', f.name), field('Visit type', f.vt)), field('HPI', f.hpi), field('Exam', f.exam), field('Plan', f.plan), field('Education', f.edu), h('div', { class: 'row', style: { justifyContent: 'flex-end' } }, btn('Cancel', closeDrawer), btn('Save', async () => { try { await saveTemplate(t?.id, { name: f.name.value.trim(), visitType: f.vt.value, hpi: f.hpi.value, exam: f.exam.value, plan: f.plan.value, edu: f.edu.value }); toast('Saved', 'success'); closeDrawer(); draw(); } catch (e) { errorToast(e); } }, { variant: 'btn-primary' }))), { wide: true });
  }
  function editP(p) {
    const key = input({ value: p?.key || '.', disabled: !!p && !p.builtin }); const text = textarea({ value: p?.text || '', rows: 4 });
    drawer(p ? `Edit ${p.key}` : 'New smart phrase', h('div', { class: 'col' }, field('Key (starts with a dot)', key), field('Text', text), h('div', { class: 'row', style: { justifyContent: 'flex-end' } }, btn('Cancel', closeDrawer), btn('Save', async () => { try { await savePhrase(key.value.trim(), text.value.trim()); toast('Saved', 'success'); closeDrawer(); draw(); } catch (e) { errorToast(e); } }, { variant: 'btn-primary' }))));
  }
  wrap.append(pageHeader('Templates & phrases', 'Documentation shortcuts for the note editor.'), body);
  await draw();
  return wrap;
}
