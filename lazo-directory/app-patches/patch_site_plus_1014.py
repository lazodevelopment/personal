r"""patch_site_plus_1014.py - JC-LAZO-WWS-1014-PLUS (Couple v154 -> v155)
The website editor gets everything the site can now show:
  - Build it with June: five questions, June drafts the story, milestones,
    hashtag, FAQ, typical weather, driving notes, headlines, hotels and a
    design picked from their photos; only empty fields are filled.
  - OUR STORY IN DATES: milestones with a date, a line and a photo.
  - WHERE TO STAY: hotel cards (Book link, room-block code, book-by, rate,
    phone), "Suggest from the venue", and the auto-suggest switch.
  - GETTING THERE: airports and driving notes.
  - THE WEDDING PARTY: names, roles, sides, photos, the two side labels.
  - HASHTAG & HEADLINES: the hashtag with ideas, and the section headlines.
  - The gallery holds 24 photos (was 6); the site shows the first frames and
    "See all" opens the rest.

  python app-patches\patch_site_plus_1014.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "Couple_master_v154.txt"
DST = HERE / "Couple_master_v155.txt"
s = SRC.read_text(encoding="utf-8")


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"anchor found {n}x (want {count}): {old[:80]!r}")
    s = s.replace(old, new)


# ---------------------------------------------------------------- 1. state
rep(r"""    final List<Map<String, dynamic>> events = <Map<String, dynamic>>[
      for (final dynamic e in (w['events'] as List?) ?? const <dynamic>[])
        if (e is Map) Map<String, dynamic>.from(e)
    ];
""", r"""    final List<Map<String, dynamic>> events = <Map<String, dynamic>>[
      for (final dynamic e in (w['events'] as List?) ?? const <dynamic>[])
        if (e is Map) Map<String, dynamic>.from(e)
    ];
    // v155: the wedding party, where to stay, getting there, the story in
    // dates, the hashtag and the headlines (JC-LAZO-WWS-1014-PLUS)
    List<Map<String, dynamic>> plusMaps(dynamic v) => <Map<String, dynamic>>[
          for (final dynamic e in (v is List) ? v : const <dynamic>[])
            if (e is Map) Map<String, dynamic>.from(e)
        ];
    final List<Map<String, dynamic>> party = plusMaps(w['weddingParty']);
    final List<Map<String, dynamic>> hotels = plusMaps(w['hotels']);
    final List<Map<String, dynamic>> airports = plusMaps(w['airports']);
    final List<Map<String, dynamic>> milestones = plusMaps(w['milestones']);
    final List<String> sides0 = ((w['partySides'] is List)
            ? (w['partySides'] as List)
            : const <dynamic>[])
        .map((dynamic e) => e.toString())
        .toList();
    final TextEditingController sideAC =
        TextEditingController(text: sides0.isNotEmpty ? sides0[0] : '');
    final TextEditingController sideBC =
        TextEditingController(text: sides0.length > 1 ? sides0[1] : '');
    final TextEditingController tagC =
        TextEditingController(text: (w['hashtag'] ?? '').toString());
    final TextEditingController driveC =
        TextEditingController(text: (w['drivingNotes'] ?? '').toString());
    bool stayAuto = w['stayAuto'] != false;
    final Map<String, dynamic> hl0 = w['headlines'] is Map
        ? Map<String, dynamic>.from(w['headlines'] as Map)
        : <String, dynamic>{};
    final Map<String, TextEditingController> hlC =
        <String, TextEditingController>{
      for (final String k in _kPlusHeadlines.keys)
        k: TextEditingController(text: (hl0[k] ?? '').toString())
    };
    List<String> tagIdeas = <String>[];
""")

# ---------------------------------------------------------------- 2. June at the top of the editor
rep(r"""                  const SizedBox(height: 6),
                  _wbJumpBar(setD),
                  const SizedBox(height: 4),
                  Flexible(
                    child: SingleChildScrollView(
                      child: Builder(builder: (BuildContext ctx3) {
                        final bool wideD =""", r"""                  const SizedBox(height: 6),
                  _wbJumpBar(setD),
                  const SizedBox(height: 8),
                  // v155: June drafts the site from five questions
                  _juneSiteBanner(onTap: () async {
                    final Map<String, dynamic>? res =
                        await _juneSiteDraft(ctx2);
                    if (res == null) {
                      return;
                    }
                    final Map<String, dynamic> d = res['draft'] is Map
                        ? Map<String, dynamic>.from(res['draft'] as Map)
                        : <String, dynamic>{};
                    final Map<String, dynamic> meta = res['meta'] is Map
                        ? Map<String, dynamic>.from(res['meta'] as Map)
                        : <String, dynamic>{};
                    final List<String> filled = <String>[];
                    void fill(TextEditingController c, String k, String label) {
                      final String v = (d[k] ?? '').toString().trim();
                      if (v.isNotEmpty && c.text.trim().isEmpty) {
                        c.text = v;
                        filled.add(label);
                      }
                    }
                    void fillList(List<Map<String, dynamic>> into, String k,
                        String label) {
                      final List<Map<String, dynamic>> v = plusMaps(d[k]);
                      if (v.isNotEmpty && into.isEmpty) {
                        into.addAll(v);
                        filled.add(label);
                      }
                    }
                    setD(() {
                      fill(storyC, 'story', 'your story');
                      fillList(milestones, 'milestones', 'milestones');
                      fill(tagC, 'hashtag', 'a hashtag');
                      fill(dressC, 'dressCode', 'dress code');
                      fill(parkC, 'parking', 'parking');
                      fill(transC, 'transport', 'getting there');
                      fill(notesC, 'travelNotes', 'the weather that week');
                      fill(driveC, 'drivingNotes', 'driving notes');
                      fillList(hotels, 'hotels', 'hotels near the venue');
                      fillList(airports, 'airports', 'airports');
                      final Map<String, dynamic> h = d['headlines'] is Map
                          ? Map<String, dynamic>.from(d['headlines'] as Map)
                          : <String, dynamic>{};
                      bool anyH = false;
                      h.forEach((String k, dynamic v) {
                        final TextEditingController? c = hlC[k];
                        if (c != null && c.text.trim().isEmpty &&
                            v.toString().trim().isNotEmpty) {
                          c.text = v.toString().trim();
                          anyH = true;
                        }
                      });
                      if (anyH) {
                        filled.add('headlines');
                      }
                      tagIdeas = ((meta['hashtags'] is List)
                              ? (meta['hashtags'] as List)
                              : const <dynamic>[])
                          .map((dynamic e) => e.toString())
                          .where((String e) => e.isNotEmpty)
                          .toList();
                    });
                    final String tpl = (d['template'] ?? '').toString();
                    final bool useTpl = await _juneSiteResult(
                        ctx2, filled, meta, tpl, template);
                    if (useTpl && tpl.isNotEmpty) {
                      setD(() => template = tpl);
                    }
                  }),
                  const SizedBox(height: 4),
                  Flexible(
                    child: SingleChildScrollView(
                      child: Builder(builder: (BuildContext ctx3) {
                        final bool wideD =""")

# ---------------------------------------------------------------- 3. story in dates
rep(r"""                          _wbSection('YOUR STORY'),
                          TextField(
                              controller: storyC,
                              maxLines: 4,
                              style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                              decoration: _lightDeco('Your story')),
                          const SizedBox(height: 10),
""", r"""                          _wbSection('YOUR STORY'),
                          TextField(
                              controller: storyC,
                              maxLines: 4,
                              style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                              decoration: _lightDeco('Your story')),
                          const SizedBox(height: 10),
                          _wbSection('OUR STORY IN DATES'),
                          _plusHint(
                              'The moments that got you here — where you met, the first trip, the proposal. Each gets a date, a line and a photo if you like.'),
                          ..._plusList(
                            ctx: ctx2,
                            setD: setD,
                            items: milestones,
                            icon: Icons.auto_stories_outlined,
                            title: (Map<String, dynamic> m) =>
                                (m['title'] ?? '').toString(),
                            sub: (Map<String, dynamic> m) => <String>[
                              (m['when'] ?? '').toString(),
                              (m['text'] ?? '').toString(),
                            ].where((String x) => x.isNotEmpty).join(' · '),
                            photo: (Map<String, dynamic> m) =>
                                (m['photo'] ?? '').toString(),
                            edit: (Map<String, dynamic>? cur) => _plusEditor(
                                ctx2,
                                cur == null ? 'Add a moment' : 'Edit moment',
                                _kPlusMilestone,
                                cur,
                                slot: 'moment'),
                            addLabel: 'Add a moment',
                            max: 16,
                          ),
                          const SizedBox(height: 10),
""")

# ---------------------------------------------------------------- 4. where to stay, getting there
rep(r"""                          TextField(
                              controller: notesC,
                              maxLines: 2,
                              style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                              decoration: _lightDeco('Travel notes')),
                          const SizedBox(height: 10),
""", r"""                          TextField(
                              controller: notesC,
                              maxLines: 2,
                              style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                              decoration: _lightDeco('Travel notes')),
                          const SizedBox(height: 10),
                          _wbSection('WHERE TO STAY'),
                          _plusHint(
                              'Each hotel gets a card with a Book button. Add your room-block code and guests can copy it in one tap.'),
                          ..._plusList(
                            ctx: ctx2,
                            setD: setD,
                            items: hotels,
                            icon: Icons.hotel_outlined,
                            title: (Map<String, dynamic> m) =>
                                (m['name'] ?? '').toString(),
                            sub: (Map<String, dynamic> m) => <String>[
                              if ((m['code'] ?? '').toString().isNotEmpty)
                                'Code ${m['code']}',
                              (m['deadline'] ?? '').toString().isEmpty
                                  ? ''
                                  : 'book by ${m['deadline']}',
                              (m['rate'] ?? '').toString(),
                              (m['note'] ?? '').toString(),
                            ].where((String x) => x.isNotEmpty).join(' · '),
                            edit: (Map<String, dynamic>? cur) => _plusEditor(
                                ctx2,
                                cur == null ? 'Add a hotel' : 'Edit hotel',
                                _kPlusHotel,
                                cur),
                            addLabel: 'Add a hotel',
                            max: 8,
                            extra: OutlinedButton.icon(
                              style: OutlinedButton.styleFrom(
                                  foregroundColor: _lzFg(plum),
                                  side: BorderSide(color: gold.withOpacity(.8))),
                              onPressed: _h(() async {
                                final Map<String, dynamic>? st =
                                    await _staySuggest(doc?.id ?? '');
                                if (st == null) {
                                  return;
                                }
                                int addedH = 0, addedA = 0;
                                setD(() {
                                  for (final Map<String, dynamic> h
                                      in plusMaps(st['hotels'])) {
                                    if (hotels.length >= 8 ||
                                        hotels.any((Map<String, dynamic> x) =>
                                            x['name'] == h['name'])) {
                                      continue;
                                    }
                                    final List<String> bits = <String>[
                                      if (h['rating'] is num)
                                        '★ ${(h['rating'] as num).toStringAsFixed(1)}',
                                      if (h['miles'] is num)
                                        '${h['miles']} mi from the venue',
                                    ];
                                    hotels.add(<String, dynamic>{
                                      'name': (h['name'] ?? '').toString(),
                                      'address': (h['address'] ?? '').toString(),
                                      'url': (h['url'] ?? '').toString(),
                                      'code': '',
                                      'deadline': '',
                                      'rate': '',
                                      'phone': '',
                                      'note': bits.join(' · '),
                                      'block': false,
                                    });
                                    addedH++;
                                  }
                                  if (airports.isEmpty) {
                                    for (final Map<String, dynamic> a
                                        in plusMaps(st['airports']).take(3)) {
                                      final num dr = (a['drive'] is num)
                                          ? a['drive'] as num
                                          : 0;
                                      airports.add(<String, dynamic>{
                                        'code': (a['code'] ?? '').toString(),
                                        'name': (a['name'] ?? '').toString(),
                                        'miles': a['miles'],
                                        'note': dr > 0
                                            ? 'About ${dr >= 90 ? '${(dr / 60).toStringAsFixed(1)} hours' : '$dr minutes'} by car'
                                            : '',
                                      });
                                      addedA++;
                                    }
                                  }
                                });
                                _toastC(addedH + addedA == 0
                                    ? 'Nothing new near the venue yet.'
                                    : 'Added ${addedH > 0 ? '$addedH hotel${addedH == 1 ? '' : 's'}' : ''}${addedH > 0 && addedA > 0 ? ' and ' : ''}${addedA > 0 ? '$addedA airport${addedA == 1 ? '' : 's'}' : ''} — add your block code if you have one.');
                              }),
                              icon: const Icon(Icons.travel_explore_rounded,
                                  size: 16),
                              label: const Text('Suggest from the venue'),
                            ),
                          ),
                          SwitchListTile(
                            dense: true,
                            contentPadding: EdgeInsets.zero,
                            activeColor: Colors.white,
                            activeTrackColor: vGreen,
                            inactiveThumbColor: Colors.white,
                            inactiveTrackColor: muted.withOpacity(.4),
                            title: const Text(
                                'Until we add a hotel, show well-rated ones near the venue',
                                style: TextStyle(fontSize: 13.5)),
                            value: stayAuto,
                            onChanged:
                                _hb((bool v) => setD(() => stayAuto = v)),
                          ),
                          _wbSection('GETTING THERE'),
                          ..._plusList(
                            ctx: ctx2,
                            setD: setD,
                            items: airports,
                            icon: Icons.flight_land_rounded,
                            title: (Map<String, dynamic> m) => <String>[
                              (m['code'] ?? '').toString(),
                              (m['name'] ?? '').toString(),
                            ].where((String x) => x.isNotEmpty).join(' · '),
                            sub: (Map<String, dynamic> m) => <String>[
                              if (m['miles'] != null &&
                                  m['miles'].toString().isNotEmpty)
                                '${m['miles']} mi',
                              (m['note'] ?? '').toString(),
                            ].where((String x) => x.isNotEmpty).join(' · '),
                            edit: (Map<String, dynamic>? cur) => _plusEditor(
                                ctx2,
                                cur == null ? 'Add an airport' : 'Edit airport',
                                _kPlusAirport,
                                cur),
                            addLabel: 'Add an airport',
                            max: 4,
                          ),
                          const SizedBox(height: 8),
                          TextField(
                              controller: driveC,
                              maxLines: 3,
                              style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                              decoration: _lightDeco('Driving notes',
                                  hint:
                                      'From the airport, head north on… allow an hour on Friday evenings.')),
                          const SizedBox(height: 10),
""")

# ---------------------------------------------------------------- 5. the wedding party, hashtag, headlines
rep(r"""                          _wbSection('LIVE ON THE DAY'),""", r"""                          _wbSection('THE WEDDING PARTY'),
                          _plusHint(
                              'Names, roles and a photo. Put each person on a side and guests get a tab for each.'),
                          Row(children: <Widget>[
                            Expanded(
                                child: TextField(
                                    controller: sideAC,
                                    style:  TextStyle(
                                        color: _lzFg(ink), fontSize: 14),
                                    decoration: _lightDeco('First side',
                                        hint: name1C.text.trim().isEmpty
                                            ? 'Her side'
                                            : '${name1C.text.trim()}’s side'))),
                            const SizedBox(width: 8),
                            Expanded(
                                child: TextField(
                                    controller: sideBC,
                                    style:  TextStyle(
                                        color: _lzFg(ink), fontSize: 14),
                                    decoration: _lightDeco('Second side',
                                        hint: name2C.text.trim().isEmpty
                                            ? 'His side'
                                            : '${name2C.text.trim()}’s side'))),
                          ]),
                          const SizedBox(height: 8),
                          ..._plusList(
                            ctx: ctx2,
                            setD: setD,
                            items: party,
                            icon: Icons.groups_2_outlined,
                            title: (Map<String, dynamic> m) =>
                                (m['name'] ?? '').toString(),
                            sub: (Map<String, dynamic> m) => <String>[
                              (m['role'] ?? '').toString(),
                              m['side'] == 'a'
                                  ? (sideAC.text.trim().isNotEmpty
                                      ? sideAC.text.trim()
                                      : 'first side')
                                  : m['side'] == 'b'
                                      ? (sideBC.text.trim().isNotEmpty
                                          ? sideBC.text.trim()
                                          : 'second side')
                                      : '',
                            ].where((String x) => x.isNotEmpty).join(' · '),
                            photo: (Map<String, dynamic> m) =>
                                (m['photo'] ?? '').toString(),
                            edit: (Map<String, dynamic>? cur) => _plusEditor(
                                ctx2,
                                cur == null ? 'Add someone' : 'Edit',
                                _kPlusPerson,
                                cur,
                                slot: 'party',
                                sides: <String>[
                                  sideAC.text.trim().isNotEmpty
                                      ? sideAC.text.trim()
                                      : (name1C.text.trim().isEmpty
                                          ? 'First side'
                                          : '${name1C.text.trim()}’s side'),
                                  sideBC.text.trim().isNotEmpty
                                      ? sideBC.text.trim()
                                      : (name2C.text.trim().isEmpty
                                          ? 'Second side'
                                          : '${name2C.text.trim()}’s side'),
                                ]),
                            addLabel: 'Add someone',
                            max: 40,
                          ),
                          _wbSection('HASHTAG & HEADLINES'),
                          TextField(
                              controller: tagC,
                              style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                              decoration: _lightDeco('Wedding hashtag',
                                      hint: 'SarahSaysYes')
                                  .copyWith(prefixText: '#')),
                          const SizedBox(height: 6),
                          Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                            for (final String t in <String>{
                              ...tagIdeas,
                              ..._tagIdeasFor(name1C.text, name2C.text,
                                  (w['dateIso'] ?? '').toString()),
                            }.take(5))
                              _Press(
                                tick: _Tick.select,
                                onTap: () => setD(() => tagC.text = t),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 10, vertical: 6),
                                  decoration: BoxDecoration(
                                    color: _lzBg(const Color(0xFFF7F0E1)),
                                    borderRadius: BorderRadius.circular(99),
                                    border: Border.all(
                                        color: gold.withOpacity(.6)),
                                  ),
                                  child: Text('#$t',
                                      style: TextStyle(
                                          fontSize: 12,
                                          color: _lzFg(plum),
                                          fontWeight: FontWeight.w600)),
                                ),
                              ),
                          ]),
                          const SizedBox(height: 8),
                          Theme(
                            data: Theme.of(ctx2)
                                .copyWith(dividerColor: Colors.transparent),
                            child: ExpansionTile(
                              tilePadding: EdgeInsets.zero,
                              childrenPadding: EdgeInsets.zero,
                              iconColor: _lzFg(plum),
                              collapsedIconColor: _lzFg(muted),
                              title: Text('Section headlines (optional)',
                                  style: TextStyle(
                                      fontSize: 13.5,
                                      color: _lzFg(plum),
                                      fontWeight: FontWeight.w600)),
                              subtitle: Text(
                                  'Left blank, your site uses plain lines that fit any venue.',
                                  style: TextStyle(
                                      fontSize: 11, color: _lzFg(muted))),
                              children: <Widget>[
                                for (final MapEntry<String, String> e
                                    in _kPlusHeadlines.entries)
                                  Padding(
                                    padding: const EdgeInsets.only(bottom: 8),
                                    child: TextField(
                                        controller: hlC[e.key],
                                        style:  TextStyle(
                                            color: _lzFg(ink), fontSize: 14),
                                        decoration: _lightDeco(e.value)),
                                  ),
                              ],
                            ),
                          ),
                          _wbSection('LIVE ON THE DAY'),""")

# ---------------------------------------------------------------- 6. save
rep(r"""        'hotelAddress': hotelAddrC.text.trim(),
        'events': events,
""", r"""        'hotelAddress': hotelAddrC.text.trim(),
        'events': events,
        // v155 (JC-LAZO-WWS-1014-PLUS)
        'weddingParty': party,
        'partySides': <String>[sideAC.text.trim(), sideBC.text.trim()],
        'hotels': hotels,
        'stayAuto': stayAuto,
        'airports': airports,
        'drivingNotes': driveC.text.trim(),
        'milestones': milestones,
        'hashtag': tagC.text
            .trim()
            .replaceAll(RegExp(r'^#+'), '')
            .replaceAll(RegExp(r'[^A-Za-z0-9_]'), ''),
        'headlines': <String, dynamic>{
          for (final MapEntry<String, TextEditingController> e
              in hlC.entries)
            if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()
        },
""")

# ---------------------------------------------------------------- 7. gallery: 24 photos
rep(r"""        if (_siteGal.length >= 6) {
          break;
        }""", r"""        if (_siteGal.length >= 24) {
          break;
        }""")
rep("_wbSection('GALLERY " + chr(92) + "u00b7 ${_siteGal.length} OF 6'),", "_wbSection('GALLERY " + chr(92) + "u00b7 ${_siteGal.length} OF 24'),")
rep(r"""if (!_siteGalBusy && _siteGal.length < 6)""", r"""if (!_siteGalBusy && _siteGal.length < 24)""")

# ---------------------------------------------------------------- 8. helpers (before _wbSection)
rep(r"""  Widget _wbSection(String label) {
""", r"""  // ---------------- v155: the site's extra sections (JC-LAZO-WWS-1014-PLUS) ----------------
  static const Map<String, String> _kPlusHeadlines = <String, String>{
    'eyebrow': 'Line above your names',
    'countdown': 'After the day count (e.g. days until we say I do)',
    'day': 'The schedule',
    'rsvp': 'The RSVP',
    'party': 'The wedding party',
    'stay': 'Where to stay',
    'thanks': 'The morning after',
  };
  // [key, label, hint, kind]: kind text | multi | url | num | photo | side | bool
  static const List<List<String>> _kPlusMilestone = <List<String>>[
    <String>['when', 'When', 'June 2019', 'text'],
    <String>['title', 'What happened', 'The wrong number', 'text'],
    <String>['text', 'A line about it (optional)', '', 'multi'],
    <String>['photo', 'Photo', '', 'photo'],
  ];
  static const List<List<String>> _kPlusHotel = <List<String>>[
    <String>['name', 'Hotel', 'The Sedona Inn', 'text'],
    <String>['address', 'Address', '120 Main St, Sedona, AZ', 'text'],
    <String>['url', 'Booking link', 'https://…', 'url'],
    <String>['code', 'Room-block code (optional)', 'SARAHMIKE27', 'text'],
    <String>['deadline', 'Book by (optional)', 'May 1, 2027', 'text'],
    <String>['rate', 'Rate (optional)', '\$189 a night', 'text'],
    <String>['phone', 'Phone (optional)', '', 'text'],
    <String>['note', 'A line for guests (optional)', 'Shuttle to the venue from 3:30', 'multi'],
    <String>['block', 'We have a room block here', '', 'bool'],
  ];
  static const List<List<String>> _kPlusAirport = <List<String>>[
    <String>['name', 'Airport', 'Phoenix Sky Harbor', 'text'],
    <String>['code', 'Code (optional)', 'PHX', 'text'],
    <String>['miles', 'Miles to the venue (optional)', '115', 'num'],
    <String>['note', 'A line for guests (optional)', 'About 2 hours by car', 'text'],
  ];
  static const List<List<String>> _kPlusPerson = <List<String>>[
    <String>['name', 'Name', 'Jenna Cole', 'text'],
    <String>['role', 'Role', 'Maid of honor', 'text'],
    <String>['side', 'Side', '', 'side'],
    <String>['note', 'A line about them (optional)', 'Sister, and keeper of every story', 'multi'],
    <String>['photo', 'Photo', '', 'photo'],
  ];

  Widget _plusHint(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(t, style: TextStyle(fontSize: 11.5, color: _lzFg(muted))),
      );

  // A short list of cards with an editor per item, like the weekend's events.
  List<Widget> _plusList({
    required BuildContext ctx,
    required StateSetter setD,
    required List<Map<String, dynamic>> items,
    required IconData icon,
    required String Function(Map<String, dynamic>) title,
    required String Function(Map<String, dynamic>) sub,
    required Future<Map<String, dynamic>?> Function(Map<String, dynamic>?) edit,
    required String addLabel,
    String Function(Map<String, dynamic>)? photo,
    int max = 12,
    Widget? extra,
  }) {
    return <Widget>[
      ...items.asMap().entries.map((MapEntry<int, Map<String, dynamic>> en) {
        final String ph = photo == null ? '' : photo(en.value);
        final String st = sub(en.value);
        return Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: _Press(
            tick: _Tick.select,
            onTap: () async {
              final Map<String, dynamic>? r = await edit(en.value);
              if (r == null) {
                return;
              }
              setD(() {
                if (r['_delete'] == true) {
                  items.removeAt(en.key);
                } else {
                  items[en.key] = r;
                }
              });
            },
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: _lzBg(Colors.white),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: gold.withOpacity(.5)),
              ),
              child: Row(children: <Widget>[
                if (ph.isNotEmpty)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: Image.network(ph,
                        width: 34,
                        height: 34,
                        fit: BoxFit.cover,
                        errorBuilder: (BuildContext c, Object e,
                                StackTrace? s) =>
                            Icon(icon, color: _lzFg(plum), size: 18)),
                  )
                else
                  Icon(icon, color: _lzFg(plum), size: 18),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(title(en.value),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                                color: _lzFg(plum),
                                fontSize: 13.5,
                                fontWeight: FontWeight.w700)),
                        if (st.isNotEmpty)
                          Text(st,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style:
                                  TextStyle(fontSize: 11, color: _lzFg(muted))),
                      ]),
                ),
                Icon(Icons.edit_outlined, color: _lzFg(muted), size: 16),
              ]),
            ),
          ),
        );
      }),
      Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
        if (items.length < max)
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
                foregroundColor: _lzFg(plum),
                side: BorderSide(color: gold.withOpacity(.8))),
            onPressed: _h(() async {
              final Map<String, dynamic>? r = await edit(null);
              if (r != null && r['_delete'] != true) {
                setD(() => items.add(r));
              }
            }),
            icon: const Icon(Icons.add_rounded, size: 16),
            label: Text(addLabel),
          ),
        if (extra != null) extra,
      ]),
    ];
  }

  // One item. Returns the map, {'_delete': true}, or null when cancelled.
  Future<Map<String, dynamic>?> _plusEditor(BuildContext ctx, String title,
      List<List<String>> fields, Map<String, dynamic>? cur,
      {String slot = 'item', List<String> sides = const <String>[]}) async {
    final Map<String, dynamic> c = cur ?? <String, dynamic>{};
    final Map<String, TextEditingController> tc =
        <String, TextEditingController>{
      for (final List<String> f in fields)
        if (<String>['text', 'multi', 'url', 'num'].contains(f[3]))
          f[0]: TextEditingController(
              text: c[f[0]] == null ? '' : c[f[0]].toString())
    };
    String photoUrl = (c['photo'] ?? '').toString();
    String side = (c['side'] ?? '').toString();
    final Map<String, bool> flags = <String, bool>{
      for (final List<String> f in fields)
        if (f[3] == 'bool') f[0]: cur == null ? true : c[f[0]] != false
    };
    bool busy = false;
    final String? act = await showDialog<String>(
      context: ctx,
      builder: (BuildContext dc) => StatefulBuilder(
        builder: (BuildContext dc2, StateSetter setE) => AlertDialog(
          backgroundColor: _lzBg(ivory),
          title: Text(title, style: TextStyle(color: _lzFg(plum))),
          content: SizedBox(
            width: 420,
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
                for (final List<String> f in fields) ...<Widget>[
                  if (tc.containsKey(f[0]))
                    TextField(
                        controller: tc[f[0]],
                        maxLines: f[3] == 'multi' ? 3 : 1,
                        keyboardType: f[3] == 'num'
                            ? TextInputType.number
                            : f[3] == 'url'
                                ? TextInputType.url
                                : TextInputType.text,
                        textCapitalization: f[3] == 'url' || f[3] == 'num'
                            ? TextCapitalization.none
                            : TextCapitalization.sentences,
                        style: TextStyle(color: _lzFg(ink), fontSize: 14),
                        decoration: _lightDeco(f[1],
                            hint: f[2].isEmpty ? null : f[2])),
                  if (f[3] == 'side')
                    Align(
                      alignment: Alignment.centerLeft,
                      child: Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                        for (final List<String> o in <List<String>>[
                          <String>['a', sides.isNotEmpty ? sides[0] : 'First side'],
                          <String>['b', sides.length > 1 ? sides[1] : 'Second side'],
                          <String>['', 'Both / neither'],
                        ])
                          ChoiceChip(
                            label: Text(o[1]),
                            selected: side == o[0],
                            selectedColor: gold.withOpacity(.45),
                            backgroundColor: _lzBg(Colors.white),
                            labelStyle:
                                TextStyle(color: _lzFg(plum), fontSize: 12.5),
                            onSelected: (bool v) => setE(() => side = o[0]),
                          ),
                      ]),
                    ),
                  if (f[3] == 'photo')
                    Row(children: <Widget>[
                      if (photoUrl.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(right: 10),
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(10),
                            child: Image.network(photoUrl,
                                width: 56, height: 56, fit: BoxFit.cover),
                          ),
                        ),
                      TextButton.icon(
                        onPressed: busy
                            ? null
                            : () async {
                                setE(() => busy = true);
                                final String? u = await _uploadSlotPhoto(slot);
                                setE(() {
                                  busy = false;
                                  if (u != null) {
                                    photoUrl = u;
                                  }
                                });
                              },
                        icon: busy
                            ? const SizedBox(
                                width: 14,
                                height: 14,
                                child: CircularProgressIndicator(strokeWidth: 2))
                            : Icon(Icons.add_a_photo_outlined,
                                size: 16, color: _lzFg(plum)),
                        label: Text(
                            photoUrl.isEmpty ? 'Add a photo' : 'Change photo',
                            style: TextStyle(color: _lzFg(plum))),
                      ),
                      if (photoUrl.isNotEmpty)
                        TextButton(
                            onPressed: () => setE(() => photoUrl = ''),
                            child: const Text('Remove',
                                style: TextStyle(color: Color(0xFF8A7D90)))),
                    ]),
                  if (f[3] == 'bool')
                    SwitchListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      activeColor: Colors.white,
                      activeTrackColor: vGreen,
                      inactiveThumbColor: Colors.white,
                      inactiveTrackColor: muted.withOpacity(.4),
                      title: Text(f[1], style: const TextStyle(fontSize: 13.5)),
                      value: flags[f[0]] ?? true,
                      onChanged: (bool v) => setE(() => flags[f[0]] = v),
                    ),
                  const SizedBox(height: 10),
                ],
              ]),
            ),
          ),
          actions: <Widget>[
            if (cur != null)
              TextButton(
                  onPressed: _h(() => Navigator.pop(dc2, 'delete')),
                  child: const Text('Remove',
                      style: TextStyle(color: Color(0xFF8A7D90)))),
            TextButton(
                onPressed: _h(() => Navigator.pop(dc2, null)),
                child: Text('Cancel', style: TextStyle(color: _lzFg(ink)))),
            FilledButton(
                style: FilledButton.styleFrom(
                    backgroundColor: gold, foregroundColor: plum),
                onPressed: busy ? null : _h(() => Navigator.pop(dc2, 'save')),
                child: const Text('Save')),
          ],
        ),
      ),
    );
    if (act == 'delete') {
      return <String, dynamic>{'_delete': true};
    }
    final String first = tc[fields.first[0]]?.text.trim() ?? '';
    if (act != 'save' || first.isEmpty) {
      return null;
    }
    final Map<String, dynamic> out = <String, dynamic>{};
    for (final List<String> f in fields) {
      switch (f[3]) {
        case 'photo':
          out[f[0]] = photoUrl;
          break;
        case 'side':
          out[f[0]] = side;
          break;
        case 'bool':
          out[f[0]] = flags[f[0]] ?? true;
          break;
        case 'num':
          final String t = tc[f[0]]!.text.trim();
          out[f[0]] = t.isEmpty ? null : num.tryParse(t.replaceAll(',', ''));
          break;
        case 'url':
          String u = tc[f[0]]!.text.trim();
          if (u.isNotEmpty && !u.startsWith('http')) {
            u = 'https://$u';
          }
          out[f[0]] = u.startsWith('https://') ? u : '';
          break;
        default:
          out[f[0]] = tc[f[0]]!.text.trim();
      }
    }
    return out;
  }

  // Hashtag ideas from their names and year: easy to spell, no symbols.
  List<String> _tagIdeasFor(String a, String b, String iso) {
    String w(String s) => s
        .trim()
        .split(RegExp(r'\s+'))
        .first
        .replaceAll(RegExp(r'[^A-Za-z0-9]'), '');
    final String x = w(a), y = w(b);
    if (x.isEmpty || y.isEmpty) {
      return <String>[];
    }
    final String yy = iso.length >= 4 ? iso.substring(0, 4) : '';
    return <String>[
      '${x}And$y',
      if (yy.isNotEmpty) '$x$y$yy',
      '${y}Says${x}Yes',
    ];
  }

  // Hotels and airports near the venue (meetlazo.com/api/stay).
  Future<Map<String, dynamic>?> _staySuggest(String slug) async {
    if (slug.isEmpty) {
      _toastC('Publish your site once, then Lazo can look up hotels near the venue.');
      return null;
    }
    try {
      _toastC('Looking near the venue…');
      final httpc.Response r = await httpc
          .get(Uri.parse(
              'https://meetlazo.com/api/stay?slug=${Uri.encodeComponent(slug)}'))
          .timeout(const Duration(seconds: 20));
      final dynamic j = jsonDecode(r.body);
      return j is Map ? Map<String, dynamic>.from(j) : null;
    } catch (_) {
      _toastC('Couldn’t reach the hotel lookup — try again.');
      return null;
    }
  }

  Widget _juneSiteBanner({required Future<void> Function() onTap}) {
    return _Press(
      tick: _Tick.light,
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.fromLTRB(14, 10, 12, 10),
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: <Color>[
            _lzBg(const Color(0xFF3D1C3B)),
            _lzBg(const Color(0xFF5A2D57)),
          ]),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: gold.withOpacity(.7)),
        ),
        child: Row(children: <Widget>[
          const Icon(Icons.auto_awesome_rounded,
              color: Color(0xFFD9B77C), size: 20),
          const SizedBox(width: 10),
          const Expanded(
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Build it with June',
                      style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w700,
                          fontSize: 14)),
                  Text(
                      'Answer five questions. June writes your story, FAQ and travel, and picks a design for your photos.',
                      style: TextStyle(color: Color(0xFFE6D6B8), fontSize: 11.5)),
                ]),
          ),
          const Icon(Icons.arrow_forward_rounded,
              color: Color(0xFFD9B77C), size: 18),
        ]),
      ),
    );
  }

  // Five questions, then June drafts. Returns {draft, meta} or null.
  Future<Map<String, dynamic>?> _juneSiteDraft(BuildContext ctx) async {
    final List<List<String>> qs = <List<String>>[
      <String>['met', 'How did you meet?', 'Where, when, who said what first'],
      <String>['proposal', 'The proposal', 'Where and how it happened'],
      <String>['moments', 'Dates that matter (optional)', 'First trip, moving in, the dog'],
      <String>['vibe', 'The feel you want', 'Garden, candlelit, relaxed but dressy'],
      <String>['notes', 'Anything guests should know (optional)', 'Outdoor ceremony, kids welcome, parking'],
    ];
    final Map<String, TextEditingController> c = <String, TextEditingController>{
      for (final List<String> q in qs) q[0]: TextEditingController()
    };
    final bool? go = await showDialog<bool>(
      context: ctx,
      builder: (BuildContext dc) => AlertDialog(
        backgroundColor: _lzBg(ivory),
        title: Text('Build it with June', style: TextStyle(color: _lzFg(plum))),
        content: SizedBox(
          width: 440,
          child: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
              Text(
                  'A few lines each is plenty. June only writes what you tell her and fills the fields you have left empty.',
                  style: TextStyle(fontSize: 12, color: _lzFg(muted))),
              const SizedBox(height: 12),
              for (final List<String> q in qs) ...<Widget>[
                TextField(
                    controller: c[q[0]],
                    maxLines: q[0] == 'vibe' ? 1 : 3,
                    minLines: 1,
                    textCapitalization: TextCapitalization.sentences,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco(q[1], hint: q[2])),
                const SizedBox(height: 10),
              ],
            ]),
          ),
        ),
        actions: <Widget>[
          TextButton(
              onPressed: _h(() => Navigator.pop(dc, false)),
              child: Text('Cancel', style: TextStyle(color: _lzFg(ink)))),
          FilledButton(
              style: FilledButton.styleFrom(
                  backgroundColor: gold, foregroundColor: plum),
              onPressed: _h(() => Navigator.pop(dc, true)),
              child: const Text('Write it')),
        ],
      ),
    );
    if (go != true) {
      return null;
    }
    if (c['met']!.text.trim().isEmpty && c['proposal']!.text.trim().isEmpty) {
      _toastC('Tell June a little about how you met first.');
      return null;
    }
    bool open = true;
    // ignore: unawaited_futures
    showDialog<void>(
      context: ctx,
      barrierDismissible: false,
      builder: (BuildContext dc) => AlertDialog(
        backgroundColor: _lzBg(ivory),
        content: Row(children: <Widget>[
          const SizedBox(
              width: 22,
              height: 22,
              child: CircularProgressIndicator(strokeWidth: 2.4)),
          const SizedBox(width: 16),
          Expanded(
              child: Text(
                  'June is writing your site… this takes about twenty seconds.',
                  style: TextStyle(color: _lzFg(ink), fontSize: 13.5))),
        ]),
      ),
    ).then((_) => open = false);
    void closeWait() {
      if (open) {
        open = false;
        Navigator.of(ctx, rootNavigator: true).pop();
      }
    }
    try {
      final String? t = await FirebaseAuth.instance.currentUser?.getIdToken();
      if (t == null) {
        closeWait();
        _toastC('Sign in again, then ask June.');
        return null;
      }
      final httpc.Response r = await httpc
          .post(Uri.parse('https://june.meetlazo.com/api/site/draft'),
              headers: <String, String>{
                'authorization': 'Bearer $t',
                'content-type': 'application/json',
              },
              body: jsonEncode(<String, dynamic>{
                'answers': <String, String>{
                  for (final MapEntry<String, TextEditingController> e
                      in c.entries)
                    e.key: e.value.text.trim()
                }
              }))
          .timeout(const Duration(seconds: 120));
      closeWait();
      final dynamic j = jsonDecode(r.body);
      if (r.statusCode != 200 || j is! Map || j['draft'] is! Map) {
        _toastC(j is Map && j['error'] != null
            ? 'June couldn’t finish: ${j['error'].toString().length > 80 ? j['error'].toString().substring(0, 80) : j['error']}'
            : 'June couldn’t finish the draft — try again in a moment.');
        return null;
      }
      return Map<String, dynamic>.from(j);
    } catch (_) {
      closeWait();
      _toastC('June couldn’t finish the draft — try again in a moment.');
      return null;
    }
  }

  // What June filled, what to check, and her design pick. true = use it.
  Future<bool> _juneSiteResult(BuildContext ctx, List<String> filled,
      Map<String, dynamic> meta, String tpl, String current) async {
    final List<String> checks = ((meta['toConfirm'] is List)
            ? (meta['toConfirm'] as List)
            : const <dynamic>[])
        .map((dynamic e) => e.toString())
        .toList();
    final String why = (meta['designWhy'] ?? '').toString();
    final bool offer = tpl.isNotEmpty && tpl != current;
    final String nice =
        tpl.isEmpty ? '' : tpl[0].toUpperCase() + tpl.substring(1);
    final bool? use = await showDialog<bool>(
      context: ctx,
      builder: (BuildContext dc) => AlertDialog(
        backgroundColor: _lzBg(ivory),
        title: Text(filled.isEmpty ? 'Nothing to fill' : 'June’s draft is in',
            style: TextStyle(color: _lzFg(plum))),
        content: SizedBox(
          width: 440,
          child: SingleChildScrollView(
            child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                      filled.isEmpty
                          ? 'Every field June writes already has your words, so she left them alone.'
                          : 'June filled ${filled.join(', ')}. Read it over before you publish — it’s your site.',
                      style: TextStyle(color: _lzFg(ink), fontSize: 13.5)),
                  if (checks.isNotEmpty) ...<Widget>[
                    const SizedBox(height: 12),
                    Text('WORTH CHECKING',
                        style: TextStyle(
                            fontSize: 10.5,
                            letterSpacing: 1.4,
                            color: _lzFg(muted),
                            fontWeight: FontWeight.w700)),
                    const SizedBox(height: 4),
                    for (final String x in checks)
                      Padding(
                        padding: const EdgeInsets.only(top: 3),
                        child: Text('• $x',
                            style: TextStyle(color: _lzFg(ink), fontSize: 13)),
                      ),
                  ],
                  if (offer) ...<Widget>[
                    const SizedBox(height: 12),
                    Text('June suggests the $nice design.',
                        style: TextStyle(
                            color: _lzFg(plum),
                            fontSize: 13.5,
                            fontWeight: FontWeight.w700)),
                    if (why.isNotEmpty)
                      Text(why,
                          style: TextStyle(color: _lzFg(muted), fontSize: 12.5)),
                  ],
                ]),
          ),
        ),
        actions: <Widget>[
          if (offer)
            TextButton(
                onPressed: _h(() => Navigator.pop(dc, false)),
                child: Text('Keep my design',
                    style: TextStyle(color: _lzFg(ink)))),
          FilledButton(
              style: FilledButton.styleFrom(
                  backgroundColor: gold, foregroundColor: plum),
              onPressed: _h(() => Navigator.pop(dc, offer)),
              child: Text(offer ? 'Use $nice' : 'Done')),
        ],
      ),
    );
    return use == true;
  }

  Widget _wbSection(String label) {
""")

DST.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {DST.name} ({len(s):,} chars)")
