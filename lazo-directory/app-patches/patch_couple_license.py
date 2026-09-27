"""patch_couple_license.py - JC-LAZO-COUPLE-0920-LIC-001
A Marriage license card on the Day-Of screen. It reads
meetlazo.com/marriage-license/data.json (built nightly from
config/marriage_license.py), picks the couple's state from their metro, and
shows: the fee, the office that issues it (tap to open), the waiting period
and how long it lasts, and the application window worked out from the
wedding date ("Apply between May 3 and June 9"). A "We have it" toggle
writes couples.licenseDone so the card collapses to one line, and June's
This-week steps can read it later. No metro yet: the card points at the
state list on the site.

Applies on top of Couple_master_timeline.txt -> Couple_master_license.txt.
Anchor-and-assert.
  python app-patches\\patch_couple_license.py [src] [out]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_timeline.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else SRC.with_name(SRC.stem.replace("_timeline", "") + "_license.txt")
s = SRC.read_text(encoding="utf-8")
if "JC-LAZO-COUPLE-0920-LIC-001" in s:
    raise SystemExit("already applied")


def swap(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"ABORT [{label}]: anchor matched {n} times, expected {count}")
    s = s.replace(old, new)
    print(f"  ok  {label}")


# 1. the card sits above the weather on the Day-Of screen
swap("""        const SizedBox(height: 14),
        _weatherCard(couple),
        const SizedBox(height: 14),
        _musicCard(),
""", """        const SizedBox(height: 14),
        _licenseCard(couple),
        const SizedBox(height: 14),
        _weatherCard(couple),
        const SizedBox(height: 14),
        _musicCard(),
""", "Day-Of card slot")

# 2. state + the card, next to the weather card
swap("""  Widget _weatherCard(Map<String, dynamic> couple) {""",
     r'''  // ---- JC-LAZO-COUPLE-0920-LIC-001: the marriage license ----
  Map<String, dynamic>? _licData;
  bool _licLoading = false;
  String _licErr = '';

  Future<void> _loadLicenseData() async {
    if (_licData != null || _licLoading) return;
    _licLoading = true;
    try {
      final httpc.Response r = await httpc
          .get(Uri.parse('https://meetlazo.com/marriage-license/data.json'))
          .timeout(const Duration(seconds: 10));
      if (r.statusCode == 200) {
        final dynamic j = jsonDecode(r.body);
        if (j is Map) _licData = Map<String, dynamic>.from(j);
      } else {
        _licErr = 'Could not load license details.';
      }
    } catch (e) {
      _licErr = 'Could not load license details.';
      debugPrint('LAZO license data: ' + e.toString());
    } finally {
      _licLoading = false;
      if (mounted) setState(() {});
    }
  }

  String _licDate(DateTime d) {
    const List<String> m = <String>['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return '${m[d.month - 1]} ${d.day}';
  }

  Widget _licenseCard(Map<String, dynamic> couple) {
    final bool done = couple['licenseDone'] == true;
    final String metro = (couple['metroId'] ?? '').toString();
    if (_licData == null && !_licLoading && _licErr.isEmpty) {
      _loadLicenseData();
    }
    Map<String, dynamic>? st;
    List<dynamic> offices = const <dynamic>[];
    String stateSlug = '';
    if (_licData != null && metro.isNotEmpty) {
      final Map<String, dynamic> ms = _licData!['metros'] is Map
          ? Map<String, dynamic>.from(_licData!['metros'] as Map)
          : <String, dynamic>{};
      final Map<String, dynamic> me = ms[metro] is Map
          ? Map<String, dynamic>.from(ms[metro] as Map)
          : <String, dynamic>{};
      stateSlug = (me['state'] ?? '').toString();
      offices = me['offices'] is List ? me['offices'] as List : const <dynamic>[];
      final Map<String, dynamic> sts = _licData!['states'] is Map
          ? Map<String, dynamic>.from(_licData!['states'] as Map)
          : <String, dynamic>{};
      if (sts[stateSlug] is Map) st = Map<String, dynamic>.from(sts[stateSlug] as Map);
    }
    DateTime? wd;
    final dynamic ts = couple['weddingDate'];
    if (ts is Timestamp) wd = ts.toDate();
    String window = '';
    if (st != null && wd != null) {
      final int v = st['valid_days'] is num ? (st['valid_days'] as num).toInt() : 0;
      final int w = st['wait_days'] is num ? (st['wait_days'] as num).toInt() : 0;
      final DateTime latest = wd.subtract(Duration(days: w));
      if (v > 0) {
        final DateTime earliest = wd.subtract(Duration(days: v));
        window = 'Apply between ${_licDate(earliest)} and ${_licDate(latest)}';
      } else {
        window = 'Apply by ${_licDate(latest)} - it does not expire';
      }
      final int daysToLatest = latest.difference(DateTime.now()).inDays;
      if (!done && daysToLatest < 0) {
        window += ' · that was ${-daysToLatest} day${daysToLatest == -1 ? '' : 's'} ago';
      } else if (!done && daysToLatest <= 14) {
        window += ' · ${daysToLatest == 0 ? 'today' : 'in $daysToLatest day${daysToLatest == 1 ? '' : 's'}'}';
      }
    }
    final String fee = st == null ? '' : (st['fee_text'] ?? '').toString();
    final String issuer = st == null ? '' : (st['issuer'] ?? '').toString();
    final String stateName = st == null ? '' : (st['name'] ?? '').toString();
    final String siteUrl = stateSlug.isEmpty
        ? 'https://meetlazo.com/marriage-license/'
        : 'https://meetlazo.com/marriage-license/$stateSlug/';

    Future<void> toggle() async {
      try {
        await _coupleRef.set(<String, dynamic>{
          'licenseDone': !done,
          'licenseDoneAt': done ? FieldValue.delete() : FieldValue.serverTimestamp(),
        }, SetOptions(merge: true));
      } catch (e) {
        _toast('Could not save that: ' + e.toString());
      }
    }

    return _glass(
      padding: const EdgeInsets.all(18),
      radius: 22,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(children: <Widget>[
            const Expanded(
              child: Text('Marriage license',
                  style: TextStyle(
                      color: plum, fontSize: 16, fontWeight: FontWeight.w800)),
            ),
            _Press(
              tick: _Tick.select,
              onTap: toggle,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: done ? vGreen : Colors.white,
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: done ? vGreen : goldLine),
                ),
                child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                  Icon(done ? Icons.check_rounded : Icons.radio_button_unchecked_rounded,
                      size: 14, color: done ? Colors.white : muted),
                  const SizedBox(width: 5),
                  Text(done ? 'We have it' : 'Not yet',
                      style: TextStyle(
                          color: done ? Colors.white : plum,
                          fontSize: 12,
                          fontWeight: FontWeight.w800)),
                ]),
              ),
            ),
          ]),
          const SizedBox(height: 8),
          if (done)
            const Text('Bring it on the day - the officiant signs it and returns it to the office.',
                style: TextStyle(fontSize: 12.5, color: muted, height: 1.4))
          else if (st == null) ...<Widget>[
            Text(
                _licLoading
                    ? 'Looking up your state…'
                    : (metro.isEmpty
                        ? 'Set your city in Account and we’ll show the fee, the office and when to apply.'
                        : (_licErr.isNotEmpty ? _licErr : 'The fee, the office and when to apply, for your state.')),
                style: const TextStyle(fontSize: 12.5, color: muted, height: 1.4)),
            const SizedBox(height: 8),
            _Press(
              onTap: () async {
                final Uri u = Uri.parse(siteUrl);
                if (await canLaunchUrl(u)) await launchUrl(u, mode: LaunchMode.externalApplication);
              },
              child: const Text('Every state, on meetlazo.com →',
                  style: TextStyle(color: plum, fontSize: 12.5, fontWeight: FontWeight.w800)),
            ),
          ] else ...<Widget>[
            Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
              _licPill(fee, 'fee'),
              _licPill((st['wait_text'] ?? '').toString(), 'wait'),
              _licPill((st['valid_text'] ?? '').toString(), 'lasts'),
              _licPill(
                  (st['witnesses'] is num && (st['witnesses'] as num) > 0)
                      ? '${(st['witnesses'] as num).toInt()} witness${(st['witnesses'] as num) > 1 ? 'es' : ''}'
                      : 'No witnesses',
                  'ceremony'),
            ]),
            if (window.isNotEmpty) ...<Widget>[
              const SizedBox(height: 10),
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                const Icon(Icons.event_available_rounded, size: 16, color: Color(0xFF8A6A2F)),
                const SizedBox(width: 6),
                Expanded(
                    child: Text(window,
                        style: const TextStyle(
                            color: Color(0xFF8A6A2F), fontSize: 13, fontWeight: FontWeight.w800, height: 1.35))),
              ]),
            ],
            const SizedBox(height: 10),
            Text('$stateName: issued by the ${issuer.toLowerCase()}. Both of you go, with photo ID.',
                style: const TextStyle(fontSize: 12.5, color: muted, height: 1.4)),
            if ((st['course'] ?? '').toString().isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text((st['course'] ?? '').toString(),
                    style: const TextStyle(fontSize: 12, color: muted, height: 1.4)),
              ),
            const SizedBox(height: 8),
            for (final dynamic o in offices.take(3))
              if (o is Map)
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: _Press(
                    onTap: () async {
                      final Uri u = Uri.parse((o['site'] ?? siteUrl).toString());
                      if (await canLaunchUrl(u)) await launchUrl(u, mode: LaunchMode.externalApplication);
                    },
                    child: Container(
                      padding: const EdgeInsets.fromLTRB(12, 9, 12, 9),
                      decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: goldLine)),
                      child: Row(children: <Widget>[
                        Expanded(
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                            Text('${o['county'] ?? ''} · ${o['office'] ?? ''}',
                                style: const TextStyle(color: ink, fontSize: 13, fontWeight: FontWeight.w700)),
                            if ((o['note'] ?? '').toString().isNotEmpty || (o['fee'] ?? '').toString().isNotEmpty)
                              Text(
                                  <String>[
                                    if ((o['fee'] ?? '').toString().isNotEmpty) 'about \$${o['fee']}',
                                    if ((o['note'] ?? '').toString().isNotEmpty) (o['note'] ?? '').toString(),
                                  ].join(' · '),
                                  style: const TextStyle(fontSize: 11.5, color: muted, height: 1.35)),
                          ]),
                        ),
                        const Icon(Icons.open_in_new_rounded, size: 15, color: plum),
                      ]),
                    ),
                  ),
                ),
            _Press(
              onTap: () async {
                final Uri u = Uri.parse(siteUrl);
                if (await canLaunchUrl(u)) await launchUrl(u, mode: LaunchMode.externalApplication);
              },
              child: Text('Everything about the $stateName license →',
                  style: const TextStyle(color: plum, fontSize: 12.5, fontWeight: FontWeight.w800)),
            ),
          ],
        ],
      ),
    );
  }

  Widget _licPill(String v, String k) {
    if (v.isEmpty) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
          color: gold.withOpacity(.16),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: gold.withOpacity(.55))),
      child: Text('$v · $k',
          style: const TextStyle(color: Color(0xFF8A6A2F), fontSize: 11.5, fontWeight: FontWeight.w800)),
    );
  }

  Widget _weatherCard(Map<String, dynamic> couple) {''', "license card")

# 3. header history line
swap("// (v131: THE TIMELINE, ANCHORED",
     "// (v132: MARRIAGE LICENSE - a card on the Day-Of screen reads meetlazo.com/marriage-license/data.json, picks the state from the couple's metro, and shows the fee, wait, validity, witnesses, the county office (tap to open) and the application window worked out from the wedding date; a We-have-it toggle writes couples.licenseDone. JC-LAZO-COUPLE-0920-LIC-001; base v131) (v131: THE TIMELINE, ANCHORED",
     "header")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT} ({len(s):,} chars)")
