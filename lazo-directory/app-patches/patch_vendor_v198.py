r"""patch_vendor_v198.py - Vendor v197 -> v198: TOWNS + EVERY METRO.  JC-LAZO-PLACES-1015-VENDOR

Same source as Couple v159: the metro list loads from https://meetlazo.com/assets/places.json (every live metro
+ every town with vendors, rebuilt nightly); the built-in 45 stay as the offline fallback. "Where you work" in the
claim flow is a search (type a town or a city; a town answers with its metro). "Markets you serve" shows the home
market, the markets picked, and an Add-a-market search - not a chip for every metro in the country - and Pro's
"Select all" collapses to one "Every market" chip. Scheduling's timezone falls back to the metro's zone from the
same file.

    python app-patches\patch_vendor_v198.py      # writes Vendor_master_v198.txt
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC, DST = HERE / "Vendor_master_v197.txt", HERE / "Vendor_master_v198.txt"
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, f"expected {n} match(es), found {c}: {old[:90]!r}"
    s = s.replace(old, new)


rep("// lazo_vendor_dashboard.dart\n",
    "// lazo_vendor_dashboard.dart\n"
    "// Build ID: JC-LAZO-PLACES-1015-VENDOR (v198: TOWNS + EVERY METRO - the metro list loads from "
    "meetlazo.com/assets/places.json (every live metro + every town with vendors, nightly; the old 45 are the offline "
    "fallback); 'Where you work' is a search over towns and cities; Markets you serve shows home + picked + Add a "
    "market instead of a chip per metro; scheduling's timezone falls back to the metro's zone; base v197)\n")

rep("  static const Map<String, List<double>> kMetroLatLng = <String, List<double>>{\n",
    "  static Map<String, List<double>> kMetroLatLng = <String, List<double>>{\n")

rep("""    'Tucson'
  ];

  final List<String> _catIds = [""", r"""    'Tucson'
  ];

  // v198: TOWNS + EVERY METRO. The two lists above are the offline fallback; the site's list (rebuilt every night)
  // replaces them once it loads, so a new metro or town needs no FlutterFlow paste.
  static List<Map<String, String>> kTowns = <Map<String, String>>[];
  static final Map<String, String> _placeTz = <String, String>{};
  bool _placesLoaded = false;
  Future<void>? _placesLoading;

  Future<void> _loadPlaces() {
    if (_placesLoaded) return Future<void>.value();
    return _placesLoading ??= _fetchPlaces();
  }

  Future<void> _fetchPlaces() async {
    try {
      final httpc.Response r = await httpc
          .get(Uri.parse('https://meetlazo.com/assets/places.json'))
          .timeout(const Duration(seconds: 12));
      if (r.statusCode != 200) return;
      final dynamic j = jsonDecode(utf8.decode(r.bodyBytes));
      if (j is! Map) return;
      final List<List<String>> ms = <List<String>>[];
      for (final dynamic m in (j['metros'] as List?) ?? const <dynamic>[]) {
        if (m is! Map) continue;
        final String id = (m['id'] ?? '').toString();
        if (id.isEmpty) continue;
        ms.add(<String>[id, (m['label'] ?? id).toString()]);
        final dynamic lat = m['lat'];
        final dynamic lng = m['lng'];
        if (lat is num && lng is num) {
          kMetroLatLng[id] = <double>[lat.toDouble(), lng.toDouble()];
        }
        final String tz = (m['tz'] ?? '').toString();
        if (tz.isNotEmpty) _placeTz[id] = tz;
      }
      if (ms.length >= 20) {
        ms.sort((List<String> a, List<String> b) => a[1].compareTo(b[1]));
        _metroIds
          ..clear()
          ..addAll(ms.map((List<String> m) => m[0]));
        _metroNames
          ..clear()
          ..addAll(ms.map((List<String> m) => m[1]));
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
      if (mounted) setState(() {});
    } catch (e) {
      debugPrint('LAZO places: ' + e.toString());
    } finally {
      _placesLoading = null;
    }
  }

  // Type a town or a city; a town answers with its Lazo metro. Returns the metro id, or null.
  Future<String?> _pickMetro({String title = 'Where do you work?'}) async {
    await _loadPlaces();
    if (!mounted) return null;
    final TextEditingController q = TextEditingController();
    final String? out = await _lzSheet<String>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setP) {
          final String s = q.text.trim().toLowerCase();
          final List<List<String>> rows = <List<String>>[]; // [metroId, title, sub, isTown]
          final Set<String> seen = <String>{};
          if (s.length >= 2) {
            for (final Map<String, String> t in kTowns) {
              if (rows.length >= 40) break;
              if ((t['n'] ?? '').toLowerCase().startsWith(s) &&
                  seen.add('${t['n']}|${t['s']}')) {
                rows.add(<String>[
                  t['m'] ?? '',
                  '${t['n']}, ${t['s']}',
                  '${_metroLabel(t['m'])} area',
                  '1'
                ]);
              }
            }
          }
          for (int i = 0; i < _metroIds.length; i++) {
            if (s.isEmpty || _metroNames[i].toLowerCase().contains(s)) {
              rows.add(<String>[_metroIds[i], _metroNames[i], 'Lazo city', '']);
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
                  cursorColor: _lzFg(plum),
                  style: TextStyle(color: _lzFg(ink), fontSize: 16),
                  decoration: _epDeco('Town or city', 'e.g. Worcester'),
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
                            final List<String> r = rows[i];
                            return ListTile(
                              dense: true,
                              leading: Icon(
                                  r[3].isEmpty
                                      ? Icons.location_city_rounded
                                      : Icons.place_rounded,
                                  color: gold,
                                  size: 20),
                              title: Text(r[1],
                                  style: TextStyle(
                                      color: _lzFg(ink),
                                      fontSize: 15,
                                      fontWeight: FontWeight.w600)),
                              subtitle: Text(r[2],
                                  style: TextStyle(color: _lzFg(muted), fontSize: 12.5)),
                              onTap: () => Navigator.pop(ctx2, r[0]),
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

  final List<String> _catIds = [""")

# load at start
rep("""  void initState() {
    super.initState();
    _lzLoadTheme(); // JC-LAZO-THEME-1009-001
    final User? u = FirebaseAuth.instance.currentUser;""", """  void initState() {
    super.initState();
    _lzLoadTheme(); // JC-LAZO-THEME-1009-001
    _loadPlaces(); // v198
    final User? u = FirebaseAuth.instance.currentUser;""")

# scheduling timezone: the metro's own zone before the East Coast default
rep("""          : (tz[metro] ?? 'America/New_York');""",
    """          : (tz[metro] ?? _placeTz[metro] ?? 'America/New_York'); // v198""")

# claim flow: "Where you work" is the search
rep("""        Expanded(
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: _claimMetro,
              dropdownColor: _lzBg(ivory),
              menuMaxHeight: 420,
              isExpanded: true,
              borderRadius: BorderRadius.circular(16),
              icon: Icon(Icons.expand_more_rounded, color: _lzFg(plum)),
              style: TextStyle(
                  color: _lzFg(plum), fontSize: 15, fontWeight: FontWeight.w700),
              items: items,
              onChanged: (String? v) {
                if (v == null) {
                  return;
                }
                setState(() {
                  _claimMetro = v;
                });
                if (_searchC.text.trim().length >= 2) {
                  _runSearch();
                }
              },
            ),
          ),
        ),""", """        Expanded(
          // v198: every Lazo city and town, as a search
          child: InkWell(
            onTap: () async {
              final String? v = await _pickMetro();
              if (v == null || v.isEmpty || !mounted) return;
              setState(() {
                _claimMetro = v;
              });
              if (_searchC.text.trim().length >= 2) {
                _runSearch();
              }
            },
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 13),
              child: Row(children: <Widget>[
                Expanded(
                  child: Text(
                      _metroLabel(_claimMetro).isEmpty
                          ? _claimMetro
                          : _metroLabel(_claimMetro),
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                          color: _lzFg(plum),
                          fontSize: 15,
                          fontWeight: FontWeight.w700)),
                ),
                Icon(Icons.search_rounded, color: _lzFg(plum), size: 20),
              ]),
            ),
          ),
        ),""")
# the dropdown's item list is no longer used
rep("""    final List<DropdownMenuItem<String>> items = <DropdownMenuItem<String>>[];
    for (int i = 0; i < _metroIds.length; i++) {
      items.add(DropdownMenuItem<String>(
          value: _metroIds[i], child: Text(_metroNames[i])));
    }
    return Container(""", """    return Container(""")

# markets you serve: home + picked + Add a market
rep("""              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: List<Widget>.generate(_metroIds.length, (int i) {
                  final String id = _metroIds[i];
                  final bool on = _epMetros.contains(id);
                  final bool isHome = id == _epHomeMetro;
                  return FilterChip(
                    selected: on,
                    onSelected: _hb((isHome || (!on && metroCap))
                        ? null
                        : (bool sel) {
                            setState(() {
                              if (sel) {
                                _epMetros.add(id);
                              } else {
                                _epMetros.remove(id);
                              }
                            });
                          }),
                    label: Text(
                        isHome ? _metroNames[i] + ' (home)' : _metroNames[i],
                        style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: on ? plumDeep : _lzFg(muted))),
                    selectedColor: gold,
                    backgroundColor: _lzBg(ivory),
                    checkmarkColor: plumDeep,
                    side: BorderSide(color: gold.withOpacity(.6)),
                  );
                }),
              ),""", """              // v198: the markets this vendor actually serves, plus a search to add one - not a chip for
              // every metro in the country. Pro's "Select all" shows as one chip.
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: <Widget>[
                  if (metroUnlimited &&
                      _metroIds.isNotEmpty &&
                      _metroIds.every(_epMetros.contains))
                    Chip(
                      label: Text('Every market (${_metroIds.length})',
                          style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: plumDeep)),
                      backgroundColor: gold,
                      side: BorderSide(color: gold.withOpacity(.6)),
                    )
                  else
                    ...(<String>{
                      if (_epHomeMetro.isNotEmpty) _epHomeMetro,
                      ..._epMetros
                    }.toList()
                          ..sort((String a, String b) =>
                              _metroLabel(a).compareTo(_metroLabel(b))))
                        .map((String id) {
                      final bool isHome = id == _epHomeMetro;
                      final String name =
                          _metroLabel(id).isEmpty ? id : _metroLabel(id);
                      return FilterChip(
                        selected: true,
                        onSelected: _hb(isHome
                            ? null
                            : (bool sel) {
                                setState(() => _epMetros.remove(id));
                              }),
                        label: Text(isHome ? name + ' (home)' : name,
                            style: const TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: plumDeep)),
                        selectedColor: gold,
                        backgroundColor: _lzBg(ivory),
                        checkmarkColor: plumDeep,
                        side: BorderSide(color: gold.withOpacity(.6)),
                      );
                    }),
                  ActionChip(
                    avatar: Icon(Icons.add_rounded,
                        size: 16, color: metroCap ? _lzFg(muted) : _lzFg(plum)),
                    label: Text(metroCap ? 'Market limit reached' : 'Add a market',
                        style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: metroCap ? _lzFg(muted) : _lzFg(plum))),
                    backgroundColor: _lzBg(ivory),
                    side: BorderSide(color: gold.withOpacity(.6)),
                    onPressed: metroCap
                        ? null
                        : () async {
                            final String? id =
                                await _pickMetro(title: 'Add a market you serve');
                            if (id != null && id.isNotEmpty && mounted) {
                              setState(() => _epMetros.add(id));
                            }
                          },
                  ),
                ],
              ),""")

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8", newline="")
print(f"wrote {DST.name} ({len(out):,} chars)")
