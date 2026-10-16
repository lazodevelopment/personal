r"""patch_vendor_v203.py - Vendor v199 -> v203: ENGAGEMENT SESSIONS.  JC-LAZO-ENGAGE-1016-VENDOR

Photographers (and videographers) can send an Engagement Session questionnaire from the thread, and June finds
places to shoot near where the couple lives.

- "Send a questionnaire" gains an Engagement session starter: 16 questions (where they live, dates, time of day,
  story, vibe, meaningful places, activities, outfits, wardrobe, pets/props/people, travel radius, things to avoid,
  camera comfort, hair and makeup, how they'll use the photos, inspiration). Edit, reorder, add your own, save as a
  template.
- Every question now has an answer type the vendor picks in the editor: Short answer, Long answer, Pick any,
  Pick one, Dates. Stored as questionnaires.spec (one entry per question). Couple v163 shows the right control;
  older couple apps still get a text box per question, and answers stay text, so nothing breaks either way.
- June's location ideas: a strip under the questionnaires in the thread, a sheet with 5-6 verified spots (why it
  fits them, best time and light, permit, fee, crowds, pets, distance, Google Maps), Share with couple (a thread
  message), Hide, and More like this. Opened from the strip, from Studio tools > Engagement location ideas, or from
  the engagement answers. June also runs on her own when the couple sends their answers (functions-dashboard
  engagementSpotsAuto).

Needs functions-dashboard june-engagement.js (juneEngagementSpots) and rules JC-LAZO-RULES-1016-ENGAGE deployed.

    python app-patches\patch_vendor_v203.py [base]     # base defaults to Vendor_master_v199.txt
                                                        # writes Vendor_master_v203.txt
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / (sys.argv[1] if len(sys.argv) > 1 else "Vendor_master_v199.txt")
DST = HERE / "Vendor_master_v203.txt"
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
    "// Build ID: JC-LAZO-ENGAGE-1016-VENDOR (v203: ENGAGEMENT SESSIONS - an Engagement session questionnaire "
    "(16 questions, editable, saveable); every question gets an answer type (short, long, pick any, pick one, dates) "
    "kept in questionnaires.spec; June's location ideas near where the couple lives - verified on Google Maps, with "
    "light, permits, fees, crowds and pets - in a thread strip and sheet, shareable to the couple; base "
    + SRC.stem.replace("Vendor_master_", "") + ")\n")

# ---- 1. the engagement starter set + answer types
rep("""  String _catLabelFor(String catId) {
""", r"""  // v203: the engagement session set. 'key' tells June which answer is which
  // (home = where they live, travel = how far); the vendor's own questions
  // have no key and still reach June as text.
  static const List<String> kQEngagement = <String>[
    'Where do you live? (city or neighborhood)',
    'Which dates work for your shoot? (up to three)',
    'What time of day do you love?',
    'How did you meet, and what’s your story so far?',
    'Pick the vibe you want',
    'Any places that mean something to you? (first date, the proposal, a favorite coffee shop)',
    'Anything you love doing together that we could build the shoot around?',
    'How many outfits are you planning?',
    'What are you thinking of wearing? (colors, dressy or casual)',
    'Bringing pets, props, or anyone else (kids, family)?',
    'How far will you travel for the shoot?',
    'Anything to avoid? (crowds, heat, certain places or poses)',
    'How do you feel in front of the camera?',
    'Will you have hair and makeup done for the shoot?',
    'How will you use the photos?',
    'Any inspiration photos or a Pinterest board to share?',
  ];

  static const List<Map<String, dynamic>> kQEngagementSpec =
      <Map<String, dynamic>>[
    <String, dynamic>{'key': 'home', 'kind': 'text'},
    <String, dynamic>{'key': 'dates', 'kind': 'dates', 'max': 3},
    <String, dynamic>{
      'key': 'time',
      'kind': 'many',
      'options': <String>['Sunrise', 'Morning', 'Afternoon', 'Golden hour', 'Blue hour / after dark', 'No preference']
    },
    <String, dynamic>{'key': 'story', 'kind': 'long'},
    <String, dynamic>{
      'key': 'vibe',
      'kind': 'many',
      'options': <String>['Urban / city streets', 'Nature / forest', 'Open fields at golden hour', 'Beach or lake', 'Desert', 'Mountains', 'Downtown night lights', 'Cozy at home', 'Vintage / historic', 'Something unexpected']
    },
    <String, dynamic>{'key': 'places', 'kind': 'long'},
    <String, dynamic>{'key': 'activity', 'kind': 'long'},
    <String, dynamic>{
      'key': 'outfits',
      'kind': 'one',
      'options': <String>['1', '2', '3 or more', 'Not sure yet']
    },
    <String, dynamic>{'key': 'wardrobe', 'kind': 'long'},
    <String, dynamic>{'key': 'pets', 'kind': 'text'},
    <String, dynamic>{
      'key': 'travel',
      'kind': 'one',
      'options': <String>['Stay local (15 mi or less)', 'Up to 30 miles', 'Up to an hour', 'Happy to road-trip']
    },
    <String, dynamic>{'key': 'avoid', 'kind': 'long'},
    <String, dynamic>{
      'key': 'comfort',
      'kind': 'one',
      'options': <String>['Totally at ease', 'A little nervous', 'Very camera-shy']
    },
    <String, dynamic>{
      'key': 'hmu',
      'kind': 'one',
      'options': <String>['Yes, professionally', 'Doing it ourselves', 'Not sure yet']
    },
    <String, dynamic>{
      'key': 'use',
      'kind': 'many',
      'options': <String>['Save-the-dates', 'Wedding website', 'Signs or a guest book', 'Announcements', 'Just for us']
    },
    <String, dynamic>{'key': 'inspo', 'kind': 'text'},
  ];

  static const Map<String, String> kQKindLabel = <String, String>{
    'text': 'Short answer',
    'long': 'Long answer',
    'many': 'Pick any',
    'one': 'Pick one',
    'dates': 'Dates',
  };

  static const Map<String, IconData> kQKindIcon = <String, IconData>{
    'text': Icons.short_text_rounded,
    'long': Icons.notes_rounded,
    'many': Icons.checklist_rounded,
    'one': Icons.radio_button_checked_rounded,
    'dates': Icons.event_rounded,
  };

  // v203: pick a question's answer type (and its choices).
  Future<Map<String, dynamic>?> _qKindSheet(Map<String, dynamic> cur) async {
    String kind = (cur['kind'] ?? 'text').toString();
    if (!kQKindLabel.containsKey(kind)) kind = 'text';
    final TextEditingController optC = TextEditingController(
        text: ((cur['options'] as List?) ?? const <dynamic>[])
            .map((dynamic e) => e.toString())
            .join(', '));
    return _lzSheet<Map<String, dynamic>>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setK) {
          final bool needs = kind == 'many' || kind == 'one';
          final List<String> opts = optC.text
              .split(',')
              .map((String x) => x.trim())
              .where((String x) => x.isNotEmpty)
              .toList();
          return _lzFrame(ctx2,
              icon: Icons.tune_rounded,
              title: 'How should they answer?',
              subtitle: 'Couples on the newest app see this. Older apps show a text box.',
              children: <Widget>[
                const SizedBox(height: 12),
                for (final MapEntry<String, String> k in kQKindLabel.entries)
                  _pv2Row(
                    icon: kQKindIcon[k.key] ?? Icons.short_text_rounded,
                    title: k.value,
                    trailing: kind == k.key
                        ? Icon(Icons.check_circle_rounded,
                            color: _lzFg(vGreen), size: 20)
                        : null,
                    onTap: () => setK(() => kind = k.key),
                  ),
                if (needs) ...<Widget>[
                  const SizedBox(height: 6),
                  TextField(
                    controller: optC,
                    maxLines: null,
                    onChanged: (String _) => setK(() {}),
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _epDeco('Choices, separated by commas',
                        'Sunrise, Golden hour, After dark'),
                  ),
                ],
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2),
                  primary: 'Use this',
                  icon: Icons.check_rounded,
                  onPrimary: needs && opts.length < 2
                      ? null
                      : () {
                          final Map<String, dynamic> out =
                              Map<String, dynamic>.from(cur);
                          out['kind'] = kind;
                          if (needs) {
                            out['options'] = opts;
                          } else {
                            out.remove('options');
                          }
                          if (kind == 'dates') {
                            out['max'] = (cur['max'] is num) ? cur['max'] : 3;
                          } else {
                            out.remove('max');
                          }
                          Navigator.pop(ctx2, out);
                        }));
        },
      ),
    );
  }

  String _catLabelFor(String catId) {
""")

# ---- 2. sending a saved template carries its answer types
rep("""                                  qs.map((dynamic e) => e.toString()).toList(),
                                  bizName);
""", """                                  qs.map((dynamic e) => e.toString()).toList(),
                                  bizName,
                                  spec: q['spec'] as List<dynamic>?);
""")

# ---- 3. the engagement starter row
rep("""                      _pv2Row(
                        icon: Icons.edit_note_rounded,
                        title: 'Write my own from scratch',
""", """                      if (((vd['categories'] as List?) ?? const <dynamic>[])
                          .any((dynamic c) =>
                              c == 'wedding-photographers' ||
                              c == 'wedding-videographers'))
                        _pv2Row(
                          icon: Icons.favorite_rounded,
                          title: 'Engagement session',
                          sub:
                              '${kQEngagement.length} questions - where they live, the vibe, outfits, pets. June uses the answers to find spots.',
                          onTap: () {
                            Navigator.pop(ctx);
                            _questionnaireEditor(
                                vendorId, null, <String, dynamic>{
                              'title': 'Engagement Session',
                              'type': 'engagement',
                              'questions': kQEngagement,
                              'spec': kQEngagementSpec,
                            });
                          },
                        ),
                      _pv2Row(
                        icon: Icons.edit_note_rounded,
                        title: 'Write my own from scratch',
""")

# ---- 4. the editor keeps an answer type per question
rep("""    if (qcs.isEmpty) qcs.add(TextEditingController());
    bool saving = false;
    String err = '';
    if (!mounted) return;
    final ButtonStyle juneBtn""", """    // v203: each question's answer type rides with its controller, so
    // reordering and removing need no bookkeeping.
    final List<dynamic> seedSpec =
        (seed['spec'] as List?) ?? const <dynamic>[];
    final Map<TextEditingController, Map<String, dynamic>> specOf =
        <TextEditingController, Map<String, dynamic>>{};
    for (int i = 0; i < qcs.length && i < seedSpec.length; i++) {
      if (seedSpec[i] is Map) {
        specOf[qcs[i]] = Map<String, dynamic>.from(seedSpec[i] as Map);
      }
    }
    if (qcs.isEmpty) qcs.add(TextEditingController());
    bool saving = false;
    String err = '';
    if (!mounted) return;
    final ButtonStyle juneBtn""")

rep("""                                        IconButton(
                                          tooltip: 'Remove question',
""", """                                        Builder(builder: (BuildContext c5) {
                                          final String k =
                                              (specOf[qcs[i]]?['kind'] ??
                                                      'text')
                                                  .toString();
                                          return IconButton(
                                            tooltip:
                                                'Answer type: ${kQKindLabel[k] ?? 'Short answer'}',
                                            icon: Icon(
                                                kQKindIcon[k] ??
                                                    Icons.short_text_rounded,
                                                color: _lzFg(k == 'text'
                                                    ? muted
                                                    : plum),
                                                size: 18),
                                            onPressed: _h(() async {
                                              final TextEditingController tc =
                                                  qcs[i];
                                              final Map<String, dynamic>? out =
                                                  await _qKindSheet(
                                                      specOf[tc] ??
                                                          <String, dynamic>{
                                                            'kind': 'text'
                                                          });
                                              if (out != null) {
                                                setE(() => specOf[tc] = out);
                                              }
                                            }),
                                          );
                                        }),
                                        IconButton(
                                          tooltip: 'Remove question',
""")

rep("""                                  if (qs.isEmpty) {
                                    return;
                                  }
                                  setE(() {
                                    saving = true;
""", """                                  if (qs.isEmpty) {
                                    return;
                                  }
                                  final List<Map<String, dynamic>> sp =
                                      <Map<String, dynamic>>[
                                    for (final TextEditingController c4 in qcs)
                                      if (c4.text.trim().isNotEmpty)
                                        Map<String, dynamic>.from(specOf[c4] ??
                                            const <String, dynamic>{
                                              'kind': 'text'
                                            })
                                  ];
                                  setE(() {
                                    saving = true;
""")

rep("""                                    'type': 'custom',
                                    'updatedAt': FieldValue.serverTimestamp(),
""", """                                    'type': (seed['type'] ?? 'custom')
                                        .toString(),
                                    'spec': sp,
                                    'updatedAt': FieldValue.serverTimestamp(),
""")

# ---- 5. sending carries the answer types
rep("""  Future<void> _createQuestionnaire(String inquiryId, String type, String title,
      List<String> qs, String bizName) async {
""", """  Future<void> _createQuestionnaire(String inquiryId, String type, String title,
      List<String> qs, String bizName, {List<dynamic>? spec}) async {
    // v203: only a spec that lines up with the questions goes out.
    final bool typed = spec != null &&
        spec.length == qs.length &&
        spec.every((dynamic e) => e is Map);
""")
rep("""        'questions': qs,
        'answers': <String, dynamic>{},
""", """        'questions': qs,
        if (typed) 'spec': spec,
        'answers': <String, dynamic>{},
""")

# ---- 6. the answers sheet opens June's ideas for an engagement questionnaire
rep("""                onTap: done
                    ? () => _questionnaireAnswersSheet(qn)
""", """                onTap: done
                    ? () => _questionnaireAnswersSheet(
                        <String, dynamic>{...qn, '_inquiryId': inquiryId})
""")
rep("""          title: (qn['title'] ?? 'Responses') as String,
          subtitle: '$answered of ${qs.length} answered',
""", """          title: (qn['title'] ?? 'Responses') as String,
          subtitle: '$answered of ${qs.length} answered',
          footer: (qn['type'] ?? '') == 'engagement' &&
                  (qn['_inquiryId'] ?? '').toString().isNotEmpty
              ? _lzActions(
                  primary: 'June\\u2019s location ideas',
                  icon: Icons.place_rounded,
                  onPrimary: () {
                    Navigator.pop(ctx);
                    _engagementIdeasSheet(qn['_inquiryId'].toString());
                  })
              : null,
""")

# ---- 7. the strip in the thread, and Studio tools
rep("""        _questionnaireStrip(inquiryId),
        _invoicesStrip(inquiryId),
""", """        _questionnaireStrip(inquiryId),
        _engagementIdeasStrip(inquiryId),
        _invoicesStrip(inquiryId),
""")
rep("""              row(Icons.fact_check_outlined, 'Send a questionnaire',
                  'Collect the details before the day',
                  () => _sendQuestionnaireSheet(inquiryId, inq)),
""", """              row(Icons.fact_check_outlined, 'Send a questionnaire',
                  'Collect the details before the day',
                  () => _sendQuestionnaireSheet(inquiryId, inq)),
              if (_delivers())
                row(Icons.place_rounded, 'Engagement location ideas',
                    'June finds spots near the couple - light, permits, crowds',
                    () => _engagementIdeasSheet(inquiryId)),
""")

# ---- 8. June's location ideas
rep("""  Widget _questionnaireStrip(String inquiryId) {
""", r"""  // ---------------- v203: JUNE'S ENGAGEMENT LOCATION IDEAS ----------------
  // juneEngagementSpots (functions-dashboard) writes a set of verified spots to
  // inquiries/{id}/engagementIdeas; the couple never sees them until the
  // vendor shares one as a message.
  Query<Map<String, dynamic>> _engIdeasQ(String inquiryId) =>
      FirebaseFirestore.instance
          .collection('inquiries')
          .doc(inquiryId)
          .collection('engagementIdeas')
          .orderBy('createdAt', descending: true)
          .limit(1);

  Widget _engagementIdeasStrip(String inquiryId) {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _threadQuery(
          inquiryId, 'engagementIdeas', () => _engIdeasQ(inquiryId)),
      builder: (BuildContext context,
          AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> snap) {
        final List<QueryDocumentSnapshot<Map<String, dynamic>>> docs =
            snap.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[];
        if (docs.isEmpty) return const SizedBox(height: 0);
        final Map<String, dynamic> set = docs.first.data();
        final List<dynamic> hidden = (set['hidden'] as List?) ?? const <dynamic>[];
        final int n = ((set['spots'] as List?) ?? const <dynamic>[])
            .where((dynamic sp) =>
                sp is Map && !hidden.contains(sp['placeId']))
            .length;
        final String home =
            ((set['home'] as Map?)?['label'] ?? '').toString();
        return Padding(
          padding: const EdgeInsets.fromLTRB(18, 0, 18, 2),
          child: InkWell(
            onTap: _h(() => _engagementIdeasSheet(inquiryId)),
            borderRadius: BorderRadius.circular(12),
            child: Container(
              margin: const EdgeInsets.only(bottom: 6),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
              decoration: BoxDecoration(
                color: _lzBg(plum.withOpacity(.06)),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: _lzLine(gold.withOpacity(.5))),
              ),
              child: Row(children: <Widget>[
                Icon(Icons.place_rounded, color: _lzFg(plum), size: 17),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                      'June’s location ideas · $n spot${n == 1 ? '' : 's'}${home.isEmpty ? '' : ' near $home'}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                          color: _lzFg(plum),
                          fontSize: 12.5,
                          fontWeight: FontWeight.w700)),
                ),
                Icon(Icons.chevron_right_rounded,
                    color: _lzFg(muted), size: 18),
              ]),
            ),
          ),
        );
      },
    );
  }

  Future<bool> _juneFindSpots(String inquiryId, {bool more = false}) async {
    _showJuneVeil(
        more ? 'June is finding more spots…' : 'June is scouting locations…',
        'She reads their answers, checks each place on Google Maps and looks up the permit rules. About a minute.');
    try {
      await FirebaseFunctions.instance
          .httpsCallable('juneEngagementSpots',
              options:
                  HttpsCallableOptions(timeout: const Duration(seconds: 300)))
          .call(<String, dynamic>{'inquiryId': inquiryId, 'more': more});
      _popJuneVeil();
      return true;
    } on FirebaseFunctionsException catch (e) {
      _popJuneVeil();
      _toast(e.code == 'resource-exhausted' ||
              e.code == 'not-found' ||
              e.code == 'failed-precondition'
          ? (e.message ?? 'June couldn’t find spots this time.')
          : _lzFnMsg(e, 'June couldn’t find spots this time - try again.'));
      return false;
    } catch (_) {
      _popJuneVeil();
      _toast('June couldn’t find spots this time - try again.');
      return false;
    }
  }

  Future<void> _shareSpot(String inquiryId, DocumentReference<Map<String, dynamic>> setRef,
      Map<String, dynamic> sp) async {
    final String name = (sp['name'] ?? '').toString();
    final String area = (sp['area'] ?? '').toString();
    final String why = (sp['why'] ?? '').toString();
    final String best = (sp['bestTime'] ?? '').toString();
    final String maps = (sp['mapsUrl'] ?? '').toString();
    final bool ok = await _lzConfirm(
        'Share $name with them?',
        'They get a message in this thread with the place, why it fits and a map link.',
        confirm: 'Share it',
        cancel: 'Not now',
        icon: Icons.place_rounded);
    if (!ok) return;
    final String text = <String>[
      'An idea for your engagement session: $name${area.isEmpty ? '' : ' ($area)'}.',
      if (why.isNotEmpty) why,
      if (best.isNotEmpty) 'Best time: $best',
      if (maps.isNotEmpty) maps,
    ].join('\n');
    try {
      await _sendVendorMessage(inquiryId, text, 'responded');
      await setRef.update(<String, dynamic>{
        'shared': FieldValue.arrayUnion(<dynamic>[sp['placeId']]),
      });
      _toast('Shared with the couple ✓');
    } catch (_) {
      _toast('Couldn’t share - try again.');
    }
  }

  Widget _spotLine(IconData ic, String label, String v) {
    if (v.trim().isEmpty) return const SizedBox(height: 0);
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        Icon(ic, color: _lzFg(muted), size: 15),
        const SizedBox(width: 7),
        Expanded(
          child: Text.rich(
              TextSpan(children: <InlineSpan>[
                TextSpan(
                    text: '$label  ',
                    style: TextStyle(
                        color: _lzFg(muted),
                        fontSize: 11,
                        letterSpacing: .4,
                        fontWeight: FontWeight.w800)),
                TextSpan(
                    text: v,
                    style: TextStyle(
                        color: _lzFg(ink), fontSize: 13, height: 1.4)),
              ])),
        ),
      ]),
    );
  }

  Widget _spotCard(String inquiryId, DocumentReference<Map<String, dynamic>> setRef,
      Map<String, dynamic> sp, bool shared) {
    final String maps = (sp['mapsUrl'] ?? '').toString();
    final String src = (sp['source'] ?? '').toString();
    final dynamic mi = sp['milesFromHome'];
    final String area = (sp['area'] ?? '').toString();
    final String sub = <String>[
      if (area.isNotEmpty) area,
      if (mi is num) '${mi < 10 ? mi.toStringAsFixed(1) : mi.round()} mi from home',
    ].join(' · ');
    final ButtonStyle small = TextButton.styleFrom(
        foregroundColor: _lzFg(plum),
        padding: const EdgeInsets.symmetric(horizontal: 8),
        minimumSize: const Size(0, 34));
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.fromLTRB(14, 12, 10, 6),
      decoration: BoxDecoration(
        color: _lzBg(card),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _lzLine(goldLine)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        Row(children: <Widget>[
          Expanded(
            child: Text((sp['name'] ?? '').toString(),
                style: TextStyle(
                    color: _lzFg(plum),
                    fontSize: 15,
                    fontWeight: FontWeight.w800)),
          ),
          if (sp['verified'] == true)
            Tooltip(
              message: 'Checked on Google Maps',
              child: Icon(Icons.verified_rounded,
                  color: _lzFg(vGreen), size: 17),
            ),
        ]),
        if (sub.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Text(sub,
                style: TextStyle(color: _lzFg(muted), fontSize: 12)),
          ),
        if ((sp['why'] ?? '').toString().isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 7),
            child: Text((sp['why'] ?? '').toString(),
                style: TextStyle(
                    color: _lzFg(ink), fontSize: 13.5, height: 1.45)),
          ),
        _spotLine(Icons.wb_twilight_rounded, 'LIGHT',
            (sp['bestTime'] ?? '').toString()),
        _spotLine(Icons.badge_outlined, 'PERMIT',
            (sp['permit'] ?? '').toString()),
        _spotLine(Icons.payments_outlined, 'FEE', (sp['fee'] ?? '').toString()),
        _spotLine(Icons.groups_rounded, 'CROWDS',
            (sp['crowds'] ?? '').toString()),
        _spotLine(Icons.pets_rounded, 'PETS', (sp['pets'] ?? '').toString()),
        const SizedBox(height: 4),
        Wrap(spacing: 2, children: <Widget>[
          if (maps.isNotEmpty)
            TextButton.icon(
              style: small,
              onPressed: _h(() => launchUrl(Uri.parse(maps),
                  mode: LaunchMode.externalApplication)),
              icon: const Icon(Icons.map_outlined, size: 16),
              label: const Text('Map',
                  style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800)),
            ),
          TextButton.icon(
            style: small,
            onPressed: shared ? null : _h(() => _shareSpot(inquiryId, setRef, sp)),
            icon: Icon(shared ? Icons.check_rounded : Icons.send_rounded,
                size: 16),
            label: Text(shared ? 'Shared' : 'Share with couple',
                style: const TextStyle(
                    fontSize: 12.5, fontWeight: FontWeight.w800)),
          ),
          if (src.isNotEmpty)
            TextButton.icon(
              style: small,
              onPressed: _h(() => launchUrl(Uri.parse(src),
                  mode: LaunchMode.externalApplication)),
              icon: const Icon(Icons.open_in_new_rounded, size: 15),
              label: const Text('Rules',
                  style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800)),
            ),
          TextButton.icon(
            style: TextButton.styleFrom(
                foregroundColor: _lzFg(muted),
                padding: const EdgeInsets.symmetric(horizontal: 8),
                minimumSize: const Size(0, 34)),
            onPressed: _h(() async {
              try {
                await setRef.update(<String, dynamic>{
                  'hidden': FieldValue.arrayUnion(<dynamic>[sp['placeId']]),
                });
              } catch (_) {
                _toast('Couldn’t hide that one - try again.');
              }
            }),
            icon: const Icon(Icons.visibility_off_outlined, size: 15),
            label: const Text('Hide',
                style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800)),
          ),
        ]),
      ]),
    );
  }

  Future<void> _engagementIdeasSheet(String inquiryId) async {
    bool busy = false;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 640),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setI) {
          return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
            stream: _engIdeasQ(inquiryId).snapshots(),
            builder: (BuildContext c3,
                AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
              final List<QueryDocumentSnapshot<Map<String, dynamic>>> docs =
                  s.data?.docs ??
                      <QueryDocumentSnapshot<Map<String, dynamic>>>[];
              final QueryDocumentSnapshot<Map<String, dynamic>>? d =
                  docs.isEmpty ? null : docs.first;
              final Map<String, dynamic> set =
                  d?.data() ?? <String, dynamic>{};
              final List<dynamic> hidden =
                  (set['hidden'] as List?) ?? const <dynamic>[];
              final List<dynamic> shared =
                  (set['shared'] as List?) ?? const <dynamic>[];
              final List<Map<String, dynamic>> spots = <Map<String, dynamic>>[
                for (final dynamic sp in (set['spots'] as List?) ?? const <dynamic>[])
                  if (sp is Map && !hidden.contains(sp['placeId']))
                    Map<String, dynamic>.from(sp)
              ];
              final Map<String, dynamic> home =
                  Map<String, dynamic>.from((set['home'] as Map?) ?? const <String, dynamic>{});
              final String note = (set['note'] ?? '').toString();
              Future<void> go(bool more) async {
                setI(() => busy = true);
                await _juneFindSpots(inquiryId, more: more);
                if (ctx2.mounted) setI(() => busy = false);
              }

              return _lzFrame(ctx2,
                  icon: Icons.place_rounded,
                  title: 'Engagement location ideas',
                  subtitle: d == null
                      ? 'June suggests spots near where the couple lives, and why each one fits them.'
                      : 'Near ${(home['label'] ?? 'them').toString()}${set['radius'] is num ? ', within ${set['radius']} mi' : ''}${set['answered'] == true ? ' · from their answers' : ' · before their answers'}',
                  children: <Widget>[
                    const SizedBox(height: 12),
                    if (!s.hasData && !s.hasError)
                      _lzBusy('Loading June’s ideas…')
                    else if (d == null)
                      _pv2Empty(Icons.travel_explore_rounded,
                          'June hasn’t looked yet. Send the engagement questionnaire and she’ll scout when the answers come back, or ask her now.')
                    else ...<Widget>[
                      if (note.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: Text(note,
                              style: TextStyle(
                                  color: _lzFg(muted),
                                  fontSize: 12.5,
                                  fontStyle: FontStyle.italic)),
                        ),
                      if (spots.isEmpty)
                        _pv2Empty(Icons.visibility_off_outlined,
                            'You hid every spot in this set. Ask June for more.'),
                      for (final Map<String, dynamic> sp in spots)
                        _spotCard(inquiryId, d.reference, sp,
                            shared.contains(sp['placeId'])),
                      Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text(
                            'June checked each place on Google Maps. Permit and fee details come from the web, so confirm them before the shoot.',
                            style: TextStyle(
                                fontSize: 11.5, color: _lzFg(muted))),
                      ),
                    ],
                  ],
                  footer: _lzActions(
                      secondary: 'Close',
                      onSecondary: () => Navigator.pop(ctx2),
                      primary: d == null ? 'Find spots' : 'More like this',
                      icon: Icons.auto_awesome_rounded,
                      busy: busy,
                      onPrimary: busy ? null : () => go(d != null)));
            },
          );
        },
      ),
    );
  }

  Widget _questionnaireStrip(String inquiryId) {
""")

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8", newline="")
print(f"wrote {DST.name} from {SRC.name}: {len(out.splitlines())} lines")
