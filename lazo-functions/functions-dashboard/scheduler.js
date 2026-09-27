// functions-dashboard/scheduler.js
// Build ID: JC-LAZO-FNDASH-0913-015
//
// BUILD C: CONSULT SCHEDULER.
//
// vendors.scheduler = {
//   enabled, tz ('America/Phoenix'), slotMinutes (30), bufferMinutes (15),
//   minNoticeHours (24), maxDaysOut (60), videoLink,
//   hours: { mon:[["09:00","17:00"]], tue:[...], ... }   (24h local strings)
//   types: [{ key, label, minutes, mode 'video'|'phone'|'in_person', location }]
// }
// consults/{id} = { vendorId, vendorName, inquiryId|null, coupleUid|null,
//   contact {name,email,phone,smsOk}, typeKey, typeLabel, mode, location,
//   startAt, endAt, tz, status 'booked'|'cancelled', note, source,
//   cancelToken, createdAt, reminded {h24, h1} }
//
// Functions
//   consultSlots     GET  ?v=&d=YYYY-MM-DD&type=      -> { slots:[iso], tz, types }
//   consultBook      POST {vendorId, start, type, name, email, phone, note,
//                          inquiryId, smsOk, page, website}  -> {id, cancelUrl}
//   consultCancel    GET  ?id=&t=                       -> cancels, notifies vendor
//   consultReminderSweep  every 30 min: 24h and 1h reminders
//
// Availability = vendor hours - existing consults (+buffer) - unavailableDates
// - booked wedding dates - now+minNotice. Times are computed in the vendor's tz.

'use strict';

const crypto = require('crypto');
const { onRequest } = require('firebase-functions/v2/https');
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
const clip = (s, n) => str(s).trim().slice(0, n);
const toDate = (v) => (v && typeof v.toDate === 'function') ? v.toDate() : (v instanceof Date ? v : null);
const emailOk = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(str(e));
const e164 = (raw) => { const d = str(raw).replace(/[^\d]/g, ''); return d.length === 10 ? '+1' + d : (d.length === 11 && d.startsWith('1')) ? '+' + d : ''; };
const DAYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];

// ---- time zone math without a library ------------------------------------
function tzParts(tz, date) {
  const f = new Intl.DateTimeFormat('en-US', { timeZone: tz, hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', weekday: 'short' });
  const p = {};
  for (const x of f.formatToParts(date)) p[x.type] = x.value;
  return { y: +p.year, m: +p.month, d: +p.day, h: +p.hour % 24, min: +p.minute, wd: p.weekday.toLowerCase().slice(0, 3), key: `${p.year}-${p.month}-${p.day}` };
}
// offset (ms) of tz at a given instant
function tzOffsetMs(tz, date) {
  const p = tzParts(tz, date);
  const asUtc = Date.UTC(p.y, p.m - 1, p.d, p.h, p.min);
  return asUtc - Math.floor(date.getTime() / 60000) * 60000;
}
// local wall-clock (Y,M,D,h,m) in tz -> UTC Date
function fromLocal(tz, y, m, d, h, min) {
  const guess = new Date(Date.UTC(y, m - 1, d, h, min));
  const off = tzOffsetMs(tz, guess);
  const t = new Date(guess.getTime() - off);
  const off2 = tzOffsetMs(tz, t);
  return off2 === off ? t : new Date(guess.getTime() - off2);
}
function fmtLocal(tz, date, opts) {
  return new Intl.DateTimeFormat('en-US', { timeZone: tz, ...opts }).format(date);
}
function whenText(tz, start) {
  return `${fmtLocal(tz, start, { weekday: 'long', month: 'long', day: 'numeric' })} at ${fmtLocal(tz, start, { hour: 'numeric', minute: '2-digit' })} (${fmtLocal(tz, start, { timeZoneName: 'short' }).split(' ').pop()})`;
}
function ics(c, start, end, uid) {
  const f = (d) => d.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
  const loc = c.mode === 'video' ? str(c.videoLink) : c.mode === 'in_person' ? str(c.location) : 'Phone call';
  return ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Lazo//Consults//EN', 'METHOD:REQUEST', 'BEGIN:VEVENT',
    `UID:${uid}@meetlazo.com`, `DTSTAMP:${f(new Date())}`, `DTSTART:${f(start)}`, `DTEND:${f(end)}`,
    `SUMMARY:${str(c.typeLabel)} with ${str(c.vendorName)}`, `DESCRIPTION:${str(c.contact && c.contact.name)}${c.note ? ' - ' + str(c.note).replace(/\n/g, ' ') : ''}`,
    loc ? `LOCATION:${loc.replace(/,/g, '\\,')}` : '', 'END:VEVENT', 'END:VCALENDAR'].filter(Boolean).join('\r\n');
}

module.exports = function schedulerModule(RESEND_API_KEY) {

  async function sendEmail(to, subject, html, text, icsText) {
    if (!emailOk(to)) return;
    const body = { from: FROM, to: [to], subject, html, text };
    if (icsText) body.attachments = [{ filename: 'consult.ics', content: Buffer.from(icsText).toString('base64') }];
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST', headers: { 'Authorization': `Bearer ${RESEND_API_KEY.value()}`, 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`resend ${r.status}: ${await r.text()}`);
  }
  async function sendSms(to, text) {
    const t = e164(to); if (!t) return false;
    const r = await fetch('https://api.telnyx.com/v2/messages', {
      method: 'POST', headers: { 'Authorization': `Bearer ${TELNYX_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: TELNYX_FROM.value(), to: t, text: str(text).slice(0, 1500) }),
    });
    if (!r.ok) console.warn('telnyx send', r.status, await r.text());
    return r.ok;
  }
  async function vendorOwnerEmail(v) {
    try {
      if (str(v.claimedBy)) {
        const u = await db().collection('users').doc(str(v.claimedBy)).get();
        if (u.exists && emailOk(u.get('email'))) return str(u.get('email'));
      }
    } catch (e) {}
    return emailOk(v.email) ? str(v.email) : '';
  }

  function schedOf(v) {
    const s = v && v.scheduler && typeof v.scheduler === 'object' ? v.scheduler : {};
    const types = Array.isArray(s.types) && s.types.length ? s.types : [{ key: 'intro', label: 'Intro call', minutes: 30, mode: 'video' }];
    return {
      enabled: s.enabled !== false,
      tz: str(s.tz) || 'America/Phoenix',
      slotMinutes: Math.max(15, Math.min(120, +s.slotMinutes || 30)),
      bufferMinutes: Math.max(0, Math.min(120, +s.bufferMinutes || 15)),
      minNoticeHours: Math.max(1, Math.min(168, +s.minNoticeHours || 24)),
      maxDaysOut: Math.max(7, Math.min(180, +s.maxDaysOut || 60)),
      videoLink: str(s.videoLink),
      hours: s.hours && typeof s.hours === 'object' ? s.hours : { mon: [['09:00', '17:00']], tue: [['09:00', '17:00']], wed: [['09:00', '17:00']], thu: [['09:00', '17:00']], fri: [['09:00', '17:00']] },
      types: types.map((t) => ({ key: str(t.key) || 'intro', label: str(t.label) || 'Intro call', minutes: Math.max(10, Math.min(240, +t.minutes || 30)), mode: ['video', 'phone', 'in_person'].includes(str(t.mode)) ? str(t.mode) : 'video', location: str(t.location) })),
    };
  }

  // all free slot starts (Date) on local day YYYY-MM-DD for a type
  async function slotsFor(v, vendorId, sch, dayKey, type) {
    const [y, m, d] = dayKey.split('-').map(Number);
    if (!y || !m || !d) return [];
    const wd = DAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
    const windows = Array.isArray(sch.hours[wd]) ? sch.hours[wd] : [];
    if (!windows.length) return [];
    if (Array.isArray(v.unavailableDates) && v.unavailableDates.includes(dayKey)) return [];
    const dur = type.minutes, step = sch.slotMinutes, buf = sch.bufferMinutes;
    const earliest = new Date(Date.now() + sch.minNoticeHours * 3600000);
    const latest = new Date(Date.now() + sch.maxDaysOut * 86400000);
    // taken: consults that day (+/- buffer) and booked weddings on that date
    const dayStart = fromLocal(sch.tz, y, m, d, 0, 0), dayEnd = fromLocal(sch.tz, y, m, d, 23, 59);
    const taken = [];
    const cs = await db().collection('consults').where('vendorId', '==', vendorId).where('status', '==', 'booked').where('startAt', '>=', Timestamp.fromDate(new Date(dayStart.getTime() - 86400000))).where('startAt', '<=', Timestamp.fromDate(new Date(dayEnd.getTime() + 86400000))).get();
    cs.forEach((c) => { const s = toDate(c.get('startAt')), e = toDate(c.get('endAt')); if (s && e) taken.push([s.getTime() - buf * 60000, e.getTime() + buf * 60000]); });
    const wq = await db().collection('inquiries').where('vendorId', '==', vendorId).where('status', '==', 'booked').where('structuredIntent.weddingDate', '==', dayKey).limit(1).get();
    if (!wq.empty) return [];
    const out = [];
    for (const w of windows) {
      const [sh, sm] = str(w[0]).split(':').map(Number), [eh, em] = str(w[1]).split(':').map(Number);
      if (isNaN(sh) || isNaN(eh)) continue;
      let t = fromLocal(sch.tz, y, m, d, sh, sm || 0);
      const end = fromLocal(sch.tz, y, m, d, eh, em || 0);
      while (t.getTime() + dur * 60000 <= end.getTime()) {
        const a = t.getTime(), b = a + dur * 60000;
        const clash = taken.some(([ta, tb]) => a < tb && b > ta);
        if (!clash && t >= earliest && t <= latest) out.push(new Date(a));
        t = new Date(a + step * 60000);
      }
    }
    return out;
  }

  // ------------------------------------------------------------ slots ----
  const consultSlots = onRequest({ cors: true, invoker: 'public', memory: '256MiB' }, async (req, res) => {
    try {
      const vendorId = clip(req.query.v, 120), dayKey = clip(req.query.d, 10), typeKey = clip(req.query.type, 40);
      if (!vendorId) return res.status(400).json({ error: 'v' });
      const vs = await db().collection('vendors').doc(vendorId).get();
      if (!vs.exists) return res.status(404).json({ error: 'vendor' });
      const v = vs.data(), sch = schedOf(v);
      if (!sch.enabled) return res.status(404).json({ error: 'off' });
      const type = sch.types.find((t) => t.key === typeKey) || sch.types[0];
      const base = { tz: sch.tz, types: sch.types.map((t) => ({ key: t.key, label: t.label, minutes: t.minutes, mode: t.mode })), vendor: { name: str(v.name), logoUrl: str(v.logoUrl), brand: v.brand || null }, maxDaysOut: sch.maxDaysOut, minNoticeHours: sch.minNoticeHours };
      if (!dayKey) {
        // which of the next N days have any opening (cheap: hours + unavailableDates only)
        const days = [];
        for (let i = 0; i <= sch.maxDaysOut; i++) {
          const dd = new Date(Date.now() + i * 86400000);
          const p = tzParts(sch.tz, dd);
          const open = Array.isArray(sch.hours[p.wd]) && sch.hours[p.wd].length > 0 && !(Array.isArray(v.unavailableDates) && v.unavailableDates.includes(p.key));
          if (open) days.push(p.key);
        }
        return res.set('cache-control', 'no-store').json({ ...base, days });
      }
      const slots = await slotsFor(v, vendorId, sch, dayKey, type);
      res.set('cache-control', 'no-store').json({ ...base, day: dayKey, type: type.key, slots: slots.map((s) => s.toISOString()) });
    } catch (e) { console.error('consultSlots', e); res.status(500).json({ error: 'failed' }); }
  });

  // ------------------------------------------------------------- book ----
  const consultBook = onRequest({ cors: true, invoker: 'public', memory: '256MiB', secrets: [RESEND_API_KEY, TELNYX_API_KEY, TELNYX_FROM] }, async (req, res) => {
    if (req.method !== 'POST') return res.status(405).json({ ok: false });
    const b = req.body || {};
    if (str(b.website)) return res.json({ ok: true });
    try {
      const vendorId = clip(b.vendorId, 120);
      const vs = await db().collection('vendors').doc(vendorId).get();
      if (!vs.exists) return res.status(404).json({ ok: false, error: 'vendor' });
      const v = vs.data(), sch = schedOf(v);
      if (!sch.enabled) return res.status(404).json({ ok: false, error: 'off' });
      const type = sch.types.find((t) => t.key === clip(b.type, 40)) || sch.types[0];
      const start = new Date(str(b.start));
      if (isNaN(start.getTime())) return res.status(400).json({ ok: false, error: 'start' });
      const name = clip(b.name, 120), email = clip(b.email, 160).toLowerCase(), phone = e164(b.phone);
      if (!name || (!emailOk(email) && !phone)) return res.status(400).json({ ok: false, error: 'contact' });
      // the slot must still be free
      const p = tzParts(sch.tz, start);
      const free = await slotsFor(v, vendorId, sch, p.key, type);
      if (!free.some((s) => s.getTime() === start.getTime())) return res.status(409).json({ ok: false, error: 'taken' });
      const end = new Date(start.getTime() + type.minutes * 60000);

      // attach to a thread: the one given, or the lead's existing one, or a new off-platform one
      let inquiryId = clip(b.inquiryId, 80), coupleUid = null, inqRef = null;
      if (inquiryId) {
        const s = await db().collection('inquiries').doc(inquiryId).get();
        if (s.exists && str(s.get('vendorId')) === vendorId) { inqRef = s.ref; coupleUid = str(s.get('coupleUid')) || null; } else inquiryId = '';
      }
      if (!inquiryId) {
        for (const f of [['contact.email', email], ['contact.phone', phone]]) {
          if (!f[1]) continue;
          const q = await db().collection('inquiries').where('vendorId', '==', vendorId).where(f[0], '==', f[1]).limit(1).get();
          if (!q.empty) { inqRef = q.docs[0].ref; inquiryId = q.docs[0].id; coupleUid = str(q.docs[0].get('coupleUid')) || null; break; }
        }
      }
      if (!inquiryId) {
        inqRef = db().collection('inquiries').doc(); inquiryId = inqRef.id; coupleUid = `lead_${inquiryId}`;
        await inqRef.set({
          vendorId, vendorName: str(v.name), coupleUid, coupleName: name,
          contact: { name, email, phone, smsOk: b.smsOk !== false && !!phone },
          offPlatform: true, source: 'book', sourceRef: { page: clip(b.page, 500), referrer: clip(b.referrer, 500) },
          structuredIntent: { weddingDate: /^\d{4}-\d{2}-\d{2}$/.test(str(b.weddingDate)) ? str(b.weddingDate) : '', message: clip(b.note, 1000) },
          status: 'new', createdAt: FieldValue.serverTimestamp(), lastMessageAt: FieldValue.serverTimestamp(), lastMessageRole: 'couple',
          lastMessagePreview: `Booked a ${type.label.toLowerCase()}`, fileToken: crypto.randomBytes(18).toString('base64url'), fileTokenAt: FieldValue.serverTimestamp(),
        });
      }
      const cancelToken = crypto.randomBytes(12).toString('base64url');
      const cRef = db().collection('consults').doc();
      const consult = {
        vendorId, vendorName: str(v.name), inquiryId, coupleUid,
        contact: { name, email, phone, smsOk: b.smsOk !== false && !!phone },
        typeKey: type.key, typeLabel: type.label, mode: type.mode, minutes: type.minutes,
        location: type.mode === 'in_person' ? (type.location || str(v.address) || '') : '', videoLink: type.mode === 'video' ? sch.videoLink : '',
        startAt: Timestamp.fromDate(start), endAt: Timestamp.fromDate(end), tz: sch.tz, status: 'booked',
        note: clip(b.note, 600), source: inquiryId && b.inquiryId ? 'thread' : 'page', cancelToken, createdAt: FieldValue.serverTimestamp(), reminded: {},
      };
      await cRef.set(consult);
      const when = whenText(sch.tz, start);
      const cancelUrl = `https://us-central1-lazo-513ec.cloudfunctions.net/consultCancel?id=${cRef.id}&t=${cancelToken}`;
      const bookUrl = `https://meetlazo.com/book/${vendorId}?inq=${inquiryId}`;
      const howText = type.mode === 'video' ? (sch.videoLink ? `Video link: ${sch.videoLink}` : 'Video link to follow') : type.mode === 'phone' ? `${str(v.name)} will call ${phone || 'you'}` : `At ${consult.location || 'a location to be confirmed'}`;
      const icsText = ics(consult, start, end, cRef.id);

      // thread note
      await inqRef.collection('messages').add({ senderRole: 'couple', system: true, text: `Booked a ${type.label.toLowerCase()} for ${when}.`, at: FieldValue.serverTimestamp(), consult: { id: cRef.id, startAt: consult.startAt } });
      await inqRef.set({ lastMessageAt: FieldValue.serverTimestamp(), lastMessageRole: 'couple', lastMessagePreview: `Booked a ${type.label.toLowerCase()} - ${fmtLocal(sch.tz, start, { month: 'short', day: 'numeric' })}`, nextConsultAt: consult.startAt }, { merge: true });

      // couple
      try {
        if (emailOk(email)) await sendEmail(email, `${type.label} with ${str(v.name)} - ${fmtLocal(sch.tz, start, { weekday: 'short', month: 'short', day: 'numeric' })}`,
          brandWrap(v, `<p>Hi ${name},</p><p>You're booked: <b>${type.label}</b> with ${str(v.name)}<br><b>${when}</b><br>${howText.replace(/</g, '&lt;')}</p><p>Calendar file attached. Need to change it? <a href="${cancelUrl}">Cancel</a> and <a href="${bookUrl}">pick a new time</a>.</p>`),
          `${type.label} with ${str(v.name)}: ${when}. ${howText}. Cancel: ${cancelUrl}`, icsText);
        if (phone && b.smsOk !== false) await sendSms(phone, `${str(v.name)}: you're booked - ${type.label}, ${when}. ${type.mode === 'video' && sch.videoLink ? sch.videoLink : ''} Reply STOP to opt out.`);
      } catch (e) { console.warn('consult couple notify', e.message); }
      // vendor
      try {
        const to = await vendorOwnerEmail(v);
        const link = `${APP}?thread=${inquiryId}`;
        if (to) await sendEmail(to, `New ${type.label.toLowerCase()}: ${name} - ${fmtLocal(sch.tz, start, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}`,
          `<p><b>${name}</b> booked a ${type.label.toLowerCase()}.</p><p><b>${when}</b><br>${howText}</p><p>${email ? 'Email: ' + email + '<br>' : ''}${phone ? 'Phone: ' + phone + '<br>' : ''}${consult.note ? 'Note: ' + consult.note.replace(/</g, '&lt;') : ''}</p><p><a href="${link}">Open the thread</a>. Calendar file attached.</p>`,
          `${name} booked a ${type.label.toLowerCase()}: ${when}. ${link}`, icsText);
        if (e164(v.phone) && v.leadSmsOff !== true) await sendSms(v.phone, `Lazo: ${name} booked a ${type.label.toLowerCase()} - ${fmtLocal(sch.tz, start, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}. ${link}`);
      } catch (e) { console.warn('consult vendor notify', e.message); }

      res.json({ ok: true, id: cRef.id, when, cancelUrl, inquiryId });
    } catch (e) { console.error('consultBook', e); res.status(500).json({ ok: false, error: 'failed' }); }
  });

  // ----------------------------------------------------------- cancel ----
  const consultCancel = onRequest({ cors: true, invoker: 'public', memory: '256MiB', secrets: [RESEND_API_KEY] }, async (req, res) => {
    try {
      const id = clip(req.query.id, 80), t = clip(req.query.t, 40);
      const ref = db().collection('consults').doc(id);
      const s = await ref.get();
      if (!s.exists || !t || str(s.get('cancelToken')) !== t) return res.status(403).send(page('This link is not valid', 'Ask your vendor to resend it.'));
      const c = s.data();
      if (str(c.status) === 'cancelled') return res.send(page('Already cancelled', 'Pick a new time any time from the booking page.'));
      await ref.set({ status: 'cancelled', cancelledAt: FieldValue.serverTimestamp(), cancelledBy: 'couple' }, { merge: true });
      if (str(c.inquiryId)) {
        await db().collection('inquiries').doc(c.inquiryId).collection('messages').add({ senderRole: 'couple', system: true, text: `Cancelled the ${str(c.typeLabel).toLowerCase()} on ${whenText(str(c.tz), toDate(c.startAt))}.`, at: FieldValue.serverTimestamp() });
        await db().collection('inquiries').doc(c.inquiryId).set({ nextConsultAt: null }, { merge: true });
      }
      const vs = await db().collection('vendors').doc(str(c.vendorId)).get();
      if (vs.exists) {
        const to = await vendorOwnerEmail(vs.data());
        if (to) await sendEmail(to, `${str(c.contact && c.contact.name)} cancelled their ${str(c.typeLabel).toLowerCase()}`, `<p>${str(c.contact && c.contact.name)} cancelled the ${str(c.typeLabel).toLowerCase()} on ${whenText(str(c.tz), toDate(c.startAt))}.</p><p><a href="${APP}?thread=${c.inquiryId}">Open the thread</a></p>`, `Cancelled: ${whenText(str(c.tz), toDate(c.startAt))}`).catch(() => {});
      }
      res.send(page('Cancelled', `Your ${str(c.typeLabel).toLowerCase()} with ${str(c.vendorName)} is cancelled. <a href="https://meetlazo.com/book/${c.vendorId}?inq=${c.inquiryId}" style="color:#52284F">Pick a new time</a> whenever you're ready.`));
    } catch (e) { console.error('consultCancel', e); res.status(500).send(page('Something went wrong', 'Try again in a minute.')); }
  });
  function page(h, p) {
    return `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>${h} - Lazo</title></head><body style="font-family:Helvetica,Arial,sans-serif;background:#FAF6F0;color:#241E2B;margin:0"><div style="max-width:480px;margin:60px auto;padding:0 20px"><h1 style="font-family:Georgia,serif;font-weight:600;color:#52284F">${h}</h1><p style="line-height:1.5">${p}</p></div></body></html>`;
  }

  // --------------------------------------------------------- reminders ----
  const consultReminderSweep = onSchedule({ schedule: '*/30 * * * *', timeZone: 'America/Phoenix', memory: '256MiB', timeoutSeconds: 120, secrets: [RESEND_API_KEY, TELNYX_API_KEY, TELNYX_FROM] }, async () => {
    const now = Date.now();
    const snap = await db().collection('consults').where('status', '==', 'booked').where('startAt', '>=', Timestamp.fromDate(new Date(now))).where('startAt', '<=', Timestamp.fromDate(new Date(now + 25 * 3600000))).get();
    let sent = 0;
    for (const d of snap.docs) {
      const c = d.data(); const start = toDate(c.startAt); if (!start) continue;
      const hrs = (start.getTime() - now) / 3600000;
      const rem = c.reminded || {};
      let key = null;
      if (hrs <= 1.5 && !rem.h1) key = 'h1'; else if (hrs <= 24.5 && hrs > 1.5 && !rem.h24) key = 'h24';
      if (!key) continue;
      const when = whenText(str(c.tz), start);
      const how = c.mode === 'video' ? (c.videoLink ? `Join: ${c.videoLink}` : 'Video call') : c.mode === 'phone' ? 'Phone call' : `At ${str(c.location)}`;
      const cancelUrl = `https://us-central1-lazo-513ec.cloudfunctions.net/consultCancel?id=${d.id}&t=${c.cancelToken}`;
      try {
        const vs = await db().collection('vendors').doc(str(c.vendorId)).get();
        const v = vs.exists ? vs.data() : {};
        const em = str(c.contact && c.contact.email), ph = str(c.contact && c.contact.phone), smsOk = c.contact && c.contact.smsOk !== false && ph;
        if (emailOk(em)) await sendEmail(em, `${key === 'h1' ? 'In about an hour' : 'Tomorrow'}: ${str(c.typeLabel)} with ${str(c.vendorName)}`,
          brandWrap(v, `<p>Reminder - <b>${str(c.typeLabel)}</b> with ${str(c.vendorName)}<br><b>${when}</b><br>${how.replace(/</g, '&lt;')}</p><p style="font-size:12px;color:#6B5F72">Can't make it? <a href="${cancelUrl}">Cancel here</a>.</p>`), `${str(c.typeLabel)} with ${str(c.vendorName)}: ${when}. ${how}`);
        if (smsOk) await sendSms(ph, `${str(c.vendorName)}: ${key === 'h1' ? 'see you in about an hour' : 'reminder for tomorrow'} - ${str(c.typeLabel)}, ${fmtLocal(str(c.tz), start, { hour: 'numeric', minute: '2-digit' })}. ${c.videoLink || ''}`);
        if (key === 'h1' && e164(v.phone) && v.leadSmsOff !== true) await sendSms(v.phone, `Lazo: ${str(c.contact && c.contact.name)} - ${str(c.typeLabel)} in about an hour (${fmtLocal(str(c.tz), start, { hour: 'numeric', minute: '2-digit' })}). ${APP}?thread=${c.inquiryId}`);
        await d.ref.set({ reminded: { ...rem, [key]: FieldValue.serverTimestamp() } }, { merge: true });
        sent++;
      } catch (e) { console.warn('consult reminder', d.id, e.message); }
    }
    console.log(`consultReminderSweep: ${snap.size} upcoming, ${sent} reminded`);
  });

  return { consultSlots, consultBook, consultCancel, consultReminderSweep };
};

// END OF FILE - JC-LAZO-FNDASH-0913-015
