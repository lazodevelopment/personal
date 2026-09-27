// functions-dashboard/june-vendor.js
// Build ID: JC-LAZO-FNDASH-0913-017
//
// JUNE FOR VENDORS, WITH HANDS. The dashboard's "Ask June" runs Claude with
// the same eleven tools the MCP connector exposes (mcp.js), scoped to the
// signed-in vendor (owner or manager) - no token, Firebase auth only.
//
//   juneVendor  callable {vendorId, messages:[{role:'user'|'assistant', content}], question?}
//               -> { reply, steps:[{tool, args, summary}], usage }
//
// Reads happen freely. Writes (send a message, add/complete a task, tag,
// move a stage) are allowed but June is instructed to state exactly what she
// is about to do and only do it when the vendor has clearly asked for it in
// this conversation - the dashboard shows every tool call she made.
//
// Model: claude-sonnet-4-6 on the shared ANTHROPIC_API_KEY (same key/balance
// as every other June function - if that balance runs out, this fails too).

'use strict';

const { onCall, HttpsError } = require('firebase-functions/v2/https');
const admin = require('firebase-admin');
const { TOOLS, callTool } = require('./mcp');

const db = () => admin.firestore();
const str = (v) => (v == null ? '' : String(v));
const MODEL = 'claude-sonnet-4-6';
const MAX_ROUNDS = 8;

function summarize(name, args, out) {
  try {
    const o = typeof out === 'string' ? JSON.parse(out) : out;
    switch (name) {
      case 'lazo_overview': return `Checked your overview - ${o.counts && o.counts.waitingOnYou} waiting on you, ${o.counts && o.counts.booked} booked, $${o.money && o.money.outstanding} outstanding.`;
      case 'lazo_pipeline': return `Read the pipeline (${o.threads ? o.threads.length : 0} threads${args.stage ? ', stage ' + args.stage : ''}${args.tag ? ', tag ' + args.tag : ''}).`;
      case 'lazo_thread': return `Opened the thread with ${o.couple || 'a couple'}.`;
      case 'lazo_upcoming': return `Looked at upcoming weddings and consults.`;
      case 'lazo_money': return `Checked money - $${o.outstanding} open, $${o.overdue} overdue.`;
      case 'lazo_search': return `Searched for "${args.query}" (${o.matches ? o.matches.length : 0} found).`;
      case 'lazo_send_message': return `Sent a message in a thread.`;
      case 'lazo_add_task': return `Added a task: ${args.title}.`;
      case 'lazo_complete_task': return `Marked a task done.`;
      case 'lazo_tag': return `${args.remove ? 'Removed' : 'Added'} the tag "${args.tag}".`;
      case 'lazo_set_stage': return `Moved a thread to ${args.stage}.`;
      default: return `Used ${name}.`;
    }
  } catch (e) { return `Used ${name}.`; }
}

module.exports = function juneVendorModule(ANTHROPIC_API_KEY) {
  const juneVendor = onCall({ memory: '512MiB', timeoutSeconds: 120, secrets: [ANTHROPIC_API_KEY] }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const d = request.data || {};
    const vendorId = str(d.vendorId);
    if (!vendorId) throw new HttpsError('invalid-argument', 'vendorId required');
    const [vs, us] = await Promise.all([db().collection('vendors').doc(vendorId).get(), db().collection('users').doc(uid).get()]);
    if (!vs.exists) throw new HttpsError('not-found', 'Vendor not found.');
    const isOwner = str(vs.get('claimedBy')) === uid;
    const isMgr = us.exists && str(us.get('vendorId')) === vendorId && str(us.get('vendorRole')) === 'manager';
    if (!isOwner && !isMgr) throw new HttpsError('permission-denied', 'Not your vendor.');
    const v = { id: vs.id, ...vs.data() };

    // conversation from the client, trimmed; the newest user turn may come as `question`
    let messages = Array.isArray(d.messages) ? d.messages.filter((m) => m && ['user', 'assistant'].includes(m.role) && str(m.content).trim()).slice(-20).map((m) => ({ role: m.role, content: str(m.content).slice(0, 6000) })) : [];
    if (str(d.question).trim()) messages.push({ role: 'user', content: str(d.question).trim().slice(0, 6000) });
    if (!messages.length || messages[messages.length - 1].role !== 'user') throw new HttpsError('invalid-argument', 'Nothing to answer.');

    const today = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric', timeZone: str(v.scheduler && v.scheduler.tz) || 'America/Phoenix' });
    const system = `You are June, the assistant inside Lazo (a wedding vendor's CRM) for ${str(v.name)} (${str(v.category || (Array.isArray(v.categories) && v.categories[0])) || 'wedding vendor'}, ${str(v.metroId) || 'US'}). Today is ${today}.
You have tools that read this vendor's real data - pipeline, threads, money, upcoming dates - and tools that act. Use them; never guess numbers or names. Start most questions with lazo_overview or lazo_search; open a thread with lazo_thread before talking about it in detail.
Voice: warm, specific, brief. Plain sentences, no headers, no bullet walls. Money in dollars. Name couples by name.
Acting: you may send a message, add or complete a task, tag, or move a stage - but only when the vendor clearly asked for that action in this conversation. When you draft a reply to a couple, show the draft and ask "Send it?" before calling lazo_send_message, unless they already said to send it. Never book, cancel, mark booked/lost, or touch money - tell them where to do that in the app.
When you finish, answer in your own words; do not paste raw JSON.`;

    const tools = TOOLS.map((t) => ({ name: t.name, description: t.description, input_schema: t.inputSchema }));
    const steps = [];
    let usage = { input: 0, output: 0 };
    for (let round = 0; round < MAX_ROUNDS; round++) {
      const r = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'x-api-key': ANTHROPIC_API_KEY.value(), 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
        body: JSON.stringify({ model: MODEL, max_tokens: 1500, system, tools, messages }),
      });
      if (!r.ok) {
        const txt = await r.text();
        console.error('juneVendor anthropic', r.status, txt.slice(0, 300));
        throw new HttpsError('unavailable', r.status === 400 && /credit/i.test(txt) ? 'June is out of credit - Jesse, top up the Anthropic balance.' : 'June could not answer right now.');
      }
      const j = await r.json();
      usage.input += (j.usage && j.usage.input_tokens) || 0; usage.output += (j.usage && j.usage.output_tokens) || 0;
      const content = Array.isArray(j.content) ? j.content : [];
      messages.push({ role: 'assistant', content });
      if (j.stop_reason !== 'tool_use') {
        const reply = content.filter((c) => c.type === 'text').map((c) => c.text).join('\n').trim();
        return { reply: reply || 'Done.', steps, usage };
      }
      const results = [];
      for (const c of content) {
        if (c.type !== 'tool_use') continue;
        let out, isError = false;
        try { out = await callTool(v, c.name, c.input || {}); } catch (e) { out = { error: e.message }; isError = true; }
        const text = JSON.stringify(out).slice(0, 60000);
        steps.push({ tool: c.name, args: c.input || {}, summary: isError ? `Tried ${c.name}: ${out.error}` : summarize(c.name, c.input || {}, out), error: isError });
        results.push({ type: 'tool_result', tool_use_id: c.id, content: text, is_error: isError });
      }
      messages.push({ role: 'user', content: results });
    }
    return { reply: 'I went as far as I could on that one - ask me the last part again and I will pick it up.', steps, usage };
  });

  return { juneVendor };
};

// END OF FILE - JC-LAZO-FNDASH-0913-017
