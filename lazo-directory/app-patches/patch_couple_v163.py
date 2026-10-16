r"""patch_couple_v163.py - Couple v159 -> v163: ENGAGEMENT SESSIONS.  JC-LAZO-ENGAGE-1016-COUPLE

A vendor's questionnaire can now say how each question is answered (questionnaires.spec, Vendor v203): short or
long answer, pick any (chips), pick one, or dates (up to three, plus "We're flexible"). The couple's form shows the
right control; answers are still saved as text, so the vendor's answer sheet and older apps are unchanged.
"Where do you live?" on an engagement questionnaire starts filled in with their wedding town or city, which they
can change. The thread card says "<Studio> sent your engagement session questions".

    python app-patches\patch_couple_v163.py [base]     # base defaults to Couple_master_v159.txt
                                                        # writes Couple_master_v163.txt
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / (sys.argv[1] if len(sys.argv) > 1 else "Couple_master_v159.txt")
DST = HERE / "Couple_master_v163.txt"
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, f"expected {n} match(es), found {c}: {old[:90]!r}"
    s = s.replace(old, new)


rep("// lazo_couple_dashboard.dart\n",
    "// lazo_couple_dashboard.dart\n"
    "// Build ID: JC-LAZO-ENGAGE-1016-COUPLE (v163: TYPED QUESTIONNAIRES - questionnaires.spec gives each question "
    "its control: short or long answer, pick any, pick one, dates; answers stay text; an engagement questionnaire's "
    "'Where do you live?' starts with the wedding town; base " + SRC.stem.replace("Couple_master_", "") + ")\n")

# ---- the card line
rep("""                          : '$vendorName sent a few questions to plan your day perfectly.',
""", """                          : (qn['type'] ?? '') == 'engagement'
                              ? '$vendorName sent your engagement session questions.'
                              : '$vendorName sent a few questions to plan your day perfectly.',
""")

# ---- a long answer gets room
rep("""  Widget _pcC_question(int i, String q, TextEditingController c,
          {bool autofocus = false, ValueChanged<String>? onChanged}) =>
""", """  Widget _pcC_question(int i, String q, TextEditingController c,
          {bool autofocus = false,
          ValueChanged<String>? onChanged,
          int minLines = 1,
          String hint = 'Your answer',
          Widget? below}) =>
""")
rep("""              TextField(
                controller: c,
                autofocus: autofocus,
                minLines: 1,
                maxLines: 5,
                textCapitalization: TextCapitalization.sentences,
                onChanged: onChanged,
                style: TextStyle(fontSize: 14.5, color: _lzFg(ink)),
                decoration: _lightDeco('', hint: 'Your answer'),
              ),
            ]),
      );
""", """              below ??
                  TextField(
                    controller: c,
                    autofocus: autofocus,
                    minLines: minLines,
                    maxLines: minLines > 1 ? 8 : 5,
                    textCapitalization: TextCapitalization.sentences,
                    onChanged: onChanged,
                    style: TextStyle(fontSize: 14.5, color: _lzFg(ink)),
                    decoration: _lightDeco('', hint: hint),
                  ),
            ]),
      );

  // v163: a question with an answer type from the vendor (questionnaires.spec).
  // Everything is still kept as text in the controller: chips joined with
  // ', ', dates with '; '.
  Widget _pcC_typed(BuildContext ctx, int i, String q, dynamic spec,
      TextEditingController c,
      {bool autofocus = false, required ValueChanged<String> onChanged}) {
    final Map<String, dynamic> sp = spec is Map
        ? Map<String, dynamic>.from(spec)
        : const <String, dynamic>{};
    final String kind = (sp['kind'] ?? 'text').toString();
    final List<String> opts = ((sp['options'] as List?) ?? const <dynamic>[])
        .map((dynamic e) => e.toString())
        .where((String e) => e.trim().isNotEmpty)
        .toList();
    void put(String v) {
      c.text = v;
      onChanged(v);
    }

    Widget chip(String label, bool on, VoidCallback go) => FilterChip(
          label: Text(label,
              style: TextStyle(
                  fontSize: 13,
                  color: on ? ivory : _lzFg(plum),
                  fontWeight: FontWeight.w600)),
          selected: on,
          showCheckmark: false,
          selectedColor: plum,
          backgroundColor: _lzBg(Colors.white),
          side: BorderSide(color: on ? plum : _lzLine(goldLine)),
          onSelected: (bool _) => go(),
        );

    if ((kind == 'many' || kind == 'one') && opts.length >= 2) {
      final List<String> picked = c.text
          .split(',')
          .map((String x) => x.trim())
          .where((String x) => x.isNotEmpty)
          .toList();
      return _pcC_question(i, q, c,
          below: Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
            for (final String o in opts)
              chip(o, picked.contains(o), () {
                if (kind == 'one') {
                  put(picked.contains(o) ? '' : o);
                } else {
                  final List<String> next = <String>[
                    for (final String x in opts)
                      if (x == o ? !picked.contains(o) : picked.contains(x)) x
                  ];
                  put(next.join(', '));
                }
              }),
          ]));
    }
    if (kind == 'dates') {
      const String flex = 'We\\u2019re flexible';
      final int max = sp['max'] is num ? (sp['max'] as num).toInt() : 3;
      final List<String> picked = c.text
          .split(';')
          .map((String x) => x.trim())
          .where((String x) => x.isNotEmpty)
          .toList();
      final List<String> days = picked.where((String x) => x != flex).toList();
      return _pcC_question(i, q, c,
          below: Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
            for (final String d in days)
              InputChip(
                label: Text(d,
                    style: TextStyle(
                        fontSize: 13,
                        color: _lzFg(plum),
                        fontWeight: FontWeight.w600)),
                backgroundColor: _lzBg(Colors.white),
                side: BorderSide(color: _lzLine(goldLine)),
                onDeleted: () =>
                    put(picked.where((String x) => x != d).join('; ')),
              ),
            if (days.length < max)
              ActionChip(
                avatar: Icon(Icons.event_rounded, size: 16, color: _lzFg(plum)),
                label: Text(days.isEmpty ? 'Pick a date' : 'Add another',
                    style: TextStyle(
                        fontSize: 13,
                        color: _lzFg(plum),
                        fontWeight: FontWeight.w700)),
                backgroundColor: _lzBg(Colors.white),
                side: BorderSide(color: _lzLine(gold)),
                onPressed: () async {
                  final DateTime now = DateTime.now();
                  final DateTime? d = await showDatePicker(
                      context: ctx,
                      initialDate: now.add(const Duration(days: 14)),
                      firstDate: now,
                      lastDate: DateTime(now.year + 3));
                  if (d == null) return;
                  const List<String> wd = <String>['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
                  final String label =
                      '${wd[d.weekday - 1]} ${_kMo[d.month - 1]} ${d.day}, ${d.year}';
                  if (picked.contains(label)) return;
                  put(<String>[...days, label, if (picked.contains(flex)) flex]
                      .join('; '));
                },
              ),
            chip(flex, picked.contains(flex), () {
              put(picked.contains(flex)
                  ? days.join('; ')
                  : <String>[...days, flex].join('; '));
            }),
          ]));
    }
    return _pcC_question(i, q, c,
        autofocus: autofocus,
        onChanged: onChanged,
        minLines: kind == 'long' ? 3 : 1,
        hint: sp['key'] == 'home'
            ? 'City or neighborhood'
            : 'Your answer');
  }
""")

# ---- the form uses the answer types, and fills in where they live
rep("""    final String from = (qn['vendorName'] ?? '').toString();
    bool saving = false;
    bool open = true;
""", """    final String from = (qn['vendorName'] ?? '').toString();
    // v163: the vendor's answer types (Vendor v203); none means text boxes.
    final List<dynamic> spec = qn['spec'] is List
        ? qn['spec'] as List<dynamic>
        : const <dynamic>[];
    for (int i = 0; i < spec.length && i < cs.length; i++) {
      if (spec[i] is Map &&
          (spec[i] as Map)['key'] == 'home' &&
          cs[i].text.trim().isEmpty) {
        final TextEditingController hc = cs[i];
        _coupleRef.get().then((DocumentSnapshot<Map<String, dynamic>> cd) {
          final Map<String, dynamic> c0 = cd.data() ?? <String, dynamic>{};
          final String town = (c0['town'] ?? '').toString();
          final String metro = _metroLabel((c0['metroId'] ?? '').toString());
          final String guess = town.isNotEmpty ? town : metro;
          if (guess.isNotEmpty && hc.text.trim().isEmpty) hc.text = guess;
        }).catchError((Object _) {});
      }
    }
    bool saving = false;
    bool open = true;
""")
rep("""                  for (int i = 0; i < questions.length; i++)
                    _pcC_question(i, questions[i].toString(), cs[i],
                        autofocus: i == 0 && cs[0].text.isEmpty,
                        onChanged: (_) => up(() {})),
""", """                  for (int i = 0; i < questions.length; i++)
                    _pcC_typed(ctx2, i, questions[i].toString(),
                        i < spec.length ? spec[i] : null, cs[i],
                        autofocus: i == 0 && cs[0].text.isEmpty &&
                            spec.isEmpty,
                        onChanged: (_) => up(() {})),
""")

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8", newline="")
print(f"wrote {DST.name} from {SRC.name}: {len(out.splitlines())} lines")
