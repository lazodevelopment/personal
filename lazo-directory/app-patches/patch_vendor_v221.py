"""Vendor v221: two Pearl Connect borrows (JC-LAZO-PEARL-1019-VENDOR).

    python app-patches\\patch_vendor_v221.py [base.txt]   # base defaults to Vendor_master_v220.txt
                                                          # writes Vendor_master_v221.txt
From the 2026-10-19 audit of David's Bridal Pearl Connect (connect.davidsbridal.com):
- "Let June draft it" under the Bio and the Services detail fields of the profile editor. June
  (the juneVendor callable, same as Ask June) writes 90-140 words from the business name, categories,
  home market, markets served, starting price and whatever is already in the field; a sheet shows the
  draft with Use it / Try again / Keep mine. Nothing is saved until the vendor saves the profile.
  (Pearl gives "AI listing optimization" away free; Lazo's profile strength only said what was missing.)
- A warmth read on every inbox row: KEEN when the couple's latest words talk about booking, dates,
  deposits or contracts; HESITANT when they are comparing, unsure or budget-shy. Read from
  lastMessagePreview / the first message, only when the last word was the couple's. A nudge next to the
  pipeline pills, not a verdict; no new fields.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Vendor_master_v220.txt"
DST = HERE / "Vendor_master_v221.txt"
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
    "// Build ID: JC-LAZO-PEARL-1019-VENDOR (v221: JUNE DRAFTS THE LISTING + WARMTH - 'Let June draft it' under Bio "
    "and Services detail (juneVendor writes from name, categories, markets, price and what is there; Use it / Try "
    "again / Keep mine); KEEN / HESITANT pills on inbox rows read from the couple's latest words; base v220)\n"
) + s[first_build:]

# ---- profile editor: June drafts the bio and the services note
rep("""            decoration: _epDeco('About your business',
                'Your story, your style, what makes you worth trusting with the day'),
          ),""", """            decoration: _epDeco('About your business',
                'Your story, your style, what makes you worth trusting with the day'),
          ),
          _juneDraftRow('bio'), // v221""")

rep("""              decoration: _epDeco('Services detail (optional)',
                  'e.g. drone coverage, second shooter, same-day edits')),""",
    """              decoration: _epDeco('Services detail (optional)',
                  'e.g. drone coverage, second shooter, same-day edits')),
          _juneDraftRow('services'), // v221""")

# ---- inbox rows: the warmth read
rep("                        if (st == 'new' || st.isEmpty) _inboxPill('NEW', gold),",
    "                        if (st == 'new' || st.isEmpty) _inboxPill('NEW', gold),\n"
    "                        ..._warmthPills(m, st), // v221")

HELPERS = r"""  // ---- v221: the warmth read ------------------------------------------------------------
  static const List<String> _kKeen = <String>[
    'book', 'booking', 'deposit', 'retainer', 'contract', 'hold the date', 'save the date', 'sign', 'lock in',
    'next step', 'how do we', 'when can we', 'love your', 'loved your', 'we’re in', "we're in", 'excited',
    'can’t wait', "can't wait", 'available on', 'are you available', 'is our date', 'our date is', 'go ahead',
    'let’s do it', "let's do it", 'send the contract', 'invoice', 'pay',
  ];
  static const List<String> _kHesitant = <String>[
    'just looking', 'just browsing', 'still deciding', 'not sure', 'unsure', 'maybe', 'thinking about',
    'compar', 'other vendors', 'other photographers', 'other options', 'a few quotes', 'quotes from', 'cheaper',
    'expensive', 'out of our budget', 'over budget', 'too much', 'discount', 'lower', 'negotiat', 'no rush',
    'get back to you', 'circle back', 'later', 'eventually', 'might', 'possibly',
  ];

  /// 'keen', 'hesitant' or '' from the couple's latest words. Only when the last word was theirs.
  String _warmthOf(Map<String, dynamic> m) {
    final String role = (m['lastMessageRole'] ?? '').toString();
    if (role.isNotEmpty && role != 'couple') return '';
    final String t = ('${m['lastMessagePreview'] ?? ''} ${m['message'] ?? ''}').toLowerCase();
    if (t.trim().length < 12) return '';
    int keen = 0, hes = 0;
    for (final String k in _kKeen) {
      if (t.contains(k)) keen++;
    }
    for (final String k in _kHesitant) {
      if (t.contains(k)) hes++;
    }
    if (keen == 0 && hes == 0) return '';
    if (keen > hes) return 'keen';
    if (hes > keen) return 'hesitant';
    return '';
  }

  List<Widget> _warmthPills(Map<String, dynamic> m, String st) {
    if (st == 'booked' || st == 'lost' || st == 'delivered') return const <Widget>[];
    final String w = _warmthOf(m);
    if (w == 'keen') return <Widget>[_inboxPill('KEEN', vGreen)];
    if (w == 'hesitant') return <Widget>[_inboxPill('HESITANT', const Color(0xFFB04343))];
    return const <Widget>[];
  }

  // ---- v221: June drafts the listing ------------------------------------------------------
  Widget _juneDraftRow(String field) {
    return Padding(
      padding: const EdgeInsets.only(top: 2, bottom: 6),
      child: Row(children: <Widget>[
        ActionChip(
          avatar: Icon(Icons.auto_awesome_rounded, size: 15, color: _lzFg(plum)),
          label: Text(field == 'bio' ? 'Let June draft it' : 'Let June list them',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: _lzFg(plum))),
          backgroundColor: _lzBg(ivory),
          side: BorderSide(color: gold.withOpacity(.6)),
          visualDensity: VisualDensity.compact,
          onPressed: _epSaving ? null : () => _juneDraftSheet(field),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text('From your name, categories, markets and what’s here. You choose what stays.',
              style: TextStyle(fontSize: 11, color: _lzFg(muted))),
        ),
      ]),
    );
  }

  Future<String> _juneDraftAsk(String field) async {
    final String name = _epName.isNotEmpty ? _epName : 'this business';
    final List<String> cats = <String>[];
    for (final String id in _epCats) {
      final int i = _catIds.indexOf(id);
      cats.add(i >= 0 ? _catNames[i] : id);
    }
    final String metro = _metroLabel(_epHomeMetro).isEmpty ? _epHomeMetro : _metroLabel(_epHomeMetro);
    final int markets = _epHome.length + _epTravel.length;
    final String current = (field == 'bio' ? _epBioC.text : _epServicesC.text).trim();
    final String ask = field == 'bio'
        ? 'Write the About section for my Lazo listing: 90 to 140 words, first person plural, warm and specific, '
            'no clichés like "capturing moments", no exclamation marks, no emoji, no markdown, no heading. '
            'Business: $name. What we do: ${cats.isEmpty ? 'wedding services' : cats.join(', ')}. '
            'Home market: ${metro.isEmpty ? 'not set' : metro}${markets > 0 ? ', serving $markets markets' : ''}. '
            'Starting price: ${_epStartPriceC.text.trim().isEmpty ? 'not set' : _epStartPriceC.text.trim()}. '
            '${current.isEmpty ? 'There is no bio yet.' : 'Keep the facts from the current bio and improve it: "$current"'} '
            'Reply with the paragraph only.'
        : 'Write the Services detail line for my Lazo listing: one paragraph of 25 to 60 words listing what is '
            'included and the add-ons, plain and specific, no exclamation marks, no emoji, no markdown. '
            'Business: $name. Categories: ${cats.isEmpty ? 'wedding services' : cats.join(', ')}. '
            '${current.isEmpty ? 'Nothing is written yet; infer sensible services for these categories and say they can edit it.' : 'Start from what is there and tidy it: "$current"'} '
            'Reply with the paragraph only.';
    final HttpsCallable fn = FirebaseFunctions.instance.httpsCallable('juneVendor',
        options: HttpsCallableOptions(timeout: const Duration(seconds: 120)));
    final HttpsCallableResult<dynamic> r = await fn.call(<String, dynamic>{
      'vendorId': _epVendorId,
      'messages': <Map<String, dynamic>>[
        <String, dynamic>{'role': 'user', 'content': ask},
      ],
    });
    final Map<String, dynamic> data = Map<String, dynamic>.from(r.data as Map);
    return (data['reply'] ?? '').toString().trim().replaceAll(RegExp(r'^["“]|["”]$'), '');
  }

  Future<void> _juneDraftSheet(String field) async {
    if (!mounted || _epVendorId.isEmpty) return;
    String draft = '';
    String err = '';
    bool busy = true;
    bool open = true;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        void up(VoidCallback f) {
          if (open) setSheet(f);
        }

        Future<void> go() async {
          up(() {
            busy = true;
            err = '';
          });
          try {
            final String d = await _juneDraftAsk(field);
            up(() {
              draft = d;
              busy = false;
              if (d.isEmpty) err = 'June came back empty - try again.';
            });
          } on FirebaseFunctionsException catch (e) {
            up(() {
              busy = false;
              err = _lzFnMsg(e, 'June could not write right now.');
            });
          } catch (_) {
            up(() {
              busy = false;
              err = 'June could not write right now.';
            });
          }
        }

        if (busy && draft.isEmpty && err.isEmpty) {
          // first open: ask once
          busy = false;
          Future<void>.microtask(go);
          busy = true;
        }
        return _lzFrame(sc,
            icon: Icons.auto_awesome_rounded,
            title: field == 'bio' ? 'June’s draft of your bio' : 'June’s draft of your services',
            subtitle: 'Written from your listing. Use it as is, or as a starting point - nothing saves until you save the profile.',
            children: <Widget>[
              const SizedBox(height: 14),
              if (busy)
                Row(children: <Widget>[
                  SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: _lzFg(plum))),
                  const SizedBox(width: 10),
                  Text('June is writing…', style: TextStyle(fontSize: 13, color: _lzFg(muted))),
                ])
              else if (err.isNotEmpty)
                Text(err, style: const TextStyle(fontSize: 13, color: Color(0xFFB04343), fontWeight: FontWeight.w600))
              else
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: _lzBg(Colors.white.withOpacity(.8)),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: _lzLine(gold.withOpacity(.6))),
                  ),
                  child: SelectableText(draft, style: TextStyle(fontSize: 14, height: 1.5, color: _lzFg(ink))),
                ),
              const SizedBox(height: 16),
              Wrap(spacing: 10, runSpacing: 10, children: <Widget>[
                FilledButton.icon(
                  onPressed: busy || draft.isEmpty
                      ? null
                      : () {
                          setState(() {
                            if (field == 'bio') {
                              _epBioC.text = draft.length > 600 ? draft.substring(0, 600) : draft;
                            } else {
                              _epServicesC.text = draft;
                            }
                          });
                          Navigator.pop(sc);
                          _toast('Dropped in. Read it over, then Save.');
                        },
                  icon: const Icon(Icons.check_rounded, size: 16),
                  label: const Text('Use it'),
                  style: FilledButton.styleFrom(backgroundColor: plum, foregroundColor: Colors.white),
                ),
                OutlinedButton.icon(
                  onPressed: busy ? null : go,
                  icon: const Icon(Icons.refresh_rounded, size: 16),
                  label: const Text('Try again'),
                  style: OutlinedButton.styleFrom(foregroundColor: _lzFg(plum), side: BorderSide(color: gold.withOpacity(.8))),
                ),
                TextButton(
                  onPressed: () => Navigator.pop(sc),
                  child: Text('Keep mine', style: TextStyle(color: _lzFg(muted))),
                ),
              ]),
            ]);
      }),
    );
    open = false;
  }

"""
rep("  Widget _inboxPill(String label, Color c) {", HELPERS + "  Widget _inboxPill(String label, Color c) {")

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8")
print("wrote", DST, len(s.splitlines()), "lines")
