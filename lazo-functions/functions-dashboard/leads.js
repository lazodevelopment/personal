// functions-dashboard/leads.js
// Build ID: JC-LAZO-FNDASH-0913-014 (014: couple-facing emails wrapped in the vendor brand via brand.js; 012a (012a: inbound ignores texts to other numbers on the shared Telnyx profile)
//
// BUILD B: LEADS FROM ANYWHERE + TWO-WAY SMS.
//
// 1. The embeddable lead form. A vendor drops one script tag on their own
//    website (served by the worker at meetlazo.com/embed/lead.js); it renders
//    a form in a shadow root and POSTs here. The lead becomes an ordinary
//    inquiries doc - same thread, same June, same files, same Money card -
//    with source 'embed', the page it came from and any UTM parameters.
//    The couple has no Lazo account: coupleUid is a synthetic 'lead_<id>'
//    that no user can ever match, contact lives on inquiries.contact, and
//    every vendor reply reaches them by text and email (below).
//
// 2. Two-way SMS on the Lazo Telnyx number (TELNYX_FROM):
//    - onLeadMessage: a vendor message in an off-platform thread goes out to
//      the lead as SMS (+ email). A couple message in any thread where the
//      couple last spoke by SMS is not re-sent (it came from SMS).
//    - telnyxInbound: the lead texts back -> matched by phone to their most
//      recent off-platform thread -> appended as a couple message, vendor
//      notified the usual way. A vendor texting the number back (replying to
//      the lead alert) -> matched by vendors.phone -> appended as a vendor
//      message in their most recent open thread and forwarded to that lead.
//      STOP/UNSUBSCRIBE opts the number out; START opts back in.
//
// Functions
//   leadIngest      POST (cors)  the form's target
//   onLeadMessage   Firestore trigger  inquiries/{id}/messages/{mid} created
//   telnyxInbound   POST  Telnyx messaging webhook (Ed25519-verified)
//
// Secrets: TELNYX_API_KEY, TELNYX_FROM (already set for the default codebase's
// lead alerts), TELNYX_PUBLIC_KEY (new: Mission Control -> Account Settings
// -> Keys & Credentials -> Public Key), RESEND_API_KEY.
//
// Wire-up (functions-dashboard/index.js):
//   const leads = require('./leads')(RESEND_API_KEY);
//   Object.assign(exports, leads);
// Telnyx: Messaging -> your profile -> Inbound settings -> Webhook URL
//   https://us-central1-lazo-513ec.cloudfunctions.net/telnyxInbound  (API v2)

'use strict';

const crypto = require('crypto');
const { onRequest } = require('firebase-functions/v2/https');
const { onDocumentCreated } = require('firebase-functions/v2/firestore');
const { defineSecret } = require('firebase-functions/params');
const admin = require('firebase-admin');
const { wrap: brandWrap } = require('./brand');

const TELNYX_API_KEY = defineSecret('TELNYX_API_KEY');
const TELNYX_FROM = defineSecret('TELNYX_FROM');
const TELNYX_PUBLIC_KEY = defineSecret('TELNYX_PUBLIC_KEY');

const APP = 'https://app.meetlazo.com/dashboard';
const FROM = 'Lazo <hello@meetlazo.com>';

const db = () => admin.firestore();
const { FieldValue, Timestamp } = admin.firestore;
const str = (v) => (v == null ? '' : String(v));
const toDate = (v) => (v && typeof v.toDate === 'function') ? v.toDate() : (v instanceof Date ? v : null);
const clip = (s, n) => str(s).trim().slice(0, n);

// E.164 for US/CA numbers; anything else returned as digits with a plus.
function e164(raw) {
  const d = str(raw).replace(/[^\d]/g, '');
  if (!d) return '';
  if (d.length === 10) return '+1' + d;
  if (d.length === 11 && d.startsWith('1')) return '+' + d;
  if (d.length > 11 && d.length < 16) return '+' + d;
  return '';
}
function phoneVariants(p) {
  const e = e164(p); if (!e) return [];
  const ten = e.startsWith('+1') ? e.slice(2) : '';
  const out = new Set([e, e.slice(1)]);
  if (ten) {
    out.add(ten);
    out.add(`(${ten.slice(0, 3)}) ${ten.slice(3, 6)}-${ten.slice(6)}`);
    out.add(`${ten.slice(0, 3)}-${ten.slice(3, 6)}-${ten.slice(6)}`);
    out.add(`${ten.slice(0, 3)}.${ten.slice(3, 6)}.${ten.slice(6)}`);
    out.add(`1${ten}`);
  }
  return [...out];
}
const emailOk = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(str(e));

module.exports = function leadsModule(RESEND_API_KEY) {

  async function sendEmail(to, subject, html, text, replyTo) {
    if (!emailOk(to)) return;
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${RESEND_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: FROM, to: [to], subject, html, text, ...(replyTo ? { reply_to: replyTo } : {}) }),
    });
    if (!r.ok) throw new Error(`resend ${r.status}: ${await r.text()}`);
  }

  async function sendSms(to, text) {
    const t = e164(to); if (!t) return false;
    const r = await fetch('https://api.telnyx.com/v2/messages', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${TELNYX_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: TELNYX_FROM.value(), to: t, text: clip(text, 1500) }),
    });
    if (!r.ok) { console.warn('telnyx send', r.status, await r.text()); return false; }
    return true;
  }

  // Telnyx signs every webhook: base64 Ed25519 over `${timestamp}|${rawBody}`.
  function verifyTelnyx(req) {
    try {
      const sig = str(req.get('telnyx-signature-ed25519'));
      const ts = str(req.get('telnyx-timestamp'));
      if (!sig || !ts) return false;
      if (Math.abs(Date.now() / 1000 - Number(ts)) > 600) return false;
      const raw = req.rawBody ? req.rawBody.toString('utf8') : JSON.stringify(req.body || {});
      const pub = Buffer.from(TELNYX_PUBLIC_KEY.value().trim(), 'base64');
      const key = crypto.createPublicKey({ key: Buffer.concat([Buffer.from('302a300506032b6570032100', 'hex'), pub]), format: 'der', type: 'spki' });
      return crypto.verify(null, Buffer.from(`${ts}|${raw}`), key, Buffer.from(sig, 'base64'));
    } catch (e) { console.warn('telnyx verify', e.message); return false; }
  }

  async function vendorDoc(vendorId) {
    const s = await db().collection('vendors').doc(vendorId).get();
    return s.exists ? { id: s.id, ...s.data() } : null;
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

  async function addMessage(inquiryId, senderRole, text, extra) {
    const inqRef = db().collection('inquiries').doc(inquiryId);
    await inqRef.collection('messages').add({ senderRole, text: clip(text, 2900), at: FieldValue.serverTimestamp(), ...(extra || {}) });
    await inqRef.set({
      lastMessageAt: FieldValue.serverTimestamp(), lastMessageRole: senderRole,
      lastMessagePreview: clip(text, 140),
      ...(senderRole === 'couple' ? { coupleLastReadAt: FieldValue.serverTimestamp() } : {}),
    }, { merge: true });
  }

  // =============================================================== INGEST ==
  // POST JSON { vendorId, key, name, email, phone, weddingDate, venue, guests,
  //             budget, message, page, referrer, utm:{source,medium,campaign,
  //             content,term}, smsOk, website (honeypot) }
  const leadIngest = onRequest({ cors: true, invoker: 'public', memory: '256MiB', secrets: [RESEND_API_KEY, TELNYX_API_KEY, TELNYX_FROM] }, async (req, res) => {
    if (req.method !== 'POST') return res.status(405).json({ ok: false });
    const b = req.body || {};
    if (str(b.website)) return res.json({ ok: true }); // honeypot
    const vendorId = clip(b.vendorId, 120), key = clip(b.key, 64);
    if (!vendorId || !key) return res.status(400).json({ ok: false, error: 'form' });
    const v = await vendorDoc(vendorId);
    const form = v && v.leadForm && typeof v.leadForm === 'object' ? v.leadForm : null;
    if (!v || !form || str(form.key) !== key || form.enabled === false) return res.status(403).json({ ok: false, error: 'form' });

    const name = clip(b.name, 120), email = clip(b.email, 160).toLowerCase(), phone = e164(b.phone);
    const message = clip(b.message, 2000);
    if (!name || (!emailOk(email) && !phone)) return res.status(400).json({ ok: false, error: 'contact' });

    const weddingDate = /^\d{4}-\d{2}-\d{2}$/.test(str(b.weddingDate)) ? str(b.weddingDate) : '';
    const utm = b.utm && typeof b.utm === 'object' ? b.utm : {};
    const sourceRef = {
      page: clip(b.page, 500), referrer: clip(b.referrer, 500),
      utm_source: clip(utm.source, 80), utm_medium: clip(utm.medium, 80), utm_campaign: clip(utm.campaign, 120),
      utm_content: clip(utm.content, 120), utm_term: clip(utm.term, 120),
    };

    // one thread per lead per vendor: same email or phone within 60 days
    const since = Timestamp.fromDate(new Date(Date.now() - 60 * 86400000));
    let existing = null;
    for (const field of [['contact.email', email], ['contact.phone', phone]]) {
      if (!field[1]) continue;
      const q = await db().collection('inquiries').where('vendorId', '==', vendorId).where(field[0], '==', field[1]).where('createdAt', '>=', since).limit(1).get();
      if (!q.empty) { existing = q.docs[0]; break; }
    }

    const intro = [
      message,
      weddingDate ? `Wedding date: ${weddingDate}` : '',
      str(b.venue) ? `Venue: ${clip(b.venue, 160)}` : '',
      str(b.guests) ? `Guests: ${clip(b.guests, 20)}` : '',
      str(b.budget) ? `Budget: ${clip(b.budget, 40)}` : '',
    ].filter(Boolean).join('\n');

    let inquiryId;
    if (existing) {
      inquiryId = existing.id;
      await addMessage(inquiryId, 'couple', intro || `${name} sent the form again.`, { via: 'embed' });
      await existing.ref.set({ contact: { name, email, phone, smsOk: b.smsOk !== false && !!phone }, sourceRef, status: str(existing.get('status')) === 'lost' ? 'new' : existing.get('status') || 'new' }, { merge: true });
    } else {
      const ref = db().collection('inquiries').doc();
      inquiryId = ref.id;
      await ref.set({
        vendorId, vendorName: str(v.name), coupleUid: `lead_${inquiryId}`, coupleName: name,
        contact: { name, email, phone, smsOk: b.smsOk !== false && !!phone },
        offPlatform: true, source: 'embed', sourceRef,
        structuredIntent: {
          weddingDate, venue: clip(b.venue, 160), guests: clip(b.guests, 20), budget: clip(b.budget, 40),
          message: clip(message, 1000), category: str(v.category || (Array.isArray(v.categories) && v.categories[0])),
        },
        status: 'new', createdAt: FieldValue.serverTimestamp(),
        lastMessageAt: FieldValue.serverTimestamp(), lastMessageRole: 'couple', lastMessagePreview: clip(intro || 'New inquiry from your website', 140),
        fileToken: crypto.randomBytes(18).toString('base64url'), fileTokenAt: FieldValue.serverTimestamp(),
      });
      await ref.collection('messages').add({ senderRole: 'couple', text: intro || `Hi! I found you through your website and would love to hear more.`, at: FieldValue.serverTimestamp(), via: 'embed' });
    }

    // tell the vendor - email always, text when they have a number
    const link = `${APP}?thread=${inquiryId}`;
    const where = sourceRef.utm_source ? ` (${sourceRef.utm_source}${sourceRef.utm_campaign ? ' / ' + sourceRef.utm_campaign : ''})` : '';
    try {
      const to = await vendorOwnerEmail(v);
      if (to) await sendEmail(to, `New lead from your website: ${name}${weddingDate ? ' - ' + weddingDate : ''}`,
        `<p><b>${name}</b> just sent your website form${where}.</p><pre style="font-family:inherit;white-space:pre-wrap">${intro.replace(/</g, '&lt;')}</pre><p>${email ? 'Email: ' + email + '<br>' : ''}${phone ? 'Phone: ' + phone + '<br>' : ''}</p><p><a href="${link}">Reply in Lazo</a> - your reply reaches them by ${phone ? 'text and ' : ''}email.</p>`,
        `${name} sent your website form. ${intro}\nReply in Lazo: ${link}`);
      if (e164(v.phone) && v.leadSmsOff !== true) await sendSms(v.phone, `Lazo: new lead from your website - ${name}${weddingDate ? ', ' + weddingDate : ''}. Reply here or open ${link}`);
    } catch (e) { console.warn('lead notify', e.message); }

    // tell the lead
    try {
      if (emailOk(email)) await sendEmail(email, `${str(v.name)} got your message`,
        brandWrap(v, `<p>Hi ${name},</p><p>Your message reached ${str(v.name)}. They'll reply by ${phone ? 'text or ' : ''}email - you don't need to do anything else.</p>`),
        `Your message reached ${str(v.name)}. They'll reply by ${phone ? 'text or ' : ''}email.`);
      if (phone && b.smsOk !== false) await sendSms(phone, `${str(v.name)}: thanks ${name.split(' ')[0]} - got your message, we'll text you back here. Reply STOP to opt out.`);
    } catch (e) { console.warn('lead ack', e.message); }

    return res.json({ ok: true, redirect: str(form.redirect) || '', thanks: str(form.thanks) || '' });
  });

  // ========================================================== OUTBOUND ==
  // Vendor writes in an off-platform thread -> lead gets it by text + email.
  const onLeadMessage = onDocumentCreated({ document: 'inquiries/{inquiryId}/messages/{messageId}', memory: '256MiB', secrets: [RESEND_API_KEY, TELNYX_API_KEY, TELNYX_FROM] }, async (event) => {
    const m = event.data && event.data.data();
    if (!m || str(m.senderRole) !== 'vendor' || m.system === true || str(m.via) === 'sms') return;
    const inqRef = db().collection('inquiries').doc(event.params.inquiryId);
    const s = await inqRef.get();
    if (!s.exists || s.get('offPlatform') !== true) return;
    const inq = s.data(), c = inq.contact || {};
    const text = str(m.text).trim();
    const att = m.attachment && typeof m.attachment === 'object' ? m.attachment : null;
    const body = text || (att ? `sent you a file: ${str(att.name) || 'attachment'}` : '');
    if (!body) return;
    const vendorName = str(inq.vendorName) || 'Your vendor';
    const page = str(inq.fileToken) ? `https://meetlazo.com/f/${s.id}?t=${inq.fileToken}` : '';
    const vDoc = await vendorDoc(str(inq.vendorId));
    const sent = {};
    if (str(c.phone) && c.smsOk !== false) {
      sent.sms = await sendSms(c.phone, `${vendorName}: ${body}${att || /invoice|proposal|contract|payment/i.test(text) ? (page ? `\n${page}` : '') : ''}`);
    }
    if (emailOk(c.email)) {
      try {
        await sendEmail(c.email, `${vendorName} replied`,
          brandWrap(vDoc, `<p>${body.replace(/</g, '&lt;').replace(/\n/g, '<br>')}</p>${page ? `<p><a href="${page}">Your booking page</a> - proposal, agreement and payments in one place.</p>` : ''}<p style="color:#6B5F72;font-size:12px">${str(c.phone) && c.smsOk !== false ? 'Reply by text to the message we sent, or ' : 'R'}eply to this email and it goes straight to ${vendorName}.</p>`),
          `${vendorName}: ${body}${page ? `\n${page}` : ''}`, emailOk(inq.vendorEmail) ? str(inq.vendorEmail) : undefined);
        sent.email = true;
      } catch (e) { console.warn('lead email', e.message); }
    }
    await event.data.ref.set({ delivered: { ...sent, at: FieldValue.serverTimestamp() } }, { merge: true });
  });

  // =========================================================== INBOUND ==
  const telnyxInbound = onRequest({ invoker: 'public', memory: '256MiB', secrets: [RESEND_API_KEY, TELNYX_API_KEY, TELNYX_FROM, TELNYX_PUBLIC_KEY] }, async (req, res) => {
    if (req.method !== 'POST') return res.status(405).send('POST only');
    if (!verifyTelnyx(req)) return res.status(401).send('bad signature');
    const evt = (req.body && req.body.data) || {};
    if (str(evt.event_type) !== 'message.received') return res.status(200).json({ ok: true, ignored: true });
    const p = evt.payload || {};
    // 012a: the messaging profile is shared with other numbers - only act on
    // texts addressed to the Lazo number, ignore the rest.
    const toNums = Array.isArray(p.to) ? p.to.map((x) => e164(x && x.phone_number)) : [];
    if (!toNums.includes(e164(TELNYX_FROM.value()))) return res.status(200).json({ ok: true, ignored: 'other number' });
    const from = e164(p.from && p.from.phone_number);
    const text = str(p.text).trim();
    const media = Array.isArray(p.media) ? p.media.map((x) => str(x.url)).filter(Boolean) : [];
    if (!from) return res.status(200).json({ ok: true });
    const upper = text.toUpperCase();

    try {
      // 1. a lead texting back
      const lq = await db().collection('inquiries').where('contact.phone', '==', from).where('offPlatform', '==', true).orderBy('lastMessageAt', 'desc').limit(1).get();
      if (!lq.empty) {
        const inq = lq.docs[0];
        if (/^(STOP|STOPALL|UNSUBSCRIBE|CANCEL|END|QUIT)$/.test(upper)) {
          const all = await db().collection('inquiries').where('contact.phone', '==', from).where('offPlatform', '==', true).get();
          const batch = db().batch();
          all.forEach((d) => batch.set(d.ref, { contact: { smsOk: false, smsOptOutAt: FieldValue.serverTimestamp() } }, { merge: true }));
          await batch.commit();
          return res.status(200).json({ ok: true, optOut: true });
        }
        if (/^(START|UNSTOP|YES)$/.test(upper)) {
          await inq.ref.set({ contact: { smsOk: true } }, { merge: true });
          return res.status(200).json({ ok: true, optIn: true });
        }
        await addMessage(inq.id, 'couple', text || (media.length ? 'Sent a photo' : ''), { via: 'sms', ...(media.length ? { attachment: { type: 'image', url: media[0], name: 'photo from text' } } : {}) });
        if (str(inq.get('status')) === 'lost') await inq.ref.set({ status: 'new' }, { merge: true });
        // the vendor's own alert
        const v = await vendorDoc(str(inq.get('vendorId')));
        if (v) {
          const link = `${APP}?thread=${inq.id}`;
          if (e164(v.phone) && v.leadSmsOff !== true) await sendSms(v.phone, `Lazo: ${str(inq.get('coupleName')) || 'A lead'} texted back - "${clip(text, 120)}". Reply here or open ${link}`);
          const to = await vendorOwnerEmail(v);
          if (to) await sendEmail(to, `${str(inq.get('coupleName')) || 'A lead'} texted back`, `<p>${text.replace(/</g, '&lt;')}</p><p><a href="${link}">Reply in Lazo</a></p>`, `${text}\nReply: ${link}`);
        }
        return res.status(200).json({ ok: true, routed: 'lead', inquiryId: inq.id });
      }

      // 2. a vendor replying to their alert text
      let vendor = null;
      for (const variant of phoneVariants(from)) {
        const vq = await db().collection('vendors').where('phone', '==', variant).limit(1).get();
        if (!vq.empty) { vendor = { id: vq.docs[0].id, ...vq.docs[0].data() }; break; }
      }
      if (vendor) {
        if (/^(STOP|STOPALL|UNSUBSCRIBE|CANCEL|END|QUIT)$/.test(upper)) {
          await db().collection('vendors').doc(vendor.id).set({ leadSmsOff: true }, { merge: true });
          return res.status(200).json({ ok: true, optOut: 'vendor' });
        }
        if (/^(START|UNSTOP)$/.test(upper)) {
          await db().collection('vendors').doc(vendor.id).set({ leadSmsOff: false }, { merge: true });
          return res.status(200).json({ ok: true, optIn: 'vendor' });
        }
        // their most recent thread where the couple spoke last (the one they were alerted about)
        const tq = await db().collection('inquiries').where('vendorId', '==', vendor.id).orderBy('lastMessageAt', 'desc').limit(5).get();
        const target = tq.docs.find((d) => str(d.get('lastMessageRole')) === 'couple') || tq.docs[0];
        if (!target) return res.status(200).json({ ok: true, routed: 'vendor', noThread: true });
        await addMessage(target.id, 'vendor', text, { via: 'sms' });
        const tinq = target.data();
        if (tinq.offPlatform === true) {
          const c = tinq.contact || {};
          if (str(c.phone) && c.smsOk !== false) await sendSms(c.phone, `${str(vendor.name)}: ${text}`);
          if (emailOk(c.email)) await sendEmail(c.email, `${str(vendor.name)} replied`, `<p>${text.replace(/</g, '&lt;')}</p>`, text).catch(() => {});
        }
        // on-platform couples see it in the app; the default codebase's onMessageWritten handles their alert
        if (tq.docs.length > 1 && tq.docs.filter((d) => str(d.get('lastMessageRole')) === 'couple').length > 1) {
          await sendSms(from, `Lazo: sent to ${str(tinq.coupleName) || 'the latest couple'}. Other couples are waiting too - ${APP}`);
        }
        return res.status(200).json({ ok: true, routed: 'vendor', inquiryId: target.id });
      }

      // 3. nobody we know
      await db().collection('smsUnmatched').add({ from, text: clip(text, 500), media, at: FieldValue.serverTimestamp() });
      await sendSms(from, `This is Lazo's number for wedding vendors and their couples. If you were texting a vendor, use the link they sent you. meetlazo.com`);
      return res.status(200).json({ ok: true, routed: 'none' });
    } catch (e) {
      console.error('telnyxInbound', e);
      return res.status(200).json({ ok: false }); // 200 so Telnyx doesn't retry forever
    }
  });

  return { leadIngest, onLeadMessage, telnyxInbound };
};

// END OF FILE - JC-LAZO-FNDASH-0913-012
