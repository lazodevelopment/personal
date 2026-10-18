"""Vendor v212: get booked on Lazo + What you can do (JC-LAZO-DISCOVER-1018-VENDOR).

    python app-patches\\patch_vendor_v212.py [base.txt]   # base defaults to Vendor_master_v211.txt
                                                          # writes Vendor_master_v212.txt
- a "Get booked on Lazo" card at the top of Today with seven steps that tick themselves
  off from the vendor doc and the leads stream: claimed page, starting price, six photos,
  packages or a price sheet, Whop connected, first reply, calendar feed on;
  Hide this / Done writes vendors.startHiddenAt
- a "What you can do" sheet: every tab, sheet and tool as a tile with one honest line,
  grouped Leads / Money / Studio / Profile, NEW badges for this month's features;
  opened from the card, the desk sheet and Account > June
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Vendor_master_v211.txt"
DST = HERE / "Vendor_master_v212.txt"
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
    "// Build ID: JC-LAZO-DISCOVER-1018-VENDOR (v212: GET BOOKED ON LAZO + WHAT YOU CAN DO - a seven-step card at the top "
    "of Today that ticks itself off (claimed, starting price, six photos, packages or a price sheet, Whop, first reply, "
    "calendar feed) with Hide / Done, and a What-you-can-do sheet of every tab and tool with one line each and NEW badges - "
    "from the card, the desk sheet and Account; base v211)\n"
) + s[first_build:]

NEW_METHODS = r'''
  // ---------------- v212: GET BOOKED ON LAZO + WHAT YOU CAN DO ----------------
  Map<String, dynamic> _wcdVd = <String, dynamic>{};
  String _wcdVendorId = '';
  static const Color _kStartGreen = Color(0xFF2E8B6B);

  bool _startWhopLive(Map<String, dynamic> vd) {
    final Map<String, dynamic> pay = Map<String, dynamic>.from(
        (vd['payments'] as Map?) ?? <String, dynamic>{});
    return (pay['processor'] ?? '') == 'whop' &&
        (pay['whopCompanyId'] ?? '').toString().isNotEmpty;
  }

  bool _startReplied(String vendorId) {
    final List<QueryDocumentSnapshot<Map<String, dynamic>>> docs =
        _liveQ['leads:$vendorId']?.latest?.docs ??
            <QueryDocumentSnapshot<Map<String, dynamic>>>[];
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in docs) {
      final Map<String, dynamic> m = d.data();
      if (m['respondedAt'] != null ||
          (m['vendorReply'] ?? '').toString().isNotEmpty ||
          (m['lastMessageRole'] ?? '') == 'vendor' ||
          (m['status'] ?? '') == 'booked') {
        return true;
      }
    }
    return false;
  }

  // [key, title, done, button, action]
  List<List<dynamic>> _startItemsV(String vendorId, Map<String, dynamic> vd) {
    final List<List<dynamic>> st = _strengthFromVendor(vd);
    bool check(String title) {
      for (final List<dynamic> c in st) {
        if (c[0] == title) return c[1] == true;
      }
      return false;
    }

    final bool claimed = (vd['claimedBy'] ?? '').toString().isNotEmpty ||
        vd['claimed'] == true;
    void editProfile() {
      if (vendorId.isNotEmpty) _openProfileEditor(vendorId, vd);
    }

    return <List<dynamic>>[
      <dynamic>[
        'claim',
        'Claim your page',
        claimed,
        'Claim',
        () {
          setState(() {
            _showInbox = false;
            _showAccount = false;
            _editingProfile = false;
            _dashMode = 'profile';
          });
        }
      ],
      <dynamic>['price', 'Set a starting price', check('Set a starting price'), 'Set', editProfile],
      <dynamic>['photos', 'Six or more photos', check('Six or more photos'), 'Add', editProfile],
      <dynamic>['packages', 'Packages or a price sheet', check('Packages or a price sheet'), 'Add', editProfile],
      <dynamic>[
        'whop',
        'Connect Whop so couples can pay you',
        _startWhopLive(vd),
        'Connect',
        () {
          if (vendorId.isNotEmpty) _connectWhopSheet(vendorId);
        }
      ],
      <dynamic>[
        'reply',
        'Reply to your first lead',
        _startReplied(vendorId),
        'Inbox',
        () {
          setState(() {
            _showAccount = false;
            _editingProfile = false;
            _showInbox = true;
          });
        }
      ],
      <dynamic>[
        'calendar',
        'Turn on the calendar feed',
        (vd['calendarToken'] ?? '').toString().isNotEmpty,
        'Open',
        () {
          if (vendorId.isNotEmpty) _calendarFeedSheet(vendorId);
        }
      ],
    ];
  }

  Widget _startCardV(String vendorId, Map<String, dynamic> vd) {
    _wcdVd = vd;
    _wcdVendorId = vendorId;
    if (vendorId.isEmpty || vd['startHiddenAt'] != null) {
      return const SizedBox.shrink();
    }
    final List<List<dynamic>> items = _startItemsV(vendorId, vd);
    final int done = items.where((List<dynamic> i) => i[2] == true).length;
    final bool all = done == items.length;
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: _glass(
        padding: const EdgeInsets.fromLTRB(18, 14, 18, 8),
        child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(children: <Widget>[
                Expanded(
                    child: Text(all ? 'You’re set up' : 'Get booked on Lazo',
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
                        'Couples can find you, book you and pay you. Nice.',
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
                            color: it[2] == true
                                ? _kStartGreen
                                : Colors.transparent,
                            border: Border.all(
                                color: it[2] == true ? _kStartGreen : gold,
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
                      onPressed: _h(() => _whatYouCanDoSheetV()),
                      child: Text('Everything Lazo can do →',
                          style: TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w700,
                              color: _lzFg(plum))),
                    ),
                    TextButton(
                      onPressed: _h(() => FirebaseFirestore.instance
                          .collection('vendors')
                          .doc(vendorId)
                          .set(<String, dynamic>{
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

  Future<void> _whatYouCanDoSheetV() async {
    final String vendorId = _wcdVendorId;
    final Map<String, dynamic> vd = _wcdVd;
    void home(String mode) {
      setState(() {
        _showInbox = false;
        _showAccount = false;
        _editingProfile = false;
        _dashMode = mode;
      });
    }

    void inbox() {
      setState(() {
        _showAccount = false;
        _editingProfile = false;
        _showInbox = true;
      });
    }

    // [section, title, line, icon, isNew, action]
    final List<List<dynamic>> tiles = <List<dynamic>>[
      <dynamic>['Leads', 'Inbox', 'Every conversation with a verified couple; first reply usually wins', Icons.inbox_rounded, false, inbox],
      <dynamic>['Leads', 'Pipeline', 'New, talking, booked, lost; drag a card, tag it, add a task', Icons.view_kanban_rounded, false, () { home('pipeline'); }],
      <dynamic>['Leads', 'Say hello first', 'Couples who fit your date, city and budget; one hello each', Icons.waving_hand_rounded, false, () { if (vendorId.isNotEmpty) _helloSheet(vendorId, vd); }],
      <dynamic>['Leads', 'Lead form for your website', 'One line of code, or a link; inquiries from anywhere land here', Icons.web_rounded, false, () { if (vendorId.isNotEmpty) _leadFormSheet(vendorId); }],
      <dynamic>['Leads', 'Consult scheduler', 'Couples book a call or a tour from your link; reminders go out alone', Icons.event_available_rounded, false, () { if (vendorId.isNotEmpty) _schedulerSheet(vendorId); }],
      <dynamic>['Leads', 'Lazo video calls', 'Call a couple from the thread; their camera stays off until you allow it', Icons.videocam_rounded, true, inbox],
      <dynamic>['Leads', 'Add a client', 'A couple from outside Lazo: they sign and pay without an account', Icons.person_add_alt_1_rounded, false, () { if (vendorId.isNotEmpty) _addClientSheet(vendorId); }],
      <dynamic>['Money', 'Invoices and payment plans', 'Itemized requests, retainer plus installments, each with a due date', Icons.receipt_long_rounded, false, () { home('money'); }],
      <dynamic>['Money', 'Get paid with Whop', 'Couples pay you directly; Lazo takes nothing and never holds it', Icons.payments_rounded, false, () { if (vendorId.isNotEmpty) _connectWhopSheet(vendorId); }],
      <dynamic>['Money', 'Booking link', 'One page with their proposal, agreement and every payment, no login', Icons.link_rounded, false, inbox],
      <dynamic>['Money', 'Money page', 'Collected, outstanding and overdue, with one-tap reminders', Icons.account_balance_wallet_rounded, false, () { home('money'); }],
      <dynamic>['Studio', 'Contract templates', 'Upload your contract once; June turns it into a reusable template', Icons.history_edu_rounded, false, () { home('studio'); }],
      <dynamic>['Studio', 'Questionnaires', 'Collect the details before the day, from the thread', Icons.fact_check_rounded, false, inbox],
      <dynamic>['Studio', 'Engagement location ideas', 'June finds spots near the couple: light, permits, crowds', Icons.place_rounded, true, inbox],
      <dynamic>['Studio', 'Galleries and sneak peeks', 'Deliver through Lazo; show the best on your public page', Icons.photo_library_rounded, false, () { home('studio'); }],
      <dynamic>['Studio', 'Meal counts', 'The couple’s meal choices and allergies, by table, for the caterer', Icons.restaurant_rounded, true, inbox],
      <dynamic>['Studio', 'Insurance on file', 'Upload your COI once; venues and planners get it and its renewals', Icons.verified_user_rounded, true, () { if (vendorId.isNotEmpty) _coiUploadSheet(vendorId, vd); }],
      <dynamic>['Studio', 'June for Studio', 'Pricing, replies, reviews, strategy; on your side of the table', Icons.auto_awesome_rounded, false, () { if (vendorId.isNotEmpty) _juneVendorSheet(vendorId); }],
      <dynamic>['Profile', 'Edit your profile', 'Photos, packages, price sheet, FAQs, video; what couples see first', Icons.edit_rounded, false, () { if (vendorId.isNotEmpty) _openProfileEditor(vendorId, vd); }],
      <dynamic>['Profile', 'Who I work with', 'Minimum, guest range, days and event types; every lead gets a Fit grade', Icons.tune_rounded, false, () { home('profile'); }],
      <dynamic>['Profile', 'Your team', 'Invite a manager; recommend your DJ, florist or planner in a thread', Icons.group_add_rounded, false, () { if (vendorId.isNotEmpty) _teamSheet(vendorId); }],
      <dynamic>['Profile', 'Your brand', 'Your colors and type on booking pages, galleries and every email', Icons.palette_rounded, false, () { if (vendorId.isNotEmpty) _brandSheet(vendorId); }],
      <dynamic>['Profile', 'Calendar feed', 'Booked weddings and blocked dates in Google or Apple Calendar', Icons.calendar_month_rounded, false, () { if (vendorId.isNotEmpty) _calendarFeedSheet(vendorId); }],
      <dynamic>['Profile', 'Verified badge and reviews', 'Download the badge; we ask every couple for a review three days after', Icons.workspace_premium_rounded, false, () { home('studio'); }],
    ];
    final List<String> sections = <String>['Leads', 'Money', 'Studio', 'Profile'];
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 680),
      builder: (BuildContext ctx) {
        Widget tile(List<dynamic> t, double w) {
          return SizedBox(
            width: w,
            child: _Press(
              onTap: () {
                Navigator.of(ctx).pop();
                (t[5] as void Function())();
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
                                  colors: <Color>[gold, Color(0xFFC9A45C)])),
                          child: Icon(t[3] as IconData, size: 17, color: plum),
                        ),
                        const Spacer(),
                        if (t[4] == true)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                            decoration: BoxDecoration(color: gold, borderRadius: BorderRadius.circular(999)),
                            child: const Text('NEW',
                                style: TextStyle(fontSize: 9, letterSpacing: 1.2, fontWeight: FontWeight.w800, color: plum)),
                          ),
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
          );
        }

        return _lzFrame(ctx,
            icon: Icons.auto_awesome_motion_rounded,
            title: 'What you can do',
            subtitle: 'Every tab and tool in Lazo, one line each. Tap to open.',
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

rep("  Widget _helloCard(String vendorId, Map<String, dynamic> vd) {\n",
    NEW_METHODS + "  Widget _helloCard(String vendorId, Map<String, dynamic> vd) {\n")

# Today: the card above Say hello
rep("""              mainKids = <Widget>[
                _fold('hello', 'Say hello', _foldSummary('hello', vendorId, vd),""",
    """              mainKids = <Widget>[
                _startCardV(vendorId, vd), // v212
                _fold('hello', 'Say hello', _foldSummary('hello', vendorId, vd),""")

# the desk sheet: a tile before Account
rep("""      <dynamic>[
        'Account',
        Icons.person_rounded,
        () => setState(() {
              _showInbox = false;
              _editingProfile = false;
              _showAccount = true;
              _acctSeeded = false;
            })
      ],""",
    """      // v212: everything Lazo can do, one line each
      <dynamic>[
        'What you can do',
        Icons.auto_awesome_motion_rounded,
        () => _whatYouCanDoSheetV()
      ],
      <dynamic>[
        'Account',
        Icons.person_rounded,
        () => setState(() {
              _showInbox = false;
              _editingProfile = false;
              _showAccount = true;
              _acctSeeded = false;
            })
      ],""")

# Account > June group, above Take the tour
rep("""                    _acctLive(Icons.tour_rounded, 'Take the tour',""",
    """                    _acctLive(Icons.auto_awesome_motion_rounded, 'What you can do', 'Every tab and tool in Lazo, one line each.', () => _whatYouCanDoSheetV()),
                    _acctLive(Icons.tour_rounded, 'Take the tour',""")

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8")
print("wrote", DST.name, len(s.splitlines()), "lines")
