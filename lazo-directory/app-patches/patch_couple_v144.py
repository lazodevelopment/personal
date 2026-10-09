"""patch_couple_v144.py - Couple dashboard v144
Couple_master_v143.txt -> Couple_master_v144.txt. Anchor-asserted.
  WELCOME PAGES LAND PRE-FILLED. The five meetlazo.com/welcome/<hook>/ ad landing
  pages (JC-LAZO-WELCOME-1003) send the app
    ?from=welcome-<page>&intent=<yes|website|budget|import>&names=&date=&metro=
     &design=&source=&guests=&month=  (+ utm_*, fbclid)
  Until now the dashboard read only ?vendor, ?save and ?template, so a couple who
  typed their names and date on the landing page got the blank start screen.
  Now _openPendingWelcome():
    - writes names, weddingDate and metroId onto the couple doc when the doc has
      none (never overwrites what a couple or partner already set), and the guest
      estimate from the budget page as couples.guestEstimate;
    - keeps first-touch attribution on couples.acq {from, intent, source, utm_*,
      fbclid, at} once, so sign-ups can be read back per ad hook;
    - opens what the ad promised: intent=website -> the website editor on the
      chosen design (through the v96 pending-template path), intent=budget -> the
      budget sheet, intent=import -> the Knot/Zola import sheet, intent=yes (or
      none) -> the setup sheet if anything is still missing, else home.
  URL first; else the JSON the auth flow stashes in SharedPreferences
  'lazo_pending_welcome' (goNamed drops the query string - see
  Auth_stash_welcome.txt for the FlutterFlow action that stashes it).
  python app-patches\\patch_couple_v144.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "Couple_master_v143.txt"
DST = HERE / "Couple_master_v144.txt"
s = SRC.read_text(encoding="utf-8")

# 1. boot: run the welcome handler beside the other pending-parameter handlers
old = """    _openPendingVendor();
    _openPendingTemplate();
    _openPendingSave();
"""
new = """    _openPendingVendor();
    _openPendingTemplate();
    _openPendingSave();
    _openPendingWelcome(); // v144
"""
assert s.count(old) == 1, f"boot anchor x{s.count(old)}"
s = s.replace(old, new)

# 2. the handler, placed before the v96 pending-template handler
anchor = """  // v96: they chose a design on meetlazo.com/wedding-websites ("Use Sage")."""
assert s.count(anchor) == 1, f"v96 anchor x{s.count(anchor)}"
handler = r"""  // v144: the meetlazo.com/welcome/<hook>/ landing pages (the Meta ad funnels)
  // send ?from=welcome-<page>&intent=<yes|website|budget|import>&names=&date=
  // &metro=&design=&source=&guests= (+ utm_*). Names, date and city land on the
  // couple doc when it has none, first-touch attribution is kept once on
  // couples.acq, and the intent opens the screen the ad promised. URL first;
  // else the JSON the auth flow stashed in SharedPreferences
  // 'lazo_pending_welcome' (goNamed drops the query string).
  Future<void> _openPendingWelcome() async {
    if (_uid == null) return;
    Map<String, String> p = <String, String>{};
    try {
      final Map<String, String> q = Uri.base.queryParameters;
      final bool ours = (q['from'] ?? '').startsWith('welcome') ||
          (q['intent'] ?? '').isNotEmpty ||
          (q['names'] ?? '').isNotEmpty ||
          (q['date'] ?? '').isNotEmpty;
      if (ours) p = Map<String, String>.from(q);
    } catch (_) {}
    SharedPreferences? prefs;
    try {
      prefs = await SharedPreferences.getInstance();
      if (p.isEmpty) {
        final String raw = prefs.getString('lazo_pending_welcome') ?? '';
        if (raw.isNotEmpty) {
          final dynamic j = jsonDecode(raw);
          if (j is Map) {
            p = j.map((dynamic k, dynamic v) =>
                MapEntry<String, String>(k.toString(), (v ?? '').toString()));
          }
        }
      }
    } catch (_) {}
    if (p.isEmpty) return;
    try {
      await prefs?.remove('lazo_pending_welcome');
    } catch (_) {}
    final String from = (p['from'] ?? '').trim();
    final String intent = (p['intent'] ?? '').trim().toLowerCase();
    final String names = (p['names'] ?? '').trim();
    final String dateS = (p['date'] ?? '').trim();
    final String metro =
        (p['metro'] ?? p['metroId'] ?? '').trim().toLowerCase();
    final String design =
        (p['design'] ?? p['template'] ?? '').trim().toLowerCase();
    final String source = (p['source'] ?? '').trim();
    final int? guests = int.tryParse((p['guests'] ?? '').trim());
    try {
      // let _loadCoupleId land first so a partner's shared plan is the target
      await Future<void>.delayed(const Duration(milliseconds: 600));
      if (!mounted) return;
      final DocumentSnapshot<Map<String, dynamic>> c = await _coupleRef.get();
      final Map<String, dynamic> couple = c.data() ?? <String, dynamic>{};
      final Map<String, dynamic> up = <String, dynamic>{};
      if (names.isNotEmpty &&
          names.length <= 80 &&
          (couple['names'] ?? '').toString().trim().isEmpty) {
        up['names'] = names;
      }
      if (dateS.isNotEmpty && couple['weddingDate'] == null) {
        final DateTime? d = DateTime.tryParse(dateS);
        if (d != null && d.year >= 2024 && d.year <= 2040) {
          up['weddingDate'] = Timestamp.fromDate(d);
        }
      }
      if (metro.isNotEmpty &&
          (couple['metroId'] ?? '').toString().isEmpty &&
          kMetros.any((Map<String, String> m) => m['id'] == metro)) {
        up['metroId'] = metro;
      }
      if (guests != null &&
          guests > 0 &&
          guests <= 2000 &&
          couple['guestEstimate'] == null) {
        up['guestEstimate'] = guests;
      }
      if (couple['acq'] == null && (from.isNotEmpty || intent.isNotEmpty)) {
        final Map<String, dynamic> acq = <String, dynamic>{
          'from': from,
          'intent': intent,
          if (source.isNotEmpty) 'source': source,
          'at': FieldValue.serverTimestamp(),
        };
        for (final String k in <String>[
          'utm_source',
          'utm_medium',
          'utm_campaign',
          'utm_content',
          'utm_term',
          'fbclid'
        ]) {
          final String v = (p[k] ?? '').trim();
          if (v.isNotEmpty) acq[k] = v.length > 200 ? v.substring(0, 200) : v;
        }
        up['acq'] = acq;
      }
      if (up.isNotEmpty) {
        up['updatedAt'] = FieldValue.serverTimestamp();
        await _coupleRef.set(up, SetOptions(merge: true));
      }
      final Map<String, dynamic> merged = <String, dynamic>{...couple, ...up};
      // give the shell a frame to mount, like the other handlers
      await Future<void>.delayed(const Duration(milliseconds: 500));
      if (!mounted) return;
      switch (intent) {
        case 'website':
          if (design.isNotEmpty) {
            try {
              await prefs?.setString('lazo_pending_template', design);
            } catch (_) {}
            await _openPendingTemplate(); // v96 path: opens the editor on it
          } else {
            setState(() => _view = _View.website);
          }
          break;
        case 'budget':
          Map<String, Map<String, dynamic>> plan =
              <String, Map<String, dynamic>>{};
          try {
            final QuerySnapshot<Map<String, dynamic>> ps = await _planRef.get();
            plan = <String, Map<String, dynamic>>{
              for (final QueryDocumentSnapshot<Map<String, dynamic>> d
                  in ps.docs)
                d.id: d.data()
            };
          } catch (_) {}
          if (!mounted) return;
          await _budgetSheet(merged, plan);
          break;
        case 'import':
          await _importSheet(merged);
          break;
        default:
          final bool missing = (merged['names'] ?? '').toString().trim().isEmpty ||
              merged['weddingDate'] == null ||
              (merged['metroId'] ?? '').toString().isEmpty;
          if (missing) {
            await _setupSheet(merged);
          } else if (up.isNotEmpty) {
            _toast('Welcome. Your date and city are in - here’s your plan.');
          }
      }
    } catch (e) {
      debugPrint('LAZO pending welcome: ' + e.toString());
    }
  }

"""
s = s.replace(anchor, handler + anchor, 1)

# 3. header note
hdr_old = "// (v142:"
assert s.count(hdr_old) >= 1
s = s.replace(
    hdr_old,
    "// (v144: WELCOME PAGES LAND PRE-FILLED - meetlazo.com/welcome/<hook>/ (the Meta ad funnels) send ?from=&intent=&names=&date=&metro=&design=&source=&guests= (+utm_*); names, date and city fill the couple doc when empty, first-touch attribution is kept on couples.acq, and the intent opens the website editor / budget sheet / Knot-Zola import / setup. JC-LAZO-COUPLE-1004-V144; base v143)\n"
    + hdr_old,
    1)

DST.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {DST.name}: {len(s):,} chars; brace balance {s.count('{') - s.count('}')}, paren balance {s.count('(') - s.count(')')}")
