r"""patch_vendor_v201.py - Vendor v199 -> v201: CERTIFICATES OF INSURANCE ON FILE.  JC-LAZO-COI-1016-VENDOR

Every vendor: an "Insurance (COI)" card on the Profile tab. Upload a PDF or a photo of the certificate, June reads
the insurer, limits, dates, holder and additional insureds (coiRead), the vendor checks them and sends it to Lazo
venues and planners (search, or the ones in their metro) or emails it to a venue that isn't on Lazo (coiSave /
coiShare). Each COI opens to "On file with": who has it, when they viewed it, whether the certificate names them,
and a remove button. "Upload renewal" replaces it at every venue that had it. Open requests from venues show on the
card with a one-tap Send.

Venues and planners (category wedding-venues / wedding-planners) also get "COIs on file": every vendor's latest
certificate, Current / Expires in N days / Expired, "Names you" or not, a 10-minute download (coiFileLink), "Ask for
renewal", and "Request" to ask any vendor for theirs (coiRequest). Bell entries with open == 'coi' land on Profile.

Numbered v201: v200 is claimed by video calls. Built on v199 because v200 is not built yet; whichever of the two
is pasted second must be rebuilt on the other (this script's anchors are all outside the video-call areas).

Needs, before the paste: functions-dashboard coi.js (coiRead, coiSave, coiShare, coiUnshare, coiFileLink,
coiRequest, coiPublic, coiSweep), firestore.rules JC-LAZO-RULES-1016-COI, storage.rules JC-LAZO-STORAGE-1016-COI.

    python app-patches\patch_vendor_v201.py      # writes Vendor_master_v201.txt
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC, DST = HERE / "Vendor_master_v199.txt", HERE / "Vendor_master_v201.txt"
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
    "// Build ID: JC-LAZO-COI-1016-VENDOR (v201: CERTIFICATES OF INSURANCE - every vendor uploads a COI once, June reads "
    "it, and it goes on file with the Lazo venues and planners they pick (or by email to a venue not on Lazo); renewals "
    "replace it everywhere; venues and planners get 'COIs on file' with expiry status, downloads, Ask for renewal and "
    "Request; base v199, v200 is video calls)\n")

# ---- the bell: COI notices open the Profile tab
rep("""          } else if (openTo == 'reviews') {
            setState(() => _dashMode = 'studio');
          }
""", """          } else if (openTo == 'reviews') {
            setState(() => _dashMode = 'studio');
          } else if (openTo == 'coi') {
            setState(() => _dashMode = 'profile');
          }
""")
rep("""  IconData _feedIcon(String k) {
    switch (k) {
""", """  IconData _feedIcon(String k) {
    switch (k) {
      case 'coi':
        return Icons.verified_user_rounded;
""")

# ---- Profile: the vendor's own COIs for everyone, COIs on file for venues and planners
rep("""                _teamCardV(vendorId, vd),
                const SizedBox(height: 16),
                _realWeddingsCard(vendorId, vd),
""", """                _teamCardV(vendorId, vd),
                const SizedBox(height: 16),
                if (_coiReceiver(vd)) ...<Widget>[
                  _coisOnFileCard(vendorId, vd),
                  const SizedBox(height: 16),
                ],
                _coiCard(vendorId, vd),
                const SizedBox(height: 16),
                _realWeddingsCard(vendorId, vd),
""")

# ---- the COI code, before _disconnectWhop
rep("  Future<void> _disconnectWhop(String vendorId) async {\n", r"""  // ===================== v201: CERTIFICATES OF INSURANCE (JC-LAZO-COI-1016-VENDOR) =====================
  // A vendor keeps their COI on file with the Lazo venues and planners they work with (functions-dashboard
  // coi.js). Venues and planners see every COI sent to them and can ask a vendor for one.
  static const List<String> _coiReceivers = <String>['wedding-venues', 'wedding-planners'];
  static const List<String> _coiMonths = <String>['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  static const Map<String, String> _coiLines = <String, String>{
    'general': 'General liability', 'auto': 'Auto', 'umbrella': 'Umbrella', 'workers': 'Workers\u2019 comp',
    'liquor': 'Liquor liability', 'professional': 'Professional', 'other': 'Other',
  };
  static const Color _coiRed = Color(0xFFB3261E);
  static const Color _coiAmber = Color(0xFFB7791F);
  String _coiFilter = 'all';

  bool _coiReceiver(Map<String, dynamic> vd) {
    final List<String> cats = <String>[
      (vd['category'] ?? '').toString(),
      ...((vd['categories'] as List?) ?? const <dynamic>[]).map((dynamic c) => c.toString()),
    ];
    return cats.any(_coiReceivers.contains);
  }

  DateTime? _coiDate(dynamic v) {
    if (v is Timestamp) return v.toDate();
    if (v is String && v.length >= 10) return DateTime.tryParse(v.substring(0, 10));
    return null;
  }

  String _coiDay(DateTime? d) => d == null ? '' : '${_coiMonths[d.month - 1]} ${d.day}, ${d.year}';
  String _coiYmd(DateTime d) => '${d.year}-${d.month < 10 ? '0' : ''}${d.month}-${d.day < 10 ? '0' : ''}${d.day}';

  int? _coiLeft(DateTime? d) {
    if (d == null) return null;
    final DateTime n = DateTime.now();
    return DateTime(d.year, d.month, d.day).difference(DateTime(n.year, n.month, n.day)).inDays;
  }

  String _coiMoney(dynamic v) {
    final num n = v is num ? v : (num.tryParse((v ?? '').toString().replaceAll(RegExp(r'[^0-9.]'), '')) ?? 0);
    if (n <= 0) return '';
    if (n >= 1000000) {
      final double m = n / 1000000;
      return '\$${m == m.roundToDouble() ? m.toInt() : m.toStringAsFixed(1)}M';
    }
    if (n >= 1000) return '\$${(n / 1000).round()}K';
    return '\$${n.round()}';
  }

  /// 'current' | 'soon' (30 days or less) | 'expired' | 'replaced'
  String _coiState(Map<String, dynamic> c) {
    final String s = (c['status'] ?? '').toString();
    if (s == 'replaced' || s == 'removed') return 'replaced';
    final int? left = _coiLeft(_coiDate(c['expiresAt']));
    if (s == 'expired' || (left != null && left < 0)) return 'expired';
    if (left != null && left <= 30) return 'soon';
    return 'current';
  }

  Widget _coiChip(Map<String, dynamic> c) {
    final String st = _coiState(c);
    final int left = _coiLeft(_coiDate(c['expiresAt'])) ?? 0;
    final Color col = st == 'expired' ? _coiRed : st == 'soon' ? _coiAmber : st == 'replaced' ? muted : vGreen;
    final String label = st == 'expired'
        ? 'Expired'
        : st == 'replaced'
            ? 'Replaced'
            : st == 'soon'
                ? (left == 0 ? 'Expires today' : 'Expires in $left day${left == 1 ? '' : 's'}')
                : 'Current';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
          color: col.withOpacity(.12),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: col.withOpacity(.45))),
      child: Text(label, style: TextStyle(color: col, fontSize: 11, fontWeight: FontWeight.w800)),
    );
  }

  /// Same test as coi.js namedOn: most of the venue's name appears in the holder or an additional insured.
  bool _coiNamed(String venue, String holder, List<String> named) {
    const Set<String> stop = <String>{
      'the', 'a', 'an', 'and', 'of', 'at', 'llc', 'inc', 'co', 'company', 'ltd', 'corp', 'venue', 'venues',
      'events', 'event', 'weddings', 'wedding', 'its', 'their', 'all', 'as', 'additional', 'insured', 'insureds',
      'certificate', 'holder'
    };
    List<String> words(String x) => x
        .toLowerCase()
        .replaceAll('&', ' and ')
        .replaceAll(RegExp(r'[^a-z0-9 ]+'), ' ')
        .split(RegExp(r'\s+'))
        .where((String w) => w.isNotEmpty && !stop.contains(w))
        .toList();
    final List<String> want = words(venue);
    if (want.isEmpty) return false;
    for (final String t in <String>[holder, ...named]) {
      final Set<String> have = words(t).toSet();
      if (want.where(have.contains).length / want.length >= .6) return true;
    }
    return false;
  }

  int _coiReach(Map<String, dynamic> c) =>
      ((c['venueIds'] as List?) ?? const <dynamic>[]).length +
      ((c['offLazo'] as List?) ?? const <dynamic>[]).whereType<Map>().where((Map o) => o['stopped'] != true).length;

  // ---------------------------------------------------------------- the vendor's card
  Widget _coiCard(String vendorId, Map<String, dynamic> vd) {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _liveQuery('cois:$vendorId',
          () => FirebaseFirestore.instance.collection('cois').where('vendorId', isEqualTo: vendorId)),
      builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> snap) {
        final List<QueryDocumentSnapshot<Map<String, dynamic>>> live =
            (snap.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[])
                .where((QueryDocumentSnapshot<Map<String, dynamic>> d) => _coiState(d.data()) != 'replaced')
                .toList()
              ..sort((QueryDocumentSnapshot<Map<String, dynamic>> a, QueryDocumentSnapshot<Map<String, dynamic>> b) =>
                  (_coiDate(b.data()['expiresAt']) ?? DateTime(2000))
                      .compareTo(_coiDate(a.data()['expiresAt']) ?? DateTime(2000)));
        return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
          stream: _liveQuery(
              'coiAsks:$vendorId',
              () => FirebaseFirestore.instance
                  .collection('coiRequests')
                  .where('vendorId', isEqualTo: vendorId)
                  .where('status', isEqualTo: 'open')),
          builder: (BuildContext c2, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> rq) {
            final List<Map<String, dynamic>> asks = (rq.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[])
                .map((QueryDocumentSnapshot<Map<String, dynamic>> d) => d.data())
                .toList();
            final int reach = live.isEmpty ? 0 : _coiReach(live.first.data());
            return _glass(
              padding: const EdgeInsets.fromLTRB(18, 16, 18, 14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                Row(children: <Widget>[
                  _cardIconChip(Icons.verified_user_rounded),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                      Text('Insurance (COI)',
                          style: TextStyle(color: _lzFg(plum), fontSize: 15, fontWeight: FontWeight.w700)),
                      Text(
                          live.isEmpty
                              ? 'Upload your certificate of insurance once and send it to the venues and planners you work with. Renewals reach them on their own.'
                              : reach == 0
                                  ? 'Not sent to a venue yet. Tap it to send.'
                                  : 'On file with $reach venue${reach == 1 ? '' : 's'}. We remind you 30 and 7 days before it expires.',
                          style: TextStyle(fontSize: 12, color: _lzFg(muted), height: 1.35)),
                    ]),
                  ),
                  TextButton.icon(
                    onPressed: _h(() => _coiUploadSheet(vendorId, vd)),
                    icon: Icon(Icons.upload_file_rounded, size: 16, color: _lzFg(plum)),
                    label: Text(live.isEmpty ? 'Upload' : 'New',
                        style: TextStyle(color: _lzFg(plum), fontSize: 12.5, fontWeight: FontWeight.w800)),
                  ),
                ]),
                for (final Map<String, dynamic> a in asks) _coiAskRow(vendorId, vd, a, live),
                for (final QueryDocumentSnapshot<Map<String, dynamic>> d in live) _coiRow(vendorId, vd, d.id, d.data()),
              ]),
            );
          },
        );
      },
    );
  }

  Widget _coiRow(String vendorId, Map<String, dynamic> vd, String id, Map<String, dynamic> c) {
    final String st = _coiState(c);
    final int reach = _coiReach(c);
    final String gl = _coiMoney(c['glEach']);
    final bool img = ((c['file'] as Map?)?['contentType'] ?? '').toString().startsWith('image/');
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: _Press(
        scale: .985,
        onTap: () => _coiDetailSheet(vendorId, vd, id),
        child: Container(
          padding: const EdgeInsets.fromLTRB(12, 10, 8, 10),
          decoration: BoxDecoration(
              color: _lzBg(Colors.white.withOpacity(.7)),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: _lzLine(goldLine))),
          child: Row(children: <Widget>[
            Icon(img ? Icons.image_rounded : Icons.picture_as_pdf_rounded, color: _lzFg(plum), size: 22),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                Text((c['insurer'] ?? '').toString().isEmpty ? 'Certificate of insurance' : (c['insurer'] ?? '').toString(),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(color: _lzFg(ink), fontSize: 13.5, fontWeight: FontWeight.w800)),
                Text(
                    'Expires ${_coiDay(_coiDate(c['expiresAt']))}${gl.isEmpty ? '' : ' \u00b7 GL $gl'} \u00b7 ${reach == 0 ? 'not sent yet' : 'on file with $reach'}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 11.5, color: _lzFg(muted))),
              ]),
            ),
            const SizedBox(width: 6),
            _coiChip(c),
            if (st == 'soon' || st == 'expired')
              IconButton(
                tooltip: 'Upload the renewal',
                visualDensity: VisualDensity.compact,
                onPressed: _h(() => _coiUploadSheet(vendorId, vd, renewId: id, renewOf: c)),
                icon: Icon(Icons.autorenew_rounded, size: 18, color: _lzFg(plum)),
              )
            else
              Icon(Icons.chevron_right_rounded, color: _lzFg(muted), size: 20),
          ]),
        ),
      ),
    );
  }

  Widget _coiAskRow(String vendorId, Map<String, dynamic> vd, Map<String, dynamic> a,
      List<QueryDocumentSnapshot<Map<String, dynamic>>> live) {
    final String venueId = (a['venueId'] ?? '').toString();
    final String venueName = (a['venueName'] ?? 'A venue').toString();
    final String note = (a['note'] ?? '').toString();
    final List<QueryDocumentSnapshot<Map<String, dynamic>>> usable = live
        .where((QueryDocumentSnapshot<Map<String, dynamic>> d) => _coiState(d.data()) != 'expired')
        .toList();
    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.fromLTRB(12, 10, 10, 10),
      decoration: BoxDecoration(
          color: gold.withOpacity(.14),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: gold.withOpacity(.6))),
      child: Row(children: <Widget>[
        Icon(Icons.mark_email_unread_rounded, color: _lzFg(plum), size: 20),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Text('$venueName asked for your COI',
                style: TextStyle(color: _lzFg(ink), fontSize: 13.5, fontWeight: FontWeight.w800)),
            if (note.isNotEmpty)
              Text('\u201c$note\u201d',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 12, color: _lzFg(muted), fontStyle: FontStyle.italic)),
          ]),
        ),
        FilledButton(
          style: FilledButton.styleFrom(
              backgroundColor: gold,
              foregroundColor: plumDeep,
              minimumSize: const Size(0, 36),
              padding: const EdgeInsets.symmetric(horizontal: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(11))),
          onPressed: _h(() => usable.isNotEmpty
              ? _coiShare(usable.first.id, <String>[venueId])
              : _coiUploadSheet(vendorId, vd,
                  preVenues: <Map<String, dynamic>>[<String, dynamic>{'id': venueId, 'name': venueName}])),
          child: Text(usable.isNotEmpty ? 'Send' : 'Upload',
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
        ),
      ]),
    );
  }

  // ---------------------------------------------------------------- upload, read, send
  Future<void> _coiUploadSheet(String vendorId, Map<String, dynamic> vd,
      {String renewId = '',
      Map<String, dynamic>? renewOf,
      List<Map<String, dynamic>> preVenues = const <Map<String, dynamic>>[]}) async {
    if (vendorId.isEmpty) {
      _toast('One moment - your profile is still loading.');
      return;
    }
    FilePickerResult? res;
    try {
      res = await FilePicker.platform.pickFiles(
          type: FileType.custom,
          allowedExtensions: <String>['pdf', 'jpg', 'jpeg', 'png', 'webp'],
          withData: true);
    } catch (e) {
      _toast('Could not open your files: ' + _errText(e));
      return;
    }
    if (res == null || res.files.isEmpty || res.files.first.bytes == null) return;
    final PlatformFile pf = res.files.first;
    final Uint8List bytes = pf.bytes!;
    if (bytes.length > 15 * 1024 * 1024) {
      _toast('That file is over 15MB. The PDF from your agent is usually much smaller.');
      return;
    }
    final String ext = (pf.extension ?? pf.name.split('.').last).toLowerCase();
    final String ct = ext == 'pdf'
        ? 'application/pdf'
        : ext == 'png'
            ? 'image/png'
            : ext == 'webp'
                ? 'image/webp'
                : 'image/jpeg';
    final int ms = DateTime.now().millisecondsSinceEpoch;
    final String safe = pf.name.replaceAll(RegExp(r'[^A-Za-z0-9._-]'), '_');
    final String path = 'vendors/$vendorId/coi/c$ms/${ms}_$safe';
    _showJuneVeil('Uploading your certificate\u2026', 'Then June reads it for you.');
    try {
      await FirebaseStorage.instance.ref(path).putData(bytes, SettableMetadata(contentType: ct));
    } catch (e) {
      _popJuneVeil();
      _toast('Upload failed: ' + _errText(e));
      return;
    }
    Map<String, dynamic> read = <String, dynamic>{};
    String err = '';
    try {
      final HttpsCallableResult<dynamic> r = await FirebaseFunctions.instance
          .httpsCallable('coiRead', options: HttpsCallableOptions(timeout: const Duration(seconds: 120)))
          .call(<String, dynamic>{'vendorId': vendorId, 'path': path});
      read = Map<String, dynamic>.from((r.data as Map?) ?? <dynamic, dynamic>{});
    } on FirebaseFunctionsException catch (e) {
      err = _lzFnMsg(e, 'June couldn\u2019t read it. Type the details in.');
    } catch (_) {
      err = 'June couldn\u2019t read it. Type the details in.';
    }
    _popJuneVeil();
    if (!mounted) return;

    final List<Map<String, dynamic>> policies = ((read['policies'] as List?) ?? const <dynamic>[])
        .whereType<Map>()
        .map((Map m) => Map<String, dynamic>.from(m))
        .toList();
    final Map<String, dynamic> gl = policies.firstWhere((Map<String, dynamic> p) => p['line'] == 'general',
        orElse: () => <String, dynamic>{});
    final TextEditingController insurerC =
        TextEditingController(text: (read['insurer'] ?? renewOf?['insurer'] ?? '').toString());
    final TextEditingController holderC = TextEditingController(text: (read['holder'] ?? '').toString());
    final TextEditingController eachC =
        TextEditingController(text: gl['limit'] is num ? (gl['limit'] as num).toInt().toString() : '');
    final TextEditingController aggC =
        TextEditingController(text: gl['aggregate'] is num ? (gl['aggregate'] as num).toInt().toString() : '');
    DateTime? exp = _coiDate(read['expiresAt']);
    final Map<String, dynamic> ai = Map<String, dynamic>.from((read['additionalInsured'] as Map?) ?? <dynamic, dynamic>{});
    final List<String> aiNamed =
        ((ai['named'] as List?) ?? const <dynamic>[]).map((dynamic x) => x.toString()).toList();
    final bool notCoi = read['isCoi'] == false;
    final List<String> heldBy =
        ((renewOf?['venueIds'] as List?) ?? const <dynamic>[]).map((dynamic x) => x.toString()).toList();
    final int inherited = renewOf == null ? 0 : _coiReach(renewOf);
    final List<Map<String, dynamic>> venues = List<Map<String, dynamic>>.from(preVenues);
    final List<Map<String, String>> outside = <Map<String, String>>[];
    bool busy = false;

    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 580),
      builder: (BuildContext ctx2) => StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        final bool ready = exp != null && insurerC.text.trim().isNotEmpty;
        Future<void> save() async {
          setSheet(() {
            busy = true;
            err = '';
          });
          final num? each = num.tryParse(eachC.text.replaceAll(RegExp(r'[^0-9.]'), ''));
          final num? agg = num.tryParse(aggC.text.replaceAll(RegExp(r'[^0-9.]'), ''));
          final List<Map<String, dynamic>> pols = policies
              .where((Map<String, dynamic> p) => p['line'] != 'general')
              .toList()
            ..insert(0, <String, dynamic>{
              ...gl,
              'line': 'general',
              'limit': each,
              'aggregate': agg,
              'expires': (gl['expires'] ?? '').toString().isEmpty ? _coiYmd(exp!) : gl['expires'],
            });
          try {
            final HttpsCallableResult<dynamic> r = await FirebaseFunctions.instance
                .httpsCallable('coiSave', options: HttpsCallableOptions(timeout: const Duration(seconds: 120)))
                .call(<String, dynamic>{
              'vendorId': vendorId,
              if (renewId.isNotEmpty) 'replaces': renewId,
              'insurer': insurerC.text.trim(),
              'holder': holderC.text.trim(),
              'additionalInsured': <String, dynamic>{'checked': ai['checked'] == true, 'named': aiNamed},
              'policies': pols,
              'expiresAt': _coiYmd(exp!),
              'file': <String, dynamic>{'path': path, 'contentType': ct, 'name': pf.name, 'size': bytes.length},
              if (read.isNotEmpty) 'june': <String, dynamic>{'confidence': read['confidence']},
              'venueIds': venues.map((Map<String, dynamic> v) => (v['id'] ?? '').toString()).toList(),
              'offLazo': outside,
            });
            final int sent = (((r.data as Map?)?['sent'] as List?) ?? const <dynamic>[]).length;
            if (ctx2.mounted) Navigator.pop(ctx2);
            _toast(renewId.isNotEmpty
                ? 'Renewal saved${sent > 0 ? ' and sent to $sent venue${sent == 1 ? '' : 's'}' : ''}.'
                : sent > 0
                    ? 'Saved and on file with $sent venue${sent == 1 ? '' : 's'}.'
                    : 'Saved. Send it to a venue any time.');
          } on FirebaseFunctionsException catch (e) {
            setSheet(() {
              busy = false;
              err = _lzFnMsg(e, 'Could not save it.');
            });
          } catch (e) {
            setSheet(() {
              busy = false;
              err = _errText(e);
            });
          }
        }

        Future<void> addVenue() async {
          final Map<String, dynamic>? v = await _coiPickListing(vendorId, vd,
              receivers: true, title: 'Send to a venue', subtitle: 'Venues and planners on Lazo.');
          if (v == null) return;
          if (venues.any((Map<String, dynamic> x) => x['id'] == v['id']) || heldBy.contains(v['id'])) {
            _toast('${v['name']} is already on the list.');
            return;
          }
          setSheet(() => venues.add(v));
        }

        Future<void> addOutside() async {
          final Map<String, String>? o = await _coiOutsideSheet();
          if (o != null) setSheet(() => outside.add(o));
        }

        Widget gap() => const SizedBox(height: 12);
        Widget field(TextEditingController ctl, String label, String hint,
                {TextInputType? kb, TextCapitalization cap = TextCapitalization.none}) =>
            TextField(
              controller: ctl,
              keyboardType: kb,
              textCapitalization: cap,
              onChanged: (_) => setSheet(() => err = ''),
              style: TextStyle(color: _lzFg(ink), fontSize: 14),
              decoration: _epDeco(label, hint),
            );
        Widget venueRow(String name, String sub, VoidCallback onRemove, {bool? named}) => Container(
              margin: const EdgeInsets.only(bottom: 6),
              padding: const EdgeInsets.fromLTRB(12, 8, 4, 8),
              decoration: BoxDecoration(
                  color: _lzBg(card),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: _lzLine(goldLine))),
              child: Row(children: <Widget>[
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                    Text(name, style: TextStyle(color: _lzFg(ink), fontSize: 13.5, fontWeight: FontWeight.w700)),
                    Text(
                        named == null
                            ? sub
                            : named
                                ? 'Named on this certificate'
                                : 'Not named on it. Many venues ask to be - your agent can issue one made out to them.',
                        style: TextStyle(
                            fontSize: 11.5,
                            color: named == null ? _lzFg(muted) : named ? vGreen : _coiAmber,
                            height: 1.3)),
                  ]),
                ),
                IconButton(
                    visualDensity: VisualDensity.compact,
                    onPressed: _h(onRemove),
                    icon: Icon(Icons.close_rounded, size: 16, color: _lzFg(muted))),
              ]),
            );

        return _lzFrame(sc,
            icon: Icons.verified_user_rounded,
            title: renewId.isNotEmpty ? 'Your renewed COI' : 'Your COI',
            subtitle: read.isNotEmpty && !notCoi
                ? 'June read your certificate. Check the details, then send it.'
                : 'Check the details, then send it.',
            children: <Widget>[
              if (notCoi) ...<Widget>[
                const SizedBox(height: 12),
                _lzNote(Icons.info_outline_rounded,
                    'June doesn\u2019t think this is a certificate of insurance. Check it\u2019s the right file.'),
              ],
              const SizedBox(height: 14),
              field(insurerC, 'Insurer', 'The Hartford', cap: TextCapitalization.words),
              gap(),
              InkWell(
                borderRadius: BorderRadius.circular(13),
                onTap: () async {
                  final DateTime now = DateTime.now();
                  final DateTime? picked = await showDatePicker(
                    context: sc,
                    initialDate: exp ?? DateTime(now.year + 1, now.month, now.day),
                    firstDate: DateTime(now.year - 1),
                    lastDate: DateTime(now.year + 3),
                  );
                  if (picked != null) setSheet(() => exp = picked);
                },
                child: InputDecorator(
                  decoration: _epDeco('Expires', ''),
                  child: Text(exp == null ? 'Pick the expiry date' : _coiDay(exp),
                      style: TextStyle(color: _lzFg(exp == null ? muted : ink), fontSize: 14)),
                ),
              ),
              gap(),
              Row(children: <Widget>[
                Expanded(child: field(eachC, 'GL each occurrence', '1000000', kb: TextInputType.number)),
                const SizedBox(width: 10),
                Expanded(child: field(aggC, 'GL aggregate', '2000000', kb: TextInputType.number)),
              ]),
              gap(),
              field(holderC, 'Certificate holder', 'Who it\u2019s made out to', cap: TextCapitalization.words),
              if (ai['checked'] == true || aiNamed.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                      'Additional insured${aiNamed.isEmpty ? ' box is checked' : ': ${aiNamed.join(', ')}'}',
                      style: TextStyle(fontSize: 12, color: _lzFg(muted), height: 1.35)),
                ),
              _lzSection(renewId.isNotEmpty ? 'Also send to' : 'Send it to'),
              if (inherited > 0) ...<Widget>[
                _lzNote(Icons.autorenew_rounded,
                    'Goes to the $inherited venue${inherited == 1 ? '' : 's'} that have your current one, automatically.'),
                const SizedBox(height: 8),
              ],
              for (final Map<String, dynamic> v in venues)
                venueRow((v['name'] ?? '').toString(), '', () => setSheet(() => venues.remove(v)),
                    named: _coiNamed((v['name'] ?? '').toString(), holderC.text, aiNamed)),
              for (final Map<String, String> o in outside)
                venueRow((o['name'] ?? '').isEmpty ? (o['email'] ?? '') : (o['name'] ?? ''),
                    'By email to ${o['email']} - with an invite to Lazo', () => setSheet(() => outside.remove(o))),
              Wrap(spacing: 8, runSpacing: 4, children: <Widget>[
                TextButton.icon(
                  onPressed: _h(addVenue),
                  icon: Icon(Icons.storefront_rounded, size: 16, color: _lzFg(plum)),
                  label: Text('Lazo venue or planner',
                      style: TextStyle(color: _lzFg(plum), fontSize: 12.5, fontWeight: FontWeight.w800)),
                ),
                TextButton.icon(
                  onPressed: _h(addOutside),
                  icon: Icon(Icons.alternate_email_rounded, size: 16, color: _lzFg(plum)),
                  label: Text('Venue not on Lazo',
                      style: TextStyle(color: _lzFg(plum), fontSize: 12.5, fontWeight: FontWeight.w800)),
                ),
              ]),
              if (err.isNotEmpty) _pv3Err(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx2),
                primary: busy
                    ? 'Saving\u2026'
                    : venues.isEmpty && outside.isEmpty && inherited == 0
                        ? 'Save'
                        : 'Save and send',
                icon: Icons.verified_user_rounded,
                busy: busy,
                onPrimary: !ready || busy ? null : save));
      }),
    );
  }

  /// A venue that isn't on Lazo: a name and an email. Lazo emails it a download link and an invite.
  Future<Map<String, String>?> _coiOutsideSheet() async {
    final TextEditingController nameC = TextEditingController();
    final TextEditingController emailC = TextEditingController();
    Map<String, String>? out;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 480),
      builder: (BuildContext ctx) => StatefulBuilder(builder: (BuildContext c, StateSetter setD) {
        final bool ok = RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$').hasMatch(emailC.text.trim());
        return _lzFrame(c,
            icon: Icons.alternate_email_rounded,
            title: 'Venue not on Lazo',
            subtitle: 'They get a download link that works for 30 days, and renewals by email.',
            children: <Widget>[
              const SizedBox(height: 14),
              TextField(
                controller: nameC,
                textCapitalization: TextCapitalization.words,
                onChanged: (_) => setD(() {}),
                style: TextStyle(color: _lzFg(ink), fontSize: 14),
                decoration: _epDeco('Venue name', 'Casa Blanca Estate'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: emailC,
                keyboardType: TextInputType.emailAddress,
                autocorrect: false,
                onChanged: (_) => setD(() {}),
                style: TextStyle(color: _lzFg(ink), fontSize: 14),
                decoration: _epDeco('Their email', 'events@casablanca.com'),
              ),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx),
                primary: 'Add',
                icon: Icons.add_rounded,
                onPrimary: !ok
                    ? null
                    : () {
                        out = <String, String>{'name': nameC.text.trim(), 'email': emailC.text.trim()};
                        Navigator.pop(ctx);
                      }));
      }),
    );
    return out;
  }

  /// Search Lazo listings by name; [receivers] keeps venues and planners only and adds "in my metro".
  Future<Map<String, dynamic>?> _coiPickListing(String selfId, Map<String, dynamic> vd,
      {required bool receivers, required String title, required String subtitle}) async {
    final TextEditingController searchC = TextEditingController();
    final String metro = (vd['metroId'] ?? '').toString();
    List<Map<String, dynamic>> results = <Map<String, dynamic>>[];
    bool searching = false;
    bool searched = false;
    bool open = true;
    Map<String, dynamic>? picked;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => StatefulBuilder(builder: (BuildContext c, StateSetter setD) {
        void up(VoidCallback f) {
          if (open) setD(f);
        }

        bool keep(QueryDocumentSnapshot<Map<String, dynamic>> d) =>
            d.id != selfId && d.data()['delisted'] != true && (!receivers || _coiReceiver(d.data()));
        Map<String, dynamic> row(QueryDocumentSnapshot<Map<String, dynamic>> d) => <String, dynamic>{
              'id': d.id,
              'name': (d.data()['name'] ?? '').toString(),
              'metroId': (d.data()['metroId'] ?? '').toString(),
              'category': (d.data()['category'] ?? '').toString(),
            };

        Future<void> run(String q) async {
          final String raw = q.trim();
          if (raw.length < 2 || searching) return;
          up(() => searching = true);
          List<Map<String, dynamic>> found = <Map<String, dynamic>>[];
          try {
            final String tq = _tcV(raw);
            final QuerySnapshot<Map<String, dynamic>> snap = await FirebaseFirestore.instance
                .collection('vendors')
                .orderBy('name')
                .startAt(<String>[tq])
                .endAt(<String>['$tq\uf8ff'])
                .limit(40)
                .get();
            found = snap.docs.where(keep).map(row).take(15).toList();
          } catch (_) {}
          up(() {
            results = found;
            searching = false;
            searched = true;
          });
        }

        Future<void> nearby() async {
          if (metro.isEmpty || searching) return;
          up(() => searching = true);
          final List<Map<String, dynamic>> found = <Map<String, dynamic>>[];
          try {
            for (final String cat in _coiReceivers) {
              final QuerySnapshot<Map<String, dynamic>> snap = await FirebaseFirestore.instance
                  .collection('vendors')
                  .where('metroId', isEqualTo: metro)
                  .where('category', isEqualTo: cat)
                  .limit(300)
                  .get();
              found.addAll(snap.docs.where(keep).map(row));
            }
            found.sort((Map<String, dynamic> a, Map<String, dynamic> b) =>
                a['name'].toString().toLowerCase().compareTo(b['name'].toString().toLowerCase()));
          } catch (_) {}
          up(() {
            results = found;
            searching = false;
            searched = true;
          });
        }

        Widget resultRow(Map<String, dynamic> r) {
          final String place = _metroLabel(r['metroId'].toString());
          final String kind = r['category'] == 'wedding-planners'
              ? 'Planner'
              : r['category'] == 'wedding-venues'
                  ? 'Venue'
                  : r['category'].toString().replaceFirst('wedding-', '').replaceAll('-', ' ');
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: _Press(
              scale: .985,
              onTap: () {
                picked = r;
                Navigator.pop(ctx);
              },
              child: Container(
                padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
                decoration: BoxDecoration(
                    color: _lzBg(card),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: _lzLine(goldLine))),
                child: Row(children: <Widget>[
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                      Text(r['name'].toString(),
                          style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w700, fontSize: 14.5)),
                      const SizedBox(height: 2),
                      Text('$kind${place.isEmpty ? '' : ' \u00b7 $place'}',
                          style: TextStyle(fontSize: 12, color: _lzFg(muted))),
                    ]),
                  ),
                  const Icon(Icons.add_circle_outline_rounded, color: gold, size: 22),
                ]),
              ),
            ),
          );
        }

        return _lzFrame(c,
            icon: Icons.storefront_rounded,
            title: title,
            subtitle: subtitle,
            headerExtra: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              TextField(
                controller: searchC,
                autofocus: true,
                textInputAction: TextInputAction.search,
                onSubmitted: run,
                cursorColor: _lzFg(plum),
                style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
                decoration: _epDeco('Search by business name', 'Any city').copyWith(
                    suffixIcon: IconButton(
                        tooltip: 'Search',
                        icon: Icon(Icons.search_rounded, color: _lzFg(plum)),
                        onPressed: _h(() => run(searchC.text)))),
              ),
              if (receivers && metro.isNotEmpty)
                TextButton.icon(
                  onPressed: _h(nearby),
                  icon: Icon(Icons.near_me_rounded, size: 16, color: _lzFg(plum)),
                  label: Text('Venues and planners in ${_metroLabel(metro)}',
                      style: TextStyle(color: _lzFg(plum), fontSize: 12.5, fontWeight: FontWeight.w800)),
                ),
            ]),
            children: <Widget>[
              const SizedBox(height: 14),
              if (searching)
                _lzBusy('Searching Lazo\u2026')
              else if (!searched)
                _lzNote(Icons.search_rounded, 'Type at least two letters of their business name, then search.')
              else if (results.isEmpty)
                _lzNote(Icons.search_off_rounded,
                    receivers
                        ? 'No venue or planner starts with that name. Try the first word of it, or send it by email instead.'
                        : 'No vendor starts with that name. Try the first word of it.')
              else ...<Widget>[
                _lzSection('Tap to pick', trailing: '${results.length} found'),
                for (final Map<String, dynamic> r in results) resultRow(r),
              ],
            ]);
      }),
    );
    open = false;
    return picked;
  }

  Future<void> _coiShare(String coiId, List<String> venueIds,
      {List<Map<String, String>> outside = const <Map<String, String>>[]}) async {
    _showJuneVeil('Sending your COI\u2026', 'It goes on file with each venue.');
    try {
      final HttpsCallableResult<dynamic> r = await FirebaseFunctions.instance
          .httpsCallable('coiShare')
          .call(<String, dynamic>{'coiId': coiId, 'venueIds': venueIds, 'offLazo': outside});
      _popJuneVeil();
      final int sent = (((r.data as Map?)?['sent'] as List?) ?? const <dynamic>[]).length;
      _toast(sent == 0 ? 'It was already on file there.' : 'Sent - it\u2019s on file with ${sent == 1 ? 'them' : '$sent venues'}.');
    } on FirebaseFunctionsException catch (e) {
      _popJuneVeil();
      _toast(_lzFnMsg(e, 'Could not send it.'));
    } catch (e) {
      _popJuneVeil();
      _toast('Could not send it: ' + _errText(e));
    }
  }

  Future<void> _coiOpen(String coiId, {String venueId = ''}) async {
    _showJuneVeil('Opening the certificate\u2026', 'A private link, good for ten minutes.');
    try {
      final HttpsCallableResult<dynamic> r = await FirebaseFunctions.instance
          .httpsCallable('coiFileLink')
          .call(<String, dynamic>{'coiId': coiId, if (venueId.isNotEmpty) 'venueId': venueId});
      _popJuneVeil();
      final String url = ((r.data as Map?)?['url'] ?? '').toString();
      if (url.isEmpty) {
        _toast('Could not open it.');
        return;
      }
      await _openUrl(url);
    } on FirebaseFunctionsException catch (e) {
      _popJuneVeil();
      _toast(_lzFnMsg(e, 'Could not open it.'));
    } catch (e) {
      _popJuneVeil();
      _toast('Could not open it: ' + _errText(e));
    }
  }

  // ---------------------------------------------------------------- where it's on file
  Future<void> _coiDetailSheet(String vendorId, Map<String, dynamic> vd, String coiId) async {
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
        stream: FirebaseFirestore.instance.collection('cois').doc(coiId).snapshots(),
        builder: (BuildContext c, AsyncSnapshot<DocumentSnapshot<Map<String, dynamic>>> s) {
          final Map<String, dynamic> d = s.data?.data() ?? <String, dynamic>{};
          final Map<String, dynamic> vs = Map<String, dynamic>.from((d['venues'] as Map?) ?? <dynamic, dynamic>{});
          final List<Map<String, dynamic>> outs = ((d['offLazo'] as List?) ?? const <dynamic>[])
              .whereType<Map>()
              .map((Map m) => Map<String, dynamic>.from(m))
              .toList();
          final List<Map<String, dynamic>> pols = ((d['policies'] as List?) ?? const <dynamic>[])
              .whereType<Map>()
              .map((Map m) => Map<String, dynamic>.from(m))
              .toList();
          final String st = _coiState(d);
          Widget line(String a, String b) => Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Row(children: <Widget>[
                  Expanded(child: Text(a, style: TextStyle(fontSize: 13, color: _lzFg(ink)))),
                  Text(b, style: TextStyle(fontSize: 13, color: _lzFg(muted), fontWeight: FontWeight.w600)),
                ]),
              );
          Widget who(String name, String sub, {bool? named, VoidCallback? onRemove}) => Container(
                margin: const EdgeInsets.only(bottom: 6),
                padding: const EdgeInsets.fromLTRB(12, 8, 4, 8),
                decoration: BoxDecoration(
                    color: _lzBg(card),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: _lzLine(goldLine))),
                child: Row(children: <Widget>[
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                      Row(children: <Widget>[
                        Flexible(
                            child: Text(name,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(color: _lzFg(ink), fontSize: 13.5, fontWeight: FontWeight.w700))),
                        if (named == true) ...<Widget>[
                          const SizedBox(width: 6),
                          const Icon(Icons.verified_rounded, size: 14, color: vGreen),
                        ],
                      ]),
                      Text(sub, style: TextStyle(fontSize: 11.5, color: _lzFg(muted), height: 1.3)),
                    ]),
                  ),
                  if (onRemove != null)
                    IconButton(
                        tooltip: 'Take it back',
                        visualDensity: VisualDensity.compact,
                        onPressed: _h(onRemove),
                        icon: Icon(Icons.close_rounded, size: 16, color: _lzFg(muted))),
                ]),
              );
          Future<void> unshare(Map<String, dynamic> body, String name) async {
            if (!await _lzConfirm('Take it back from $name?',
                'It leaves their COIs on file. You can send it again any time.',
                confirm: 'Take it back')) return;
            try {
              await FirebaseFunctions.instance.httpsCallable('coiUnshare').call(<String, dynamic>{'coiId': coiId, ...body});
            } catch (e) {
              _toast('Could not take it back: ' + _errText(e));
            }
          }

          return _lzFrame(c,
              icon: Icons.verified_user_rounded,
              title: (d['insurer'] ?? '').toString().isEmpty ? 'Your COI' : (d['insurer'] ?? '').toString(),
              subtitle: d.isEmpty ? '' : 'Expires ${_coiDay(_coiDate(d['expiresAt']))}',
              headerExtra: d.isEmpty ? null : Align(alignment: Alignment.centerLeft, child: _coiChip(d)),
              children: <Widget>[
                const SizedBox(height: 12),
                for (final Map<String, dynamic> p in pols)
                  line(
                      '${_coiLines[p['line']] ?? 'Other'}${(p['number'] ?? '').toString().isEmpty ? '' : ' \u00b7 ${p['number']}'}',
                      [_coiMoney(p['limit']), if (_coiMoney(p['aggregate']).isNotEmpty) '${_coiMoney(p['aggregate'])} agg']
                          .where((String x) => x.isNotEmpty)
                          .join(' / ')),
                if ((d['holder'] ?? '').toString().isNotEmpty) line('Holder', (d['holder'] ?? '').toString().split(',').first),
                _lzSection('On file with', trailing: '${vs.length + outs.where((Map<String, dynamic> o) => o['stopped'] != true).length}'),
                if (vs.isEmpty && outs.isEmpty)
                  _lzNote(Icons.storefront_rounded, 'Not sent to anyone yet.'),
                for (final MapEntry<String, dynamic> e in vs.entries)
                  Builder(builder: (BuildContext _) {
                    final Map<String, dynamic> v = Map<String, dynamic>.from((e.value as Map?) ?? <dynamic, dynamic>{});
                    final String name = (v['name'] ?? '').toString();
                    final DateTime? seen = _coiDate(v['viewedAt']);
                    final String sub = [
                      v['kind'] == 'planner' ? 'Planner' : 'Venue',
                      'sent ${_coiDay(_coiDate(v['sharedAt']))}',
                      if (seen != null) 'viewed ${_coiDay(seen)}',
                      if (v['claimed'] != true) 'emailed to their listing',
                      if (v['namedOnCert'] != true) 'not named on it',
                    ].join(' \u00b7 ');
                    return who(name, sub,
                        named: v['namedOnCert'] == true,
                        onRemove: st == 'replaced' ? null : () => unshare(<String, dynamic>{'venueId': e.key}, name));
                  }),
                for (final Map<String, dynamic> o in outs)
                  who(
                      (o['name'] ?? '').toString().isEmpty ? (o['email'] ?? '').toString() : (o['name'] ?? '').toString(),
                      o['stopped'] == true
                          ? 'Not on Lazo \u00b7 asked for no more emails'
                          : 'Not on Lazo \u00b7 emailed ${_coiDay(_coiDate(o['sentAt']))}${_coiDate(o['openedAt']) != null ? ' \u00b7 opened ${_coiDay(_coiDate(o['openedAt']))}' : ''}',
                      onRemove: st == 'replaced'
                          ? null
                          : () => unshare(<String, dynamic>{'email': o['email']}, (o['name'] ?? o['email'] ?? '').toString())),
              ],
              footer: Wrap(alignment: WrapAlignment.end, spacing: 8, runSpacing: 6, children: <Widget>[
                TextButton.icon(
                  onPressed: _h(() => _coiOpen(coiId)),
                  icon: Icon(Icons.download_rounded, size: 17, color: _lzFg(plum)),
                  label: Text('Download', style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w700)),
                ),
                if (st != 'replaced' && st != 'expired') ...<Widget>[
                  TextButton.icon(
                    onPressed: _h(() async {
                      final Map<String, dynamic>? v = await _coiPickListing(vendorId, vd,
                          receivers: true, title: 'Send to a venue', subtitle: 'Venues and planners on Lazo.');
                      if (v != null) await _coiShare(coiId, <String>[(v['id'] ?? '').toString()]);
                    }),
                    icon: Icon(Icons.storefront_rounded, size: 17, color: _lzFg(plum)),
                    label: Text('Send to a venue', style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w700)),
                  ),
                  TextButton.icon(
                    onPressed: _h(() async {
                      final Map<String, String>? o = await _coiOutsideSheet();
                      if (o != null) await _coiShare(coiId, const <String>[], outside: <Map<String, String>>[o]);
                    }),
                    icon: Icon(Icons.alternate_email_rounded, size: 17, color: _lzFg(plum)),
                    label: Text('Email it', style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w700)),
                  ),
                ],
                if (st != 'replaced')
                  FilledButton.icon(
                    style: FilledButton.styleFrom(
                        backgroundColor: gold,
                        foregroundColor: plumDeep,
                        minimumSize: const Size(0, 42),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                    onPressed: _h(() {
                      Navigator.pop(ctx);
                      _coiUploadSheet(vendorId, vd, renewId: coiId, renewOf: d);
                    }),
                    icon: const Icon(Icons.autorenew_rounded, size: 17),
                    label: const Text('Upload renewal', style: TextStyle(fontWeight: FontWeight.w800)),
                  ),
              ]));
        },
      ),
    );
  }

  // ---------------------------------------------------------------- venues and planners: COIs on file
  Widget _coisOnFileCard(String venueId, Map<String, dynamic> vd) {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _liveQuery('coisOnFile:$venueId',
          () => FirebaseFirestore.instance.collection('vendors').doc(venueId).collection('coisOnFile')),
      builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> snap) {
        // the newest certificate per vendor; replaced ones are history
        final Map<String, Map<String, dynamic>> byVendor = <String, Map<String, dynamic>>{};
        for (final QueryDocumentSnapshot<Map<String, dynamic>> d
            in snap.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[]) {
          final Map<String, dynamic> m = <String, dynamic>{...d.data(), 'id': d.id};
          if (_coiState(m) == 'replaced') continue;
          final String v = (m['vendorId'] ?? '').toString();
          final Map<String, dynamic>? prev = byVendor[v];
          if (prev == null ||
              (_coiDate(m['expiresAt']) ?? DateTime(2000)).isAfter(_coiDate(prev['expiresAt']) ?? DateTime(2000))) {
            byVendor[v] = m;
          }
        }
        final List<Map<String, dynamic>> rows = byVendor.values.toList()
          ..sort((Map<String, dynamic> a, Map<String, dynamic> b) =>
              (_coiDate(a['expiresAt']) ?? DateTime(2100)).compareTo(_coiDate(b['expiresAt']) ?? DateTime(2100)));
        final int attn = rows.where((Map<String, dynamic> m) => _coiState(m) != 'current').length;
        final List<Map<String, dynamic>> shown =
            _coiFilter == 'attn' ? rows.where((Map<String, dynamic> m) => _coiState(m) != 'current').toList() : rows;
        return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
          stream: _liveQuery(
              'coiWaits:$venueId',
              () => FirebaseFirestore.instance
                  .collection('coiRequests')
                  .where('venueId', isEqualTo: venueId)
                  .where('status', isEqualTo: 'open')),
          builder: (BuildContext c2, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> rq) {
            final List<String> waiting = (rq.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[])
                .map((QueryDocumentSnapshot<Map<String, dynamic>> d) => (d.data()['vendorName'] ?? '').toString())
                .where((String n) => n.isNotEmpty)
                .toList();
            return _glass(
              padding: const EdgeInsets.fromLTRB(18, 16, 18, 14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                Row(children: <Widget>[
                  _cardIconChip(Icons.fact_check_rounded),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                      Text('COIs on file',
                          style: TextStyle(color: _lzFg(plum), fontSize: 15, fontWeight: FontWeight.w700)),
                      Text(
                          rows.isEmpty
                              ? 'When vendors send you their certificate of insurance on Lazo, it lands here. You hear before one lapses, and renewals replace it on their own.'
                              : '${rows.length} vendor${rows.length == 1 ? '' : 's'}${attn > 0 ? ' \u00b7 $attn need${attn == 1 ? 's' : ''} attention' : ' \u00b7 all current'}',
                          style: TextStyle(fontSize: 12, color: _lzFg(muted), height: 1.35)),
                    ]),
                  ),
                  TextButton.icon(
                    onPressed: _h(() => _coiAsk(venueId, vd)),
                    icon: Icon(Icons.forward_to_inbox_rounded, size: 16, color: _lzFg(plum)),
                    label: Text('Request',
                        style: TextStyle(color: _lzFg(plum), fontSize: 12.5, fontWeight: FontWeight.w800)),
                  ),
                ]),
                if (rows.length > 3 && attn > 0)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Wrap(spacing: 6, children: <Widget>[
                      for (final List<String> f in const <List<String>>[
                        <String>['all', 'All'],
                        <String>['attn', 'Needs attention']
                      ])
                        ChoiceChip(
                          label: Text(f[1], style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                          selected: _coiFilter == f[0],
                          selectedColor: gold.withOpacity(.35),
                          onSelected: (bool _) => setState(() => _coiFilter = f[0]),
                        ),
                    ]),
                  ),
                for (final Map<String, dynamic> m in shown) _coiFileRow(venueId, vd, m),
                if (waiting.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text('Waiting on ${waiting.join(', ')}',
                        style: TextStyle(fontSize: 12, color: _lzFg(muted), fontStyle: FontStyle.italic)),
                  ),
              ]),
            );
          },
        );
      },
    );
  }

  Widget _coiFileRow(String venueId, Map<String, dynamic> vd, Map<String, dynamic> m) {
    final String st = _coiState(m);
    final String name = (m['vendorName'] ?? '').toString();
    final String cat = (m['vendorCategory'] ?? '').toString().replaceFirst('wedding-', '').replaceAll('-', ' ');
    final String gl = _coiMoney(m['glEach']);
    final bool named = m['namedOnCert'] == true;
    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.fromLTRB(10, 8, 4, 8),
      decoration: BoxDecoration(
          color: _lzBg(Colors.white.withOpacity(.7)),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: st == 'expired' ? _coiRed.withOpacity(.4) : _lzLine(goldLine))),
      child: Row(children: <Widget>[
        Container(
          width: 34,
          height: 34,
          alignment: Alignment.center,
          decoration: BoxDecoration(color: plum, borderRadius: BorderRadius.circular(10)),
          child: Text(name.isEmpty ? '?' : name[0].toUpperCase(),
              style: const TextStyle(color: gold, fontSize: 14, fontWeight: FontWeight.w800)),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Text(name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: _lzFg(ink), fontSize: 13.5, fontWeight: FontWeight.w800)),
            Text(
                [cat, (m['insurer'] ?? '').toString(), if (gl.isNotEmpty) 'GL $gl', 'to ${_coiDay(_coiDate(m['expiresAt']))}']
                    .where((String x) => x.isNotEmpty)
                    .join(' \u00b7 '),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 11.5, color: _lzFg(muted))),
            const SizedBox(height: 3),
            Row(children: <Widget>[
              _coiChip(m),
              const SizedBox(width: 6),
              Flexible(
                child: Text(named ? 'Names you' : 'Doesn\u2019t name you',
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                        fontSize: 11, fontWeight: FontWeight.w700, color: named ? vGreen : _coiAmber)),
              ),
            ]),
          ]),
        ),
        if (st != 'current')
          TextButton(
            style: TextButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 8), visualDensity: VisualDensity.compact),
            onPressed: _h(() => _coiAskVendor(venueId, (m['vendorId'] ?? '').toString(), name, renewal: true)),
            child: Text('Ask for\nrenewal',
                textAlign: TextAlign.center,
                style: TextStyle(color: _lzFg(plum), fontSize: 11.5, fontWeight: FontWeight.w800, height: 1.15)),
          ),
        IconButton(
          tooltip: 'Download',
          visualDensity: VisualDensity.compact,
          onPressed: _h(() => _coiOpen((m['coiId'] ?? m['id'] ?? '').toString(), venueId: venueId)),
          icon: Icon(Icons.download_rounded, size: 19, color: _lzFg(plum)),
        ),
      ]),
    );
  }

  Future<void> _coiAsk(String venueId, Map<String, dynamic> vd) async {
    final Map<String, dynamic>? v = await _coiPickListing(venueId, vd,
        receivers: false,
        title: 'Request a COI',
        subtitle: 'Pick the vendor. They get an email and a nudge in Lazo.');
    if (v == null) return;
    await _coiAskVendor(venueId, (v['id'] ?? '').toString(), (v['name'] ?? '').toString());
  }

  Future<void> _coiAskVendor(String venueId, String vendorId, String name, {bool renewal = false}) async {
    final TextEditingController noteC = TextEditingController();
    bool busy = false;
    String err = '';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 480),
      builder: (BuildContext ctx) => StatefulBuilder(builder: (BuildContext c, StateSetter setD) {
        Future<void> send() async {
          setD(() {
            busy = true;
            err = '';
          });
          try {
            final HttpsCallableResult<dynamic> r = await FirebaseFunctions.instance
                .httpsCallable('coiRequest')
                .call(<String, dynamic>{'venueId': venueId, 'vendorId': vendorId, 'note': noteC.text.trim()});
            final Map<dynamic, dynamic> d = (r.data as Map?) ?? <dynamic, dynamic>{};
            if (ctx.mounted) Navigator.pop(ctx);
            _toast(d['already'] == true
                ? '$name already has a current COI on file with you.'
                : 'Asked. It lands in COIs on file when they send it.');
          } on FirebaseFunctionsException catch (e) {
            setD(() {
              busy = false;
              err = _lzFnMsg(e, 'Could not send the request.');
            });
          } catch (e) {
            setD(() {
              busy = false;
              err = _errText(e);
            });
          }
        }

        return _lzFrame(c,
            icon: Icons.forward_to_inbox_rounded,
            title: renewal ? 'Ask $name for the renewal' : 'Ask $name for their COI',
            subtitle: 'They get an email and a nudge in Lazo. When they send it, it lands in COIs on file.',
            children: <Widget>[
              const SizedBox(height: 14),
              TextField(
                controller: noteC,
                maxLines: 3,
                minLines: 2,
                textCapitalization: TextCapitalization.sentences,
                style: TextStyle(color: _lzFg(ink), fontSize: 14),
                decoration: _epDeco('A note (optional)', 'Please name us as additional insured.'),
              ),
              if (err.isNotEmpty) _pv3Err(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx),
                primary: busy ? 'Sending\u2026' : 'Send request',
                icon: Icons.send_rounded,
                busy: busy,
                onPrimary: busy ? null : send));
      }),
    );
  }

  Future<void> _disconnectWhop(String vendorId) async {
""")

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8", newline="")
print(f"wrote {DST.name} ({len(s):,} chars)")
