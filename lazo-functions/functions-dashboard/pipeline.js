// functions-dashboard/pipeline.js
// Build ID: JC-LAZO-FNDASH-0913-018 (018: task reminders skip the practice couple; 014: couple reminder carries the vendor brand; base 013)
//
// BUILD D: PIPELINE, TAGS, TASKS - the server half.
//
// The dashboard writes inquiries.stage / inquiries.tags and
// inquiries/{id}/tasks/{taskId} directly (rules 0913-010). This module keeps
// the roll-ups and sends the reminders:
//
//   onTaskWritten     inquiries/{id}/tasks/{tid} created/updated/deleted ->
//                     inquiries.{openTasks, nextTaskAt, nextTaskTitle} so the
//                     Kanban card and the inbox row show the next thing due
//                     without reading the subcollection.
//   taskReminderSweep 07:30 America/Phoenix daily -> one email per vendor
//                     with today's + overdue tasks (deep link per thread);
//                     couple-assigned tasks due today go to the couple (email,
//                     and SMS for off-platform leads with smsOk).
//
// Task doc: { title, note, dueAt (ts|null), assignedTo 'vendor'|'couple'|<uid>,
//             done bool, doneAt, createdBy, createdAt, remindedOn 'YYYY-MM-DD' }

'use strict';

const { onDocumentWritten } = require('firebase-functions/v2/firestore');
const { onSchedule } = require('firebase-functions/v2/scheduler');
const { defineSecret } = require('firebase-functions/params');
const admin = require('firebase-admin');
const { wrap: brandWrap } = require('./brand');

const TELNYX_API_KEY = defineSecret('TELNYX_API_KEY');
const TELNYX_FROM = defineSecret('TELNYX_FROM');
const APP = 'https://app.meetlazo.com/dashboard';
const FROM = 'Lazo <hello@meetlazo.com>';

const db = () => admin.firestore();
const { FieldValue, Timestamp } = admin.firestore;
const str = (v) => (v == null ? '' : String(v));
const toDate = (v) => (v && typeof v.toDate === 'function') ? v.toDate() : (v instanceof Date ? v : null);
const emailOk = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(str(e));
const fmtDate = (d) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
const e164 = (raw) => { const d = str(raw).replace(/[^\d]/g, ''); return d.length === 10 ? '+1' + d : (d.length === 11 && d.startsWith('1')) ? '+' + d : ''; };

module.exports = function pipelineModule(RESEND_API_KEY) {

  async function sendEmail(to, subject, html, text) {
    if (!emailOk(to)) return;
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${RESEND_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: FROM, to: [to], subject, html, text }),
    });
    if (!r.ok) throw new Error(`resend ${r.status}: ${await r.text()}`);
  }
  async function sendSms(to, text) {
    const t = e164(to); if (!t) return false;
    const r = await fetch('https://api.telnyx.com/v2/messages', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${TELNYX_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: TELNYX_FROM.value(), to: t, text: str(text).slice(0, 1500) }),
    });
    if (!r.ok) console.warn('telnyx send', r.status, await r.text());
    return r.ok;
  }

  // ------------------------------------------------------------- roll-up --
  const onTaskWritten = onDocumentWritten({ document: 'inquiries/{inquiryId}/tasks/{taskId}', memory: '256MiB' }, async (event) => {
    const inqRef = db().collection('inquiries').doc(event.params.inquiryId);
    const open = await inqRef.collection('tasks').where('done', '==', false).get();
    let next = null, title = '', count = 0;
    open.forEach((d) => {
      count++;
      const due = toDate(d.get('dueAt'));
      if (due && (!next || due < next)) { next = due; title = str(d.get('title')); }
    });
    await inqRef.set({
      openTasks: count,
      nextTaskAt: next ? Timestamp.fromDate(next) : null,
      nextTaskTitle: next ? title.slice(0, 80) : '',
    }, { merge: true });
  });

  // ------------------------------------------------------------ reminders --
  const taskReminderSweep = onSchedule({
    schedule: '30 7 * * *', timeZone: 'America/Phoenix', memory: '512MiB', timeoutSeconds: 300,
    secrets: [RESEND_API_KEY, TELNYX_API_KEY, TELNYX_FROM],
  }, async () => {
    const now = new Date();
    const endOfToday = new Date(now); endOfToday.setHours(23, 59, 59, 999);
    const todayKey = now.toISOString().slice(0, 10);
    const snap = await db().collectionGroup('tasks').where('done', '==', false).where('dueAt', '<=', Timestamp.fromDate(endOfToday)).get();
    if (snap.empty) { console.log('taskReminderSweep: nothing due'); return; }

    const byVendor = new Map(); // vendorId -> [{inquiryId, coupleName, title, due, assignedTo}]
    const coupleTasks = [];      // couple-assigned, due today, not yet reminded today
    const inqCache = new Map();
    for (const t of snap.docs) {
      const inquiryId = t.ref.parent.parent.id;
      let inq = inqCache.get(inquiryId);
      if (!inq) {
        const s = await db().collection('inquiries').doc(inquiryId).get();
        inq = s.exists ? s.data() : null; inqCache.set(inquiryId, inq);
      }
      if (!inq || inq.demo === true) continue;
      const row = { taskRef: t.ref, inquiryId, coupleName: str(inq.coupleName) || 'A couple', vendorName: str(inq.vendorName), title: str(t.get('title')), due: toDate(t.get('dueAt')), assignedTo: str(t.get('assignedTo')) || 'vendor', remindedOn: str(t.get('remindedOn')) };
      const vid = str(inq.vendorId);
      if (row.assignedTo === 'couple') {
        if (row.remindedOn !== todayKey) coupleTasks.push({ ...row, inq });
      } else {
        if (!byVendor.has(vid)) byVendor.set(vid, []);
        byVendor.get(vid).push(row);
      }
    }

    // vendors: one digest each
    let sent = 0;
    for (const [vendorId, rows] of byVendor) {
      try {
        const v = await db().collection('vendors').doc(vendorId).get();
        if (!v.exists) continue;
        let to = str(v.get('email'));
        if (str(v.get('claimedBy'))) {
          const u = await db().collection('users').doc(str(v.get('claimedBy'))).get();
          if (u.exists && emailOk(u.get('email'))) to = str(u.get('email'));
        }
        if (!emailOk(to)) continue;
        rows.sort((a, b) => (a.due || 0) - (b.due || 0));
        const overdue = rows.filter((r) => r.due && r.due < new Date(now.getFullYear(), now.getMonth(), now.getDate()));
        const today = rows.filter((r) => !overdue.includes(r));
        const line = (r) => `<li><a href="${APP}?thread=${r.inquiryId}">${r.title.replace(/</g, '&lt;')}</a> - ${r.coupleName}${r.due ? ` (${fmtDate(r.due)})` : ''}</li>`;
        await sendEmail(to, `${rows.length} task${rows.length === 1 ? '' : 's'} for today${overdue.length ? `, ${overdue.length} overdue` : ''}`,
          `${today.length ? `<p><b>Today</b></p><ul>${today.map(line).join('')}</ul>` : ''}${overdue.length ? `<p><b>Overdue</b></p><ul>${overdue.map(line).join('')}</ul>` : ''}<p>Tick them off in the thread, or from the Pipeline view.</p>`,
          rows.map((r) => `${r.title} - ${r.coupleName}${r.due ? ` (${fmtDate(r.due)})` : ''}: ${APP}?thread=${r.inquiryId}`).join('\n'));
        sent++;
      } catch (e) { console.warn('task digest', vendorId, e.message); }
    }

    // couples: per task, once per day
    for (const r of coupleTasks) {
      try {
        const inq = r.inq;
        let email = '', phone = '', smsOk = false;
        if (inq.offPlatform === true) {
          email = str(inq.contact && inq.contact.email); phone = str(inq.contact && inq.contact.phone); smsOk = !!(inq.contact && inq.contact.smsOk !== false && phone);
        } else {
          const u = await db().collection('users').doc(str(inq.coupleUid)).get();
          email = u.exists ? str(u.get('email')) : '';
        }
        const vendorName = r.vendorName || 'your vendor';
        const link = inq.offPlatform === true && str(inq.fileToken) ? `https://meetlazo.com/f/${r.inquiryId}?t=${inq.fileToken}` : `${APP}?thread=${r.inquiryId}`;
        const vS = await db().collection('vendors').doc(str(inq.vendorId)).get();
        if (emailOk(email)) await sendEmail(email, `${vendorName} needs one thing from you: ${r.title}`,
          brandWrap(vS.exists ? vS.data() : null, `<p>${vendorName} is waiting on: <b>${r.title.replace(/</g, '&lt;')}</b>${r.due ? ` (due ${fmtDate(r.due)})` : ''}.</p><p><a href="${link}">Open it on Lazo</a></p>`),
          `${vendorName} is waiting on: ${r.title}. ${link}`);
        if (smsOk) await sendSms(phone, `${vendorName}: quick one - ${r.title}${r.due ? ` (due ${fmtDate(r.due)})` : ''}. ${link}`);
        await r.taskRef.set({ remindedOn: todayKey }, { merge: true });
      } catch (e) { console.warn('couple task reminder', r.inquiryId, e.message); }
    }
    console.log(`taskReminderSweep: ${snap.size} due, ${sent} vendor digests, ${coupleTasks.length} couple reminders`);
  });

  return { onTaskWritten, taskReminderSweep };
};

// END OF FILE - JC-LAZO-FNDASH-0913-013
