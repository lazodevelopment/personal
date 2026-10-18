'use strict';
// JC-LAZO-LEADSMAIL-1018-001: leads@meetlazo.com - a vendor forwards a Knot / Zola /
// WeddingWire / any inquiry email and it lands in their Lazo inbox as a lead.
//
// Every 2 minutes: read the unread Inbox of the leads@ mailbox (its own Zoho user, its
// own self-client token - secrets ZOHO_LEADS_*), match the forwarding address to a vendor
// (the owner's users.email, or vendors.email / publicEmail / ownerEmail), have June pull
// the couple out of the forwarded text, and create the lead the way the website form does
// (offPlatform inquiry, source 'email-forward'). Dedupe: same email or phone for the same
// vendor within 60 days joins the existing thread. Texts are off by default for these
// leads (no SMS consent came through the forward); the couple is not auto-acknowledged
// (the platform they wrote on already did that). The vendor gets one reply per forward:
// added, no account, or couldn't read it. Every forward is logged in leadMailImports/{messageId}.

const crypto = require('crypto');
const { onSchedule } = require('firebase-functions/v2/scheduler');
const { defineSecret } = require('firebase-functions/params');
const admin = require('firebase-admin');
const OP = require('./offplatform');
const { frame, esc } = require('./email-frame');

const ZOHO_LEADS_CLIENT_ID = defineSecret('ZOHO_LEADS_CLIENT_ID');
const ZOHO_LEADS_CLIENT_SECRET = defineSecret('ZOHO_LEADS_CLIENT_SECRET');
const ZOHO_LEADS_REFRESH_TOKEN = defineSecret('ZOHO_LEADS_REFRESH_TOKEN');

const LEADS_ADDRESS = 'leads@meetlazo.com';
const APP = 'https://app.meetlazo.com/dashboard';
const FROM = 'Lazo <hello@meetlazo.com>';

const db = () => admin.firestore();
const FieldValue = admin.firestore.FieldValue;
const Timestamp = admin.firestore.Timestamp;
const str = (v) => (v == null ? '' : String(v));
const clip = (s, n) => str(s).trim().slice(0, n);
const emailOk = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(str(e));

function e164(raw) {
  const d = str(raw).replace(/[^\d+]/g, '');
  if (!d) return '';
  if (d.startsWith('+')) return d.length >= 11 ? d : '';
  if (d.length === 10) return '+1' + d;
  if (d.length === 11 && d.startsWith('1')) return '+' + d;
  return '';
}

function stripHtml(html) {
  return String(html || '')
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<noscript[\s\S]*?<\/noscript>/gi, ' ')
    .replace(/<br\s*\/?>/gi, '\n').replace(/<\/(p|div|li|h[1-6]|tr|section|article)>/gi, '\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/[ \t]+/g, ' ').replace(/\n\s*\n+/g, '\n').trim();
}

function platformOf(text, subject) {
  const t = (subject + ' ' + text).toLowerCase();
  if (/theknot|the knot/.test(t)) return 'theknot';
  if (/zola/.test(t)) return 'zola';
  if (/weddingwire/.test(t)) return 'weddingwire';
  if (/withjoy|joy\.com/.test(t)) return 'joy';
  if (/instagram/.test(t)) return 'instagram';
  return 'email';
}

const PARSE_SYSTEM = `You read an inquiry email that a wedding vendor forwarded to Lazo. The email usually came from The Knot, Zola, WeddingWire, Joy, Instagram or the couple directly, and may include quoted headers and the platform's boilerplate. Return ONLY a JSON object:
{"name":"<the couple's name(s) as written, e.g. 'Maya & Leo' or 'Maya Chen'>","email":"<the couple's email or empty>","phone":"<the couple's phone or empty>","weddingDate":"<YYYY-MM-DD or empty>","venue":"<venue or city if named, else empty>","guests":"<guest count as written or empty>","budget":"<budget as written or empty>","message":"<the couple's own words, cleaned of boilerplate, max 1500 chars>","confidence":<0..1>}
Rules: the couple is the person asking about the vendor's services, never the vendor, never Lazo, never the platform. Do not use the forwarding vendor's own name or email. If there is no inquiry from a couple in this email, return {"name":"","confidence":0}. Never invent an email, phone or date.`;

// what the sweep expects back from June - exported for the local test
function normalizeParsed(out) {
  const o = out && typeof out === 'object' ? out : {};
  const name = clip(o.name, 120);
  const email = emailOk(str(o.email).trim().toLowerCase()) ? str(o.email).trim().toLowerCase() : '';
  const phone = e164(o.phone);
  const weddingDate = /^\d{4}-\d{2}-\d{2}$/.test(str(o.weddingDate)) ? str(o.weddingDate) : '';
  return {
    name, email, phone, weddingDate,
    venue: clip(o.venue, 160), guests: clip(o.guests, 20), budget: clip(o.budget, 40),
    message: clip(o.message, 1500), confidence: Number(o.confidence) || 0,
  };
}

module.exports = function leadsMailModule(RESEND_API_KEY, ANTHROPIC_API_KEY) {
  async function sendEmail(to, subject, html, text) {
    if (!emailOk(to)) return;
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { Authorization: `Bearer ${RESEND_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: FROM, to: [to], subject, html, text }),
    });
    if (!r.ok) throw new Error(`resend ${r.status}: ${await r.text()}`);
  }

  async function claudeJson(system, userText) {
    const r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'x-api-key': ANTHROPIC_API_KEY.value(), 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
      body: JSON.stringify({ model: 'claude-sonnet-4-6', max_tokens: 1200, system, messages: [{ role: 'user', content: [{ type: 'text', text: userText }] }] }),
    });
    if (!r.ok) throw new Error(`anthropic ${r.status}: ${(await r.text()).slice(0, 200)}`);
    const j = await r.json();
    const text = (j.content || []).filter((c) => c.type === 'text').map((c) => c.text).join('\n');
    const m = /\{[\s\S]*\}/.exec(text.replace(/```json|```/g, ''));
    if (!m) throw new Error('no json in reply');
    return JSON.parse(m[0]);
  }

  // ---- Zoho (the leads@ user's own token; values trimmed because PowerShell adds a newline)
  let ACCOUNT_ID = '';
  async function zohoToken() {
    const r = await fetch('https://accounts.zoho.com/oauth/v2/token', {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        client_id: ZOHO_LEADS_CLIENT_ID.value().trim(),
        client_secret: ZOHO_LEADS_CLIENT_SECRET.value().trim(),
        refresh_token: ZOHO_LEADS_REFRESH_TOKEN.value().trim(),
      }),
    });
    const j = await r.json();
    if (!j.access_token) throw new Error('zoho token: ' + JSON.stringify(j).slice(0, 200));
    return j.access_token;
  }
  async function zohoAccount(token) {
    if (ACCOUNT_ID) return ACCOUNT_ID;
    const r = await fetch('https://mail.zoho.com/api/accounts', { headers: { Authorization: `Zoho-oauthtoken ${token}` } });
    const j = await r.json().catch(() => ({}));
    const acc = (j.data || []).find((a) => str(a.primaryEmailAddress).toLowerCase() === LEADS_ADDRESS) || (j.data || [])[0];
    if (!acc) throw new Error('zoho: no mailbox visible to this token');
    ACCOUNT_ID = str(acc.accountId);
    return ACCOUNT_ID;
  }
  async function zoho(path, token, opts) {
    const r = await fetch(`https://mail.zoho.com/api/accounts/${ACCOUNT_ID}${path}`, {
      ...(opts || {}),
      headers: { Authorization: `Zoho-oauthtoken ${token}`, 'content-type': 'application/json', ...((opts && opts.headers) || {}) },
    });
    return r.json().catch(() => ({}));
  }
  const markRead = (token, messageId) =>
    zoho('/updatemessage', token, { method: 'PUT', body: JSON.stringify({ mode: 'markAsRead', messageId: [messageId] }) }).catch(() => {});

  // ---- who forwarded it: a vendor's sign-in email first, then the listing's own addresses
  async function vendorForSender(sender) {
    const us = await db().collection('users').where('email', '==', sender).limit(3).get();
    for (const u of us.docs) {
      const vid = str(u.get('vendorId'));
      if (!vid) continue;
      const v = await db().collection('vendors').doc(vid).get();
      if (v.exists) return { id: v.id, ...v.data(), ownerEmail: sender };
    }
    for (const field of ['email', 'publicEmail', 'ownerEmail']) {
      const q = await db().collection('vendors').where(field, '==', sender).limit(1).get();
      if (!q.empty) return { id: q.docs[0].id, ...q.docs[0].data(), ownerEmail: sender };
    }
    // extra forwarding addresses the vendor added (Lead form sheet > From other sites), e.g. the
    // Gmail their Zola or Knot notices go to
    const fq = await db().collection('vendors').where('forwardFrom', 'array-contains', sender).limit(1).get();
    if (!fq.empty) return { id: fq.docs[0].id, ...fq.docs[0].data(), ownerEmail: sender };
    return null;
  }

  async function createOrJoinLead(v, p, meta) {
    const vendorId = v.id;
    const since = Timestamp.fromDate(new Date(Date.now() - 60 * 86400000));
    let existing = null;
    for (const field of [['contact.email', p.email], ['contact.phone', p.phone]]) {
      if (!field[1]) continue;
      const q = await db().collection('inquiries').where('vendorId', '==', vendorId).where(field[0], '==', field[1]).where('createdAt', '>=', since).limit(1).get();
      if (!q.empty) { existing = q.docs[0]; break; }
    }
    const intro = [
      p.message,
      p.weddingDate ? `Wedding date: ${p.weddingDate}` : '',
      p.venue ? `Venue: ${p.venue}` : '',
      p.guests ? `Guests: ${p.guests}` : '',
      p.budget ? `Budget: ${p.budget}` : '',
    ].filter(Boolean).join('\n') || `${p.name} wrote through ${meta.platformLabel}.`;
    const sc = OP.scan(intro);
    const flag = sc.level === 'strong' || sc.level === 'weak' ? { level: sc.level, matches: [...sc.strong, ...sc.weak].slice(0, 5) } : null;
    const sourceRef = { platform: meta.platform, forwardedFrom: meta.sender, subject: clip(meta.subject, 200), messageId: meta.messageId };

    if (existing) {
      const ref = existing.ref;
      await ref.collection('messages').add({ senderRole: 'couple', text: clip(intro, 2900), at: FieldValue.serverTimestamp(), via: 'email-forward', ...(flag ? { safetyFlag: flag } : {}) });
      await ref.set({
        contact: { name: p.name, email: p.email, phone: p.phone, smsOk: false },
        sourceRef,
        status: str(existing.get('status')) === 'lost' ? 'new' : (existing.get('status') || 'new'),
        lastMessageAt: FieldValue.serverTimestamp(), lastMessageRole: 'couple', lastMessagePreview: clip(intro, 140),
        ...(flag ? { safetyFlag: { ...flag, at: FieldValue.serverTimestamp() } } : {}),
      }, { merge: true });
      return { inquiryId: existing.id, existing: true };
    }
    const ref = db().collection('inquiries').doc();
    await ref.set({
      vendorId, vendorName: str(v.name), coupleUid: `lead_${ref.id}`, coupleName: p.name,
      contact: { name: p.name, email: p.email, phone: p.phone, smsOk: false },
      offPlatform: true, source: 'email-forward', sourceRef,
      structuredIntent: {
        weddingDate: p.weddingDate, venue: p.venue, guests: p.guests, budget: p.budget,
        message: clip(p.message, 1000), category: str(v.category || (Array.isArray(v.categories) && v.categories[0])),
      },
      status: 'new', createdAt: FieldValue.serverTimestamp(),
      lastMessageAt: FieldValue.serverTimestamp(), lastMessageRole: 'couple', lastMessagePreview: clip(intro, 140),
      fileToken: crypto.randomBytes(18).toString('base64url'), fileTokenAt: FieldValue.serverTimestamp(),
      ...(flag ? { safetyFlag: { ...flag, at: FieldValue.serverTimestamp() } } : {}),
    });
    await ref.collection('messages').add({ senderRole: 'couple', text: clip(intro, 2900), at: FieldValue.serverTimestamp(), via: 'email-forward', ...(flag ? { safetyFlag: flag } : {}) });
    return { inquiryId: ref.id, existing: false };
  }

  const leadsMailSweep = onSchedule({
    schedule: 'every 2 minutes', timeZone: 'UTC', memory: '512MiB', timeoutSeconds: 120,
    secrets: [ZOHO_LEADS_CLIENT_ID, ZOHO_LEADS_CLIENT_SECRET, ZOHO_LEADS_REFRESH_TOKEN, ANTHROPIC_API_KEY, RESEND_API_KEY],
  }, async () => {
    const token = await zohoToken();
    await zohoAccount(token);
    // No folder lookup: the token's scope is messages + accounts only (/folders answers 401),
    // and messages/view without a folderId lists the Inbox. Each item carries its folderId.
    const list = await zoho('/messages/view?status=unread&limit=20&sortorder=false', token);
    const msgs = list.data || [];
    if (!msgs.length) return;

    for (const m of msgs) {
      const messageId = str(m.messageId);
      const logRef = db().collection('leadMailImports').doc(messageId);
      if ((await logRef.get()).exists) { await markRead(token, messageId); continue; }
      const sender = (str(m.fromAddress) || (/<([^>]+)>/.exec(str(m.sender)) || [])[1] || '').toLowerCase().trim();
      const subject = str(m.subject);
      const record = { sender, subject: clip(subject, 200), receivedAt: FieldValue.serverTimestamp(), status: 'skipped' };
      try {
        // our own address, bounces, and Zoho's own welcome / notice mail: file and move on
        if (sender === LEADS_ADDRESS || /mailer-daemon|postmaster|no-?reply@meetlazo|@zoho[a-z]*\./.test(sender)) {
          record.status = 'self';
          await logRef.set(record); await markRead(token, messageId); continue;
        }
        const v = await vendorForSender(sender);
        if (!v) {
          await sendEmail(sender, 'We couldn’t match that forward to your Lazo account',
            frame({
              preheader: `Nothing was added. ${sender} isn’t on a Lazo vendor account yet.`,
              kicker: 'Forwarded inquiry', title: 'We couldn’t match that one.',
              lede: `Thanks for forwarding it. We couldn’t find a Lazo vendor account under <b>${esc(sender)}</b>, so nothing was added.`,
              body: `<p style="margin:0 0 12px;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#241E2B">Two ways to fix it, either takes a minute:</p>
<p style="margin:0 0 10px;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#241E2B"><b>1.</b> Forward it again from the email you sign in to Lazo with.</p>
<p style="margin:0;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#241E2B"><b>2.</b> Or add <b>${esc(sender)}</b> as a forwarding address in Lazo: Account › Lead form for your website › From other sites. After that, every forward from it lands in your inbox.</p>`,
              cta: 'Open Lazo', ctaHref: APP,
              footerWhy: 'You’re getting this because an email was forwarded to leads@meetlazo.com from this address.',
            }),
            `We couldn't find a Lazo vendor account under ${sender}. Forward it again from the address you sign in with, or add ${sender} under Account > Lead form > From other sites.`);
          record.status = 'no-account';
          await logRef.set(record); await markRead(token, messageId); continue;
        }
        const content = await zoho(`/folders/${str(m.folderId)}/messages/${messageId}/content`, token);
        const bodyText = stripHtml(content.data && content.data.content).slice(0, 20000);
        const platform = platformOf(bodyText, subject);
        const platformLabel = { theknot: 'The Knot', zola: 'Zola', weddingwire: 'WeddingWire', joy: 'Joy', instagram: 'Instagram', email: 'email' }[platform];
        const userText = `Forwarded by the vendor ${str(v.name)} (${sender}).\nSubject: ${subject}\n\n${bodyText}\n\nExtract the couple's inquiry.`;
        let parsed;
        try { parsed = normalizeParsed(await claudeJson(PARSE_SYSTEM, userText)); } catch (e) { parsed = normalizeParsed(null); record.parseError = str(e.message).slice(0, 200); }
        if (!parsed.name || parsed.confidence < 0.4 || (!parsed.email && !parsed.phone && !parsed.message)) {
          await sendEmail(sender, 'We couldn’t read that one',
            frame({
              preheader: 'June couldn’t find a couple’s inquiry in that email, so nothing was added.',
              kicker: 'Forwarded inquiry', title: 'June couldn’t find a couple in it.',
              lede: `Thanks for forwarding <i>${esc(subject || 'that email')}</i>. There wasn’t a couple’s inquiry June could read, so nothing was added.`,
              body: `<p style="margin:0;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#241E2B">If it is one, forward the original message rather than a notification that only links to it. Or add the couple yourself in a few seconds with <b>Add a client</b> in your Lazo inbox.</p>`,
              cta: 'Open your inbox', ctaHref: APP,
              footerWhy: 'You’re getting this because you forwarded an email to leads@meetlazo.com.',
            }),
            `June couldn't find a couple's inquiry in "${subject}". Nothing was added.`);
          record.status = 'unrecognized'; record.vendorId = v.id;
          await logRef.set(record); await markRead(token, messageId); continue;
        }
        // a couple the vendor blocked as spam / scam (Vendor v218): file it, tell nobody
        const blocked = Array.isArray(v.blockedSenders) ? v.blockedSenders.map((x) => str(x).toLowerCase()) : [];
        if ((parsed.email && blocked.includes(parsed.email)) || (parsed.phone && blocked.includes(parsed.phone))) {
          record.status = 'blocked'; record.vendorId = v.id; record.name = parsed.name;
          await logRef.set(record); await markRead(token, messageId); continue;
        }
        const r = await createOrJoinLead(v, parsed, { platform, platformLabel, sender, subject, messageId });
        const link = `${APP}?thread=${r.inquiryId}`;
        const when = parsed.weddingDate ? ` · ${parsed.weddingDate}` : '';
        const details = [
          parsed.weddingDate ? ['Wedding date', parsed.weddingDate] : null,
          parsed.venue ? ['Venue', parsed.venue] : null,
          parsed.guests ? ['Guests', parsed.guests] : null,
          parsed.budget ? ['Budget', parsed.budget] : null,
          parsed.email ? ['Email', parsed.email] : null,
          parsed.phone ? ['Phone', parsed.phone] : null,
        ].filter(Boolean);
        await sendEmail(sender, `${parsed.name} is in your inbox${when}`,
          frame({
            preheader: `${parsed.name} from ${platformLabel} is ${r.existing ? 'back in their thread' : 'a new lead in your Lazo inbox'}.`,
            kicker: r.existing ? 'Back in their thread' : 'New lead',
            title: `${esc(parsed.name)} is in your inbox.`,
            lede: `Forwarded from ${esc(platformLabel)} and filed by June. Reply in Lazo and they get it by email${parsed.phone ? '; texts stay off until they opt in' : ''}.`,
            body: `${parsed.message ? `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:6px 0 16px"><tr><td style="border-left:3px solid #D9B77C;padding:4px 0 4px 16px;font-family:Georgia,'Times New Roman',serif;font-size:16px;line-height:1.55;color:#3D1C3B">${esc(parsed.message).replace(/\n/g, '<br>')}</td></tr></table>` : ''}${details.length ? `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:0 0 6px">${details.map((d) => `<tr><td style="padding:5px 0;font-family:Helvetica,Arial,sans-serif;font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:#8A6A2F;width:130px">${esc(d[0])}</td><td style="padding:5px 0;font-family:Helvetica,Arial,sans-serif;font-size:15px;color:#241E2B">${esc(d[1])}</td></tr>`).join('')}</table>` : ''}`,
            cta: 'Open the thread', ctaHref: link,
            footerWhy: 'You’re getting this because you forwarded an inquiry to leads@meetlazo.com.',
          }),
          `${parsed.name} from ${platformLabel} is in your Lazo inbox. ${link}`);
        record.status = r.existing ? 'joined' : 'added'; record.vendorId = v.id; record.inquiryId = r.inquiryId; record.platform = platform; record.name = parsed.name;
        await logRef.set(record); await markRead(token, messageId);
      } catch (e) {
        console.error('leadsMailSweep', messageId, e.message);
        record.status = 'error'; record.error = str(e.message).slice(0, 300);
        await logRef.set(record).catch(() => {});
        await markRead(token, messageId);
      }
    }
  });

  return { leadsMailSweep };
};

// local test hook (test/leads-mail-parse.js): the same prompt and normaliser the sweep uses
module.exports.parseInquiry = async function parseInquiry(apiKey, vendorName, sender, subject, bodyText) {
  const r = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'x-api-key': apiKey, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
    body: JSON.stringify({ model: 'claude-sonnet-4-6', max_tokens: 1200, system: PARSE_SYSTEM, messages: [{ role: 'user', content: [{ type: 'text', text: `Forwarded by the vendor ${vendorName} (${sender}).\nSubject: ${subject}\n\n${bodyText}\n\nExtract the couple's inquiry.` }] }] }),
  });
  if (!r.ok) throw new Error(`anthropic ${r.status}: ${(await r.text()).slice(0, 200)}`);
  const j = await r.json();
  const text = (j.content || []).filter((c) => c.type === 'text').map((c) => c.text).join('\n');
  const m = /\{[\s\S]*\}/.exec(text.replace(/```json|```/g, ''));
  return normalizeParsed(m ? JSON.parse(m[0]) : null);
};
module.exports.normalizeParsed = normalizeParsed;
module.exports.platformOf = platformOf;
module.exports.stripHtml = stripHtml;
module.exports.PARSE_SYSTEM = PARSE_SYSTEM;
