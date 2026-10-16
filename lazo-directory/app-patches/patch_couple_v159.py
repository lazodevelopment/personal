r"""patch_couple_v159.py - Couple v158 -> v159: TOWNS + EVERY METRO.  JC-LAZO-PLACES-1015-COUPLE

The city list used to live only in this widget (45 metros, a dropdown). It now comes from the site -
https://meetlazo.com/assets/places.json, rebuilt every night by generate/build.py - so a new metro or town
shows up without a FlutterFlow paste; the old list stays as the offline fallback. "Where" becomes a search:
type a town or a city, and a town answers with its Lazo metro ("Worcester, MA - Boston area"); the couple's
town is kept on couples.town. Browse's metro dropdown is the same search.

    python app-patches\patch_couple_v159.py      # writes Couple_master_v159.txt
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC, DST = HERE / "Couple_master_v158.txt", HERE / "Couple_master_v159.txt"
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, f"expected {n} match(es), found {c}: {old[:90]!r}"
    s = s.replace(old, new)


# 0. build id
rep("// lazo_couple_dashboard.dart\n",
    "// lazo_couple_dashboard.dart\n"
    "// Build ID: JC-LAZO-PLACES-1015-COUPLE (v159: TOWNS + EVERY METRO - the city list loads from "
    "meetlazo.com/assets/places.json (every live metro + every town with vendors, rebuilt nightly; the old 45 stay as "
    "the offline fallback); 'Where' in setup and Browse's city are one search - type a town or a city, a town answers "
    "with its metro and is kept on couples.town; base v158)\n")

# 1. the lists become loadable
rep("  static const List<Map<String, String>> kMetros = [\n",
    "  static List<Map<String, String>> kMetros = <Map<String, String>>[\n")
rep("  static const Map<String, List<double>> kMetroLatLng = <String, List<double>>{\n",
    "  static Map<String, List<double>> kMetroLatLng = <String, List<double>>{\n")

# 2. loader + picker, right after the metro list
rep("""    {'id': 'tucson', 'label': 'Tucson'},
  ];
""", r"""    {'id': 'tucson', 'label': 'Tucson'},
  ];

  // v159: TOWNS + EVERY METRO. The list above is the offline fallback; the real one is the site's, rebuilt every
  // night, so a new metro or town shows up here without a FlutterFlow paste.
  static List<Map<String, String>> kTowns = <Map<String, String>>[];
  static bool _placesLoaded = false;
  static Future<void>? _placesLoading;

  static Future<void> _loadPlaces() {
    if (_placesLoaded) return Future<void>.value();
    return _placesLoading ??= _fetchPlaces();
  }

  static Future<void> _fetchPlaces() async {
    try {
      final httpc.Response r = await httpc
          .get(Uri.parse('https://meetlazo.com/assets/places.json'))
          .timeout(const Duration(seconds: 12));
      if (r.statusCode != 200) return;
      final dynamic j = jsonDecode(utf8.decode(r.bodyBytes));
      if (j is! Map) return;
      final List<Map<String, String>> ms = <Map<String, String>>[];
      for (final dynamic m in (j['metros'] as List?) ?? const <dynamic>[]) {
        if (m is! Map) continue;
        final String id = (m['id'] ?? '').toString();
        if (id.isEmpty) continue;
        ms.add(<String, String>{
          'id': id,
          'label': (m['label'] ?? id).toString(),
          'state': (m['state'] ?? '').toString(),
        });
        final dynamic lat = m['lat'];
        final dynamic lng = m['lng'];
        if (lat is num && lng is num) {
          kMetroLatLng[id] = <double>[lat.toDouble(), lng.toDouble()];
        }
      }
      if (ms.length >= 20) {
        ms.sort((Map<String, String> a, Map<String, String> b) =>
            (a['label'] ?? '').compareTo(b['label'] ?? ''));
        kMetros = ms;
      }
      final List<Map<String, String>> ts = <Map<String, String>>[];
      for (final dynamic t in (j['towns'] as List?) ?? const <dynamic>[]) {
        if (t is! Map) continue;
        final String n = (t['n'] ?? '').toString();
        final String m = (t['m'] ?? '').toString();
        if (n.isEmpty || m.isEmpty) continue;
        ts.add(<String, String>{'n': n, 's': (t['s'] ?? '').toString(), 'm': m});
      }
      kTowns = ts;
      _placesLoaded = true;
    } catch (e) {
      debugPrint('LAZO places: ' + e.toString());
    } finally {
      _placesLoading = null;
    }
  }

  // One picker for "where": type a town or a city. A town answers with its Lazo metro, because vendors live in
  // metros; the town comes back too so the couple's own town is kept. Returns {metro, town} or null.
  Future<Map<String, String>?> _pickPlace(
      {String title = 'Where’s the wedding?'}) async {
    await _loadPlaces();
    if (!mounted) return null;
    final TextEditingController q = TextEditingController();
    final Map<String, String>? out = await _lzSheet<Map<String, String>>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setP) {
          final String s = q.text.trim().toLowerCase();
          final List<Map<String, String>> rows = <Map<String, String>>[];
          final Set<String> seen = <String>{};
          if (s.length >= 2) {
            for (final Map<String, String> t in kTowns) {
              if (rows.length >= 40) break;
              final String n = (t['n'] ?? '').toLowerCase();
              if (n.startsWith(s) && seen.add('${t['n']}|${t['s']}')) {
                rows.add(<String, String>{
                  'metro': t['m'] ?? '',
                  'town': t['n'] ?? '',
                  'title': '${t['n']}, ${t['s']}',
                  'sub': '${_metroLabel(t['m'] ?? '')} area',
                });
              }
            }
          }
          for (final Map<String, String> m in kMetros) {
            final String l = (m['label'] ?? '').toLowerCase();
            if (s.isEmpty || l.contains(s)) {
              rows.add(<String, String>{
                'metro': m['id'] ?? '',
                'town': '',
                'title': m['label'] ?? '',
                'sub': (m['state'] ?? '').isEmpty ? 'Lazo city' : 'Lazo city · ${m['state']}',
              });
            }
          }
          return Padding(
            padding: EdgeInsets.fromLTRB(
                20, 18, 20, 12 + MediaQuery.of(ctx2).viewInsets.bottom),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                Text(title,
                    style: TextStyle(
                        color: _lzFg(plumDeep),
                        fontSize: 20,
                        fontWeight: FontWeight.w700)),
                const SizedBox(height: 4),
                Text('Type your town or the nearest city.',
                    style: TextStyle(color: _lzFg(muted), fontSize: 13)),
                const SizedBox(height: 12),
                TextField(
                  controller: q,
                  autofocus: true,
                  textCapitalization: TextCapitalization.words,
                  onChanged: (String _) => setP(() {}),
                  style: TextStyle(color: _lzFg(ink), fontSize: 16),
                  decoration: _lightDeco('Town or city', hint: 'Worcester'),
                ),
                const SizedBox(height: 8),
                SizedBox(
                  height: 380,
                  child: rows.isEmpty
                      ? Center(
                          child: Text(
                              'No Lazo city near “${q.text.trim()}” yet.\nTry the nearest larger city.',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: _lzFg(muted), fontSize: 13)))
                      : ListView.builder(
                          itemCount: rows.length,
                          itemBuilder: (BuildContext c, int i) {
                            final Map<String, String> r = rows[i];
                            return ListTile(
                              dense: true,
                              leading: Icon(
                                  (r['town'] ?? '').isEmpty
                                      ? Icons.location_city_rounded
                                      : Icons.place_rounded,
                                  color: gold,
                                  size: 20),
                              title: Text(r['title'] ?? '',
                                  style: TextStyle(
                                      color: _lzFg(ink),
                                      fontSize: 15,
                                      fontWeight: FontWeight.w600)),
                              subtitle: Text(r['sub'] ?? '',
                                  style: TextStyle(color: _lzFg(muted), fontSize: 12.5)),
                              onTap: () => Navigator.pop(ctx2, <String, String>{
                                'metro': r['metro'] ?? '',
                                'town': r['town'] ?? '',
                              }),
                            );
                          },
                        ),
                ),
              ],
            ),
          );
        },
      ),
    );
    q.dispose();
    return out;
  }
""")

# 3. load at start, and repaint once it lands (labels, weather and browse then see every metro)
rep("""    _openPendingWelcome(); // v144
""", """    _openPendingWelcome(); // v144
    _loadPlaces().then((_) {
      if (mounted) setState(() {});
    }); // v159
""")

# 4. a welcome-page metro outside the old 45 is accepted once the list has loaded
rep("""      final DocumentSnapshot<Map<String, dynamic>> c = await _coupleRef.get();
      final Map<String, dynamic> couple = c.data() ?? <String, dynamic>{};
      final Map<String, dynamic> up = <String, dynamic>{};
      if (names.isNotEmpty &&""", """      await _loadPlaces(); // v159: a welcome-page metro outside the old 45 is real too
      final DocumentSnapshot<Map<String, dynamic>> c = await _coupleRef.get();
      final Map<String, dynamic> couple = c.data() ?? <String, dynamic>{};
      final Map<String, dynamic> up = <String, dynamic>{};
      if (names.isNotEmpty &&""")

# 5. setup: the city step is the search, and the town is kept
rep("""    String metro = (couple['metroId'] ?? '').toString();
    DateTime? date = couple['weddingDate'] is Timestamp""", """    String metro = (couple['metroId'] ?? '').toString();
    String town = (couple['town'] ?? '').toString(); // v159
    DateTime? date = couple['weddingDate'] is Timestamp""")
rep("""                if (metro.isNotEmpty) 'metroId': metro,
                if (date != null) 'weddingDate': Timestamp.fromDate(date!),""", """                if (metro.isNotEmpty) 'metroId': metro,
                if (metro.isNotEmpty) 'town': town, // v159
                if (date != null) 'weddingDate': Timestamp.fromDate(date!),""")
rep("""          } else if (step == 2) {
            body = DropdownButtonFormField<String>(
              value: metro.isEmpty ? null : metro,
              dropdownColor: _lzBg(ivory),
              style: TextStyle(color: _lzFg(ink), fontSize: 15),
              decoration: _lightDeco('City'),
              items: <DropdownMenuItem<String>>[
                for (final Map<String, String> m in kMetros)
                  DropdownMenuItem<String>(
                      value: m['id'], child: Text(m['label'] ?? ''))
              ],
              onChanged: (String? v) => setD(() => metro = v ?? ''),
            );""", """          } else if (step == 2) {
            // v159: a search over every town and city, not a 45-row dropdown
            body = OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                  foregroundColor: _lzFg(plum),
                  side: const BorderSide(color: gold),
                  alignment: Alignment.centerLeft,
                  padding:
                      const EdgeInsets.symmetric(vertical: 16, horizontal: 16),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14))),
              onPressed: _h(() async {
                final Map<String, String>? p = await _pickPlace();
                if (p != null && (p['metro'] ?? '').isNotEmpty) {
                  setD(() {
                    metro = p['metro']!;
                    town = p['town'] ?? '';
                  });
                }
              }),
              icon: const Icon(Icons.place_rounded, size: 18),
              label: Text(
                  metro.isEmpty
                      ? 'Your town or city'
                      : (town.isNotEmpty
                          ? '$town · ${_metroLabel(metro)} area'
                          : _metroLabel(metro)),
                  style: const TextStyle(
                      fontSize: 15, fontWeight: FontWeight.w700)),
            );""")

# 6. Browse: the city is the same search
rep("""          child: _browseField(
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: _browseMetro,
                isExpanded: true,
                dropdownColor: _lzBg(ivory),
                icon: const Icon(Icons.expand_more_rounded, color: gold),
                selectedItemBuilder: (BuildContext c) => kMetros
                    .map((m) => Align(
                        alignment: Alignment.centerLeft,
                        child: Text(m['label']!,
                            style: const TextStyle(
                                color: ivory,
                                fontSize: 15,
                                fontWeight: FontWeight.w600))))
                    .toList(),
                style:  TextStyle(
                    color: _lzFg(plum), fontSize: 15, fontWeight: FontWeight.w600),
                items: kMetros
                    .map((m) => DropdownMenuItem(
                        value: m['id'], child: Text(m['label']!)))
                    .toList(),
                onChanged: (v) =>
                    setState(() => _browseMetro = v ?? _browseMetro),
              ),
            ),
          ),""", """          child: _browseField(
            // v159: every Lazo city and town, as a search
            child: InkWell(
              onTap: _h(() async {
                final Map<String, String>? p =
                    await _pickPlace(title: 'Find vendors near…');
                if (p != null && (p['metro'] ?? '').isNotEmpty) {
                  setState(() => _browseMetro = p['metro']!);
                }
              }),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Row(children: <Widget>[
                  Expanded(
                    child: Text(
                        _metroLabel(_browseMetro).isEmpty
                            ? _browseMetro
                            : _metroLabel(_browseMetro),
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            color: ivory,
                            fontSize: 15,
                            fontWeight: FontWeight.w600)),
                  ),
                  const Icon(Icons.search_rounded, color: gold, size: 20),
                ]),
              ),
            ),
          ),""")

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8", newline="")
print(f"wrote {DST.name} ({len(out):,} chars)")
