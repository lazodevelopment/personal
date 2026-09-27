// functions-dashboard/seating.js
// Build ID: JC-LAZO-FNDASH-0912-SEATING-001
// juneSeating - June proposes a full seating plan from the couple's tables,
// guests (with parties, sides, groups, plus-ones, flags), rules and notes.
// Nothing is written; the widget previews the plan and applies it.
//
// Wire-up in functions-dashboard/index.js (two lines, next to the other
// Claude-backed functions that already use ANTHROPIC_API_KEY):
//
//   const seating = require('./seating')(ANTHROPIC_API_KEY);
//   exports.juneSeating = seating.juneSeating;
//
// Deploy: firebase deploy --only functions:dashboard

const { onCall, HttpsError } = require('firebase-functions/v2/https');
const { logger } = require('firebase-functions/v2');

module.exports = (ANTHROPIC_API_KEY) => {
  const MODEL = 'claude-sonnet-4-6';

  function stripFence(t) {
    return String(t || '')
      .replace(/^\s*```(?:json)?/i, '')
      .replace(/```\s*$/i, '')
      .trim();
  }

  async function askClaude(system, user, apiKey) {
    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: 8000,
        temperature: 0.2,
        system,
        messages: [{ role: 'user', content: user }],
      }),
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`anthropic ${res.status}: ${body.slice(0, 300)}`);
    }
    const j = await res.json();
    const text = (j.content || [])
      .filter((c) => c.type === 'text')
      .map((c) => c.text)
      .join('\n');
    return JSON.parse(stripFence(text));
  }

  const SYSTEM = `You are June, Lazo's wedding planning assistant, seating a wedding.
You receive tables (with seat counts and what they are near), guests (with party/household, side, group, RSVP, plus-ones, flags and notes), the couple's rules, and their free-text notes.
Produce a complete seating assignment.

Hard constraints, in order:
1. Never exceed a table's seat count.
2. Keep every party (household) at one table. A guest's plus-ones sit with that guest.
3. Honor every rule: "together" parties share a table; "apart" parties never share a table.
4. Guests listed under a table's "fixed" list are already seated there and must stay there.
5. Follow the couple's notes wherever they don't break 1-4.

Then, softly: keep sides and groups together where it makes sense; family near the couple's table (a sweetheart or head table is not in your list - the front of the room is the lowest y); older family away from the DJ/stage/dance floor and near the entrance/bar; wedding party together; kids with their parents; accessible-flagged guests at tables near the entrance; mix only when a table would otherwise sit near-empty; RSVP-pending guests get seats too but at the edges of tables so a no costs nothing.

Return ONLY JSON, no prose, in this exact shape:
{"assignments":[{"guest":"<guest id>","table":"<table id>"}],
 "tableNotes":{"<table id>":"<one short line on who sits here and why>"},
 "unseated":["<guest id>"],
 "summary":"<two sentences for the couple>"}
Every guest id you were given appears exactly once, in assignments or in unseated. Assignment order within a table is seat order; put plus-ones right after their guest.`;

  const juneSeating = onCall(
    {
      region: 'us-central1',
      secrets: [ANTHROPIC_API_KEY],
      timeoutSeconds: 120,
      memory: '512MiB',
    },
    async (request) => {
      if (!request.auth) {
        throw new HttpsError('unauthenticated', 'Sign in first.');
      }
      const d = request.data || {};
      const tables = Array.isArray(d.tables) ? d.tables : [];
      const guests = Array.isArray(d.guests) ? d.guests : [];
      const rules = Array.isArray(d.rules) ? d.rules : [];
      if (tables.length === 0) {
        throw new HttpsError('failed-precondition', 'Lay out your tables first.');
      }
      if (guests.length === 0) {
        throw new HttpsError('failed-precondition', 'Add your guests first.');
      }
      if (guests.length > 600) {
        throw new HttpsError('invalid-argument', 'June seats up to 600 guests at a time.');
      }

      const capacity = {};
      const fixedByTable = {};
      tables.forEach((t) => {
        capacity[t.id] = Number(t.seats) || 0;
        fixedByTable[t.id] = new Set();
      });
      // guests already seated stay seated: the widget passed seatedAt names,
      // resolve to ids here so the model can't move them.
      const seatedIds = new Set();
      guests.forEach((g) => {
        if (g.seatedAt) {
          const tid = tables.find((t) => t.name === g.seatedAt);
          if (tid) {
            seatedIds.add(g.id);
            fixedByTable[tid.id].add(g.id);
          }
        }
      });

      const user = JSON.stringify(
        {
          couple: d.couple || '',
          plan: d.plan === 'ceremony' ? 'ceremony rows' : 'reception',
          notes: String(d.notes || '').slice(0, 1500),
          rules,
          tables: tables.map((t) => ({
            id: t.id,
            name: t.name,
            seats: Number(t.seats) || 0,
            shape: t.shape,
            near: t.near || [],
            fixed: Array.from(fixedByTable[t.id] || []),
          })),
          guests: guests.map((g) => ({
            id: g.id,
            name: g.name,
            party: g.party || '',
            group: g.group || '',
            side: g.side || '',
            rsvp: g.rsvp || '',
            plusOf: g.plusOf || '',
            flags: g.flags || [],
            note: String(g.note || '').slice(0, 120),
            fixedAt: seatedIds.has(g.id) ? g.seatedAt : '',
          })),
        },
        null,
        0
      );

      let out;
      try {
        out = await askClaude(SYSTEM, user, ANTHROPIC_API_KEY.value());
      } catch (e) {
        logger.error('juneSeating', e);
        throw new HttpsError('internal', 'June could not draft the plan - try again.');
      }

      // Validate: capacity, known ids, fixed guests unmoved, everyone once.
      const known = new Set(guests.map((g) => g.id));
      const seen = new Set();
      const count = {};
      const assignments = [];
      const unseated = [];
      (Array.isArray(out.assignments) ? out.assignments : []).forEach((a) => {
        const gid = String(a.guest || '');
        const tid = String(a.table || '');
        if (!known.has(gid) || seen.has(gid)) return;
        if (!(tid in capacity)) return;
        // a fixed guest stays where they are
        let target = tid;
        for (const t of tables) {
          if (fixedByTable[t.id].has(gid)) {
            target = t.id;
            break;
          }
        }
        count[target] = (count[target] || 0) + 1;
        if (count[target] > capacity[target]) {
          count[target]--;
          unseated.push(gid);
          seen.add(gid);
          return;
        }
        seen.add(gid);
        assignments.push({ guest: gid, table: target });
      });
      guests.forEach((g) => {
        if (!seen.has(g.id)) unseated.push(g.id);
      });
      const tableNotes = {};
      if (out.tableNotes && typeof out.tableNotes === 'object') {
        Object.keys(out.tableNotes).forEach((k) => {
          if (k in capacity) tableNotes[k] = String(out.tableNotes[k]).slice(0, 160);
        });
      }
      return {
        assignments,
        unseated,
        tableNotes,
        summary: String(out.summary || '').slice(0, 400),
      };
    }
  );

  return { juneSeating };
};
