"""patch_couple_v146.py - JC-LAZO-COUPLE-1007-V146
COUPLE VIEW, DONE PROPERLY. A vendor who taps "Couple view" on their dashboard
used to land in a bare couple plan with no way back (the return button was
shown only to the App Store review account), seed a real couples/{uid} doc that
analytics counted as a couple, and could message listings - including their
own - creating real inquiries. Now:
  - the role is read once up front (users/{uid}); a vendor-role login is PREVIEW
    MODE: a gold bar across the top says "Previewing as a couple" with "Back to
    your dashboard" always present, and the role guard never bounces them;
  - the preview plan is seeded as theirs would look to a couple: couples/{uid}
    {preview: true, names 'Jordan & Sam', a date ~6 months out, their metro},
    their own category booked with their business name, the rest 'needed';
  - messaging vendors is off in preview (toast), so no inquiries, leads, texts
    or counts come from a vendor looking around;
  - "View your public page" in the bar opens their meetlazo.com listing.
Server side (functions-dashboard 025 / functions analytics): couples with
preview: true are skipped by the analytics rollup, the welcome email and the
couple milestone emails.

Anchor-and-assert against Couple_master_v145.txt; writes Couple_master_v146.txt.
  python app-patches\\patch_couple_v146.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent
src = HERE / "Couple_master_v145.txt"; dst = HERE / "Couple_master_v146.txt"
s = src.read_text(encoding="utf-8")
if "COUPLE-1007-V146" in s:
    raise SystemExit("already patched")

def rep(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    s = s.replace(old, new)

rep("// (v145: TALK TO JUNE",
    "// (v146: COUPLE VIEW DONE PROPERLY - a vendor-role login is preview mode: gold bar with Back to your dashboard and View your public page, no role bounce, preview-flagged plan seeded with their own listing booked, messaging off. JC-LAZO-COUPLE-1007-V146; base v145)\n// (v145: TALK TO JUNE",
    "build note")

# ---- state: who is previewing
rep("  String? _coupleIdCache;",
    "  String? _coupleIdCache;\n"
    "  // v146: set when a vendor-role login is looking at the couple side.\n"
    "  Map<String, dynamic>? _previewVendor;\n"
    "  String _previewVendorId = '';\n"
    "  bool _roleChecked = false;",
    "state")

# ---- seeding: read the role first; vendors get a flagged preview plan with their own listing booked
rep('''  Future<void> _ensureSeeded() async {
    if (_uid == null || _seeding) return;
    _seeding = true;
    try {
      final snap = await _planRef.limit(1).get();
      if (snap.docs.isEmpty) {
        final batch = FirebaseFirestore.instance.batch();
        for (final c in kCategories) {
          batch.set(_planRef.doc(c['slug']), {
            'status': 'needed',
            'vendorName': '',
            'vendorId': null,
            'budgetPlanned': null,
            'budgetActual': null,
            'updatedAt': FieldValue.serverTimestamp(),
          });
        }
        batch.set(_coupleRef, {'createdAt': FieldValue.serverTimestamp()},
            SetOptions(merge: true));
        await batch.commit();
      }
    } catch (_) {
    } finally {
      _seeding = false;
    }
  }''',
'''  // v146: a vendor looking at the couple side. Reads users/{uid} once; a
  // vendor-role login resolves to their listing (users.vendorId, else the
  // listing they claimed). Null for couples.
  Future<Map<String, dynamic>?> _loadPreviewVendor() async {
    if (_uid == null) return null;
    try {
      final DocumentSnapshot<Map<String, dynamic>> us =
          await FirebaseFirestore.instance.collection('users').doc(_uid).get();
      final Map<String, dynamic> u = us.data() ?? <String, dynamic>{};
      if ((u['role'] ?? '').toString() != 'vendor') return null;
      String vid = (u['vendorId'] ?? '').toString();
      Map<String, dynamic>? v;
      if (vid.isNotEmpty) {
        final DocumentSnapshot<Map<String, dynamic>> vs =
            await FirebaseFirestore.instance.collection('vendors').doc(vid).get();
        v = vs.data();
      }
      if (v == null) {
        final QuerySnapshot<Map<String, dynamic>> q = await FirebaseFirestore
            .instance
            .collection('vendors')
            .where('claimedBy', isEqualTo: _uid)
            .limit(1)
            .get();
        if (q.docs.isNotEmpty) {
          vid = q.docs.first.id;
          v = q.docs.first.data();
        }
      }
      _previewVendorId = vid;
      return v ?? <String, dynamic>{'name': 'Your business'};
    } catch (e) {
      debugPrint('LAZO preview vendor: ' + e.toString());
      return null;
    }
  }

  Future<void> _ensureSeeded() async {
    if (_uid == null || _seeding) return;
    _seeding = true;
    try {
      // v146: know who this is before writing anything
      if (!_roleChecked) {
        final Map<String, dynamic>? pv = await _loadPreviewVendor();
        _roleChecked = true;
        if (mounted) setState(() => _previewVendor = pv);
      }
      final snap = await _planRef.limit(1).get();
      if (snap.docs.isEmpty) {
        final batch = FirebaseFirestore.instance.batch();
        final Map<String, dynamic>? pv = _previewVendor;
        final String mine = pv == null ? '' : _vendorCat(pv);
        for (final c in kCategories) {
          final bool own = pv != null && c['slug'] == mine;
          batch.set(_planRef.doc(c['slug']), {
            'status': own ? 'booked' : 'needed',
            'vendorName': own ? (pv['name'] ?? '').toString() : '',
            'vendorId': own && _previewVendorId.isNotEmpty ? _previewVendorId : null,
            'budgetPlanned': null,
            'budgetActual': null,
            if (pv != null) 'preview': true,
            'updatedAt': FieldValue.serverTimestamp(),
          });
        }
        if (pv == null) {
          batch.set(_coupleRef, {'createdAt': FieldValue.serverTimestamp()},
              SetOptions(merge: true));
        } else {
          // a stand-in couple so the vendor sees the product as a couple does;
          // preview: true keeps it out of analytics, June and every email
          batch.set(
              _coupleRef,
              {
                'createdAt': FieldValue.serverTimestamp(),
                'preview': true,
                'names': 'Jordan & Sam',
                'weddingDate': Timestamp.fromDate(
                    DateTime.now().add(const Duration(days: 183))),
                if ((pv['metroId'] ?? '').toString().isNotEmpty)
                  'metroId': (pv['metroId'] ?? '').toString(),
                'guestEstimate': 120,
              },
              SetOptions(merge: true));
        }
        await batch.commit();
      }
    } catch (_) {
    } finally {
      _seeding = false;
    }
  }''',
    "seeding")

# ---- the role guard never bounces a previewing vendor
rep('''  Future<void> _guardRole() async {
    if (_uid == null) {
      return;
    }
    if (await _consumeViewSwitch()) {
      return; // v130: they asked to be here
    }''',
'''  Future<void> _guardRole() async {
    if (_uid == null) {
      return;
    }
    // v146: a vendor on the couple side is in preview mode, with the bar and
    // the way back always on screen - nothing to bounce.
    if (_previewVendor != null) {
      return;
    }
    if (await _consumeViewSwitch()) {
      return; // v130: they asked to be here
    }''',
    "guard")
rep('''      final String role = data['role'] == null ? '' : data['role'].toString();
      if (role == 'vendor') {
        if (mounted) {
          context.goNamed('VendorHome');
        }
      }''',
'''      final String role = data['role'] == null ? '' : data['role'].toString();
      if (role == 'vendor') {
        // v146: late discovery (seeding hadn't resolved yet): stay, in preview.
        if (_previewVendor == null) {
          final Map<String, dynamic>? pv = await _loadPreviewVendor();
          if (mounted) setState(() => _previewVendor = pv ?? <String, dynamic>{'name': 'Your business'});
        }
      }''',
    "guard role")

# ---- messaging is off in preview
rep('''  Future<void> _sendInquiry(Map<String, dynamic> v) async {
    final placeId = (v['placeId'] as String?) ?? '';
    final vendorName = (v['name'] as String?) ?? 'this vendor';
    if (placeId.isEmpty || _uid == null) return;''',
'''  Future<void> _sendInquiry(Map<String, dynamic> v) async {
    final placeId = (v['placeId'] as String?) ?? '';
    final vendorName = (v['name'] as String?) ?? 'this vendor';
    if (placeId.isEmpty || _uid == null) return;
    // v146: a vendor looking around must never create a real inquiry
    if (_previewVendor != null) {
      _toast(
          'Preview mode: messaging vendors is off here. This is what a couple would see when they reach out to $vendorName.');
      return;
    }''',
    "send inquiry gate")

# ---- the bar: wrap the shell
rep('''              _syncBookedFromInquiries(plan);
              return _shell(couple, plan);''',
'''              _syncBookedFromInquiries(plan);
              return _withPreviewBar(_shell(couple, plan));''',
    "shell wrap")
rep('''  Widget _shell(
      Map<String, dynamic> couple, Map<String, Map<String, dynamic>> plan) {''',
'''  // v146: the preview frame for a vendor on the couple side. Always carries
  // the way back; the demo-account button below the hero is no longer needed
  // for real vendors.
  Widget _withPreviewBar(Widget shell) {
    final Map<String, dynamic>? pv = _previewVendor;
    if (pv == null) return shell;
    final String name = (pv['name'] ?? 'your business').toString();
    final String metro = (pv['metroId'] ?? '').toString();
    final String slug = (pv['slug'] ?? _previewVendorId).toString();
    final String pageUrl = metro.isNotEmpty && slug.isNotEmpty
        ? 'https://meetlazo.com/vendors/$metro/$slug'
        : 'https://meetlazo.com/vendors/';
    return Column(children: <Widget>[
      SafeArea(
        bottom: false,
        child: Container(
          width: double.infinity,
          color: gold,
          padding: const EdgeInsets.fromLTRB(14, 8, 10, 8),
          child: Wrap(
            crossAxisAlignment: WrapCrossAlignment.center,
            alignment: WrapAlignment.spaceBetween,
            runSpacing: 6,
            children: <Widget>[
              Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                const Icon(Icons.visibility_rounded, size: 16, color: plumDeep),
                const SizedBox(width: 8),
                Text('Previewing as a couple \\u00b7 $name',
                    style: const TextStyle(
                        color: plumDeep,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w700)),
              ]),
              Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                TextButton(
                  onPressed: () async {
                    try {
                      await launchUrl(Uri.parse(pageUrl),
                          mode: LaunchMode.externalApplication);
                    } catch (_) {}
                  },
                  style: TextButton.styleFrom(
                      foregroundColor: plumDeep,
                      padding: const EdgeInsets.symmetric(horizontal: 10),
                      minimumSize: const Size(0, 34)),
                  child: const Text('View your public page',
                      style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600)),
                ),
                const SizedBox(width: 4),
                FilledButton(
                  onPressed: () async {
                    await _markViewSwitch();
                    if (mounted) {
                      context.goNamed('VendorHome');
                    }
                  },
                  style: FilledButton.styleFrom(
                      backgroundColor: plumDeep,
                      foregroundColor: gold,
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      minimumSize: const Size(0, 34),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(999))),
                  child: const Text('Back to your dashboard',
                      style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
                ),
              ]),
            ],
          ),
        ),
      ),
      Expanded(child: shell),
    ]);
  }

  Widget _shell(
      Map<String, dynamic> couple, Map<String, Map<String, dynamic>> plan) {''',
    "preview bar")

dst.write_text(s, encoding="utf-8")
print("wrote", dst.name, len(s), "chars")
