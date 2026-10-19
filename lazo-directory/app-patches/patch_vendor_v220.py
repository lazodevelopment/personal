"""Vendor v220: Zola-style markets (JC-LAZO-MARKETS-1019-VENDOR).

    python app-patches\\patch_vendor_v220.py [base.txt]   # base defaults to Vendor_master_v219.txt
                                                          # writes Vendor_master_v220.txt

- A vendor now lists HOME markets (standard rates) and TRAVEL markets (a travel fee may apply)
  from Zola's 566 named markets (generate/data/markets.json, pasted in as kLzMarkets from
  app-patches/v220_parts/markets_dart.txt). vendors.homeMarkets / vendors.travelMarkets hold the
  market keys; metroId, serviceMetros and prefs.travelMiles stay exactly as they were.
- The market picker (_pickMarkets): pick a state, tick its markets, flip "Travel fee" per market,
  search across every state, or "Everywhere in the US (travel included)" which fills every home
  market. The same sheet serves two places:
    * Add your business, step 2 (Services): a WHERE DO YOU TAKE BOOKINGS? section; the request
      carries homeMarkets / travelMarkets (rules 1019-MARKETS adds them to the listingRequests
      allowlist - release those rules BEFORE this paste or new listing requests that pick a market
      are refused) and approval copies both lists onto the vendor doc.
    * Profile editor: a "Where you take bookings" card under "Markets you serve".
- Admin queue cards show how many home / travel markets a request picked.
- meetlazo.com (worker JC-LAZO-MARKETS-1019) lists the vendor in every Lazo metro that overlaps one
  of their markets, with a "Travel fee may apply" tag for travel-only metros.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Vendor_master_v219.txt"
DST = HERE / "Vendor_master_v220.txt"
MARKETS = (HERE / "v220_parts" / "markets_dart.txt").read_text(encoding="utf-8").replace("\r\n", "\n")
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, f"expected {n}, found {c}: {a[:90]!r}"
    s = s.replace(a, b)


first_build = s.index("// Build ID:")
s = s[:first_build] + (
    "// Build ID: JC-LAZO-MARKETS-1019-VENDOR (v220: MARKETS, ZOLA-STYLE - home markets at standard rates and travel "
    "markets where a travel fee may apply, from Zola's 566 named markets (kLzMarkets); the picker takes a state, ticks "
    "markets, flips Travel fee per market, or Everywhere in the US; in Add your business step 2 (listingRequests."
    "homeMarkets / travelMarkets, copied on approval) and the profile editor (vendors.homeMarkets / travelMarkets); "
    "metroId / serviceMetros / travelMiles untouched; base v219)\n"
) + s[first_build:]

# ---- the market table + state names, top level, just before the widget
STATE_NAMES = """// JC-LAZO-MARKETS-1019: state names for the market picker
const Map<String, String> kLzStateNames = <String, String>{
  'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California', 'CO': 'Colorado',
  'CT': 'Connecticut', 'DE': 'Delaware', 'DC': 'Washington, D.C.', 'FL': 'Florida', 'GA': 'Georgia',
  'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
  'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts',
  'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana',
  'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico',
  'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
  'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
  'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
  'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
};

"""
rep("class LazoVendorDashboard extends StatefulWidget {",
    MARKETS + "\n" + STATE_NAMES + "class LazoVendorDashboard extends StatefulWidget {")

# ---- editor state
rep("  Set<String> _epMetros = <String>{};",
    "  Set<String> _epMetros = <String>{};\n"
    "  Set<String> _epHome = <String>{}; // v220: Zola-style home markets (market keys)\n"
    "  Set<String> _epTravel = <String>{}; // v220: markets where a travel fee may apply")

rep("""    _epMetros = <String>{};
    if (v['serviceMetros'] is List) {
      for (final dynamic m in v['serviceMetros'] as List<dynamic>) {
        _epMetros.add(m.toString());
      }
    }
""", """    _epMetros = <String>{};
    if (v['serviceMetros'] is List) {
      for (final dynamic m in v['serviceMetros'] as List<dynamic>) {
        _epMetros.add(m.toString());
      }
    }
    // v220: Zola-style markets
    _epHome = _lzKeys(v['homeMarkets']);
    _epTravel = _lzKeys(v['travelMarkets'])..removeAll(_epHome);
""")

rep("        'serviceMetros': _epMetros.toList(),",
    "        'serviceMetros': _epMetros.toList(),\n"
    "        'homeMarkets': (_epHome.toList()..sort()), // v220\n"
    "        'travelMarkets': (_epTravel.toList()..sort()),")

# ---- profile editor card, under "Markets you serve"
rep("""        _epCard(
            'Announcement',""", """        // v220: Zola-style markets - home at standard rates, travel where a fee may apply
        _epCard(
            'Where you take bookings',
            'Home markets are where you work at your standard rates; a travel market is one where a travel fee may apply. Couples in any of them find you on meetlazo.com.',
            <Widget>[
              _marketsSummary(_epHome, _epTravel),
              const SizedBox(height: 10),
              Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                ActionChip(
                  avatar: Icon(Icons.map_outlined, size: 16, color: _lzFg(plum)),
                  label: Text(_epHome.isEmpty && _epTravel.isEmpty ? 'Choose markets' : 'Edit markets',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: _lzFg(plum))),
                  backgroundColor: _lzBg(ivory),
                  side: BorderSide(color: gold.withOpacity(.6)),
                  onPressed: () async {
                    await _pickMarkets(home: _epHome, travel: _epTravel);
                    if (mounted) setState(() {});
                  },
                ),
                ActionChip(
                  avatar: Icon(Icons.public_rounded, size: 16, color: _lzFg(plum)),
                  label: Text('Everywhere in the US',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: _lzFg(plum))),
                  backgroundColor: _lzBg(ivory),
                  side: BorderSide(color: gold.withOpacity(.6)),
                  onPressed: _h(() => setState(() {
                        _epHome = <String>{for (final List<String> m in kLzMarkets) m[1]};
                        _epTravel = <String>{};
                      })),
                ),
              ]),
            ]),
        _epCard(
            'Announcement',""")

# ---- Add your business: locals, step 2 section, the request
rep("""    int step = 0; // v190: Business -> Services -> Verify
    final Set<String> picked = <String>{};""",
    """    int step = 0; // v190: Business -> Services -> Verify
    final Set<String> picked = <String>{};
    final Set<String> obHome = <String>{}; // v220: Zola-style markets
    final Set<String> obTravel = <String>{};""")

rep("""                Wrap(spacing: 8, runSpacing: 8, children: chips),
                const SizedBox(height: 24),
                _onbLabel('ONE LAST QUESTION'),""",
    """                Wrap(spacing: 8, runSpacing: 8, children: chips),
                const SizedBox(height: 24),
                // v220: Zola-style markets
                _onbLabel('WHERE DO YOU TAKE BOOKINGS?'),
                const SizedBox(height: 4),
                Text('Your home markets at standard rates, plus any you travel to for a fee. Optional - your city above is always included.',
                    style: TextStyle(color: _lzFg(muted), fontSize: 12.5)),
                const SizedBox(height: 10),
                _marketsSummary(obHome, obTravel),
                const SizedBox(height: 8),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  _onbChip(
                      label: obHome.isEmpty && obTravel.isEmpty ? 'Choose markets' : 'Edit markets',
                      selected: false,
                      onTap: busy
                          ? null
                          : () async {
                              await _pickMarkets(home: obHome, travel: obTravel);
                              setD(() {});
                            }),
                  _onbChip(
                      label: 'Everywhere in the US',
                      selected: obHome.length == kLzMarkets.length,
                      onTap: busy
                          ? null
                          : () => setD(() {
                                obHome
                                  ..clear()
                                  ..addAll(<String>[for (final List<String> m in kLzMarkets) m[1]]);
                                obTravel.clear();
                              })),
                ]),
                const SizedBox(height: 24),
                _onbLabel('ONE LAST QUESTION'),""")

rep("""                  'serviceArea': true,
                  'status': 'pending',""",
    """                  'serviceArea': true,
                  'homeMarkets': (obHome.toList()..sort()), // v220
                  'travelMarkets': (obTravel.toList()..sort()),
                  'status': 'pending',""")

# ---- approval copies the lists onto the vendor doc
rep("""            'serviceArea': true,
            'heardAbout': req['heardAbout'] == null ? '' : req['heardAbout'].toString(),""",
    """            'serviceArea': true,
            'homeMarkets': _lzKeys(req['homeMarkets']).toList(), // v220
            'travelMarkets': _lzKeys(req['travelMarkets']).toList(),
            'heardAbout': req['heardAbout'] == null ? '' : req['heardAbout'].toString(),""")

# ---- admin card line
rep("""    if (req['metroId'] != null) {
      lines.add('Metro: ' + _metroLabel(req['metroId'].toString()));
    }""", """    if (req['metroId'] != null) {
      lines.add('Metro: ' + _metroLabel(req['metroId'].toString()));
    }
    if (_lzKeys(req['homeMarkets']).isNotEmpty || _lzKeys(req['travelMarkets']).isNotEmpty) {
      lines.add('Markets: ${_lzKeys(req['homeMarkets']).length} home, ${_lzKeys(req['travelMarkets']).length} travel'); // v220
    }""")

# ---- helpers: keys, labels, summary chips, the picker sheet
HELPERS = r"""  // ---- v220: Zola-style markets ----------------------------------------------------
  Set<String> _lzKeys(dynamic v) =>
      v is List ? <String>{for (final dynamic k in v) if (k != null && k.toString().isNotEmpty) k.toString()} : <String>{};

  String _marketLabel(String key) {
    for (final List<String> m in kLzMarkets) {
      if (m[1] == key) return '${m[2]}, ${m[0]}';
    }
    return key;
  }

  /// The picked markets as chips: every home market, then the travel ones with a plane, capped.
  Widget _marketsSummary(Set<String> home, Set<String> travel) {
    if (home.isEmpty && travel.isEmpty) {
      return Text('No markets picked yet.', style: TextStyle(fontSize: 12.5, color: _lzFg(muted)));
    }
    if (home.length >= kLzMarkets.length) {
      return Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
        Chip(
          avatar: const Icon(Icons.public_rounded, size: 15, color: plumDeep),
          label: Text('Everywhere in the US (${kLzMarkets.length} markets, travel included)',
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: plumDeep)),
          backgroundColor: gold,
          side: BorderSide(color: gold.withOpacity(.6)),
        ),
      ]);
    }
    final List<String> h = home.toList()..sort((String a, String b) => _marketLabel(a).compareTo(_marketLabel(b)));
    final List<String> t = travel.toList()..sort((String a, String b) => _marketLabel(a).compareTo(_marketLabel(b)));
    const int cap = 14;
    final List<Widget> chips = <Widget>[];
    for (final String k in h) {
      if (chips.length >= cap) break;
      chips.add(Chip(
        label: Text(_marketLabel(k), style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: _lzFg(ink))),
        backgroundColor: _lzBg(ivory),
        side: BorderSide(color: gold.withOpacity(.6)),
        visualDensity: VisualDensity.compact,
      ));
    }
    for (final String k in t) {
      if (chips.length >= cap) break;
      chips.add(Chip(
        avatar: Icon(Icons.flight_takeoff_rounded, size: 14, color: _lzFg(plum)),
        label: Text(_marketLabel(k), style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: _lzFg(plum))),
        backgroundColor: _lzBg(gold.withOpacity(.18)),
        side: BorderSide(color: gold.withOpacity(.6)),
        visualDensity: VisualDensity.compact,
      ));
    }
    final int more = h.length + t.length - chips.length;
    if (more > 0) {
      chips.add(Chip(
        label: Text('+$more more', style: TextStyle(fontSize: 12, color: _lzFg(muted))),
        backgroundColor: _lzBg(Colors.white.withOpacity(.6)),
        side: BorderSide(color: _lzLine(goldLine)),
        visualDensity: VisualDensity.compact,
      ));
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
      Wrap(spacing: 6, runSpacing: 6, children: chips),
      const SizedBox(height: 6),
      Text('${h.length} home market${h.length == 1 ? '' : 's'}'
          '${t.isNotEmpty ? ' · ${t.length} with a travel fee' : ''}',
          style: TextStyle(fontSize: 12, color: _lzFg(muted))),
    ]);
  }

  /// The market picker. Edits [home] and [travel] in place (a market is in one or the other);
  /// the caller rebuilds afterwards. Pick a state, tick markets, flip the travel fee per market,
  /// search across every state, or take every market in the country.
  Future<void> _pickMarkets({
    required Set<String> home,
    required Set<String> travel,
    String title = 'Where do you take bookings?',
  }) async {
    if (!mounted) return;
    final List<String> states = <String>[];
    for (final List<String> m in kLzMarkets) {
      if (!states.contains(m[0])) states.add(m[0]);
    }
    states.sort((String a, String b) => (kLzStateNames[a] ?? a).compareTo(kLzStateNames[b] ?? b));
    String state = '';
    for (final List<String> m in kLzMarkets) {
      if (home.contains(m[1]) || travel.contains(m[1])) {
        state = m[0];
        break;
      }
    }
    if (state.isEmpty) {
      // start on the home city's state when we know it
      for (final List<String> m in kLzMarkets) {
        if (_epHomeMetro.isNotEmpty && m[1] == _epHomeMetro) {
          state = m[0];
          break;
        }
      }
    }
    if (state.isEmpty) state = states.first;
    final TextEditingController q = TextEditingController();
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 640),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setP) {
          final String s = q.text.trim().toLowerCase();
          final List<List<String>> rows = <List<String>>[];
          for (final List<String> m in kLzMarkets) {
            if (s.isNotEmpty
                ? (m[2].toLowerCase().contains(s) || (kLzStateNames[m[0]] ?? '').toLowerCase().contains(s))
                : m[0] == state) {
              rows.add(m);
            }
          }
          final bool everywhere = home.length >= kLzMarkets.length;
          int inState = 0;
          for (final List<String> m in kLzMarkets) {
            if (m[0] == state && (home.contains(m[1]) || travel.contains(m[1]))) inState++;
          }
          final TextStyle small = TextStyle(fontSize: 12, color: _lzFg(muted));
          return Padding(
            padding: EdgeInsets.fromLTRB(20, 18, 20, 12 + MediaQuery.of(ctx2).viewInsets.bottom),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                Row(children: <Widget>[
                  Expanded(
                    child: Text(title,
                        style: TextStyle(color: _lzFg(plumDeep), fontSize: 20, fontWeight: FontWeight.w700)),
                  ),
                  TextButton(
                    onPressed: () => Navigator.pop(ctx2),
                    child: Text('Done', style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w800)),
                  ),
                ]),
                const SizedBox(height: 2),
                Text('Tick the markets you work in. Flip Travel fee on any market where you charge for travel.', style: small),
                const SizedBox(height: 10),
                Wrap(spacing: 8, runSpacing: 8, crossAxisAlignment: WrapCrossAlignment.center, children: <Widget>[
                  FilterChip(
                    avatar: Icon(Icons.public_rounded, size: 15, color: everywhere ? plumDeep : _lzFg(plum)),
                    label: Text('Everywhere in the US (travel included)',
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: everywhere ? plumDeep : _lzFg(plum))),
                    selected: everywhere,
                    showCheckmark: false,
                    selectedColor: gold,
                    backgroundColor: _lzBg(ivory),
                    side: BorderSide(color: gold.withOpacity(.6)),
                    onSelected: (bool on) => setP(() {
                      if (on) {
                        home
                          ..clear()
                          ..addAll(<String>[for (final List<String> m in kLzMarkets) m[1]]);
                        travel.clear();
                      } else {
                        home.clear();
                        travel.clear();
                      }
                    }),
                  ),
                  if (!everywhere && (home.isNotEmpty || travel.isNotEmpty))
                    TextButton(
                      onPressed: () => setP(() {
                        home.clear();
                        travel.clear();
                      }),
                      child: Text('Clear all', style: TextStyle(color: _lzFg(muted), fontSize: 12.5)),
                    ),
                  Text('${home.length} home · ${travel.length} travel', style: small),
                ]),
                const SizedBox(height: 10),
                Row(children: <Widget>[
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      value: state,
                      isExpanded: true,
                      decoration: _epDeco('State', ''),
                      style: TextStyle(color: _lzFg(ink), fontSize: 14.5, fontWeight: FontWeight.w600),
                      dropdownColor: _lzBg(ivory),
                      borderRadius: BorderRadius.circular(16),
                      items: <DropdownMenuItem<String>>[
                        for (final String st in states)
                          DropdownMenuItem<String>(value: st, child: Text(kLzStateNames[st] ?? st)),
                      ],
                      onChanged: (String? v) => setP(() {
                        if (v != null) state = v;
                        q.clear();
                      }),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      controller: q,
                      onChanged: (String _) => setP(() {}),
                      cursorColor: _lzFg(plum),
                      style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
                      decoration: _epDeco('Search every state', 'e.g. Hudson'),
                    ),
                  ),
                ]),
                const SizedBox(height: 6),
                if (s.isEmpty)
                  Row(children: <Widget>[
                    Expanded(
                        child: Text('${kLzStateNames[state] ?? state}: $inState of ${rows.length} picked', style: small)),
                    TextButton(
                      onPressed: () => setP(() {
                        final bool all = rows.every((List<String> m) => home.contains(m[1]) || travel.contains(m[1]));
                        for (final List<String> m in rows) {
                          if (all) {
                            home.remove(m[1]);
                            travel.remove(m[1]);
                          } else if (!travel.contains(m[1])) {
                            home.add(m[1]);
                          }
                        }
                      }),
                      child: Text(
                          rows.every((List<String> m) => home.contains(m[1]) || travel.contains(m[1]))
                              ? 'Clear ${kLzStateNames[state] ?? state}'
                              : 'All of ${kLzStateNames[state] ?? state}',
                          style: TextStyle(color: _lzFg(plum), fontSize: 12.5, fontWeight: FontWeight.w700)),
                    ),
                  ]),
                SizedBox(
                  height: 360,
                  child: rows.isEmpty
                      ? Center(
                          child: Text('No market matches “${q.text.trim()}”.',
                              textAlign: TextAlign.center, style: TextStyle(color: _lzFg(muted), fontSize: 13)))
                      : ListView.builder(
                          itemCount: rows.length,
                          itemBuilder: (BuildContext c, int i) {
                            final List<String> m = rows[i];
                            final String key = m[1];
                            final bool isHome = home.contains(key);
                            final bool isTravel = travel.contains(key);
                            final bool on = isHome || isTravel;
                            return InkWell(
                              borderRadius: BorderRadius.circular(12),
                              onTap: () => setP(() {
                                if (on) {
                                  home.remove(key);
                                  travel.remove(key);
                                } else {
                                  home.add(key);
                                }
                              }),
                              child: Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                                child: Row(children: <Widget>[
                                  Checkbox(
                                    value: on,
                                    activeColor: plum,
                                    checkColor: gold,
                                    visualDensity: VisualDensity.compact,
                                    onChanged: (bool? v) => setP(() {
                                      if (v == true) {
                                        home.add(key);
                                      } else {
                                        home.remove(key);
                                        travel.remove(key);
                                      }
                                    }),
                                  ),
                                  Expanded(
                                    child: Text(s.isEmpty ? m[2] : '${m[2]}, ${m[0]}',
                                        style: TextStyle(
                                            color: _lzFg(ink),
                                            fontSize: 14.5,
                                            fontWeight: on ? FontWeight.w700 : FontWeight.w500)),
                                  ),
                                  if (on)
                                    FilterChip(
                                      avatar: Icon(Icons.flight_takeoff_rounded,
                                          size: 14, color: isTravel ? plumDeep : _lzFg(muted)),
                                      label: Text('Travel fee',
                                          style: TextStyle(
                                              fontSize: 11.5,
                                              fontWeight: FontWeight.w700,
                                              color: isTravel ? plumDeep : _lzFg(muted))),
                                      selected: isTravel,
                                      showCheckmark: false,
                                      selectedColor: gold,
                                      backgroundColor: _lzBg(Colors.white.withOpacity(.6)),
                                      side: BorderSide(color: isTravel ? gold : _lzLine(goldLine)),
                                      visualDensity: VisualDensity.compact,
                                      onSelected: (bool fee) => setP(() {
                                        if (fee) {
                                          home.remove(key);
                                          travel.add(key);
                                        } else {
                                          travel.remove(key);
                                          home.add(key);
                                        }
                                      }),
                                    ),
                                ]),
                              ),
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
  }

"""
rep("  Widget _epCard(String title, String subtitle, List<Widget> children) {",
    HELPERS + "  Widget _epCard(String title, String subtitle, List<Widget> children) {")

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8")
print("wrote", DST, len(s.splitlines()), "lines")
