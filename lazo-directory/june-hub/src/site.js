// JC-LAZO-JUNE-SITE-1014: June drafts the couple's wedding website from a short conversation.
// She reads what Lazo already knows (names, date, venue, the couple's photos), asks Places for hotels
// and airports near the venue (meetlazo.com/api/stay), looks up what the weather has actually been on
// that date for the last three years, and writes: the story and its milestones, a hashtag, the FAQ
// (dress code, parking, getting there, typical weather), driving notes, the section headlines, and a
// design picked to suit their photos. Nothing is published by this: the editor fills its fields for
// the couple to read over, and the chat path queues a confirm card that writes only empty fields.
export function makeSite(D) {
  const { fsGet, fsQuery, fsPatch, str, clip, Anthropic, METROS } = D;

  const DESIGNS = {
    sage: "Botanical, garden, forest light; sage green and eucalyptus",
    noir: "Black tie, editorial, midnight gold; black, gold, champagne",
    dune: "Desert modern, dusk hills, golden hour; terracotta and dusty rose",
    fete: "Classic, formal, the first dance; navy, gold, blush",
    tide: "Coastal, sea light, barefoot by the water; seaglass and navy",
    flora: "Romantic, garden roses, candlelight; rose, peony, blush",
    atelier: "Minimal, editorial, black and white; black, white, stone",
    verona: "Vineyard, Italian villa, harvest light; burgundy and Tuscan gold",
    shore: "Ocean, sand and sea light, barefoot vows; lagoon, sunset, driftwood",
    summit: "Mountains, alpine lakes, thin air; alpine green and granite",
    ranch: "Rustic, big sky, barn and bonfire; saddle brown and denim",
    starlit: "Night sky, a hill full of stars; midnight, nebula, gold",
    frost: "Winter, snow light, candlelight; ice blue and evergreen",
    harvest: "Fall, maple, pumpkin and plum, a bonfire after; maple, pumpkin, plum, moss",
    aquarelle: "Watercolor, soft washes; blush, sky, lilac, sage",
    prism: "Geometric, terrazzo, clean lines, big windows; terrazzo, ink, coral, mint",
    meadow: "Boho, pampas, terracotta and golden hour; pampas, terracotta, rust, olive",
    gilded: "Art deco, gold fans, onyx and emerald; onyx, emerald, ivory, burgundy",
    marigold: "South Asian, marigold garlands, a multi-day celebration; marigold, magenta, royal blue, emerald",
    papel: "Latin fiesta, papel picado, mariachi until late; fiesta colors, cobalt, terracotta, jade",
    peony: "Blush, peony and champagne, petals in the air; peony, champagne, dusk, ivory",
  };

  const isoDay = (v) => { if (!v) return ""; const s = str(v); if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s; const d = new Date(s); return isNaN(d) ? "" : d.toISOString().slice(0, 10); };
  const httpsUrl = (u) => (/^https:\/\//.test(str(u)) ? str(u) : "");
  const within = (p, ms, dflt) => Promise.race([p.catch(() => dflt), new Promise((r) => setTimeout(() => r(dflt), ms))]);

  // What the weather has actually done on this date: three past years, a week either side.
  async function climate(lat, lon, dateIso) {
    if (lat == null || lon == null || !/^\d{4}-\d{2}-\d{2}$/.test(dateIso)) return null;
    const md = dateIso.slice(5), y0 = new Date().getUTCFullYear() - 1;
    const days = [];
    await Promise.all([0, 1, 2].map(async (k) => {
      const c = new Date(`${y0 - k}-${md}T12:00:00Z`); if (isNaN(c)) return;
      const a = new Date(c - 3 * 864e5).toISOString().slice(0, 10), b = new Date(+c + 3 * 864e5).toISOString().slice(0, 10);
      const u = `https://archive-api.open-meteo.com/v1/archive?latitude=${lat}&longitude=${lon}&start_date=${a}&end_date=${b}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&temperature_unit=fahrenheit&precipitation_unit=inch&timezone=auto`;
      const r = await fetch(u).catch(() => null); if (!r || !r.ok) return;
      const j = await r.json().catch(() => null); const d = j && j.daily; if (!d || !d.time) return;
      d.time.forEach((_, i) => { if (d.temperature_2m_max[i] != null) days.push({ hi: d.temperature_2m_max[i], lo: d.temperature_2m_min[i], wet: (d.precipitation_sum[i] || 0) >= 0.04 }); });
    }));
    if (days.length < 5) return null;
    const avg = (f) => Math.round(days.reduce((s, x) => s + f(x), 0) / days.length);
    return { hi: avg((x) => x.hi), lo: avg((x) => x.lo), wetShare: Math.round(100 * days.filter((x) => x.wet).length / days.length), sample: days.length };
  }

  async function gather(who, coup) {
    const token = who.token, cid = coup.coupleId;
    const c = (await fsGet(token, `couples/${encodeURIComponent(cid)}`).catch(() => null)) || {};
    const sites = await fsQuery(token, { collection: "weddingSites", where: [["coupleUid", "EQUAL", cid]], limit: 1 }).catch(() => []);
    const site = sites[0] || null;
    const w = site || (c.siteDraft && typeof c.siteDraft === "object" ? c.siteDraft : {});
    let venueName = str(w.venueName), venueAddress = str(w.venueAddress);
    if (!venueName) {
      const plan = await fsGet(token, `couples/${encodeURIComponent(cid)}/plan/wedding-venues`).catch(() => null);
      venueName = str(plan && plan.vendorName);
      if (plan && plan.vendorId && !venueAddress) {
        const v = await fsGet(token, `vendors/${encodeURIComponent(str(plan.vendorId))}`).catch(() => null);
        venueAddress = str(v && v.address);
      }
    }
    const metro = METROS[str(c.metroId)] || null;
    const dateIso = isoDay(w.dateIso) || isoDay(c.weddingDate);
    const photos = [httpsUrl(w.heroPhoto && w.heroPhoto.url), httpsUrl(w.coverUrl), ...((Array.isArray(w.siteGallery) ? w.siteGallery : []).map(httpsUrl)), httpsUrl(c.photoUrl)]
      .filter(Boolean).filter((u, i, a) => a.indexOf(u) === i).slice(0, 3);
    const [stay, wx] = await Promise.all([
      site ? within(fetch(`https://meetlazo.com/api/stay?slug=${encodeURIComponent(site.id)}`).then((r) => r.json()), 6000, null) : null,
      within(climate(metro ? metro.lat : null, metro ? metro.lon : null, dateIso), 6000, null),
    ]);
    return { cid, c, site, w, venueName, venueAddress, metro, dateIso, photos, stay: stay || { hotels: [], airports: [] }, wx,
      names: str(w.names) || str(c.names), events: Array.isArray(w.events) ? w.events : [] };
  }

  const SCHEMA = {
    type: "object", additionalProperties: false,
    required: ["story", "milestones", "hashtags", "dressCode", "weatherNote", "parking", "transport", "drivingNotes", "headlines", "design", "designWhy", "hotelPicks", "toConfirm", "summary"],
    properties: {
      story: { type: "string", description: "Our story, 70-130 words, first person plural, from their answers only." },
      milestones: { type: "array", items: { type: "object", additionalProperties: false, required: ["when", "title", "text"], properties: { when: { type: "string" }, title: { type: "string" }, text: { type: "string" } } } },
      hashtags: { type: "array", items: { type: "string" }, description: "Three hashtag ideas, no #, letters and digits only, easy to spell." },
      dressCode: { type: "string" },
      weatherNote: { type: "string", description: "One or two sentences on the typical weather that week and what to bring; empty if no weather data." },
      parking: { type: "string", description: "Only what is known; empty if unknown." },
      transport: { type: "string", description: "Only what is known; empty if unknown." },
      drivingNotes: { type: "string", description: "How to get there from the nearest airport in general terms (direction, rough drive time), no invented road numbers." },
      headlines: { type: "object", additionalProperties: false, required: ["eyebrow", "countdown", "day", "rsvp", "thanks", "party", "stay"],
        properties: { eyebrow: { type: "string" }, countdown: { type: "string", description: "Words after the day count, e.g. 'days until we say I do'." }, day: { type: "string" }, rsvp: { type: "string" }, thanks: { type: "string" }, party: { type: "string" }, stay: { type: "string" } } },
      design: { type: "string", enum: Object.keys(DESIGNS) },
      designWhy: { type: "string", description: "One sentence: why this design suits their photos, venue and season." },
      hotelPicks: { type: "array", items: { type: "object", additionalProperties: false, required: ["index", "note"], properties: { index: { type: "integer" }, note: { type: "string" } } } },
      toConfirm: { type: "array", items: { type: "string" }, description: "Facts the couple should check before publishing." },
      summary: { type: "string", description: "One warm spoken sentence describing what June drafted." },
    },
  };

  const RULES = `You are June, Lazo's wedding planner, drafting a couple's wedding website for them to read over before they publish.
Write as the couple (we, us, our), warm, specific and plain. No clichés ("fairytale", "happily ever after", "journey", "soulmate"), no exclamation marks, no emoji.
Never invent facts. The story and milestones come only from what they told you; never add details, reactions, feelings or dialogue they did not give you. If they told you little, keep it short and true. Resolve relative dates ("last December") against TODAY. Milestones are the moments before the wedding; do not add the wedding itself. Never invent parking, shuttles, prices, road numbers or room blocks: leave a field empty and add it to toConfirm instead.
Dress code: suggest one that suits the venue, season and design, and add "dress code" to toConfirm if they did not state one.
Headlines: short, in the couple's voice, true for THEIR venue and season. eyebrow: 2-5 words above their names. countdown: the words after the number of days, under 6 words. day: the schedule section. rsvp: the RSVP section. thanks: shown the morning after the wedding. party: the wedding party section (the people standing up with them). stay: the where-to-stay section.
Design: look at their photos if there are any and pick the design whose mood and colors suit them, the venue and the season.
Hotels: pick up to four from NEARBY HOTELS by index (best mix of rating and distance), with a short honest note each; none if the list is empty.`;

  async function draftSite(env, who, coup, answers) {
    if (!env.ANTHROPIC_API_KEY) throw new Error("June's brain is not configured.");
    const g = await gather(who, coup);
    const A = answers || {};
    const facts = [
      `TODAY: ${new Date().toISOString().slice(0, 10)}`,
      `NAMES: ${g.names || "unknown"}`,
      `DATE: ${g.dateIso || "not set"}`,
      `VENUE: ${[g.venueName, g.venueAddress].filter(Boolean).join(", ") || "not set"}`,
      `CITY: ${g.metro ? g.metro.display : str(g.c.metroId) || "unknown"}`,
      `GUESTS EXPECTED: ${g.c.guestEstimate || "unknown"}`,
      `EVENTS THAT WEEKEND: ${g.events.map((e) => [e.name, e.dateIso, e.venueName].filter(Boolean).join(" ")).join(" | ") || "just the wedding"}`,
      `ALREADY ON THEIR SITE: story=${str(g.w.story) ? "yes" : "no"}, dress code=${str(g.w.dressCode) || "none"}, hotel block=${str(g.w.hotelBlock) || "none"}, parking=${str(g.w.parking) || "none"}, transport=${str(g.w.transport) || "none"}`,
      `TYPICAL WEATHER THAT WEEK: ${g.wx ? `highs around ${g.wx.hi}F, lows around ${g.wx.lo}F, rain on about ${g.wx.wetShare}% of days (last three years)` : "no data"}`,
      `NEARBY HOTELS: ${(g.stay.hotels || []).map((h, i) => `[${i}] ${h.name} (${[h.kind, h.rating ? h.rating + " stars" : "", h.price, h.miles != null ? h.miles + " mi" : ""].filter(Boolean).join(", ")})`).join(" | ") || "none found"}`,
      `NEAREST AIRPORTS: ${(g.stay.airports || []).map((a) => `${a.code || ""} ${a.name}, ${a.miles} mi, about ${a.drive} min by car`).join(" | ") || "unknown"}`,
      `DESIGNS: ${Object.entries(DESIGNS).map(([k, v]) => `${k}: ${v}`).join(" | ")}`,
    ];
    const told = [
      `How we met: ${clip(A.met, 1200) || "(not given)"}`,
      `The proposal: ${clip(A.proposal, 1200) || "(not given)"}`,
      `Milestones or dates that matter: ${clip(A.moments, 1200) || "(not given)"}`,
      `The feel we want: ${clip(A.vibe, 400) || "(not given)"}`,
      `Anything guests should know: ${clip(A.notes, 1500) || "(not given)"}`,
    ];
    const content = [];
    for (const u of g.photos) content.push({ type: "image", source: { type: "url", url: `https://wsrv.nl/?url=${encodeURIComponent(u)}&w=800&q=70&output=jpg` } });
    content.push({ type: "text", text: `WHAT LAZO KNOWS:\n${facts.join("\n")}\n\nWHAT THEY TOLD JUNE:\n${told.join("\n")}\n\n${g.photos.length ? "The images above are their own photos." : "They have not added photos yet; pick the design from the venue, season and feel."}\nDraft the site.` });
    const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
    const req = { model: env.CHAT_MODEL || "claude-sonnet-5-5", max_tokens: 3000, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "medium" },
      system: RULES, messages: [{ role: "user", content }] };
    req.output_config.format = { type: "json_schema", schema: SCHEMA };
    let r;
    try { r = await client.beta.messages.create(req); }
    catch (e) { // a photo the model could not fetch should not sink the draft
      if (!g.photos.length) throw e;
      req.messages = [{ role: "user", content: content.filter((b) => b.type === "text") }];
      r = await client.beta.messages.create(req);
    }
    let out = null;
    try { out = JSON.parse(r.content.filter((b) => b.type === "text").map((b) => b.text).join("")); } catch (e) { out = null; }
    if (!out) throw new Error("June couldn't finish the draft. Try again in a moment.");
    const tag = (s) => str(s).replace(/^#+/, "").replace(/[^A-Za-z0-9_]/g, "").slice(0, 40);
    const hotels = (out.hotelPicks || []).map((p) => ({ p, h: (g.stay.hotels || [])[p.index] })).filter((x) => x.h)
      .map(({ p, h }) => ({ name: h.name, address: str(h.address), url: httpsUrl(h.url), code: "", deadline: "", rate: "", phone: "", note: clip(p.note, 200), block: false }));
    const airports = (g.stay.airports || []).slice(0, 2).map((a) => ({ code: str(a.code), name: str(a.name), miles: a.miles != null ? Math.round(a.miles) : null, note: a.drive ? `About ${a.drive >= 90 ? Math.round(a.drive / 30) / 2 + " hours" : a.drive + " minutes"} by car` : "" }));
    const travel = [str(g.w.travelNotes), clip(out.weatherNote, 400)].filter(Boolean).join(" ");
    const draft = {
      story: clip(out.story, 1500),
      milestones: (out.milestones || []).slice(0, 6).map((m) => ({ when: clip(m.when, 40), title: clip(m.title, 100), text: clip(m.text, 500), photo: "" })),
      hashtag: tag((out.hashtags || [])[0]),
      dressCode: clip(out.dressCode, 200), parking: clip(out.parking, 300), transport: clip(out.transport, 300),
      travelNotes: clip(travel, 600), drivingNotes: clip(out.drivingNotes, 800),
      headlines: Object.fromEntries(Object.entries(out.headlines || {}).map(([k, v]) => [k, clip(v, 140)]).filter(([, v]) => v)),
      template: DESIGNS[out.design] ? out.design : "",
      hotels, airports,
    };
    const meta = { hashtags: (out.hashtags || []).map(tag).filter(Boolean), designWhy: clip(out.designWhy, 240), toConfirm: (out.toConfirm || []).map((x) => clip(x, 160)).slice(0, 6),
      summary: clip(out.summary, 300), slug: g.site ? g.site.id : null, weather: g.wx, photosSeen: g.photos.length };
    return { draft, meta };
  }

  // The confirm card's write. Only fields the couple left empty are filled; their own words stay.
  async function applyDraft(who, coup, draft) {
    const token = who.token, cid = coup.coupleId;
    const sites = await fsQuery(token, { collection: "weddingSites", where: [["coupleUid", "EQUAL", cid]], limit: 1 }).catch(() => []);
    const site = sites[0] || null;
    const empty = (v) => v == null || v === "" || (Array.isArray(v) && !v.length) || (typeof v === "object" && !Array.isArray(v) && !Object.keys(v).length);
    const KEYS = ["story", "milestones", "hashtag", "dressCode", "parking", "transport", "travelNotes", "drivingNotes", "headlines", "hotels", "airports", "template"];
    if (site) {
      const obj = {};
      for (const k of KEYS) if (!empty(draft[k]) && empty(site[k])) obj[k] = draft[k];
      if (!Object.keys(obj).length) return "Your site already has all of that; nothing was changed.";
      obj.updatedAt = new Date();
      await fsPatch(token, `weddingSites/${encodeURIComponent(site.id)}`, obj);
      return `Added to your site: ${Object.keys(obj).filter((k) => k !== "updatedAt").join(", ")}. Open Website to read it over.`;
    }
    const c = (await fsGet(token, `couples/${encodeURIComponent(cid)}`).catch(() => null)) || {};
    const prev = c.siteDraft && typeof c.siteDraft === "object" ? c.siteDraft : {};
    const next = { ...prev };
    for (const k of KEYS) if (!empty(draft[k]) && empty(prev[k])) next[k] = draft[k];
    await fsPatch(token, `couples/${encodeURIComponent(cid)}`, { siteDraft: next });
    return "Your website draft is ready. Open Website, read it over, and publish when you like it.";
  }

  const TOOL = { name: "draft_site", description: "Draft the couple's wedding website (story, milestones, hashtag, FAQ, travel, headlines, a design to suit their photos, nearby hotels) from what they told you. Ask them first, conversationally, how they met, about the proposal, and the feel they want; then call this. It queues a confirm card; nothing changes until they confirm.",
    input_schema: { type: "object", additionalProperties: false, required: ["met"], properties: { met: { type: "string" }, proposal: { type: "string" }, moments: { type: "string" }, vibe: { type: "string" }, notes: { type: "string" } } } };

  return { draftSite, applyDraft, TOOL, DESIGNS };
}
