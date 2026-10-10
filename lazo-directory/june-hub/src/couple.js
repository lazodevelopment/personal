// June for couples. The same hub, the same voice, scoped to one wedding: the signed-in couple's own
// plan (vendor team by category, budget), their vendor threads, tasks vendors gave them, invoices,
// guests and RSVPs, the day-of timeline, the shopping list, the wedding-day forecast, and a brief.
// Every Firestore read and write is made AS THE COUPLE with their ID token, so firestore.rules decide
// what June can see (couples/{cid}/**, inquiries where coupleUid, consults where coupleUid, their site).
// Free for every couple on Lazo. Built 2026-10-07 beside the vendor side in index.js; the worker picks
// the side by who the login is (users/{uid}.vendorId → vendor, else users/{uid}.coupleUid or the uid → couple).
export function makeCouple(D) {
  const { fsGet, fsQuery, fsCreate, fsPatch, kv, str, clip, uid, money, dayKey, fmtDay, fmtWhen, localTime, localToIso, within, weatherFor, dayWeather, weatherSummary, localNews, METROS, elevenlabs, speakWithTrack, audioType, Anthropic, BUILD } = D;
  const K = (cid, k) => `${k}_c_${cid}`;   // KV keys for memory, queue, brief, reminders; "_c_" keeps them apart from vendor ids
  const CATS = { "wedding-photographers": "Photographer", "wedding-videographers": "Videographer", "wedding-venues": "Venue", "wedding-planners": "Planner", "wedding-djs": "DJ", "wedding-florists": "Florist", "wedding-caterers": "Caterer", "wedding-cakes": "Cake & desserts", "hair-and-makeup": "Hair & makeup", "wedding-officiants": "Officiant", "wedding-transportation": "Transportation", "wedding-rentals": "Rentals", "wedding-bands": "Live band", "wedding-invitations": "Invitations", "day-of-coordination": "Day-of coordinator" };
  const label = (slug) => CATS[slug] || str(slug).replace(/^wedding-/, "").replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  // the order a wedding usually books in: June uses it to say what to look at next
  const ORDER = ["wedding-venues", "wedding-planners", "wedding-photographers", "wedding-caterers", "wedding-videographers", "wedding-djs", "wedding-bands", "wedding-florists", "wedding-officiants", "hair-and-makeup", "wedding-cakes", "wedding-invitations", "wedding-rentals", "wedding-transportation", "day-of-coordination"];
  const isoDay = (v) => { if (!v) return null; const s = str(v); if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s; const d = new Date(s); return isNaN(d) ? null : d.toISOString().slice(0, 10); };
  const toDate = (v) => { if (!v) return null; const d = new Date(str(v)); return isNaN(d) ? null : d.toISOString(); };

  /* ---------- who ---------- */
  async function resolveCouple(env, who) {
    const cached = await kv.get(env, "couple_of_" + who.uid);
    if (cached && Date.now() - cached.at < 30 * 60e3) return cached;
    const u = await fsGet(who.token, `users/${encodeURIComponent(who.uid)}`).catch(() => null);
    if (u?.vendorId) return null;   // a vendor login never lands here
    const cid = str(u?.coupleUid) || who.uid;
    const c = await fsGet(who.token, `couples/${encodeURIComponent(cid)}`).catch(() => null);
    if (!c && str(u?.role) !== "couple") return null;
    const out = { coupleId: cid, partner: cid !== who.uid, at: Date.now(), names: str(c?.names) };
    await kv.put(env, "couple_of_" + who.uid, out, { expirationTtl: 3600 });
    return out;
  }

  /* ---------- the couple's data ---------- */
  function coupleCard(c, cid) {
    const metro = METROS[str(c.metroId)] || null;
    const keyDates = (Array.isArray(c.keyDates) ? c.keyDates : []).map((k) => (k && typeof k === "object" ? { label: str(k.label || k.title || k.name), date: isoDay(k.date || k.at || k.when) } : null)).filter((k) => k && k.label && k.date);
    return {
      id: cid, names: str(c.names) || "You two", partnerName: str(c.partnerName) || null, weddingDate: isoDay(c.weddingDate), metroId: str(c.metroId), metro: metro ? metro.display : (str(c.metroId) || "your city"), lat: metro?.lat || null, lon: metro?.lon || null,
      budgetTotal: c.budgetTotal != null ? +c.budgetTotal || 0 : null, guestEstimate: c.guestEstimate != null ? +c.guestEstimate || 0 : null, photoUrl: str(c.photoUrl) || null, keyDates, registry: Array.isArray(c.registryLinks) ? c.registryLinks.map(String).slice(0, 6) : [],
      hellosOk: c.hellosOk !== false, createdAt: toDate(c.createdAt),
    };
  }
  function threadRow(m) {
    const si = m.structuredIntent || {};
    const lastFrom = str(m.lastMessageRole) || null, st = str(m.status) || "new";
    const lastAt = toDate(m.lastMessageAt || m.createdAt);
    return {
      inquiryId: m.id, vendor: str(m.vendorName) || label(str(m.vendorCategory || si.category)) || "A vendor", vendorId: str(m.vendorId) || null, category: str(m.vendorCategory || si.category) || null,
      status: st, lastMessageAt: lastAt, lastMessageFrom: lastFrom, lastMessagePreview: str(m.lastMessagePreview || si.message) || null,
      waitingOnMe: lastFrom === "vendor" && !["lost", "booked"].includes(st) || (lastFrom === "vendor" && st === "booked" && m.coupleLastReadAt && lastAt && new Date(lastAt) > new Date(toDate(m.coupleLastReadAt))),
      unread: !!(lastFrom === "vendor" && lastAt && (!m.coupleLastReadAt || new Date(lastAt) > new Date(toDate(m.coupleLastReadAt)))),
      waitingOnVendor: lastFrom === "couple" || (!lastFrom && (st === "new" || !m.status)),
      weddingDate: isoDay(si.weddingDate), venue: str(si.venue) || null, invoiceStatus: str(m.invoiceStatus) || null, contractStatus: str(m.contractStatus) || null, questionnaireStatus: str(m.questionnaireStatus) || null,
      createdAt: toDate(m.createdAt), bookedAt: toDate(m.bookedAt), blocked: m.blockedByCouple === true, offPlatform: m.offPlatform === true,
    };
  }
  async function loadThreads(token, cid) {
    const docs = await fsQuery(token, { collection: "inquiries", where: [["coupleUid", "EQUAL", cid]] });
    return docs.filter((m) => str(m.status) !== "flagged" && m.demo !== true).map(threadRow).sort((a, b) => str(b.lastMessageAt).localeCompare(str(a.lastMessageAt)));
  }
  async function loadPlan(token, cid) {
    const docs = await fsQuery(token, { collection: "plan", parent: `couples/${encodeURIComponent(cid)}` }).catch(() => []);
    return docs.map((d) => ({ slug: d.id, label: label(d.id), status: str(d.status) || "needed", vendorName: str(d.vendorName) || null, vendorId: str(d.vendorId) || null, inquiryId: str(d.inquiryId) || null, planned: d.budgetPlanned != null ? +d.budgetPlanned || 0 : null, actual: d.budgetActual != null ? +d.budgetActual || 0 : null, updatedAt: toDate(d.updatedAt) }))
      .sort((a, b) => (ORDER.indexOf(a.slug) + 100) % 100 - (ORDER.indexOf(b.slug) + 100) % 100);
  }
  const rsvpOf = (g) => { if (g.rsvp === true) return "yes"; if (g.rsvp === false) return "no"; const v = str(g.rsvp || g.status).toLowerCase(); return /^(yes|attending|accepted|coming|true)/.test(v) ? "yes" : /^(no|declin|regret|not|false)/.test(v) ? "no" : "pending"; };
  async function loadGuests(token, cid) {
    const docs = await fsQuery(token, { collection: "guests", parent: `couples/${encodeURIComponent(cid)}` }).catch(() => []);
    const list = docs.map((g) => ({ id: g.id, name: str(g.name), party: str(g.party) || null, rsvp: rsvpOf(g), meal: str(g.meal) || null, side: str(g.side) || null, count: Math.max(1, +g.count || +g.qty || 1), email: str(g.email) || null }));
    const tally = { total: list.reduce((s, g) => s + g.count, 0), people: list.length, yes: 0, no: 0, pending: 0, parties: new Set(list.map((g) => g.party).filter(Boolean)).size };
    for (const g of list) tally[g.rsvp] += g.count;
    return { list, tally };
  }
  async function loadSite(token, cid) {
    const sites = await fsQuery(token, { collection: "weddingSites", where: [["coupleUid", "EQUAL", cid]], limit: 1 }).catch(() => []);
    const s = sites[0]; if (!s) return null;
    const rsvps = await fsQuery(token, { collection: "rsvps", parent: `weddingSites/${encodeURIComponent(s.id)}` }).catch(() => []);
    const yes = rsvps.filter((r) => r.attending === true || /^(yes|attend|accept)/i.test(str(r.rsvp || r.status || r.attending))).length;
    return { slug: s.id, url: `https://meetlazo.com/w/${encodeURIComponent(s.id)}/`, published: s.published !== false, rsvps: rsvps.length, rsvpYes: yes, rsvpNo: rsvps.length - yes };
  }
  async function loadConsults(token, cid) {
    const docs = await fsQuery(token, { collection: "consults", where: [["coupleUid", "EQUAL", cid], ["status", "EQUAL", "booked"]] }).catch(() => []);
    const now = Date.now();
    return docs.filter((c) => c.startAt && new Date(c.startAt) >= now - 3600e3).sort((a, b) => str(a.startAt).localeCompare(str(b.startAt)))
      .map((c) => ({ consultId: c.id, inquiryId: str(c.inquiryId), vendor: str(c.vendorName) || "your vendor", type: str(c.typeLabel) || "consult", mode: str(c.mode), startAt: toDate(c.startAt), videoLink: str(c.videoLink) || null })).slice(0, 8);
  }
  async function loadDayOf(token, cid) {
    const docs = await fsQuery(token, { collection: "dayof", parent: `couples/${encodeURIComponent(cid)}` }).catch(() => []);
    return docs.map((d) => ({ id: d.id, time: str(d.time), label: str(d.label), note: str(d.note) || null, dur: d.dur != null ? +d.dur || 0 : null, owners: Array.isArray(d.owners) ? d.owners.map(String) : [], anchor: d.anchor === true })).filter((d) => d.label).sort((a, b) => a.time.localeCompare(b.time));
  }
  async function loadShopping(token, cid) {
    const docs = await fsQuery(token, { collection: "shopping", parent: `couples/${encodeURIComponent(cid)}` }).catch(() => []);
    return docs.map((d) => ({ id: d.id, name: str(d.name), cat: str(d.cat) || "other", qty: d.qty != null ? +d.qty || 1 : 1, est: d.est != null ? +d.est || 0 : null, bought: d.bought === true, note: str(d.note) || null, order: +d.order || 0 })).filter((d) => d.name).sort((a, b) => a.order - b.order);
  }
  // per thread, read as the couple: tasks the vendor assigned to them, and invoices
  async function loadPerThread(token, rows) {
    const active = rows.filter((r) => r.status !== "lost").slice(0, 14);
    const out = await Promise.all(active.map(async (r) => {
      const p = `inquiries/${encodeURIComponent(r.inquiryId)}`;
      const [tasks, invs] = await Promise.all([
        within(fsQuery(token, { collection: "tasks", parent: p, where: [["assignedTo", "EQUAL", "couple"]] }), 3500, []),
        r.status === "booked" || r.invoiceStatus ? within(fsQuery(token, { collection: "invoices", parent: p }), 3500, []) : [],
      ]);
      return { tasks: tasks.filter((t) => t.done !== true).map((t) => ({ taskId: t.id, inquiryId: r.inquiryId, vendor: r.vendor, title: str(t.title), note: str(t.note) || null, dueAt: toDate(t.dueAt) })),
        invoices: invs.filter((i) => str(i.status) !== "void" && i.demo !== true).map((i) => ({ invoiceId: i.id, inquiryId: r.inquiryId, vendor: r.vendor, title: str(i.title) || "Invoice", total: +i.total || 0, status: str(i.status), dueDate: isoDay(i.dueDate), paidAt: toDate(i.paidAt), payUrl: str(i.payUrl || i.url) || null })) };
    }));
    return { tasks: out.flatMap((x) => x.tasks).sort((a, b) => str(a.dueAt || "9").localeCompare(str(b.dueAt || "9"))), invoices: out.flatMap((x) => x.invoices) };
  }
  async function ownThread(token, cid, inquiryId) {
    const m = await fsGet(token, `inquiries/${encodeURIComponent(clip(inquiryId, 80))}`);
    if (!m || str(m.coupleUid) !== cid) throw new Error("No such vendor thread on this account.");
    return m;
  }
  async function threadDetail(token, cid, inquiryId) {
    const m = await ownThread(token, cid, inquiryId); const p = `inquiries/${m.id}`;
    const [msgs, props, cons, invs, tasks, qs] = await Promise.all([
      fsQuery(token, { collection: "messages", parent: p, orderBy: ["at", "ASCENDING"], limit: 300 }).catch(() => []), fsQuery(token, { collection: "proposals", parent: p, limit: 6 }).catch(() => []),
      fsQuery(token, { collection: "contracts", parent: p, limit: 5 }).catch(() => []), fsQuery(token, { collection: "invoices", parent: p }).catch(() => []),
      fsQuery(token, { collection: "tasks", parent: p }).catch(() => []), fsQuery(token, { collection: "questionnaires", parent: p, limit: 5 }).catch(() => []),
    ]);
    return { ...threadRow(m), intent: m.structuredIntent || {},
      messages: msgs.map((x) => ({ at: toDate(x.at), from: x.system ? "system" : str(x.senderRole), text: str(x.text), attachment: x.attachment ? str(x.attachment.name || x.attachment.title || "attachment") : null })),
      proposals: props.map((x) => ({ id: x.id, title: str(x.title), price: x.price ?? x.total ?? null, status: str(x.status) })), contracts: cons.map((x) => ({ id: x.id, title: str(x.title), status: str(x.status), signedAt: toDate(x.signedAt), total: x.values?.total_price ?? null })),
      invoices: invs.filter((x) => str(x.status) !== "void").map((x) => ({ id: x.id, title: str(x.title), total: +x.total || 0, status: str(x.status), dueDate: isoDay(x.dueDate), paidAt: toDate(x.paidAt) })),
      tasks: tasks.map((x) => ({ taskId: x.id, title: str(x.title), note: str(x.note) || null, dueAt: toDate(x.dueAt), assignedTo: str(x.assignedTo), done: x.done === true })),
      questionnaires: qs.map((x) => ({ id: x.id, title: str(x.title), status: str(x.status) })) };
  }

  /* ---------- the snapshot ---------- */
  async function snapshot(env, who, coup) {
    const token = who.token, cid = coup.coupleId;
    const c = (await fsGet(token, `couples/${encodeURIComponent(cid)}`).catch(() => null)) || {};
    const card = coupleCard(c, cid); const metro = METROS[card.metroId] || null;
    const [rows, plan, guests, site, consults, dayof, shopping, wx, news, memory, queue, brief, reminders] = await Promise.all([
      loadThreads(token, cid).catch(() => []), loadPlan(token, cid), loadGuests(token, cid), within(loadSite(token, cid), 4000, null), loadConsults(token, cid), loadDayOf(token, cid), loadShopping(token, cid),
      metro ? within(weatherFor(env, card.metroId, metro.lat, metro.lon), 4000) : null, within(localNews(env, metro), 3500, { items: [] }),
      kv.get(env, K(cid, "memory")), kv.get(env, K(cid, "queue")), kv.get(env, K(cid, "brief")), kv.get(env, K(cid, "reminders")),
    ]);
    const per = await loadPerThread(token, rows);
    const tz = wx?.tz || "America/Phoenix"; const today = dayKey(tz); const nowIso = new Date().toISOString();
    const daysToGo = card.weddingDate ? Math.round((new Date(card.weddingDate + "T12:00:00") - new Date(today + "T12:00:00")) / 86400e3) : null;
    const in14 = dayKey(tz, new Date(Date.now() + 14 * 86400e3));
    const weddingWx = card.weddingDate && card.weddingDate >= today && card.weddingDate <= in14 ? dayWeather(wx, card.weddingDate) : null;
    const waiting = rows.filter((r) => r.waitingOnMe && !r.blocked).map((r) => ({ ...r, waitedHours: r.lastMessageAt ? Math.round((Date.now() - new Date(r.lastMessageAt)) / 3600e3) : null }));
    const awaitingVendor = rows.filter((r) => r.waitingOnVendor && !["lost", "booked"].includes(r.status)).map((r) => ({ ...r, waitedHours: r.lastMessageAt ? Math.round((Date.now() - new Date(r.lastMessageAt)) / 3600e3) : null }));
    const booked = plan.filter((p) => p.status === "booked"), gaps = plan.filter((p) => ["needed", "researching"].includes(p.status));
    const invoices = per.invoices; const open = invoices.filter((i) => i.status === "sent").sort((a, b) => str(a.dueDate || "9").localeCompare(str(b.dueDate || "9")));
    const sum = (xs, f = (x) => x) => Math.round(xs.reduce((s, x) => s + (+f(x) || 0), 0));
    const moneyOut = { budgetTotal: card.budgetTotal, planned: sum(plan, (p) => p.planned), committed: sum(plan, (p) => p.actual), invoicesOpen: sum(open, (i) => i.total), overdue: sum(open.filter((i) => i.dueDate && i.dueDate < today), (i) => i.total), dueSoon: open.filter((i) => i.dueDate && i.dueDate <= dayKey(tz, new Date(Date.now() + 14 * 86400e3))), paid: sum(invoices.filter((i) => i.status === "paid"), (i) => i.total), open: open.slice(0, 10), paidList: invoices.filter((i) => i.status === "paid").slice(0, 8) };
    const upcoming = [
      ...consults.map((x) => ({ when: x.startAt, kind: x.type, who: x.vendor, mode: x.mode, inquiryId: x.inquiryId, time: true })),
      ...card.keyDates.filter((k) => k.date >= today).map((k) => ({ when: k.date, kind: "Key date", who: k.label })),
      ...per.tasks.filter((t) => t.dueAt).map((t) => ({ when: t.dueAt.slice(0, 10), kind: "Task", who: t.title, inquiryId: t.inquiryId })),
    ].sort((a, b) => str(a.when).localeCompare(str(b.when))).slice(0, 14);
    const remindersAll = (reminders || []).filter((r) => !r.done).sort((a, b) => str(a.at).localeCompare(str(b.at)));
    return {
      kind: "couple", at: nowIso, tz, today, build: BUILD, couple: card, partner: coup.partner, user: { uid: who.uid, email: who.email }, daysToGo, weddingWx,
      counts: { threads: rows.length, waiting: waiting.length, unread: rows.filter((r) => r.unread).length, booked: booked.length, gaps: gaps.length, tasks: per.tasks.length, guests: guests.tally.total, yes: guests.tally.yes },
      waiting: waiting.slice(0, 12), awaitingVendor: awaitingVendor.slice(0, 8), tasks: per.tasks.slice(0, 20), team: plan, gaps, next: gaps.slice(0, 3), threads: rows.slice(0, 40),
      guests: guests.tally, guestsSample: guests.list.filter((g) => g.rsvp === "pending").slice(0, 10).map((g) => g.name), site, consults, upcoming, dayof, shopping: { items: shopping.length, left: shopping.filter((s) => !s.bought).length, est: sum(shopping.filter((s) => !s.bought), (s) => s.est || 0), nextUp: shopping.filter((s) => !s.bought).slice(0, 6) },
      money: moneyOut, weather: wx, news: news?.items || [], memory: memory || [], recent: (queue || []).slice(0, 8), brief: brief && brief.day === today ? brief : null, briefStale: !!(brief && brief.day !== today),
      reminders: remindersAll.slice(0, 30), due: remindersAll.filter((r) => r.at <= nowIso),
      _rows: rows, _guests: guests.list, _shopping: shopping,
    };
  }

  /* ---------- what the brain sees ---------- */
  function buildContext(s) {
    const L = [], c = s.couple, tz = s.tz;
    L.push(`TIME: ${localTime(tz)} (${tz})`);
    L.push(`THE COUPLE: ${c.names}${c.partnerName ? " (partner " + c.partnerName + ")" : ""}; wedding ${c.weddingDate ? fmtDay(c.weddingDate, tz) + " (" + (s.daysToGo === 0 ? "TODAY" : s.daysToGo > 0 ? s.daysToGo + " days to go" : Math.abs(s.daysToGo) + " days ago") + ")" : "date not set yet"}; in ${c.metro}; budget ${c.budgetTotal ? money(c.budgetTotal) : "not set"}; expecting ${c.guestEstimate || "an unknown number of"} guests${s.partner ? "; this login is the partner planning on the shared plan" : ""}.`);
    L.push(`TEAM (vendor categories, [slug]): ` + (s.team.map((p) => `[${p.slug}] ${p.label}: ${p.status}${p.vendorName ? " with " + p.vendorName : ""}${p.planned ? ", planned " + money(p.planned) : ""}${p.actual ? ", committed " + money(p.actual) : ""}`).join(" | ") || "no plan started yet"));
    if (s.gaps.length) L.push(`STILL TO BOOK (in the order weddings usually book): ` + s.gaps.map((p) => p.label + (p.status === "researching" ? " (researching)" : "")).join(", "));
    L.push(`VENDOR THREADS ([inquiryId]): ` + (s.threads.map((r) => `[${r.inquiryId}] ${r.vendor}${r.category ? " (" + label(r.category) + ")" : ""}: ${r.status}${r.waitingOnMe ? ", THEY WROTE LAST (waiting on you)" : r.waitingOnVendor ? ", waiting on them" : ""}${r.lastMessageAt ? ", last " + fmtDay(r.lastMessageAt, tz) : ""}${r.lastMessagePreview ? ': "' + clip(r.lastMessagePreview, 110) + '"' : ""}`).join(" | ") || "none yet"));
    L.push(`WAITING ON YOU (vendors who wrote last): ` + (s.waiting.map((r) => `[${r.inquiryId}] ${r.vendor}, ${r.waitedHours}h: "${clip(r.lastMessagePreview, 140)}"`).join(" | ") || "nobody"));
    if (s.awaitingVendor.length) L.push(`WAITING ON VENDORS: ` + s.awaitingVendor.map((r) => `[${r.inquiryId}] ${r.vendor} (${r.waitedHours}h)`).join(" | "));
    L.push(`TASKS VENDORS GAVE YOU ([taskId] in [inquiryId]): ` + (s.tasks.map((t) => `[${t.taskId}] in [${t.inquiryId}] from ${t.vendor}: ${t.title}${t.dueAt ? " by " + fmtDay(t.dueAt, tz) : ""}${t.dueAt && t.dueAt.slice(0, 10) < s.today ? " OVERDUE" : ""}`).join(" | ") || "none open"));
    L.push(`MONEY: budget ${c.budgetTotal ? money(c.budgetTotal) : "not set"}; planned across categories ${money(s.money.planned)}; committed to booked vendors ${money(s.money.committed)}; invoices open ${money(s.money.invoicesOpen)}${s.money.overdue ? " (" + money(s.money.overdue) + " overdue)" : ""}; paid so far ${money(s.money.paid)}. Open invoices: ` + (s.money.open.map((i) => `${i.vendor} ${i.title} ${money(i.total)}${i.dueDate ? " due " + fmtDay(i.dueDate, tz) : ""}`).join(" | ") || "none"));
    L.push(`GUESTS: ${s.guests.total} invited across ${s.guests.parties} parties; ${s.guests.yes} yes, ${s.guests.no} no, ${s.guests.pending} not answered` + (s.site ? `. Wedding website ${s.site.url} (${s.site.rsvps} online RSVPs, ${s.site.rsvpYes} attending)` : ". No wedding website yet"));
    L.push(`UPCOMING: ` + (s.upcoming.map((u) => `${u.time ? fmtWhen(u.when, tz) : fmtDay(u.when, tz)} ${u.kind}: ${u.who}${u.mode ? " (" + u.mode + ")" : ""}`).join(" | ") || "nothing scheduled"));
    L.push(`DAY-OF TIMELINE: ` + (s.dayof.map((d) => `${d.time} ${d.label}${d.owners.length ? " (" + d.owners.join("/") + ")" : ""}`).join(" | ") || "not built yet (the app builds a classic day around the ceremony time)"));
    L.push(`SHOPPING LIST: ${s.shopping.items} items, ${s.shopping.left} still to buy${s.shopping.est ? " (about " + money(s.shopping.est) + ")" : ""}. Next up: ` + (s.shopping.nextUp.map((x) => x.name + (x.qty > 1 ? " x" + x.qty : "")).join(", ") || "nothing"));
    L.push(`WEATHER: ${weatherSummary(s.weather, c.metro)}` + (s.weddingWx ? `. WEDDING DAY FORECAST: ${s.weddingWx.text}, high ${s.weddingWx.hi}, rain ${s.weddingWx.rain}%, wind ${s.weddingWx.wind} mph, sunset ${s.weddingWx.sunset}` : ""));
    L.push(`LOCAL NEWS (${c.metro}): ` + (s.news.slice(0, 5).map((n) => n.title).join(" / ") || "unavailable"));
    L.push(`REMINDERS (June's own, [id]): ` + (s.reminders.map((r) => `[${r.id}] ${fmtWhen(r.at, tz)}: ${r.text}${r.at <= s.at ? " DUE NOW" : ""}${r.repeat && r.repeat !== "none" ? " repeats " + r.repeat : ""}`).join(" | ") || "none"));
    L.push(`MEMORY (what they asked June to remember): ` + (s.memory.map((m) => `[${m.id}] ${m.text}`).join(" | ") || "nothing yet"));
    L.push(`RECENT ACTIONS: ` + (s.recent.map((q) => `${q.summary} → ${q.status}${q.result ? " (" + q.result + ")" : ""}`).join(" | ") || "none"));
    if (s.brief?.text) L.push(`TODAY'S BRIEF (already given): ${s.brief.text.slice(0, 500)}`);
    return L.join("\n");
  }

  const SYSTEM = (c) => `You are June, the planning assistant inside Lazo for ${c.names}, who are getting married${c.weddingDate ? " on " + c.weddingDate : ""} in ${c.metro}. Lazo is the wedding planning app and vendor directory; the couple plans there: their vendor team by category, messages with vendors, proposals, contracts and invoices, guests and RSVPs, a wedding website, a day-of timeline and a shopping list.
Persona: warm, bright, precise, British; the friend who happens to be a brilliant wedding planner and read everything before she walked in. Calm about money, never pushy, never gushing. You are on the couple's side only.
Your replies are spoken aloud through text-to-speech: plain prose, no markdown, no lists, no headers, no URLs or ids read aloud. Two to four sentences unless they ask for detail. Lead with the answer. Say vendors by name, money in dollars, round sensibly.
Everything current is in the LIVE CONTEXT; answer from it and never invent figures, names or prices. For anything deeper use the tools: lazo_thread before discussing one vendor conversation in detail, lazo_guests to look up guests, lazo_find_vendors to suggest vendors from the Lazo directory in their metro, lazo_prices for what a category typically costs there, lazo_timeline and lazo_shopping for the day-of plan. If something isn't there, say so.
Actions: request_action queues a change for the couple's confirmation; a card appears on screen and nothing happens until they tap Confirm, so say it is ready to confirm. Kinds: send_message (to a vendor, params.inquiryId + params.text; write the message yourself in the couple's voice, friendly and brief, first person plural), complete_task (params.inquiryId + params.taskId), set_team (params.slug + status needed|researching|booked|skipped, optional vendorName, planned, actual), add_guest (params.name, party, count), set_rsvp (params.guestId or params.name, params.rsvp yes|no|pending), add_shopping (params.name, qty, est, cat), tick_shopping (params.itemId), add_moment (params.time HH:MM 24h, params.label, note), set_details (params.weddingDate YYYY-MM-DD, budgetTotal, guestEstimate: only the ones they want changed).
Booking a vendor, signing, paying and reviews happen in the Lazo app; use open_thread to send them there. Never promise a vendor's availability or price; suggest they ask, and offer to draft the message.
remember / forget hold durable preferences (use remember whenever they say "remember", "note that", "from now on"). Use the ids shown in brackets for every tool call.
Reminders: set_reminder whenever they say "remind me" (resolve the time in their timezone; default 9am if none given; "every Monday" is repeat weekly). complete_reminder when it's done. Due reminders are listed as DUE NOW: mention them first when they greet you.
Planning advice: when asked what to do next, look at STILL TO BOOK, days to go, the budget and what is waiting, and give one or two concrete next steps. Typical timing: venue and planner first, then photographer, caterer, videographer, music, florist, officiant, hair and makeup, cake, invitations (send 8 weeks out), rentals, transport, a day-of coordinator; final headcount to the caterer 2 weeks out.`;

  const TOOLS = [
    { name: "lazo_thread", description: "One vendor conversation in full: messages, proposals, contracts, invoices, tasks, questionnaires.", input_schema: { type: "object", properties: { inquiryId: { type: "string" } }, required: ["inquiryId"], additionalProperties: false } },
    { name: "lazo_guests", description: "Search the guest list by name or party, or list everyone with a given RSVP (yes, no, pending).", input_schema: { type: "object", properties: { query: { type: "string" }, rsvp: { type: "string", enum: ["yes", "no", "pending"] } }, required: [], additionalProperties: false } },
    { name: "lazo_find_vendors", description: "Vendors in the Lazo directory for the couple's metro and a category slug (e.g. wedding-florists), best first, with starting price, rating and page link.", input_schema: { type: "object", properties: { category: { type: "string" }, limit: { type: "integer" } }, required: ["category"], additionalProperties: false } },
    { name: "lazo_prices", description: "What a category typically costs in the couple's metro (starting-price p25, median, p75 from Lazo listings).", input_schema: { type: "object", properties: { category: { type: "string" } }, required: ["category"], additionalProperties: false } },
    { name: "lazo_timeline", description: "The full day-of timeline with notes, durations and owners.", input_schema: { type: "object", properties: {}, required: [], additionalProperties: false } },
    { name: "lazo_shopping", description: "The full shopping list with ids, quantities, estimates and what is bought.", input_schema: { type: "object", properties: { onlyLeft: { type: "boolean" } }, required: [], additionalProperties: false } },
    { name: "open_thread", description: "Open a vendor conversation in the Lazo app on the couple's screen.", input_schema: { type: "object", properties: { inquiryId: { type: "string" }, label: { type: "string" } }, required: ["inquiryId", "label"], additionalProperties: false } },
    { name: "remember", description: "Store a durable fact or preference in June's memory for this couple.", input_schema: { type: "object", properties: { text: { type: "string" } }, required: ["text"], additionalProperties: false } },
    { name: "forget", description: "Delete a memory by its id (shown in MEMORY as [id]).", input_schema: { type: "object", properties: { id: { type: "string" } }, required: ["id"], additionalProperties: false } },
    { name: "set_reminder", description: "Set a reminder from June (shown in the hub and spoken when due). when = local date-time ISO like 2026-10-09T09:00.", input_schema: { type: "object", properties: { text: { type: "string" }, when: { type: "string" }, repeat: { type: "string", enum: ["none", "daily", "weekly"] } }, required: ["text", "when"], additionalProperties: false } },
    { name: "complete_reminder", description: "Mark a reminder done (id from REMINDERS), or delete it.", input_schema: { type: "object", properties: { id: { type: "string" }, remove: { type: "boolean" } }, required: ["id", "remove"], additionalProperties: false } },
    { name: "request_action", description: "Queue a change for the couple's confirmation. summary = one plain sentence of what will happen.",
      input_schema: { type: "object", properties: { kind: { type: "string", enum: ["send_message", "complete_task", "set_team", "add_guest", "set_rsvp", "add_shopping", "tick_shopping", "add_moment", "set_details"] }, summary: { type: "string" },
        params: { type: "object", properties: { inquiryId: { type: "string" }, text: { type: "string" }, taskId: { type: "string" }, slug: { type: "string" }, status: { type: "string" }, vendorName: { type: "string" }, planned: { type: "number" }, actual: { type: "number" }, name: { type: "string" }, party: { type: "string" }, count: { type: "integer" }, guestId: { type: "string" }, rsvp: { type: "string" }, qty: { type: "integer" }, est: { type: "number" }, cat: { type: "string" }, itemId: { type: "string" }, time: { type: "string" }, label: { type: "string" }, note: { type: "string" }, weddingDate: { type: "string" }, budgetTotal: { type: "number" }, guestEstimate: { type: "integer" } }, additionalProperties: false } }, required: ["kind", "summary", "params"], additionalProperties: false } },
  ];

  async function runTool(name, input, env, who, coup, snap, actions) {
    const token = who.token, cid = coup.coupleId, tz = snap.tz;
    switch (name) {
      case "lazo_thread": { const t = await threadDetail(token, cid, input.inquiryId); return JSON.stringify(t).slice(0, 30000); }
      case "lazo_guests": { let g = snap._guests; if (input.rsvp) g = g.filter((x) => x.rsvp === input.rsvp); if (input.query) { const q = clip(input.query, 60).toLowerCase(); g = g.filter((x) => [x.name, x.party, x.meal].some((s) => str(s).toLowerCase().includes(q))); } return JSON.stringify({ tally: snap.guests, guests: g.slice(0, 60) }); }
      case "lazo_find_vendors": {
        const cat = clip(input.category, 60).toLowerCase(); const metroId = snap.couple.metroId; if (!metroId) return "The couple has no metro set, so I can't search the directory; ask them which city.";
        let docs = await fsQuery(token, { collection: "vendors", where: [["metroId", "EQUAL", metroId], ["categories", "ARRAY_CONTAINS", cat]], limit: 40 }).catch(() => []);
        if (!docs.length) docs = await fsQuery(token, { collection: "vendors", where: [["metroId", "EQUAL", metroId], ["category", "EQUAL", cat]], limit: 40 }).catch(() => []);
        const list = docs.filter((v) => str(v.status) !== "hidden").map((v) => ({ vendorId: v.id, name: str(v.name), startingPrice: v.startingPrice ?? null, rating: +v.reviewAverage || null, reviews: +v.reviewCount || 0, verified: v.verified === true, claimed: !!v.claimedBy, score: v.score != null ? +v.score : 65, url: `https://meetlazo.com/vendors/${metroId}/${str(v.slug || v.id)}`, blurb: clip(v.bio || v.tagline, 140) }))
          .sort((a, b) => (b.verified - a.verified) || (b.claimed - a.claimed) || (b.score - a.score)).slice(0, Math.min(12, +input.limit || 8));
        return JSON.stringify({ category: cat, metro: snap.couple.metro, vendors: list, note: list.length ? "The couple can message any of them from the Lazo app." : "No listings for that category in this metro." });
      }
      case "lazo_prices": { const cat = clip(input.category, 60).toLowerCase(); const ms = await fsGet(token, `metroStats/${encodeURIComponent(snap.couple.metroId + "__" + cat)}`).catch(() => null); return JSON.stringify(ms ? { category: cat, metro: snap.couple.metro, vendors: ms.vendors || 0, priceFrom: ms.priceFrom || null } : { category: cat, note: "No price data for that category here yet." }); }
      case "lazo_timeline": return JSON.stringify({ weddingDate: snap.couple.weddingDate, moments: snap.dayof });
      case "lazo_shopping": return JSON.stringify({ items: (input.onlyLeft ? snap._shopping.filter((s) => !s.bought) : snap._shopping).slice(0, 80) });
      case "open_thread": actions.push({ type: "open", url: `${env.COUPLE_APP_URL || "https://app.meetlazo.com/"}?thread=${encodeURIComponent(input.inquiryId)}`, label: input.label }); return "Opened " + input.label + " in the Lazo app.";
      case "remember": { const mem = (await kv.get(env, K(cid, "memory"))) || []; const m = { id: uid(), text: clip(input.text, 400), at: new Date().toISOString() }; mem.unshift(m); await kv.put(env, K(cid, "memory"), mem.slice(0, 100)); actions.push({ type: "memory", value: mem }); return "Remembered [" + m.id + "]."; }
      case "forget": { const mem = ((await kv.get(env, K(cid, "memory"))) || []).filter((m) => m.id !== input.id); await kv.put(env, K(cid, "memory"), mem); actions.push({ type: "memory", value: mem }); return "Forgotten."; }
      case "set_reminder": {
        const list = (await kv.get(env, K(cid, "reminders"))) || []; const at = localToIso(str(input.when), tz); if (!at) return "I couldn't read that time; give it as YYYY-MM-DDTHH:MM.";
        const r = { id: uid(), text: clip(input.text, 240), at, repeat: ["daily", "weekly"].includes(input.repeat) ? input.repeat : "none", done: false, notified: false, createdAt: new Date().toISOString() };
        list.push(r); await kv.put(env, K(cid, "reminders"), list.slice(-200)); actions.push({ type: "reminders" }); return `Reminder set for ${fmtWhen(at, tz)} [${r.id}].`;
      }
      case "complete_reminder": { let list = (await kv.get(env, K(cid, "reminders"))) || []; const r = list.find((x) => x.id === input.id); if (!r) return "No reminder with that id."; if (input.remove) list = list.filter((x) => x.id !== input.id); else { r.done = true; r.doneAt = new Date().toISOString(); } await kv.put(env, K(cid, "reminders"), list); actions.push({ type: "reminders" }); return input.remove ? "Deleted." : "Marked done."; }
      case "request_action": {
        const KINDS = ["send_message", "complete_task", "set_team", "add_guest", "set_rsvp", "add_shopping", "tick_shopping", "add_moment", "set_details"]; if (!KINDS.includes(input.kind) || !input.summary) return "Invalid action.";
        const p = input.params || {}; let vendor = null;
        if (["send_message", "complete_task"].includes(input.kind)) { const row = snap._rows.find((r) => r.inquiryId === p.inquiryId); if (!row) return "That needs params.inquiryId from VENDOR THREADS."; if (row.blocked) return "The couple blocked this vendor; nothing can be sent."; vendor = row.vendor; }
        if (input.kind === "set_team" && !snap.team.some((t) => t.slug === p.slug) && !CATS[p.slug]) return "params.slug must be one of the TEAM slugs.";
        if (input.kind === "add_moment" && !/^\d{1,2}:\d{2}$/.test(str(p.time))) return "add_moment needs params.time as HH:MM.";
        const item = { id: uid(), kind: input.kind, params: p, vendor, summary: clip(input.summary, 200), status: "awaiting confirmation", at: new Date().toISOString() };
        actions.push({ type: "confirm", item }); return "Queued for the couple's confirmation: " + item.summary;
      }
      default: return "Unknown tool";
    }
  }

  /* ---------- hands: run a confirmed action as the couple ---------- */
  async function execute(env, who, coup, item) {
    const token = who.token, cid = coup.coupleId, p = item.params || {}, base = `couples/${encodeURIComponent(cid)}`;
    switch (item.kind) {
      case "send_message": {
        const m = await ownThread(token, cid, p.inquiryId); const text = clip(p.text, 2900); if (!text) throw new Error("Nothing to send."); if (m.blockedByCouple === true) throw new Error("You blocked this vendor.");
        await fsCreate(token, `inquiries/${m.id}`, "messages", { senderRole: "couple", text, at: new Date() });
        await fsPatch(token, `inquiries/${m.id}`, { coupleActiveAt: new Date() }).catch(() => {});
        return `Sent to ${str(m.vendorName) || "the vendor"}.`;
      }
      case "complete_task": { const m = await ownThread(token, cid, p.inquiryId); const tp = `inquiries/${m.id}/tasks/${encodeURIComponent(clip(p.taskId, 80))}`; const t = await fsGet(token, tp); if (!t) throw new Error("No such task."); if (str(t.assignedTo) !== "couple") throw new Error("That task belongs to the vendor."); await fsPatch(token, tp, { done: true, doneAt: new Date() }); return `Done: ${str(t.title)}.`; }
      case "set_team": {
        const slug = clip(p.slug, 60); const status = ["needed", "researching", "booked", "skipped"].includes(str(p.status)) ? str(p.status) : null;
        const obj = { updatedAt: new Date() }; if (status) obj.status = status; if (p.vendorName != null) obj.vendorName = clip(p.vendorName, 120); if (p.planned != null) obj.budgetPlanned = Math.max(0, Math.round(+p.planned || 0)); if (p.actual != null) obj.budgetActual = Math.max(0, Math.round(+p.actual || 0));
        await fsPatch(token, `${base}/plan/${encodeURIComponent(slug)}`, obj); return `${label(slug)} updated${status ? ": " + status : ""}${obj.vendorName ? " with " + obj.vendorName : ""}.`;
      }
      case "add_guest": { const name = clip(p.name, 120); if (!name) throw new Error("A guest needs a name."); await fsCreate(token, base, "guests", { name, party: clip(p.party, 80), count: Math.max(1, Math.min(20, +p.count || 1)), rsvp: "", meal: "", createdAt: new Date() }); return `Added ${name} to the guest list.`; }
      case "set_rsvp": {
        const docs = await fsQuery(token, { collection: "guests", parent: base }); let g = p.guestId ? docs.find((x) => x.id === p.guestId) : null;
        if (!g && p.name) { const q = clip(p.name, 80).toLowerCase(); g = docs.find((x) => str(x.name).toLowerCase() === q) || docs.find((x) => str(x.name).toLowerCase().includes(q)); }
        if (!g) throw new Error("I couldn't find that guest."); const v = ["yes", "no"].includes(str(p.rsvp)) ? str(p.rsvp) : "";
        await fsPatch(token, `${base}/guests/${g.id}`, { rsvp: v, updatedAt: new Date() }); return `${str(g.name)}: ${v || "not answered"}.`;
      }
      case "add_shopping": { const name = clip(p.name, 120); if (!name) throw new Error("What should I add?"); await fsCreate(token, base, "shopping", { name, cat: ["ceremony", "reception", "attire", "stationery", "favors", "dayof", "other"].includes(str(p.cat)) ? str(p.cat) : "other", qty: Math.max(1, +p.qty || 1), est: p.est != null ? Math.max(0, +p.est || 0) : 0, bought: false, note: clip(p.note, 200), link: "", order: Date.now(), createdAt: new Date() }); return `Added ${name} to the shopping list.`; }
      case "tick_shopping": { const tp = `${base}/shopping/${encodeURIComponent(clip(p.itemId, 80))}`; const it = await fsGet(token, tp); if (!it) throw new Error("No such item."); await fsPatch(token, tp, { bought: true, updatedAt: new Date() }); return `${str(it.name)} marked bought.`; }
      case "add_moment": { const time = str(p.time).padStart(5, "0"); const lab = clip(p.label, 120); if (!lab) throw new Error("What happens then?"); await fsCreate(token, base, "dayof", { time, label: lab, note: clip(p.note, 300), dur: Math.max(0, +p.dur || 0), owners: [], anchor: false, updatedAt: new Date() }); return `${time} ${lab} added to the day.`; }
      case "set_details": {
        const obj = {}; if (/^\d{4}-\d{2}-\d{2}$/.test(str(p.weddingDate))) obj.weddingDate = new Date(p.weddingDate + "T12:00:00"); if (p.budgetTotal != null) obj.budgetTotal = Math.max(0, Math.round(+p.budgetTotal || 0)); if (p.guestEstimate != null) obj.guestEstimate = Math.max(0, Math.round(+p.guestEstimate || 0));
        if (!Object.keys(obj).length) throw new Error("Nothing to change."); await fsPatch(token, base, obj); return "Details updated: " + Object.keys(obj).join(", ") + ".";
      }
      default: throw new Error("Unknown action");
    }
  }

  /* ---------- today's brief ---------- */
  const BRIEF_PROMPT = `Compose today's spoken brief for the couple: 110 to 180 words, flowing prose, no lists, no headers, no ids or URLs, no questions. Open with a greeting that carries the day, the countdown and the weather in one breath. Then whoever is waiting on them (vendors who wrote last) and any task or invoice due, by name. Then one or two concrete next steps from STILL TO BOOK and the timing for how far out they are, and a line on the guest list if RSVPs are still coming in. Mention DUE NOW reminders. Close warmly in a single short sentence. If the wedding was today or has passed, make it a congratulations and skip the planning.`;
  async function makeBrief(env, ctx, who, coup, force, snapIn = null) {
    const snap = snapIn || await snapshot(env, who, coup); const key = K(coup.coupleId, "brief");
    if (!force && snap.brief?.text) return snap.brief;
    if (!env.ANTHROPIC_API_KEY) return { error: "no brain" };
    const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
    const r = await client.beta.messages.create({ model: env.BRIEF_MODEL || "claude-sonnet-5-5", max_tokens: 1200, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "medium" },
      system: SYSTEM(snap.couple) + "\n" + BRIEF_PROMPT, messages: [{ role: "user", content: `Compose today's brief.\n\nLIVE CONTEXT:\n${buildContext({ ...snap, brief: null })}` }] });
    const text = r.content.filter((b) => b.type === "text").map((b) => b.text).join(" ").trim();
    const brief = { id: uid(), slot: "daily", day: snap.today, at: new Date().toISOString(), text, audio: false, audioPending: !!env.ELEVENLABS_API_KEY };
    await kv.put(env, key, brief, { expirationTtl: 3 * 86400 });
    if (env.ELEVENLABS_API_KEY && text) ctx.waitUntil((async () => {
      try { const sp = await speakWithTrack(env, text); if (sp) { await env.JUNE.put(K(coup.coupleId, "brief_audio"), sp.wav, { expirationTtl: 2 * 86400 }); await env.JUNE.put(K(coup.coupleId, "brief_env"), JSON.stringify(sp.env), { expirationTtl: 2 * 86400 }); brief.audio = true; } } catch {}
      brief.audioPending = false; await kv.put(env, key, brief, { expirationTtl: 3 * 86400 });
    })());
    return brief;
  }

  async function recordAction(env, cid, item) { const q = (await kv.get(env, K(cid, "queue"))) || []; const i = q.findIndex((x) => x.id === item.id); if (i >= 0) q[i] = item; else q.unshift(item); await kv.put(env, K(cid, "queue"), q.slice(0, 30)); }

  /* ---------- routes (called by the worker once the login resolved to a couple) ---------- */
  async function route(p, request, env, ctx, who, coup, chat) {
    const cid = coup.coupleId;
    if (p === "/api/state" && request.method === "GET") { const s = await snapshot(env, who, coup); delete s._rows; delete s._guests; delete s._shopping; return D.json(s); }
    if (p === "/api/chat" && request.method === "POST") return chat(request, env, ctx, who, coup, { snapshot, buildContext, system: (s) => SYSTEM(s.couple), tools: TOOLS, runTool });
    if (p === "/api/brief" && request.method === "POST") { const { force } = await request.json().catch(() => ({})); return D.json(await makeBrief(env, ctx, who, coup, !!force)); }
    if (p === "/api/brief" && request.method === "GET") return D.json((await kv.get(env, K(cid, "brief"))) || null);
    if (p === "/api/brief/audio") { const a = await env.JUNE.get(K(cid, "brief_audio"), "arrayBuffer"); if (!a) return D.json({ error: "no audio yet" }, 404); return new Response(a, { headers: { "content-type": audioType(a), "cache-control": "private, max-age=600" } }); }
    if (p === "/api/thread" && request.method === "GET") return D.json(await threadDetail(who.token, cid, new URL(request.url).searchParams.get("id") || ""));
    if (p === "/api/read" && request.method === "POST") { const { inquiryId } = await request.json(); const m = await ownThread(who.token, cid, inquiryId); await fsPatch(who.token, `inquiries/${m.id}`, { coupleLastReadAt: new Date() }).catch(() => {}); return D.json({ ok: true }); }
    if (p === "/api/act" && request.method === "POST") {
      const { item, decision } = await request.json(); if (!item?.id || !item.kind) return D.json({ error: "bad item" }, 400);
      if (decision !== "confirm") { const rec = { ...item, status: "cancelled", doneAt: new Date().toISOString() }; await recordAction(env, cid, rec); return D.json(rec); }
      let rec; try { const result = await execute(env, who, coup, item); rec = { ...item, status: "done", result, doneAt: new Date().toISOString() }; } catch (e) { rec = { ...item, status: "failed", result: e.message, doneAt: new Date().toISOString() }; }
      await recordAction(env, cid, rec); return D.json(rec);
    }
    if (p === "/api/reminders" && request.method === "GET") return D.json((await kv.get(env, K(cid, "reminders"))) || []);
    if (p === "/api/reminders" && request.method === "POST") {
      const b = await request.json(); let list = (await kv.get(env, K(cid, "reminders"))) || [];
      if (b.text && b.when) { const at = localToIso(b.when, b.tz || "America/Phoenix"); if (!at) return D.json({ error: "bad time" }, 400); list.push({ id: uid(), text: clip(b.text, 240), at, repeat: ["daily", "weekly"].includes(b.repeat) ? b.repeat : "none", done: false, notified: false, createdAt: new Date().toISOString() }); }
      if (b.done) { const r = list.find((x) => x.id === b.done); if (r) { r.done = true; r.doneAt = new Date().toISOString(); } }
      if (b.remove) list = list.filter((x) => x.id !== b.remove);
      if (b.snooze) { const r = list.find((x) => x.id === b.snooze); if (r) { r.at = new Date(Date.now() + (+b.minutes || 60) * 60e3).toISOString(); r.notified = false; } }
      await kv.put(env, K(cid, "reminders"), list.slice(-200)); return D.json(list.filter((x) => !x.done).sort((a, c) => a.at.localeCompare(c.at)));
    }
    if (p === "/api/memory" && request.method === "POST") { const { id, text } = await request.json(); let mem = (await kv.get(env, K(cid, "memory"))) || []; if (id) mem = mem.filter((m) => m.id !== id); if (text) mem.unshift({ id: uid(), text: clip(text, 400), at: new Date().toISOString() }); await kv.put(env, K(cid, "memory"), mem.slice(0, 100)); return D.json(mem); }
    if (p === "/api/subscribe" || p === "/api/weekly" || p === "/api/triage" || p === "/api/social" || p.startsWith("/api/social/")) return D.json({ error: "not for couples" }, 404);
    return null;
  }

  return { resolveCouple, snapshot, buildContext, SYSTEM, TOOLS, runTool, execute, makeBrief, route, threadDetail };
}
