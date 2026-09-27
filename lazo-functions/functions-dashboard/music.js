// functions-dashboard/music.js
// Build ID: JC-LAZO-FNDASH-0912-MUSIC-001
// juneMusic - June suggests three songs for an empty moment (first dance,
// cake cutting...) from the couple's vibe chips, what they've already picked,
// their do-not-play list and their notes. Nothing is written; the widget
// searches each suggestion so the couple can hear it before choosing.
//
// Wire-up in functions-dashboard/index.js, next to seating:
//
//   const music = require('./music')(ANTHROPIC_API_KEY);
//   exports.juneMusic = music.juneMusic;
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
        max_tokens: 1200,
        temperature: 0.7,
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

  const SYSTEM = `You are June, Lazo's wedding planning assistant, helping a couple pick music.
You receive the moment they need a song for, their vibe, songs they have already chosen, their do-not-play list, artists or genres they want avoided, and free-text notes.
Suggest exactly three real, released, well-known songs that a wedding DJ can actually find. Prefer songs that fit the moment's function (a processional needs a build and a clean ending; a first dance should be slow enough to dance to and under about four minutes; a grand entrance needs an immediate hook; a last dance should send everyone off happy).
Respect every constraint: never suggest anything on the do-not-play list, by an avoided artist, or in an avoided genre; if the vibe says no explicit lyrics, suggest only clean songs; match the genres in the vibe when given.
Vary the three: not three songs by the same artist, not three from the same decade unless the vibe demands it. Do not repeat songs they already picked for other moments.
Reply with JSON only, no prose and no code fence:
{"suggestions":[{"title":"...","artist":"...","why":"one short sentence, plain and specific, no marketing tone"}]}`;

  const juneMusic = onCall(
    {
      region: 'us-central1',
      secrets: [ANTHROPIC_API_KEY],
      timeoutSeconds: 60,
      memory: '256MiB',
    },
    async (request) => {
      if (!request.auth) {
        throw new HttpsError('unauthenticated', 'Sign in first.');
      }
      const d = request.data || {};
      const moment = String(d.momentLabel || d.moment || '').slice(0, 80);
      if (!moment) {
        throw new HttpsError('invalid-argument', 'Which moment?');
      }
      const vibe = Array.isArray(d.vibe) ? d.vibe.map(String).slice(0, 20) : [];
      const picked = Array.isArray(d.picked) ? d.picked.slice(0, 80) : [];
      const dont = Array.isArray(d.doNotPlay) ? d.doNotPlay.slice(0, 80) : [];
      const avoid = Array.isArray(d.avoid) ? d.avoid.map(String).slice(0, 30) : [];
      const notes = String(d.notes || '').slice(0, 1500);
      const hint = String(d.hint || '').slice(0, 200);

      const user = JSON.stringify(
        {
          moment,
          momentHint: hint,
          vibe,
          alreadyPicked: picked.map((s) => ({ title: String(s.title || ''), artist: String(s.artist || ''), moment: String(s.moment || '') })),
          doNotPlay: dont.map((s) => ({ title: String(s.title || ''), artist: String(s.artist || '') })),
          avoidArtistsOrGenres: avoid,
          coupleNotes: notes,
        },
        null,
        0,
      );

      const apiKey = ANTHROPIC_API_KEY.value();
      let out;
      try {
        out = await askClaude(SYSTEM, user, apiKey);
      } catch (e) {
        logger.error('juneMusic', e);
        throw new HttpsError('internal', 'June could not think of one - try again.');
      }
      const list = Array.isArray(out && out.suggestions) ? out.suggestions : [];
      const suggestions = list
        .map((s) => ({
          title: String((s && s.title) || '').slice(0, 120),
          artist: String((s && s.artist) || '').slice(0, 120),
          why: String((s && s.why) || '').slice(0, 220),
        }))
        .filter((s) => s.title && s.artist)
        .slice(0, 3);
      if (!suggestions.length) {
        throw new HttpsError('internal', 'June came back empty - try again.');
      }
      return { suggestions };
    },
  );

  return { juneMusic };
};
