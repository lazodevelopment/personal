"""Couple v172: getting started + What you can do (JC-LAZO-DISCOVER-1018-COUPLE).

    python app-patches\\patch_couple_v172.py [base.txt]   # base defaults to Couple_master_v171.txt
                                                          # writes Couple_master_v172.txt
- a Getting started card on Home (above the widgets rail) with seven steps that tick
  themselves off from data the app already has: date+city, guest count (new one-field
  sheet writes couples.guestEstimate), budget, partner invite, first vendor message,
  website published, first question to June (couples.starts.{partner,june} marks);
  Hide this / Done writes couples.startHiddenAt
- a "What you can do" sheet: every screen and tool as a tile with one honest line,
  grouped Plan / Guests / Vendors / Day-of, NEW badges for this month's features,
  a check on the ones already used; opened from the card, the desk sheet (15th
  tile) and Account > More
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v171.txt"
DST = HERE / "Couple_master_v172.txt"
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
    "// Build ID: JC-LAZO-DISCOVER-1018-COUPLE (v172: GETTING STARTED + WHAT YOU CAN DO - a seven-step card on Home that "
    "ticks itself off from the plan (date and city, guest count, budget, partner, first vendor message, website, first "
    "question to June) with Hide / Done, and a What-you-can-do sheet of every screen and tool with one line each, NEW "
    "badges and a check on the ones already used - from the card, the desk sheet and Account; base v171)\n"
) + s[first_build:]

NEW_METHODS = r'''
  // ---------------- v172: GETTING STARTED + WHAT YOU CAN DO ----------------
  // The card ticks itself: every step is a signal the plan already carries.
  // couples.starts.{partner,june} are the two the data cannot tell on its own.
  Map<String, dynamic> _wcdCouple = <String, dynamic>{};
  List<QueryDocumentSnapshot<Map<String, dynamic>>> _wcdInqs =
      <QueryDocumentSnapshot<Map<String, dynamic>>>[];

  Future<void> _markStart(String key) async {
    try {
      await _coupleRef.set(<String, dynamic>{
        'starts': <String, dynamic>{key: true}
      }, SetOptions(merge: true));
    } catch (_) {}
  }

  // [key, title, done, button, action]
  List<List<dynamic>> _startItems(Map<String, dynamic> couple,
      List<QueryDocumentSnapshot<Map<String, dynamic>>> inqs) {
    final Map<String, dynamic> st = Map<String, dynamic>.from(
        (couple['starts'] as Map?) ?? <String, dynamic>{});
    final bool siteOn =
        (_liveQ['site:$_cid']?.latest?.docs.isNotEmpty ?? false) ||
            st['website'] == true;
    final bool partner = st['partner'] == true ||
        (_liveQ['cinv:$_cid']?.latest?.docs.isNotEmpty ?? false);
    final num? budget = couple['budgetTotal'] is num ? couple['budgetTotal'] as num : null;
    final num? guests = couple['guestEstimate'] is num ? couple['guestEstimate'] as num : null;
    return <List<dynamic>>[
      <dynamic>[
        'date',
        'Set your date and city',
        couple['weddingDate'] is Timestamp &&
            (couple['metroId'] ?? '').toString().isNotEmpty,
        'Set',
        () {
          _setupSheet(couple);
        }
      ],
      <dynamic>[
        'guests',
        'Add your guest count',
        guests != null && guests > 0,
        'Add',
        () {
          _guestEstimateSheet(couple);
        }
      ],
      <dynamic>[
        'budget',
        'Set a budget',
        budget != null && budget > 0,
        'Set',
        () {
          _setBudgetSheet(budget);
        }
      ],
      <dynamic>[
        'partner',
        'Invite your partner',
        partner,
        'Invite',
        () {
          _partnerSheet(couple);
        }
      ],
      <dynamic>[
        'vendor',
        'Message your first vendor',
        inqs.isNotEmpty,
        'Browse',
        () {
          setState(() => _view = _View.browse);
        }
      ],
      <dynamic>[
        'website',
        'Publish your wedding website',
        siteOn,
        'Open',
        () {
          setState(() => _view = _View.website);
        }
      ],
      <dynamic>[
        'june',
        'Ask June something',
        st['june'] == true,
        'Ask',
        () {
          _askJune('');
        }
      ],
    ];
  }

  Widget _startCard(Map<String, dynamic> couple,
      List<QueryDocumentSnapshot<Map<String, dynamic>>> inqs) {
    _wcdCouple = couple;
    _wcdInqs = inqs;
    if (couple['startHiddenAt'] != null) return const SizedBox.shrink();
    final List<List<dynamic>> items = _startItems(couple, inqs);
    final int done = items.where((List<dynamic> i) => i[2] == true).length;
    final bool all = done == items.length;
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: _glass(
        padding: const EdgeInsets.fromLTRB(18, 14, 18, 8),
        child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(children: <Widget>[
                Expanded(
                    child: Text(all ? 'You’re all set' : 'Getting started',
                        style: _serif(size: 21))),
                Text('$done OF ${items.length}',
                    style: TextStyle(
                        fontSize: 11,
                        letterSpacing: 1.2,
                        fontWeight: FontWeight.w700,
                        color: _lzFg(muted))),
              ]),
              const SizedBox(height: 8),
              ClipRRect(
                borderRadius: BorderRadius.circular(3),
                child: LinearProgressIndicator(
                    value: done / items.length,
                    minHeight: 6,
                    backgroundColor: _lzBg(const Color(0xFFEFE6DA)),
                    valueColor: const AlwaysStoppedAnimation<Color>(gold)),
              ),
              const SizedBox(height: 6),
              if (all)
                Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(
                        'Everything is in place. June takes it from here.',
                        style: TextStyle(fontSize: 13, color: _lzFg(muted))))
              else
                for (final List<dynamic> it in items)
                  Container(
                    padding: const EdgeInsets.symmetric(vertical: 7),
                    decoration: BoxDecoration(
                        border: Border(
                            top: BorderSide(
                                color: _lzLine(const Color(0xFFF0E8DD))))),
                    child: Row(children: <Widget>[
                      Container(
                        width: 22,
                        height: 22,
                        decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: it[2] == true ? vGreen : Colors.transparent,
                            border: Border.all(
                                color: it[2] == true ? vGreen : gold,
                                width: 1.5)),
                        child: it[2] == true
                            ? const Icon(Icons.check_rounded,
                                size: 14, color: Colors.white)
                            : null,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                          child: Text(it[1] as String,
                              style: TextStyle(
                                  fontSize: 13.5,
                                  color: _lzFg(it[2] == true ? muted : ink),
                                  decoration: it[2] == true
                                      ? TextDecoration.lineThrough
                                      : TextDecoration.none))),
                      if (it[2] != true)
                        _Press(
                          onTap: _h(() => (it[4] as void Function())()),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 10, vertical: 6),
                            decoration: BoxDecoration(
                                color: _lzBg(const Color(0xFFF3EADF)),
                                borderRadius: BorderRadius.circular(999)),
                            child: Text(it[3] as String,
                                style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w700,
                                    color: _lzFg(plum))),
                          ),
                        ),
                    ]),
                  ),
              Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: <Widget>[
                    TextButton(
                      onPressed: _h(() => _whatYouCanDoSheet()),
                      child: Text('Everything Lazo can do →',
                          style: TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w700,
                              color: _lzFg(plum))),
                    ),
                    TextButton(
                      onPressed: _h(() => _coupleRef.set(<String, dynamic>{
                            'startHiddenAt': FieldValue.serverTimestamp()
                          }, SetOptions(merge: true))),
                      child: Text(all ? 'Done' : 'Hide this',
                          style: TextStyle(
                              fontSize: 12, color: _lzFg(muted))),
                    ),
                  ]),
            ]),
      ),
    );
  }

  Future<void> _guestEstimateSheet(Map<String, dynamic> couple) async {
    final TextEditingController c = TextEditingController(
        text: couple['guestEstimate'] is num
            ? (couple['guestEstimate'] as num).toInt().toString()
            : '');
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.group_rounded,
          title: 'About how many guests?',
          subtitle:
              'A rough number is fine. Venues and caterers quote by headcount; change it any time.',
          children: <Widget>[
            TextField(
              controller: c,
              keyboardType: TextInputType.number,
              autofocus: true,
              style: TextStyle(color: _lzFg(ink), fontSize: 16),
              decoration: InputDecoration(
                hintText: '120',
                filled: true,
                fillColor: _lzBg(Colors.white),
                border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: gold)),
                enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: gold)),
              ),
            ),
            const SizedBox(height: 14),
            FilledButton(
              style: FilledButton.styleFrom(
                  backgroundColor: gold,
                  foregroundColor: plum,
                  padding: const EdgeInsets.symmetric(vertical: 13)),
              onPressed: () async {
                final int n = int.tryParse(c.text.trim()) ?? 0;
                if (n <= 0) return;
                await _coupleRef.set(<String, dynamic>{'guestEstimate': n},
                    SetOptions(merge: true));
                if (ctx.mounted) Navigator.of(ctx).pop();
                _toastC('Saved: about $n guests.');
              },
              child: const Text('Save',
                  style: TextStyle(fontWeight: FontWeight.w800)),
            ),
          ]),
    );
  }

  Future<void> _whatYouCanDoSheet() async {
    final Map<String, dynamic> couple = _wcdCouple;
    final bool hasBudget =
        couple['budgetTotal'] is num && (couple['budgetTotal'] as num) > 0;
    final bool hasGuests = couple['guestEstimate'] is num &&
        (couple['guestEstimate'] as num) > 0;
    final bool hasInq = _wcdInqs.isNotEmpty;
    final bool hasSite =
        _liveQ['site:$_cid']?.latest?.docs.isNotEmpty ?? false;
    final Map<String, dynamic> st = Map<String, dynamic>.from(
        (couple['starts'] as Map?) ?? <String, dynamic>{});
    // [section, title, line, icon, used, isNew, action]
    final List<List<dynamic>> tiles = <List<dynamic>>[
      <dynamic>['Plan', 'Budget', '15 categories, planned vs paid; June adjusts as you book', Icons.savings_rounded, hasBudget, false, () { _setBudgetSheet(couple['budgetTotal'] is num ? couple['budgetTotal'] as num : null); }],
      <dynamic>['Plan', 'Dream board', 'Pin Pinterest or Etsy links, photos and colors; share it with your florist', Icons.auto_awesome_mosaic_rounded, false, false, () { setState(() => _view = _View.board); }],
      <dynamic>['Plan', 'Shopping list', 'What you buy yourselves, with rough prices; send it to your planner', Icons.shopping_bag_rounded, false, false, () { setState(() => _view = _View.shopping); }],
      <dynamic>['Plan', 'Registry', 'Link any store, fund or charity; it shows on your website', Icons.card_giftcard_rounded, false, false, () { setState(() => _view = _View.registry); }],
      <dynamic>['Plan', 'Contracts vault', 'Every agreement your vendors sent, signed or waiting, with the PDFs', Icons.history_edu_rounded, false, false, () { _contractsVaultSheet(); }],
      <dynamic>['Plan', 'Switching from The Knot or Zola', 'Bring your guest list, website, budget and booked vendors', Icons.move_down_rounded, false, false, () { _importSheet(couple); }],
      <dynamic>['Guests', 'Guest list and RSVPs', 'Everyone invited, who said yes, plus-ones and tables', Icons.group_rounded, hasGuests, false, () { setState(() => _view = _View.guests); }],
      <dynamic>['Guests', 'Meal choices', 'Guests pick a meal when they RSVP; send the counts to your caterer', Icons.restaurant_rounded, false, true, () { setState(() => _view = _View.guests); }],
      <dynamic>['Guests', 'Seating chart', 'Tables, the dance floor and the bar; drag guests to seats', Icons.table_restaurant_rounded, false, false, () { _openSeating(); }],
      <dynamic>['Guests', 'Thank-you notes', 'Who gave what and who has been thanked', Icons.mark_email_read_rounded, false, false, () { setState(() => _view = _View.guests); }],
      <dynamic>['Guests', 'Wedding website', 'Your story, RSVPs, registry, hotels, a day-before note and a photo wall', Icons.language_rounded, hasSite, false, () { setState(() => _view = _View.website); }],
      <dynamic>['Vendors', 'Browse verified vendors', 'Photo, price and reviews up front; check your date in one tap', Icons.storefront_rounded, hasInq, false, () { setState(() => _view = _View.browse); }],
      <dynamic>['Vendors', 'Vendor team', 'The categories you need, who is booked and who is running late', Icons.checklist_rounded, false, false, () { setState(() => _view = _View.vendors); }],
      <dynamic>['Vendors', 'Messages', 'One thread per vendor: proposals, contracts, invoices and files', Icons.chat_bubble_rounded, hasInq, false, () { setState(() => _view = _View.messages); }],
      <dynamic>['Vendors', 'Lazo video calls', 'Meet a vendor inside the app; your camera stays off until you say so', Icons.videocam_rounded, false, true, () { setState(() => _view = _View.messages); }],
      <dynamic>['Vendors', 'Engagement questionnaire', 'Your photographer sends it; June suggests spots near you', Icons.photo_camera_rounded, false, true, () { setState(() => _view = _View.messages); }],
      <dynamic>['Vendors', 'Plan together', 'Invite your partner: same plan, same inbox', Icons.favorite_rounded, st['partner'] == true, false, () { _partnerSheet(couple); }],
      <dynamic>['Day-of', 'Day-of timeline', 'Every moment with owners and times; shared to each vendor’s thread', Icons.event_rounded, false, false, () { setState(() => _view = _View.dayof); }],
      <dynamic>['Day-of', 'Music and DJ set list', 'First dance, must-plays and never-plays; your DJ sees the list', Icons.music_note_rounded, false, true, () { _openMusic(); }],
      <dynamic>['Day-of', 'Marriage license', 'Fee, wait and the county office for your state, timed to your date', Icons.verified_rounded, false, false, () { setState(() => _view = _View.dayof); }],
      <dynamic>['Day-of', 'Weather on your date', 'The forecast, or what that day has been like for five years', Icons.wb_sunny_rounded, false, false, () { setState(() => _view = _View.dayof); }],
      <dynamic>['Day-of', 'June', 'Ask anything about vendors, guests, money or the day; she remembers', Icons.auto_awesome_rounded, st['june'] == true, false, () { setState(() => _view = _View.june); }],
    ];
    final List<String> sections = <String>['Plan', 'Guests', 'Vendors', 'Day-of'];
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 680),
      builder: (BuildContext ctx) {
        Widget tile(List<dynamic> t, double w) {
          return SizedBox(
            width: w,
            child: Opacity(
              opacity: t[4] == true ? .6 : 1,
              child: _Press(
                onTap: () {
                  Navigator.of(ctx).pop();
                  (t[6] as void Function())();
                },
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                      color: _lzBg(Colors.white),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: _lzLine(const Color(0xFFEADFD3)))),
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Row(children: <Widget>[
                          Container(
                            width: 32,
                            height: 32,
                            decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(10),
                                gradient: const LinearGradient(
                                    colors: <Color>[gold, gold2])),
                            child: Icon(t[3] as IconData, size: 17, color: plum),
                          ),
                          const Spacer(),
                          if (t[5] == true)
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                              decoration: BoxDecoration(color: gold, borderRadius: BorderRadius.circular(999)),
                              child: const Text('NEW',
                                  style: TextStyle(fontSize: 9, letterSpacing: 1.2, fontWeight: FontWeight.w800, color: plum)),
                            ),
                          if (t[4] == true)
                            const Icon(Icons.check_circle_rounded, size: 16, color: vGreen),
                        ]),
                        const SizedBox(height: 8),
                        Text(t[1] as String,
                            style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800, color: _lzFg(plum))),
                        const SizedBox(height: 2),
                        Text(t[2] as String,
                            style: TextStyle(fontSize: 11.5, height: 1.3, color: _lzFg(muted))),
                      ]),
                ),
              ),
            ),
          );
        }

        return _lzFrame(ctx,
            icon: Icons.auto_awesome_motion_rounded,
            title: 'What you can do',
            subtitle:
                'Every screen and tool in Lazo, one line each. Tap to open. A check means you’ve used it.',
            children: <Widget>[
              LayoutBuilder(builder: (BuildContext lc, BoxConstraints box) {
                final double w = (box.maxWidth - 10) / 2;
                return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      for (final String sec in sections) ...<Widget>[
                        Padding(
                          padding: const EdgeInsets.fromLTRB(2, 10, 0, 8),
                          child: Text(sec.toUpperCase(),
                              style: TextStyle(
                                  fontSize: 10.5,
                                  letterSpacing: 2,
                                  fontWeight: FontWeight.w800,
                                  color: _lzFg(plum))),
                        ),
                        Wrap(spacing: 10, runSpacing: 10, children: <Widget>[
                          for (final List<dynamic> t in tiles)
                            if (t[0] == sec) tile(t, w),
                        ]),
                      ],
                    ]);
              }),
            ]);
      },
    );
  }
'''

rep("  // ---------------- v91: THIS WEEK, WITH JUNE ----------------\n",
    NEW_METHODS + "\n  // ---------------- v91: THIS WEEK, WITH JUNE ----------------\n")

# the card on Home, under the booking banner and above the widgets rail
rep("""              _linkBookingBanner(couple, inqs),
              if (!railSide) ...<Widget>[
                const SizedBox(height: 12),
                _crStrip(couple, plan, inqs, weddingDate, daysOut),
              ],""",
    """              _linkBookingBanner(couple, inqs),
              // v172: getting started, ticks itself off
              if (!needsSetup) _startCard(couple, inqs),
              if (!railSide) ...<Widget>[
                const SizedBox(height: 12),
                _crStrip(couple, plan, inqs, weddingDate, daysOut),
              ],""")

# the desk sheet: a 15th tile
rep("""      <dynamic>[
        'Account',
        Icons.person_rounded,
        () => setState(() => _view = _View.account),
        _View.account
      ],
    ];""",
    """      // v172: everything Lazo can do, one line each
      <dynamic>[
        'What you can do',
        Icons.auto_awesome_motion_rounded,
        () => _whatYouCanDoSheet(),
        null
      ],
      <dynamic>[
        'Account',
        Icons.person_rounded,
        () => setState(() => _view = _View.account),
        _View.account
      ],
    ];""")

# Account > More
rep("""        _accountGroup(label: 'MORE', rows: <Widget>[
          _accountRow(
            icon: Icons.move_down_rounded,""",
    """        _accountGroup(label: 'MORE', rows: <Widget>[
          _accountRow(
            icon: Icons.auto_awesome_motion_rounded,
            title: 'What you can do',
            value: 'Every screen and tool in Lazo, one line each',
            onTap: () => _whatYouCanDoSheet(),
          ),
          _accountRow(
            icon: Icons.move_down_rounded,""")

# signals the data cannot tell on its own
rep("""  Future<void> _juneSend() async {
    final String text = _juneC.text.trim();
    if (text.isEmpty || _juneBusy) {
      return;
    }
""",
    """  Future<void> _juneSend() async {
    final String text = _juneC.text.trim();
    if (text.isEmpty || _juneBusy) {
      return;
    }
    _markStart('june'); // v172
""")
rep("""          Future<void> invite() async {
            if (!emailOk || inviting) return;
""",
    """          Future<void> invite() async {
            if (!emailOk || inviting) return;
            _markStart('partner'); // v172
""")

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8")
print("wrote", DST.name, len(s.splitlines()), "lines")
