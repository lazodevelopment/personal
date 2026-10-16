// JARVIS hub: Faith: the rosary, daily Mass readings and the saint of the day.
import Anthropic from "@anthropic-ai/sdk";
import { MODEL, json, kv, within } from "./core.js";
import { elevenlabs } from "./brain.js";

/* ---------------- faith: the rosary (led aloud) and the daily Mass readings with a plain-words reading ---------------- */
const PRAYERS = {
  sign: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.",
  creed: "I believe in God, the Father almighty, Creator of heaven and earth, and in Jesus Christ, his only Son, our Lord, who was conceived by the Holy Spirit, born of the Virgin Mary, suffered under Pontius Pilate, was crucified, died and was buried; he descended into hell; on the third day he rose again from the dead; he ascended into heaven, and is seated at the right hand of God the Father almighty; from there he will come to judge the living and the dead. I believe in the Holy Spirit, the holy catholic Church, the communion of saints, the forgiveness of sins, the resurrection of the body, and life everlasting. Amen.",
  our: "Our Father, who art in heaven, hallowed be thy name; thy kingdom come, thy will be done on earth as it is in heaven. Give us this day our daily bread, and forgive us our trespasses, as we forgive those who trespass against us; and lead us not into temptation, but deliver us from evil. Amen.",
  hail: "Hail Mary, full of grace, the Lord is with thee. Blessed art thou among women, and blessed is the fruit of thy womb, Jesus. Holy Mary, Mother of God, pray for us sinners, now and at the hour of our death. Amen.",
  glory: "Glory be to the Father, and to the Son, and to the Holy Spirit, as it was in the beginning, is now, and ever shall be, world without end. Amen.",
  fatima: "O my Jesus, forgive us our sins, save us from the fires of hell, and lead all souls to heaven, especially those in most need of thy mercy.",
  salve: "Hail, holy Queen, Mother of mercy, our life, our sweetness and our hope. To thee do we cry, poor banished children of Eve; to thee do we send up our sighs, mourning and weeping in this valley of tears. Turn then, most gracious advocate, thine eyes of mercy toward us, and after this our exile show unto us the blessed fruit of thy womb, Jesus. O clement, O loving, O sweet Virgin Mary. Pray for us, O holy Mother of God, that we may be made worthy of the promises of Christ.",
  closing: "Let us pray. O God, whose only begotten Son, by his life, death and resurrection, has purchased for us the rewards of eternal life: grant, we beseech thee, that by meditating upon these mysteries of the most holy Rosary of the Blessed Virgin Mary, we may imitate what they contain and obtain what they promise, through the same Christ our Lord. Amen.",
};
const MYSTERIES = {
  joyful: { name: "Joyful Mysteries", days: "Mondays and Saturdays", list: [
    ["The Annunciation", "Luke 1:26-38", "humility", "The angel Gabriel tells Mary she will bear the Son of God, and she answers: let it be done to me according to your word."],
    ["The Visitation", "Luke 1:39-56", "love of neighbour", "Mary hurries to help her cousin Elizabeth, and the child in Elizabeth's womb leaps for joy."],
    ["The Nativity", "Luke 2:1-20", "poverty of spirit", "Jesus is born in a stable at Bethlehem, and shepherds are the first to find him."],
    ["The Presentation in the Temple", "Luke 2:22-38", "obedience", "Mary and Joseph bring the child to the Temple, where old Simeon holds him and calls him a light for all nations."],
    ["The Finding in the Temple", "Luke 2:41-52", "joy in finding Jesus", "After three days of searching, Mary and Joseph find the twelve-year-old Jesus among the teachers, about his Father's business."] ] },
  sorrowful: { name: "Sorrowful Mysteries", days: "Tuesdays and Fridays", list: [
    ["The Agony in the Garden", "Matthew 26:36-46", "sorrow for sin", "In Gethsemane Jesus sweats blood and prays: not my will, but yours be done."],
    ["The Scourging at the Pillar", "John 19:1", "purity", "Pilate has Jesus scourged; he bears it in silence for us."],
    ["The Crowning with Thorns", "Matthew 27:27-31", "courage", "Soldiers press a crown of thorns onto his head and mock him as a king."],
    ["The Carrying of the Cross", "John 19:17", "patience", "Jesus carries his cross to Calvary, falling and rising, helped by Simon of Cyrene."],
    ["The Crucifixion", "Luke 23:33-46", "perseverance", "Jesus forgives his executioners, entrusts his mother to John, and gives up his spirit."] ] },
  glorious: { name: "Glorious Mysteries", days: "Wednesdays and Sundays", list: [
    ["The Resurrection", "Matthew 28:1-10", "faith", "On the third day the tomb is empty; death has lost."],
    ["The Ascension", "Acts 1:6-11", "hope", "Forty days later Jesus is taken up to heaven, promising to be with us always."],
    ["The Descent of the Holy Spirit", "Acts 2:1-4", "love of God", "At Pentecost the Spirit comes as wind and fire, and frightened disciples become apostles."],
    ["The Assumption of Mary", "Revelation 12:1", "the grace of a happy death", "At the end of her life Mary is taken body and soul into heaven."],
    ["The Coronation of Mary", "Revelation 12:1", "trust in Mary's intercession", "Mary is crowned Queen of heaven and earth, and prays for us still."] ] },
  luminous: { name: "Luminous Mysteries", days: "Thursdays", list: [
    ["The Baptism in the Jordan", "Matthew 3:13-17", "openness to the Holy Spirit", "John baptises Jesus; the heavens open and the Father says: this is my beloved Son."],
    ["The Wedding at Cana", "John 2:1-11", "to Jesus through Mary", "At Mary's word, do whatever he tells you, Jesus turns water into wine, his first sign."],
    ["The Proclamation of the Kingdom", "Mark 1:14-15", "repentance and trust", "Jesus preaches: the kingdom of God is at hand; repent and believe the good news."],
    ["The Transfiguration", "Matthew 17:1-8", "desire for holiness", "On the mountain Jesus shines like the sun, with Moses and Elijah beside him."],
    ["The Institution of the Eucharist", "Matthew 26:26-28", "adoration", "At the Last Supper Jesus takes bread and wine: this is my body, this is my blood, given for you."] ] },
};
function easter(y) { const a = y % 19, b = Math.floor(y / 100), c = y % 100, d = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25), g = Math.floor((b - f + 1) / 3), h = (19 * a + b - d - g + 15) % 30, i = Math.floor(c / 4), k = c % 4, l = (32 + 2 * e + 2 * i - h - k) % 7, m = Math.floor((a + 11 * h + 22 * l) / 451), mo = Math.floor((h + l - 7 * m + 114) / 31), da = ((h + l - 7 * m + 114) % 31) + 1; return new Date(Date.UTC(y, mo - 1, da)); }
function liturgicalSeason(d) {   // d: UTC midnight of the local date
  const y = d.getUTCFullYear(), E = easter(y), day = 86400e3;
  if (d >= new Date(E - 46 * day) && d < E) return "Lent";
  if (d >= E && d < new Date(+E + 50 * day)) return "Easter";
  const xmas = new Date(Date.UTC(y, 11, 25)), adv = new Date(xmas - ((xmas.getUTCDay() || 7) + 21) * day);
  if (d >= adv && d < xmas) return "Advent";
  if (d >= xmas || d < new Date(Date.UTC(y, 0, 13))) return "Christmas";
  return "Ordinary Time";
}
export function mysteriesFor(env, when = new Date()) {
  const local = new Date(when.toLocaleString("en-US", { timeZone: env.TZ || "America/Chicago" })); const dow = local.getDay();
  const d = new Date(Date.UTC(local.getFullYear(), local.getMonth(), local.getDate())); const season = liturgicalSeason(d);
  let key = ["glorious", "joyful", "sorrowful", "glorious", "luminous", "sorrowful", "joyful"][dow], why = MYSTERIES[key].days;
  if (dow === 0 && (season === "Advent" || season === "Christmas")) { key = "joyful"; why = "Sundays of Advent and Christmas"; }
  if (dow === 0 && season === "Lent") { key = "sorrowful"; why = "Sundays of Lent"; }
  return { key, season, why, date: d.toISOString().slice(0, 10), ...MYSTERIES[key] };
}
export function rosaryScript(key) {
  const M = MYSTERIES[key] || MYSTERIES.glorious, hail10 = Array(10).fill(PRAYERS.hail).join(" "), segs = [];
  segs.push({ id: "open", label: "Opening prayers", text: `${PRAYERS.sign} ${PRAYERS.creed} ${PRAYERS.our} For faith: ${PRAYERS.hail} For hope: ${PRAYERS.hail} For charity: ${PRAYERS.hail} ${PRAYERS.glory}` });
  M.list.forEach(([name, ref, fruit, med], i) => segs.push({ id: "d" + (i + 1), label: `${i + 1}. ${name}`, ref, fruit, med, text: `The ${["first", "second", "third", "fourth", "fifth"][i]} ${M.name.replace(" Mysteries", "").toLowerCase()} mystery: ${name}. ${med} We ask for the grace of ${fruit}. ${PRAYERS.our} ${hail10} ${PRAYERS.glory} ${PRAYERS.fatima}` }));
  segs.push({ id: "close", label: "Closing prayers", text: `${PRAYERS.salve} ${PRAYERS.closing} ${PRAYERS.sign}` });
  return { key, name: M.name, segments: segs };
}
export const stripHtml = (h) => String(h || "").replace(/<br\s*\/?>/gi, "\n").replace(/<\/p>/gi, "\n\n").replace(/<[^>]+>/g, "").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&#8217;|&rsquo;/g, "’").replace(/&#8220;|&ldquo;/g, "“").replace(/&#8221;|&rdquo;/g, "”").replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
const unesc = (t) => String(t || "").replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#039;/g, "'").replace(/&amp;/g, "&");
async function fetchReadings(env, dateStr) {
  const r = await within(fetch("https://bible.usccb.org/readings.rss", { headers: { "user-agent": "Mozilla/5.0 (JARVIS hub; personal dashboard)" } }), 10000, null);
  if (!r || !r.ok) throw new Error("USCCB feed " + (r?.status || "timeout"));
  const xml = await r.text(); const want = dateStr.slice(5, 7) + dateStr.slice(8, 10) + dateStr.slice(2, 4);   // MMDDYY in the link
  const items = [...xml.matchAll(/<item>([\s\S]*?)<\/item>/g)].map((m) => m[1]);
  const item = items.find((it) => it.includes(`/readings/${want}.cfm`)); if (!item) throw new Error("feed has no readings for " + dateStr);
  const title = stripHtml(unesc((item.match(/<title>([\s\S]*?)<\/title>/) || [])[1])), link = ((item.match(/<link>([\s\S]*?)<\/link>/) || [])[1] || "").trim();
  const desc = unesc((item.match(/<description>([\s\S]*?)<\/description>/) || [])[1]);
  const parts = []; const re = /<h4>\s*([^<]+?)\s*(?:<a[^>]*>([\s\S]*?)<\/a>)?\s*<\/h4>([\s\S]*?)(?=<h4>|$)/g; let m;
  while ((m = re.exec(desc))) { const kind = m[1].trim(), ref = stripHtml(m[2] || ""), text = stripHtml(m[3]); if (text.length > 20) parts.push({ kind, ref, text }); }
  return { date: dateStr, title, link, parts };
}
export async function fetchReadingsPage(env, dateStr) {
  const mmddyy = dateStr.slice(5, 7) + dateStr.slice(8, 10) + dateStr.slice(2, 4), link = `https://bible.usccb.org/bible/readings/${mmddyy}.cfm`;
  const r = await within(fetch(link, { headers: { "user-agent": "Mozilla/5.0 (JARVIS hub; personal dashboard)" } }), 10000, null);
  if (!r || !r.ok) throw new Error("USCCB page " + (r?.status || "timeout"));
  const h = await r.text(); const title = stripHtml((h.match(/<title>([^<|]+)/) || [])[1] || "").trim();
  const parts = []; const re = /<h3 class="name">([\s\S]*?)<\/h3>\s*<div class="address">([\s\S]*?)<\/div>\s*<\/div>\s*<div class="content-body">([\s\S]*?)<\/div>/g; let m;
  while ((m = re.exec(h))) { const kind = stripHtml(m[1]), ref = stripHtml(m[2]), text = stripHtml(m[3]); if (text.length > 20) parts.push({ kind, ref, text }); }
  if (!parts.length) throw new Error("no readings on that page");
  return { date: dateStr, title, link, parts };
}
export async function dailyReadings(env, { fresh = false, date = null } = {}) {
  const today = new Date().toLocaleDateString("en-CA", { timeZone: env.TZ || "America/Chicago" }); const dateStr = date || today;
  const cached = await kv.get(env, "readings_" + dateStr); if (cached?.reflection && !fresh) return cached;
  let base, firstErr; try { base = dateStr === today ? await fetchReadings(env, dateStr) : await fetchReadingsPage(env, dateStr); } catch (e) { firstErr = e.message; try { base = dateStr === today ? await fetchReadingsPage(env, dateStr) : await fetchReadings(env, dateStr); } catch (e2) { throw new Error(firstErr + " / " + e2.message); } }
  if (base.date !== dateStr && !base.link.includes(dateStr.slice(5, 7) + dateStr.slice(8, 10) + dateStr.slice(2, 4))) throw new Error("readings for " + dateStr + " not published yet");
  let reflection = null;
  if (env.ANTHROPIC_API_KEY) {
    const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
    const params_rd = {
      model: MODEL, max_tokens: 6000, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "medium" },
      system: "You explain the Catholic daily Mass readings to a busy layman in plain, warm, modern English, faithful to Catholic teaching. No jargon, no sermon voice, no headers or markdown. Return JSON only: {\"theme\": one short line tying the day together, \"parts\": [{\"kind\": the reading's kind exactly as given, \"plain\": 2-4 sentences on what this passage is saying and why it is here today}], \"conclusion\": 90-140 words: what the readings and gospel together mean for an ordinary person's day, ending with one concrete thing to do or notice today}. Keep the parts in the same order as given; include every part.",
      messages: [{ role: "user", content: `${base.title} (${base.date})\n\n` + base.parts.map((p) => `${p.kind} ${p.ref}\n${p.text}`).join("\n\n---\n\n") }],
    };
    const r = await client.beta.messages.create(params_rd);
    const txt = await finishText(client, r, params_rd);
    reflection = parseJsonLoose(txt) || { theme: "", parts: [], conclusion: txt.replace(/[{}"]/g, " ").slice(0, 900) };
  }
  const out = { ...base, reflection, at: new Date().toISOString() };
  await env.HUB.put("readings_" + dateStr, JSON.stringify(out), { expirationTtl: 3 * 86400 });
  return out;
}
const parseJsonLoose = (txt) => {
  const cut = txt.slice(txt.indexOf("{"), txt.lastIndexOf("}") + 1);
  const clean = cut.replace(/[\u0000-\u001f]+/g, " ")                 // raw newlines inside strings
    .replace(/\\(?!["\\\/bfnrtu])/g, "")                                 // invalid escapes such as \' or \-
    .replace(/,\s*([}\]])/g, "$1");                                      // trailing commas
  for (const c of [cut, clean]) { try { return JSON.parse(c); } catch {} }
  return null;
};
// saint of the day: Vatican News keeps a page per calendar date, with a story page per saint
async function fetchSaint(env, dateStr) {
  const mm = dateStr.slice(5, 7), dd = dateStr.slice(8, 10), base = "https://www.vaticannews.va";
  const hdr = { "user-agent": "Mozilla/5.0 (JARVIS hub; personal dashboard)", "accept-language": "en-US,en;q=0.9" };
  const r = await within(fetch(`${base}/en/saints/${mm}/${dd}.html`, { headers: hdr }), 10000, null);
  if (!r || !r.ok) throw new Error("Vatican News " + (r?.status || "timeout"));
  const h = await r.text(); const entries = [];
  const chunksRe = /([\s\S]*?)<a class="saintReadMore" href="([^"]+)"/g; let m, last = 0;
  while ((m = chunksRe.exec(h))) {
    const before = m[1]; const h2s = [...before.matchAll(/<h2[^>]*>([\s\S]*?)<\/h2>/g)]; const name = stripHtml((h2s.pop() || [])[1] || "").replace(/\s+/g, " ").trim();
    const ps = [...before.matchAll(/<p[^>]*>([\s\S]*?)<\/p>/g)]; const blurb = stripHtml((ps.pop() || [])[1] || "").replace(/\s+/g, " ").trim();
    const img = (before.match(/data-original="([^"]+)"/g) || []).pop(); const image = img ? base + img.match(/data-original="([^"]+)"/)[1] : null;
    if (name && !/^(menu|search)$/i.test(name)) entries.push({ name, blurb, link: base + m[2], image });
  }
  if (!entries.length) throw new Error("no saint listed for " + dateStr);
  const main = entries[0]; let story = "";
  try {
    const d = await within(fetch(main.link, { headers: hdr }), 10000, null);
    if (d && d.ok) { const dh = await d.text(); const i = dh.indexOf('class="section__content'); const seg = dh.slice(i, i + 60000); story = [...seg.matchAll(/<p[^>]*>([\s\S]*?)<\/p>/g)].map((x) => stripHtml(x[1]).replace(/\s+/g, " ").trim()).filter((t) => t.length > 40 && !/©/.test(t)).join("\n\n").slice(0, 6000); }
  } catch {}
  return { date: dateStr, name: main.name, blurb: main.blurb, link: main.link, image: main.image, story, others: entries.slice(1).map((e) => ({ name: e.name, link: e.link })) };
}
async function finishText(client, r, params) {
  let txt = r.content.filter((b) => b.type === "text").map((b) => b.text).join("");
  if (r.stop_reason === "max_tokens" && params) {
    try { const r2 = await client.beta.messages.create({ ...params, messages: [...params.messages, { role: "assistant", content: r.content }, { role: "user", content: "You were cut off. Continue exactly where you stopped; output only the remainder." }] }); txt += r2.content.filter((b) => b.type === "text").map((b) => b.text).join(""); } catch {}
  }
  return txt;
}
export async function saintOfDay(env, { fresh = false, date = null } = {}) {
  const dateStr = date || new Date().toLocaleDateString("en-CA", { timeZone: env.TZ || "America/Chicago" });
  const cached = await kv.get(env, "saint_" + dateStr); if (cached?.plain && !fresh) return cached;
  const base = await fetchSaint(env, dateStr); let plain = null;
  if (env.ANTHROPIC_API_KEY) {
    const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
    const params_saint_marker = {
      model: MODEL, max_tokens: 5000, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "medium" },
      system: "You introduce the Catholic saint of the day to a busy layman in plain, warm, modern English, faithful to Catholic teaching and to the source text; do not invent dates or facts that are not in the source. Return JSON only: {\"title\": the saint's role in a few words (e.g. 'Founder of the Franciscans, patron of Italy'), \"life\": 110-150 words telling the life story simply, \"why\": 2-3 sentences on why this saint still matters, \"today\": one sentence, a concrete thing to carry into today inspired by this saint, \"patron\": what they are patron of if known from the source or well established, else \"\"}.",
      messages: [{ role: "user", content: `${base.name}\n\n${base.blurb}\n\n${base.story || "(no longer story available; use what is above and well-established facts only)"}` }],
    };
    const r = await client.beta.messages.create(params_saint_marker);
    const txt = await finishText(client, r, params_saint_marker);
    plain = parseJsonLoose(txt) || { title: "", life: txt.replace(/[{}"`]/g, " ").replace(/^\s*json\s*/i, "").slice(0, 800), why: "", today: "", patron: "", raw: txt.slice(0, 3000), stop: r.stop_reason, out: r.usage?.output_tokens, blocks: r.content.map((b) => b.type) };
  }
  const out = { ...base, plain, at: new Date().toISOString() };
  await env.HUB.put("saint_" + dateStr, JSON.stringify(out), { expirationTtl: 3 * 86400 });
  return out;
}
export async function rosaryAudio(env, key, segId) {
  const kvKey = `rosary_audio_${key}_${segId}`; const have = await env.HUB.get(kvKey, "arrayBuffer");
  if (have) return new Response(have, { headers: { "content-type": "audio/mpeg", "cache-control": "private, max-age=86400" } });
  const seg = rosaryScript(key).segments.find((x) => x.id === segId); if (!seg) return json({ error: "no such segment" }, 404);
  let r = await elevenlabs(env, seg.text, "mp3_44100_128", "eleven_turbo_v2_5", { speed: 0.92, stability: 0.7, style: 0 });
  if (!r.ok) r = await elevenlabs(env, seg.text, "mp3_44100_128", "eleven_turbo_v2_5");
  if (!r.ok) return json({ error: "voice failed", status: r.status }, 502);
  const buf = await r.arrayBuffer(); await env.HUB.put(kvKey, buf, { expirationTtl: 60 * 86400 });
  return new Response(buf, { headers: { "content-type": "audio/mpeg", "cache-control": "private, max-age=86400" } });
}
