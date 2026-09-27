// functions-dashboard/mcp.js
// Build ID: JC-LAZO-FNDASH-0913-018 (018: practice-couple threads and their invoices are invisible to the assistant; base 016)
//
// BUILD F: THE LAZO MCP CONNECTOR.
//
// A Model Context Protocol server (Streamable HTTP, JSON-RPC 2.0, POST-only)
// so a vendor can ask Claude, ChatGPT, Cursor or any MCP client about their
// business and have it act inside Lazo:
//
//   https://us-central1-lazo-513ec.cloudfunctions.net/mcp/<token>
//
// The token is minted on the vendor's Account screen ("Connect Claude"); only
// sha256(token) is stored at vendors.mcp.tokenHash, so a leaked Firestore
// export exposes nothing. Rotating it invalidates every client at once.
//
// Read tools:  lazo_overview, lazo_pipeline, lazo_thread, lazo_upcoming,
//              lazo_money, lazo_search
// Write tools: lazo_send_message, lazo_add_task, lazo_complete_task,
//              lazo_tag, lazo_set_stage
// Writes are ordinary vendor writes (same fields the dashboard writes),
// stamped via: 'mcp' so the thread shows they came from the assistant.
//
// Wire-up (index.js):  Object.assign(exports, require('./mcp')());

'use strict';

const crypto = require('crypto');
const { onRequest, onCall, HttpsError } = require('firebase-functions/v2/https');
const admin = require('firebase-admin');

const db = () => admin.firestore();
const { FieldValue, Timestamp } = admin.firestore;
const str = (v) => (v == null ? '' : String(v));
const clip = (s, n) => str(s).trim().slice(0, n);
const toDate = (v) => (v && typeof v.toDate === 'function') ? v.toDate() : (v instanceof Date ? v : null);
const iso = (v) => { const d = toDate(v); return d ? d.toISOString() : null; };
const sha = (t) => crypto.createHash('sha256').update(str(t)).digest('hex');
const PROTOCOL = '2025-03-26';

// ------------------------------------------------------------- tools -----
const TOOLS = [
  { name: 'lazo_overview', description: 'A one-screen summary of the vendor\'s business on Lazo: unread leads, threads waiting on a reply, upcoming weddings and consults, money outstanding, open tasks due today.', inputSchema: { type: 'object', properties: {} } },
  { name: 'lazo_pipeline', description: 'List threads (leads and couples) with their stage, tags, wedding date, last message and next task. Filter by stage or tag.', inputSchema: { type: 'object', properties: { stage: { type: 'string', description: 'new | talking | booked | delivered | lost | <custom stage key>' }, tag: { type: 'string' }, limit: { type: 'integer', default: 50 } } } },
  { name: 'lazo_thread', description: 'Everything about one thread: the couple, their contact details and wedding info, the full conversation, proposals, contracts, invoices/payment plan, tasks and consults.', inputSchema: { type: 'object', properties: { inquiryId: { type: 'string' } }, required: ['inquiryId'] } },
  { name: 'lazo_upcoming', description: 'Booked weddings and scheduled consults in date order.', inputSchema: { type: 'object', properties: { days: { type: 'integer', default: 90 } } } },
  { name: 'lazo_money', description: 'Open and overdue invoices/installments across every thread, and what was collected recently.', inputSchema: { type: 'object', properties: {} } },
  { name: 'lazo_search', description: 'Find threads by couple name, venue, email, phone or tag.', inputSchema: { type: 'object', properties: { query: { type: 'string' } }, required: ['query'] } },
  { name: 'lazo_send_message', description: 'Send a message to the couple in a thread, as the vendor. Off-platform leads receive it by text and email automatically.', inputSchema: { type: 'object', properties: { inquiryId: { type: 'string' }, text: { type: 'string' } }, required: ['inquiryId', 'text'] } },
  { name: 'lazo_add_task', description: 'Add a task to a thread, for the vendor or for the couple, with an optional due date (YYYY-MM-DD).', inputSchema: { type: 'object', properties: { inquiryId: { type: 'string' }, title: { type: 'string' }, dueDate: { type: 'string' }, assignedTo: { type: 'string', enum: ['vendor', 'couple'], default: 'vendor' }, note: { type: 'string' } }, required: ['inquiryId', 'title'] } },
  { name: 'lazo_complete_task', description: 'Mark a task done.', inputSchema: { type: 'object', properties: { inquiryId: { type: 'string' }, taskId: { type: 'string' } }, required: ['inquiryId', 'taskId'] } },
  { name: 'lazo_tag', description: 'Add or remove a tag on a thread.', inputSchema: { type: 'object', properties: { inquiryId: { type: 'string' }, tag: { type: 'string' }, remove: { type: 'boolean', default: false } }, required: ['inquiryId', 'tag'] } },
  { name: 'lazo_set_stage', description: 'Move a thread to a pipeline stage (new, talking, or a custom stage key). Booked/delivered/lost are statuses the vendor sets in the app, not here.', inputSchema: { type: 'object', properties: { inquiryId: { type: 'string' }, stage: { type: 'string' } }, required: ['inquiryId', 'stage'] } },
];

function stageOf(inq, customKeys) {
  const st = str(inq.status);
  if (st === 'lost') return 'lost';
  if (st === 'booked') return inq.deliveredAt ? 'delivered' : 'booked';
  const ex = str(inq.stage);
  if (ex && customKeys.includes(ex)) return ex;
  if (st === 'responded' || st === 'replied' || str(inq.lastMessageRole) === 'vendor') return 'talking';
  return 'new';
}
function threadRow(d, customKeys) {
  const m = d.data(); const si = m.structuredIntent || {};
  return {
    inquiryId: d.id, couple: str(m.coupleName), stage: stageOf(m, customKeys), status: str(m.status) || 'new',
    tags: Array.isArray(m.tags) ? m.tags : [], weddingDate: str(si.weddingDate) || null, venue: str(si.venue) || null, budget: str(si.budget) || null,
    source: str(m.source) || 'lazo', offPlatform: m.offPlatform === true,
    lastMessageAt: iso(m.lastMessageAt), lastMessageFrom: str(m.lastMessageRole) || null, lastMessagePreview: str(m.lastMessagePreview) || null,
    waitingOnVendor: str(m.lastMessageRole) === 'couple' || (!m.lastMessageRole && (str(m.status) === 'new' || !m.status)),
    contractStatus: str(m.contractStatus) || null, invoiceStatus: str(m.invoiceStatus) || null,
    openTasks: m.openTasks || 0, nextTask: str(m.nextTaskTitle) ? { title: str(m.nextTaskTitle), dueAt: iso(m.nextTaskAt) } : null,
    nextConsultAt: iso(m.nextConsultAt),
  };
}

async function vendorByToken(token) {
  if (!token || token.length < 20) return null;
  const q = await db().collection('vendors').where('mcp.tokenHash', '==', sha(token)).limit(1).get();
  if (q.empty) return null;
  const v = q.docs[0];
  if (v.get('mcp.enabled') === false) return null;
  return { id: v.id, ...v.data() };
}
async function ownThread(vendorId, inquiryId) {
  const s = await db().collection('inquiries').doc(clip(inquiryId, 80)).get();
  if (!s.exists || str(s.get('vendorId')) !== vendorId) throw new Error('No such thread on this account.');
  return s;
}

async function callTool(v, name, a) {
  const vendorId = v.id;
  const customKeys = (Array.isArray(v.pipeline) ? v.pipeline : []).map((p) => str(p && p.key)).filter(Boolean);
  const threads = async () => (await db().collection('inquiries').where('vendorId', '==', vendorId).get()).docs.filter((d) => str(d.get('status')) !== 'flagged' && d.get('demo') !== true);

  switch (name) {
    case 'lazo_overview': {
      const docs = await threads();
      const rows = docs.map((d) => threadRow(d, customKeys));
      const now = new Date(), in30 = new Date(Date.now() + 30 * 86400000);
      const weddings = rows.filter((r) => r.status === 'booked' && r.weddingDate).sort((x, y) => x.weddingDate.localeCompare(y.weddingDate)).slice(0, 5);
      const cons = await db().collection('consults').where('vendorId', '==', vendorId).where('status', '==', 'booked').where('startAt', '>=', Timestamp.fromDate(now)).orderBy('startAt').limit(5).get();
      const inv = await db().collectionGroup('invoices').where('vendorId', '==', vendorId).where('status', '==', 'sent').get();
      let outstanding = 0, overdue = 0;
      inv.forEach((i) => { if (i.get('demo') === true) return; const t = +i.get('total') || 0; outstanding += t; const due = toDate(i.get('dueDate')); if (due && due < now) overdue += t; });
      const tasks = await db().collectionGroup('tasks').where('vendorId', '==', vendorId).where('done', '==', false).get();
      const endToday = new Date(now); endToday.setHours(23, 59, 59, 999);
      const dueToday = tasks.docs.filter((t) => { const d = toDate(t.get('dueAt')); return d && d <= endToday; }).map((t) => ({ taskId: t.id, inquiryId: t.ref.parent.parent.id, title: str(t.get('title')), dueAt: iso(t.get('dueAt')), assignedTo: str(t.get('assignedTo')) }));
      return {
        vendor: { id: vendorId, name: str(v.name), tier: str(v.tier) || 'free' },
        counts: { threads: rows.length, waitingOnYou: rows.filter((r) => r.waitingOnVendor && r.status !== 'lost').length, booked: rows.filter((r) => r.status === 'booked').length, byStage: rows.reduce((acc, r) => { acc[r.stage] = (acc[r.stage] || 0) + 1; return acc; }, {}) },
        waitingOnYou: rows.filter((r) => r.waitingOnVendor && r.status !== 'lost').sort((x, y) => (y.lastMessageAt || '').localeCompare(x.lastMessageAt || '')).slice(0, 10),
        upcomingWeddings: weddings, upcomingConsults: cons.docs.map((c) => ({ consultId: c.id, inquiryId: str(c.get('inquiryId')), who: str(c.get('contact') && c.get('contact').name), type: str(c.get('typeLabel')), mode: str(c.get('mode')), startAt: iso(c.get('startAt')), tz: str(c.get('tz')) })),
        money: { outstanding: Math.round(outstanding), overdue: Math.round(overdue), openInvoices: inv.size },
        tasksDueToday: dueToday, next30Days: weddings.filter((w) => new Date(w.weddingDate) <= in30).length,
      };
    }
    case 'lazo_pipeline': {
      const docs = await threads();
      let rows = docs.map((d) => threadRow(d, customKeys));
      if (a.stage) rows = rows.filter((r) => r.stage === str(a.stage));
      if (a.tag) rows = rows.filter((r) => r.tags.includes(str(a.tag)));
      rows.sort((x, y) => (y.lastMessageAt || '').localeCompare(x.lastMessageAt || ''));
      return { stages: ['new', 'talking', ...customKeys, 'booked', 'delivered', 'lost'], customStages: v.pipeline || [], threads: rows.slice(0, Math.min(200, +a.limit || 50)) };
    }
    case 'lazo_search': {
      const q = clip(a.query, 80).toLowerCase();
      const docs = await threads();
      const rows = docs.filter((d) => { const m = d.data(); const si = m.structuredIntent || {}; const c = m.contact || {}; return [m.coupleName, si.venue, c.email, c.phone, (m.tags || []).join(' ')].some((x) => str(x).toLowerCase().includes(q)); }).map((d) => threadRow(d, customKeys));
      return { query: q, matches: rows.slice(0, 25) };
    }
    case 'lazo_thread': {
      const s = await ownThread(vendorId, a.inquiryId);
      const m = s.data();
      const [msgs, props, cons, invs, tasks, consults] = await Promise.all([
        s.ref.collection('messages').orderBy('at').limit(300).get(),
        s.ref.collection('proposals').orderBy('createdAt', 'desc').limit(5).get(),
        s.ref.collection('contracts').orderBy('createdAt', 'desc').limit(5).get(),
        s.ref.collection('invoices').orderBy('createdAt').get(),
        s.ref.collection('tasks').orderBy('dueAt').get(),
        db().collection('consults').where('inquiryId', '==', s.id).get(),
      ]);
      const row = threadRow(s, customKeys);
      return {
        ...row, contact: m.contact || null, intent: m.structuredIntent || {}, sourceRef: m.sourceRef || null, paymentPlan: m.paymentPlan || null,
        bookingPage: str(m.fileToken) ? `https://meetlazo.com/f/${s.id}?t=${m.fileToken}` : null, bookingLink: `https://meetlazo.com/book/${vendorId}?inq=${s.id}`,
        messages: msgs.docs.map((d) => { const x = d.data(); return { at: iso(x.at), from: x.system ? 'system' : str(x.senderRole), via: str(x.via) || null, text: str(x.text), attachment: x.attachment ? { name: str(x.attachment.name), type: str(x.attachment.type) } : null }; }),
        proposals: props.docs.map((d) => { const x = d.data(); return { id: d.id, title: str(x.title), price: x.price, status: str(x.status), createdAt: iso(x.createdAt) }; }),
        contracts: cons.docs.map((d) => { const x = d.data(); return { id: d.id, title: str(x.title), status: str(x.status), signedAt: iso(x.signedAt), total: x.values && x.values.total_price }; }),
        invoices: invs.docs.filter((d) => str(d.get('status')) !== 'void').map((d) => { const x = d.data(); return { id: d.id, title: str(x.title), total: x.total, status: str(x.status), dueDate: iso(x.dueDate), paidAt: iso(x.paidAt), paidVia: str(x.paidVia) || null, installment: x.installmentCount ? `${(x.installmentIndex || 0) + 1} of ${x.installmentCount}` : null }; }),
        tasks: tasks.docs.map((d) => { const x = d.data(); return { taskId: d.id, title: str(x.title), note: str(x.note), dueAt: iso(x.dueAt), assignedTo: str(x.assignedTo), done: x.done === true }; }),
        consults: consults.docs.map((d) => { const x = d.data(); return { consultId: d.id, type: str(x.typeLabel), mode: str(x.mode), startAt: iso(x.startAt), status: str(x.status) }; }),
      };
    }
    case 'lazo_upcoming': {
      const days = Math.min(365, +a.days || 90);
      const until = new Date(Date.now() + days * 86400000);
      const docs = await threads();
      const weddings = docs.map((d) => threadRow(d, customKeys)).filter((r) => r.status === 'booked' && r.weddingDate && new Date(r.weddingDate) <= until).sort((x, y) => x.weddingDate.localeCompare(y.weddingDate));
      const cons = await db().collection('consults').where('vendorId', '==', vendorId).where('status', '==', 'booked').where('startAt', '>=', Timestamp.fromDate(new Date())).where('startAt', '<=', Timestamp.fromDate(until)).orderBy('startAt').get();
      return { weddings, consults: cons.docs.map((c) => ({ consultId: c.id, inquiryId: str(c.get('inquiryId')), who: str(c.get('contact') && c.get('contact').name), type: str(c.get('typeLabel')), mode: str(c.get('mode')), startAt: iso(c.get('startAt')), tz: str(c.get('tz')), videoLink: str(c.get('videoLink')) || null })), blockedDates: Array.isArray(v.unavailableDates) ? v.unavailableDates : [] };
    }
    case 'lazo_money': {
      const inv = await db().collectionGroup('invoices').where('vendorId', '==', vendorId).get();
      const now = new Date(), since = new Date(Date.now() - 30 * 86400000);
      const open = [], paid = [];
      inv.forEach((i) => { const x = i.data(); const row = { invoiceId: i.id, inquiryId: i.ref.parent.parent.id, couple: '', title: str(x.title), total: x.total, dueDate: iso(x.dueDate), status: str(x.status), paidAt: iso(x.paidAt), paidVia: str(x.paidVia) || null, installment: x.installmentCount ? `${(x.installmentIndex || 0) + 1} of ${x.installmentCount}` : null }; if (row.status === 'sent') { row.overdue = !!(toDate(x.dueDate) && toDate(x.dueDate) < now); open.push(row); } else if (row.status === 'paid' && toDate(x.paidAt) && toDate(x.paidAt) >= since) paid.push(row); });
      const names = {};
      for (const r of [...open, ...paid]) { if (!names[r.inquiryId]) { const s = await db().collection('inquiries').doc(r.inquiryId).get(); names[r.inquiryId] = s.exists ? str(s.get('coupleName')) : ''; } r.couple = names[r.inquiryId]; }
      return { outstanding: Math.round(open.reduce((s, r) => s + (+r.total || 0), 0)), overdue: Math.round(open.filter((r) => r.overdue).reduce((s, r) => s + (+r.total || 0), 0)), collectedLast30Days: Math.round(paid.reduce((s, r) => s + (+r.total || 0), 0)), open: open.sort((x, y) => (x.dueDate || '').localeCompare(y.dueDate || '')), recentlyPaid: paid, rail: str(v.payments && v.payments.processor) || (v.stripeChargesEnabled ? 'stripe' : v.squareConnected ? 'square' : 'links') };
    }
    case 'lazo_send_message': {
      const s = await ownThread(vendorId, a.inquiryId);
      const text = clip(a.text, 2900);
      if (!text) throw new Error('text is required');
      await s.ref.collection('messages').add({ senderRole: 'vendor', text, at: FieldValue.serverTimestamp(), via: 'mcp' });
      const st = str(s.get('status'));
      await s.ref.set({ lastMessageAt: FieldValue.serverTimestamp(), lastMessageRole: 'vendor', lastMessagePreview: clip(text, 140), ...(st === 'new' || !st ? { status: 'responded', respondedAt: FieldValue.serverTimestamp() } : {}) }, { merge: true });
      return { ok: true, inquiryId: s.id, delivered: s.get('offPlatform') === true ? 'text/email to the lead' : 'in-app (couple is notified)' };
    }
    case 'lazo_add_task': {
      const s = await ownThread(vendorId, a.inquiryId);
      const title = clip(a.title, 160); if (!title) throw new Error('title is required');
      let dueAt = null;
      if (/^\d{4}-\d{2}-\d{2}$/.test(str(a.dueDate))) dueAt = Timestamp.fromDate(new Date(a.dueDate + 'T17:00:00'));
      const who = str(a.assignedTo) === 'couple' ? 'couple' : 'vendor';
      const ref = await s.ref.collection('tasks').add({ title, note: clip(a.note, 600), dueAt, assignedTo: who, vendorId, coupleUid: str(s.get('coupleUid')), done: false, createdAt: FieldValue.serverTimestamp(), createdBy: 'mcp' });
      if (who === 'couple') await s.ref.collection('messages').add({ senderRole: 'vendor', system: true, text: `Quick one for you: ${title}${dueAt ? ' - by ' + a.dueDate : ''}.`, at: FieldValue.serverTimestamp() });
      return { ok: true, taskId: ref.id };
    }
    case 'lazo_complete_task': {
      const s = await ownThread(vendorId, a.inquiryId);
      const t = s.ref.collection('tasks').doc(clip(a.taskId, 80));
      if (!(await t.get()).exists) throw new Error('No such task.');
      await t.set({ done: true, doneAt: FieldValue.serverTimestamp() }, { merge: true });
      return { ok: true };
    }
    case 'lazo_tag': {
      const s = await ownThread(vendorId, a.inquiryId);
      const tag = clip(a.tag, 24).toLowerCase(); if (!tag) throw new Error('tag is required');
      await s.ref.set({ tags: a.remove ? FieldValue.arrayRemove(tag) : FieldValue.arrayUnion(tag) }, { merge: true });
      if (!a.remove) await db().collection('vendors').doc(vendorId).set({ tagPalette: FieldValue.arrayUnion(tag) }, { merge: true });
      return { ok: true, tags: a.remove ? 'removed' : 'added', tag };
    }
    case 'lazo_set_stage': {
      const s = await ownThread(vendorId, a.inquiryId);
      const stage = clip(a.stage, 40);
      if (!['new', 'talking', ...customKeys].includes(stage)) throw new Error(`Stage must be one of: new, talking${customKeys.length ? ', ' + customKeys.join(', ') : ''}. Booked/delivered/lost are set in the app.`);
      await s.ref.set({ stage }, { merge: true });
      return { ok: true, stage };
    }
    default: throw new Error(`Unknown tool ${name}`);
  }
}

// --------------------------------------------------------- JSON-RPC ------
function rpcResult(id, result) { return { jsonrpc: '2.0', id, result }; }
function rpcError(id, code, message) { return { jsonrpc: '2.0', id, error: { code, message } }; }

const mcp = onRequest({ cors: true, invoker: 'public', memory: '512MiB', timeoutSeconds: 60 }, async (req, res) => {
  res.set('Access-Control-Allow-Headers', 'content-type, authorization, mcp-session-id, mcp-protocol-version');
  res.set('Access-Control-Expose-Headers', 'mcp-session-id');
  if (req.method === 'OPTIONS') return res.status(204).send('');
  const parts = str(req.path).split('/').filter(Boolean);
  const token = parts[parts.length - 1] || (str(req.get('authorization')).replace(/^Bearer\s+/i, ''));
  if (req.method === 'GET') return res.status(405).json({ error: 'This server speaks MCP over POST. Add it to your client as a remote MCP server.' });
  if (req.method === 'DELETE') return res.status(204).send('');
  if (req.method !== 'POST') return res.status(405).end();
  const v = await vendorByToken(token);
  if (!v) return res.status(401).json(rpcError(null, -32001, 'Unauthorized: unknown or revoked Lazo token.'));

  const handle = async (msg) => {
    const { id, method, params } = msg || {};
    try {
      switch (method) {
        case 'initialize':
          await db().collection('vendors').doc(v.id).set({ mcp: { lastUsedAt: FieldValue.serverTimestamp(), lastClient: clip(params && params.clientInfo && params.clientInfo.name, 60) } }, { merge: true });
          return rpcResult(id, { protocolVersion: PROTOCOL, capabilities: { tools: { listChanged: false } }, serverInfo: { name: 'Lazo', version: '0913-016' }, instructions: `You are connected to ${str(v.name)}'s Lazo account (wedding vendor CRM). Start with lazo_overview. Threads are conversations with couples; inquiryId identifies one. Amounts are USD. When the vendor asks you to reply to a couple, draft it, confirm, then lazo_send_message. Never invent thread ids - use lazo_pipeline or lazo_search to find them.` });
        case 'notifications/initialized': case 'notifications/cancelled': return null;
        case 'ping': return rpcResult(id, {});
        case 'tools/list': return rpcResult(id, { tools: TOOLS });
        case 'tools/call': {
          const name = str(params && params.name), args = (params && params.arguments) || {};
          try {
            const out = await callTool(v, name, args);
            return rpcResult(id, { content: [{ type: 'text', text: JSON.stringify(out, null, 2) }], isError: false });
          } catch (e) {
            return rpcResult(id, { content: [{ type: 'text', text: `Error: ${e.message}` }], isError: true });
          }
        }
        case 'resources/list': return rpcResult(id, { resources: [] });
        case 'prompts/list': return rpcResult(id, { prompts: [] });
        default: return rpcError(id, -32601, `Method not found: ${method}`);
      }
    } catch (e) { console.error('mcp', method, e); return rpcError(id, -32603, e.message); }
  };

  const body = req.body;
  if (Array.isArray(body)) {
    const outs = (await Promise.all(body.map(handle))).filter(Boolean);
    return outs.length ? res.json(outs) : res.status(202).send('');
  }
  const out = await handle(body);
  return out ? res.json(out) : res.status(202).send('');
});

// ------------------------------------------------------------ token -----
// mcpToken {vendorId, action:'mint'|'revoke'} - the dashboard never handles
// hashing; it gets the token back once and shows it.
const mcpToken = onCall({ memory: '256MiB' }, async (request) => {
  const uid = request.auth && request.auth.uid;
  if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
  const vendorId = str(request.data && request.data.vendorId);
  const action = str(request.data && request.data.action) || 'mint';
  const [vs, us] = await Promise.all([db().collection('vendors').doc(vendorId).get(), db().collection('users').doc(uid).get()]);
  if (!vs.exists) throw new HttpsError('not-found', 'Vendor not found.');
  const isOwner = str(vs.get('claimedBy')) === uid;
  const isMgr = us.exists && str(us.get('vendorId')) === vendorId && str(us.get('vendorRole')) === 'manager';
  if (!isOwner && !isMgr) throw new HttpsError('permission-denied', 'Not your vendor.');
  if (action === 'revoke') {
    await vs.ref.set({ mcp: { enabled: false, tokenHash: FieldValue.delete(), revokedAt: FieldValue.serverTimestamp() } }, { merge: true });
    return { ok: true };
  }
  const token = crypto.randomBytes(24).toString('base64url');
  await vs.ref.set({ mcp: { enabled: true, tokenHash: sha(token), mintedAt: FieldValue.serverTimestamp(), mintedBy: uid } }, { merge: true });
  return { ok: true, token, url: `https://us-central1-lazo-513ec.cloudfunctions.net/mcp/${token}` };
});

module.exports = function mcpModule() { return { mcp, mcpToken }; };
// shared with juneVendor (june-vendor.js): same tools, same scoping
module.exports.TOOLS = TOOLS;
module.exports.callTool = callTool;

// END OF FILE - JC-LAZO-FNDASH-0913-016
