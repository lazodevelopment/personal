r"""patch_couple_v156.py - Couple v155 -> v156 (JC-LAZO-COUPLE-1014-156)
What the vendor dashboard got (v192-v195), for couples:

1. JUNE KEEPS YOU POSTED - spoken and on a card at the top of the screen:
   a vendor replied (with the start of the message), a contract to sign, an
   invoice, a booking confirmed, a payment due in the next three days, an RSVP
   from the wedding website; once a day the countdown, the next milestone and
   today's weather (the wedding-day forecast once it is inside two weeks); a
   catch-up line after time away. Open jumps to the thread; a speaker mutes
   her (remembered); nothing repeats; quiet during the tour.
2. JUNE NARRATES THE TOUR - she greets them by name and talks them through
   each step; a speaker on the tour card mutes her.
3. WIDGETS - weather and a stack of widgets they pick and drag into order:
   on wide screens a column on the right, on phones at the end of the hub.
     weather   countdown (days to go + the next milestone)   budget
     rsvp      team (booked of needed, next to book)          payments due
     replies   (vendors waiting on you)   website (RSVPs online, link)
     dayof     (the first moments of the timeline)   shopping   notes (private)
   Saved on couples/{cid}.layout.rail; notes on couples/{cid}.deskNotes.

Needs JuneNative v8 (JuneNative.say / stopSpeaking / holdLine).

    python app-patches\patch_couple_v156.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / "Couple_master_v155.txt").read_text(encoding="utf-8")
OUT = HERE / "Couple_master_v156.txt"


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"anchor found {n}x (want {count}): {old[:90]!r}")
    s = s.replace(old, new)


# ---------------------------------------------------------------- 2. the tour, narrated
rep("""class _TourStep {
  const _TourStep(this.title, this.body, {this.key, this.before});
  final String title;
  final String body;
  final GlobalKey? key;
  final VoidCallback? before;
}""", """class _TourStep {
  const _TourStep(this.title, this.body, {this.key, this.before, this.say});
  final String title;
  final String body;
  final GlobalKey? key;
  final VoidCallback? before;
  final String? say; // v156: what June says on this step (else title + body)
}""")

rep("""  void _startTour(List<_TourStep> steps) {
    if (steps.isEmpty) return;
    setState(() {""", """  bool _tourVoice = true; // v156: June narrates the tour

  void _startTour(List<_TourStep> steps) {
    if (steps.isEmpty) return;
    JuneNative.holdLine = true;
    _tourVoice = true;
    setState(() {""")

rep("""    if (tc == null && st.key != null) {
      // target not on this screen - skip it
      if (mounted) _tourGo(1);
      return;
    }""", """    if (tc == null && st.key != null) {
      // target not on this screen - skip it
      if (mounted) _tourGo(1);
      return;
    }
    if (_tourVoice) JuneNative.say(st.say ?? '${st.title}. ${st.body}');""")

rep("""                      Text('${_tourIdx + 1} of ${_tourSteps.length}',""", """                      Tooltip(
                        message: _tourVoice ? 'Mute June' : 'Let June talk you through it',
                        child: InkWell(
                          customBorder: const CircleBorder(),
                          onTap: () {
                            setState(() => _tourVoice = !_tourVoice);
                            if (_tourVoice) {
                              final _TourStep cur = _tourSteps[_tourIdx];
                              JuneNative.say(cur.say ?? '${cur.title}. ${cur.body}');
                            } else {
                              JuneNative.stopSpeaking();
                            }
                          },
                          child: Padding(
                            padding: const EdgeInsets.all(4),
                            child: Icon(_tourVoice ? Icons.volume_up_rounded : Icons.volume_off_rounded, size: 17, color: _tourVoice ? plum : muted),
                          ),
                        ),
                      ),
                      const SizedBox(width: 4),
                      Text('${_tourIdx + 1} of ${_tourSteps.length}',""")

rep("""  Future<void> _endTour({required bool completed}) async {
    _tourChecked = true;""", """  Future<void> _endTour({required bool completed}) async {
    _tourChecked = true;
    JuneNative.holdLine = false;
    if (completed && _tourVoice) {
      JuneNative.say('That\\'s the tour. I\\'m right here whenever you need me. Ask me anything about the wedding, any time.');
    } else {
      JuneNative.stopSpeaking();
    }""")

rep("""  List<_TourStep> _coupleTourSteps({required bool needsSetup}) {
    return <_TourStep>[
      _TourStep('Welcome to your planning desk',
          'Everything for the wedding lives on this one page - your vendors, messages, money, website and day-of plan. Here is the thirty-second lay of the land.'),""", """  List<_TourStep> _coupleTourSteps({required bool needsSetup}) {
    final String tFirst = (FirebaseAuth.instance.currentUser?.displayName ?? '').trim().split(RegExp(r'\\s+')).first;
    return <_TourStep>[
      _TourStep('Welcome to your planning desk',
          'Everything for the wedding lives on this one page - your vendors, messages, money, website and day-of plan. Here is the thirty-second lay of the land.',
          say: 'Hi${tFirst.isEmpty ? '' : ' ' + tFirst}, I\\'m June, and congratulations! Welcome to Lazo. This is your planning desk. Your vendors, messages, money, website and day-of plan all live here. Let me show you around. It takes about thirty seconds.'),""")
rep("""            'Your names, the date, the city, a rough budget and the vendors you actually need. Everything on the page builds from that, so this comes first.',
            key: _kTourSetup),""", """            'Your names, the date, the city, a rough budget and the vendors you actually need. Everything on the page builds from that, so this comes first.',
            key: _kTourSetup,
            say: 'Start here. Give me one minute: your names, the date, the city, a rough budget and the vendors you actually need. Everything on this page builds from that.'),""")
rep("""          'Days to go, what June thinks you should do next, and four honest numbers: vendors booked, next up, budget, vendor replies.',
          key: _kTourHero),""", """          'Days to go, what June thinks you should do next, and four honest numbers: vendors booked, next up, budget, vendor replies.',
          key: _kTourHero,
          say: 'This is your countdown. Days to go, what I think you should do next, and four honest numbers: vendors booked, who\\'s next, your budget, and vendor replies.'),""")
rep("""          'Three concrete steps, in order, with a button each. She only lists what is actually waiting on you.',
          key: _kTourWeek),""", """          'Three concrete steps, in order, with a button each. She only lists what is actually waiting on you.',
          key: _kTourWeek,
          say: 'This week, I\\'ll give you three concrete steps, in order, each with a button. I only list what\\'s actually waiting on you.'),""")
rep("""          'The categories you said you need - not our fifteen, yours. Tap in to see when couples in your city usually book each one and to check a date.',
          key: _kTourTeam),""", """          'The categories you said you need - not our fifteen, yours. Tap in to see when couples in your city usually book each one and to check a date.',
          key: _kTourTeam,
          say: 'Your vendor team. These are the vendors you said you need. Tap in to see when couples in your city usually book each one, and to check a date.'),""")
rep("""          'One thread per vendor. Proposals, contracts and payments all happen inside the thread. This tile lights up when someone is waiting on you.',
          key: _kTourMessages),""", """          'One thread per vendor. Proposals, contracts and payments all happen inside the thread. This tile lights up when someone is waiting on you.',
          key: _kTourMessages,
          say: 'Messages. One thread per vendor, and proposals, contracts and payments all happen inside it. I\\'ll tell you the moment a vendor writes back.'),""")
rep("""          'Timeline, guests, seating, music - and one tap to share any of them with your vendors when the time comes. Website, budget and saved vendors sit right beside it.',
          key: _kTourDayOf),""", """          'Timeline, guests, seating, music - and one tap to share any of them with your vendors when the time comes. Website, budget and saved vendors sit right beside it.',
          key: _kTourDayOf,
          say: 'Day-of. Your timeline, guests, seating and music, and one tap to share any of them with your vendors. Your website, budget and saved vendors sit right beside it.'),""")
rep("""          key: _kTourJune),
      if (!_hasRail)""", """          key: _kTourJune,
          say: 'And this is me. Tap the microphone or type to me. Ask what\\'s realistic for your budget, or what to ask a photographer. I know your plan, your budget and your city, and I\\'ll read you a short brief every day.'),
      if (!_hasRail)""")

# ---------------------------------------------------------------- 3. the hub gets a widget column
rep("""        return LayoutBuilder(builder: (BuildContext lc, BoxConstraints cons) {
          final bool twoUp = cons.maxWidth >= 720;
          return ListView(
            cacheExtent: 4000,
            padding: const EdgeInsets.fromLTRB(18, 16, 18, 96),""", """        _cwWatch(couple);
        return LayoutBuilder(builder: (BuildContext lc, BoxConstraints cons) {
          final bool twoUp = cons.maxWidth >= 720;
          // v156: widgets on the right when there is room, else at the end
          final bool railSide = cons.maxWidth >= 1040;
          final Widget railStack = _crStack(couple, plan, inqs, weddingDate, daysOut);
          final Widget mainList = ListView(
            cacheExtent: 4000,
            padding: const EdgeInsets.fromLTRB(18, 16, 18, 96),""")
rep("""              // v131: the two big cards fold to a line.
              _fold('weather', 'Weather', _weatherFoldSummary(couple),
                  _weatherHubWidget(couple)),
              const SizedBox(height: 14),
              KeyedSubtree(""", """              // v156: the weather moved into the widgets
              KeyedSubtree(""")
rep("""              _deskTiles(couple, plan, inqs, weddingDate, daysOut, twoUp),
            ],
          );
        });""", """              _deskTiles(couple, plan, inqs, weddingDate, daysOut, twoUp),
              if (!railSide) ...<Widget>[
                const SizedBox(height: 18),
                railStack,
              ],
            ],
          );
          if (!railSide) return mainList;
          return Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Expanded(child: mainList),
            SizedBox(
              width: 340,
              child: ListView(
                cacheExtent: 3000,
                padding: const EdgeInsets.fromLTRB(0, 76, 18, 96),
                children: <Widget>[railStack],
              ),
            ),
          ]);
        });""")

# the notice card paints above the dashboard, under the tour
rep("""                    _tourOverlay(),""", """                    _cwNoticeOverlay(),
                    _tourOverlay(),""")

# ---------------------------------------------------------------- 1 + 3. the code
rep("""  List<_TourStep> _coupleTourSteps({required bool needsSetup}) {""", r"""  // ===================================================================
  // v156: JUNE KEEPS YOU POSTED (couples)
  // ===================================================================
  String _cwFor = '';
  final List<StreamSubscription<dynamic>> _cwSubs = <StreamSubscription<dynamic>>[];
  final Map<String, StreamSubscription<dynamic>> _cwInvSubs = <String, StreamSubscription<dynamic>>{};
  final Map<String, List<Map<String, dynamic>>> _cwInv = <String, List<Map<String, dynamic>>>{};
  final Map<String, Map<String, dynamic>> _cwInq = <String, Map<String, dynamic>>{};
  final Set<String> _cwArmed = <String>{};
  Set<String> _cwSaid = <String>{};
  bool _cwVoice = true;
  DateTime? _cwLastSeen;
  final List<Map<String, dynamic>> _cwQueue = <Map<String, dynamic>>[];
  Map<String, dynamic>? _cwNotice;
  Timer? _cwNoticeT;
  Timer? _cwSeenT;
  final List<String> _cwAway = <String>[];
  Timer? _cwAwayT;
  String _cwSlug = '';
  Map<String, dynamic> _cwCouple = <String, dynamic>{};

  bool _cwFresh(dynamic v, {int minutes = 15}) => v is Timestamp && DateTime.now().difference(v.toDate()).inMinutes.abs() <= minutes;
  bool _cwSince(dynamic v) {
    final DateTime? ls = _cwLastSeen;
    return ls != null && v is Timestamp && v.toDate().isAfter(ls) && DateTime.now().difference(v.toDate()).inDays < 14;
  }

  String _cwVendor(Map<String, dynamic> m) {
    final String n = (m['vendorName'] ?? '').toString().trim();
    return n.isEmpty ? 'Your vendor' : n;
  }

  String _cwDay(DateTime d) {
    const List<String> wd = <String>['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    final DateTime t = DateTime(DateTime.now().year, DateTime.now().month, DateTime.now().day);
    final int n = DateTime(d.year, d.month, d.day).difference(t).inDays;
    if (n == 0) return 'today';
    if (n == 1) return 'tomorrow';
    if (n > 1 && n < 7) return 'on ${wd[d.weekday - 1]}';
    return 'on ${_kMoLong[d.month - 1]} ${d.day}';
  }

  Future<void> _cwRemember(String key) async {
    if (key.isEmpty) return;
    _cwSaid.add(key);
    try {
      final SharedPreferences p = await SharedPreferences.getInstance();
      final List<String> l = _cwSaid.toList();
      await p.setStringList('juneSaidC_$_cwFor', l.length > 400 ? l.sublist(l.length - 400) : l);
    } catch (_) {}
  }

  Future<void> _cwMarkSeen() async {
    try {
      final SharedPreferences p = await SharedPreferences.getInstance();
      await p.setString('juneSeenC_$_cwFor', DateTime.now().toIso8601String());
    } catch (_) {}
  }

  void _cwSay(String key, String text, {String? threadId, IconData icon = Icons.auto_awesome_rounded, bool speak = true, _View? go}) {
    if (key.isNotEmpty) {
      if (_cwSaid.contains(key)) return;
      _cwRemember(key);
    }
    _cwQueue.add(<String, dynamic>{'text': text, 'thread': threadId, 'icon': icon, 'speak': speak, 'go': go});
    if (_cwNotice == null) _cwNext();
  }

  void _cwNext() {
    _cwNoticeT?.cancel();
    if (_cwQueue.isEmpty) {
      if (mounted) setState(() => _cwNotice = null);
      return;
    }
    final Map<String, dynamic> n = _cwQueue.removeAt(0);
    if (mounted) setState(() => _cwNotice = n);
    if (n['speak'] == true && _cwVoice && !JuneNative.holdLine && _tourIdx < 0) JuneNative.say(n['text'] as String);
    _cwNoticeT = Timer(Duration(milliseconds: 4500 + (n['text'] as String).split(' ').length * 330), _cwNext);
  }

  void _cwAwayAdd(String key, String phrase) {
    if (_cwSaid.contains(key)) return;
    _cwRemember(key);
    _cwAway.add(phrase);
    _cwAwayKick();
  }

  void _cwAwayKick() {
    _cwAwayT?.cancel();
    _cwAwayT = Timer(const Duration(seconds: 3), () {
      if (_cwAway.isEmpty) return;
      final List<String> a = List<String>.from(_cwAway);
      _cwAway.clear();
      final String list = a.length == 1 ? a.first : a.sublist(0, a.length - 1).join(', ') + ', and ' + a.last;
      _cwSay('', 'While you were away: $list.', icon: Icons.history_rounded);
    });
  }

  Future<void> _cwWatch(Map<String, dynamic> couple) async {
    _cwCouple = couple;
    if (_cid.isEmpty || couple.isEmpty || _cwFor == _cid) return;
    _cwFor = _cid;
    for (final StreamSubscription<dynamic> x in _cwSubs) {
      x.cancel();
    }
    _cwSubs.clear();
    try {
      final SharedPreferences p = await SharedPreferences.getInstance();
      _cwSaid = (p.getStringList('juneSaidC_$_cid') ?? <String>[]).toSet();
      _cwVoice = p.getBool('juneAnnounce') ?? true;
      _cwLastSeen = DateTime.tryParse(p.getString('juneSeenC_$_cid') ?? '');
    } catch (_) {}
    if (!mounted || _cwFor != _cid) return;
    _cwSeenT?.cancel();
    _cwSeenT = Timer.periodic(const Duration(minutes: 1), (_) => _cwMarkSeen());

    // ---- vendor threads
    _cwSubs.add(_inqStream().listen((QuerySnapshot<Map<String, dynamic>> snap) {
      final bool first = !_cwArmed.contains('inq');
      int awayReplies = 0;
      for (final QueryDocumentSnapshot<Map<String, dynamic>> d in snap.docs) {
        final Map<String, dynamic> m = d.data();
        if ((m['status'] ?? '') == 'flagged') continue;
        final Map<String, dynamic>? was = _cwInq[d.id];
        _cwInq[d.id] = <String, dynamic>{'status': m['status'], 'contract': m['contractStatus'], 'invoice': m['invoiceStatus'], 'lastAt': m['lastMessageAt'], 'vendor': _cwVendor(m), 'data': m};
        final String v = _cwVendor(m);
        // invoices for threads that have any
        if ((m['invoiceStatus'] ?? '').toString().isNotEmpty || (m['status'] ?? '') == 'booked') _cwWatchInvoices(d.id);
        if (first) {
          if ((m['lastMessageRole'] ?? '') == 'vendor' && _cwSince(m['lastMessageAt'])) {
            awayReplies++;
            _cwRemember('msg:${d.id}:${(m['lastMessageAt'] as Timestamp).seconds}');
          }
          if ((m['contractStatus'] ?? '') == 'sent' && _cwSince(m['lastMessageAt'])) _cwAwayAdd('contract:${d.id}', 'a contract to sign from $v');
          continue;
        }
        if (was == null) continue;
        if ((m['status'] ?? '') == 'booked' && (was['status'] ?? '') != 'booked') {
          _cwSay('booked:${d.id}', 'You booked $v. One more off the list!', threadId: d.id, icon: Icons.celebration_rounded);
        } else if ((m['contractStatus'] ?? '') == 'sent' && (was['contract'] ?? '') != 'sent') {
          _cwSay('contract:${d.id}', '$v sent you a contract to sign.', threadId: d.id, icon: Icons.draw_rounded);
        } else if (<String>['sent', 'due'].contains((m['invoiceStatus'] ?? '').toString()) && (was['invoice'] ?? '') != (m['invoiceStatus'] ?? '')) {
          _cwSay('invoice:${d.id}:${m['invoiceStatus']}', '$v sent you an invoice.', threadId: d.id, icon: Icons.receipt_long_rounded);
        } else if ((m['lastMessageRole'] ?? '') == 'vendor' && m['lastMessageAt'] is Timestamp &&
            (was['lastAt'] is! Timestamp || (m['lastMessageAt'] as Timestamp).compareTo(was['lastAt'] as Timestamp) > 0) &&
            _cwFresh(m['lastMessageAt'], minutes: 5) && d.id != _openThreadId) {
          final String prev = (m['lastMessagePreview'] ?? '').toString().trim();
          final String line = prev.isEmpty ? '' : ' "${prev.length > 90 ? prev.substring(0, 87).trimRight() + '...' : prev}"';
          _cwSay('msg:${d.id}:${(m['lastMessageAt'] as Timestamp).seconds}', '$v just replied.$line', threadId: d.id, icon: Icons.chat_bubble_rounded);
        }
      }
      if (first) {
        if (awayReplies > 0) {
          _cwAway.insert(0, awayReplies == 1 ? 'a vendor replied' : '$awayReplies vendors replied');
          _cwAwayKick();
        }
        _cwArmed.add('inq');
        _cwMarkSeen();
      }
    }, onError: (Object _) {}));

    // ---- RSVPs from the wedding website
    try {
      final QuerySnapshot<Map<String, dynamic>> sites = await FirebaseFirestore.instance.collection('weddingSites').where('coupleUid', isEqualTo: _cid).limit(1).get();
      if (sites.docs.isNotEmpty && mounted) {
        _cwSlug = sites.docs.first.id;
        _cwSubs.add(_liveQuery('rsvp:$_cwSlug', () => FirebaseFirestore.instance.collection('weddingSites').doc(_cwSlug).collection('rsvps')).listen((QuerySnapshot<Map<String, dynamic>> snap) {
          final bool first = !_cwArmed.contains('rsvp');
          int away = 0;
          for (final DocumentChange<Map<String, dynamic>> ch in snap.docChanges) {
            if (ch.type != DocumentChangeType.added) continue;
            final Map<String, dynamic> r = ch.doc.data() ?? <String, dynamic>{};
            final String who = (r['name'] ?? 'A guest').toString().trim();
            final bool yes = (r['attending'] ?? 'yes').toString() == 'yes';
            final int plus = r['plusOnes'] is num ? (r['plusOnes'] as num).toInt() : 0;
            if (first) {
              if (_cwSince(r['createdAt'])) {
                away++;
                _cwRemember('rsvp:${ch.doc.id}');
              }
              continue;
            }
            _cwSay('rsvp:${ch.doc.id}', yes ? '$who RSVP\'d yes${plus > 0 ? ', plus $plus' : ''}!' : '$who sent their regrets.', icon: yes ? Icons.how_to_reg_rounded : Icons.person_off_rounded, go: _View.guests);
          }
          if (first) {
            if (away > 0) {
              _cwAway.add(away == 1 ? 'one new RSVP' : '$away new RSVPs');
              _cwAwayKick();
            }
            _cwArmed.add('rsvp');
            if (mounted) setState(() {});
          }
        }, onError: (Object _) {}));
      }
    } catch (_) {}

    Future<void>.delayed(const Duration(seconds: 6), _cwDaily);
  }

  void _cwWatchInvoices(String inqId) {
    if (_cwInvSubs.containsKey(inqId)) return;
    _cwInvSubs[inqId] = FirebaseFirestore.instance.collection('inquiries').doc(inqId).collection('invoices').snapshots().listen((QuerySnapshot<Map<String, dynamic>> snap) {
      _cwInv[inqId] = snap.docs.map((QueryDocumentSnapshot<Map<String, dynamic>> d) => <String, dynamic>{...d.data(), '_id': d.id, '_inq': inqId}).toList();
      final String v = (_cwInq[inqId]?['vendor'] ?? 'your vendor').toString();
      final DateTime now = DateTime.now();
      for (final Map<String, dynamic> i in _cwInv[inqId]!) {
        final String st = (i['status'] ?? '').toString();
        if (st == 'paid' || st == 'void' || i['demo'] == true) continue;
        final dynamic dd = i['dueDate'];
        if (dd is! Timestamp) continue;
        final int days = DateTime(dd.toDate().year, dd.toDate().month, dd.toDate().day).difference(DateTime(now.year, now.month, now.day)).inDays;
        if (days >= 0 && days <= 3) {
          final String amt = i['total'] is num ? _money(i['total'] as num) : '';
          _cwSay('due:${i['_id']}', 'Your ${amt.isEmpty ? '' : '\$$amt '}payment to $v is due ${_cwDay(dd.toDate())}.', threadId: inqId, icon: Icons.payments_rounded);
        }
      }
      if (mounted) setState(() {});
    }, onError: (Object _) {});
  }

  // once a day: the countdown, the next milestone, the weather
  Future<void> _cwDaily() async {
    if (!mounted || _cwFor != _cid) return;
    final DateTime now = DateTime.now();
    final String key = 'day:${_ymd(now)}';
    if (_cwSaid.contains(key) || now.hour < 5) return;
    final Map<String, dynamic> c = _cwCouple;
    final DateTime? wed = c['weddingDate'] is Timestamp ? (c['weddingDate'] as Timestamp).toDate() : null;
    final String metro = (c['metroId'] ?? '').toString();
    final List<String> parts = <String>[];
    if (wed != null) {
      final int days = DateTime(wed.year, wed.month, wed.day).difference(DateTime(now.year, now.month, now.day)).inDays;
      if (days > 1) parts.add('$days days to go.');
      if (days == 1) parts.add('Tomorrow is the day!');
      if (days == 0) parts.add('Today is the day. Congratulations!');
      final List<dynamic>? ms = _crMilestone(days);
      if (ms != null && days > 0) parts.add(ms[0] == 0 ? 'Today: ${ms[1]}.' : 'Next up, in ${ms[0]} day${ms[0] == 1 ? '' : 's'}: ${ms[1]}.');
      if (metro.isNotEmpty && days >= 0 && days <= 15) {
        await _loadWeather(wed, metro);
        final Map<String, dynamic>? w = _wxCache['${_ymd(wed)}|$metro'];
        if (w != null && w['hi'] != null) parts.add('Your wedding-day forecast: ${_crSky(w)}, a high of ${w['hi']}${w['rainPct'] is num && (w['rainPct'] as num) >= 20 ? ', ${w['rainPct']} percent chance of rain' : ''}.');
      }
    }
    if (metro.isNotEmpty && (wed == null || DateTime(wed.year, wed.month, wed.day).difference(DateTime(now.year, now.month, now.day)).inDays > 15)) {
      await _loadWeather(now, metro);
      final Map<String, dynamic>? w = _wxCache['${_ymd(now)}|$metro'];
      if (w != null && w['hi'] != null) parts.add('Today it\'s ${_crSky(w)}, a high of ${w['hi']}.');
    }
    if (parts.isEmpty) return;
    _cwSay(key, parts.join(' '), icon: Icons.wb_sunny_rounded);
  }

  String _crSky(Map<String, dynamic> w) {
    final int code = (w['code'] is num) ? (w['code'] as num).toInt() : 0;
    return code == 0 ? 'clear skies' : code <= 2 ? 'sun and a few clouds' : code == 3 ? 'cloudy' : (code == 45 || code == 48) ? 'foggy' : code >= 95 ? 'stormy' : (code >= 71 && code <= 86 && code != 80 && code != 81 && code != 82) ? 'snowy' : code >= 51 ? 'rainy' : 'mixed skies';
  }

  // the usual planning milestones, by days before the wedding: [days until it, what]
  static const List<List<dynamic>> _kCrMilestones = <List<dynamic>>[
    <dynamic>[300, 'book your venue and photographer'],
    <dynamic>[240, 'send save-the-dates'],
    <dynamic>[180, 'order your attire'],
    <dynamic>[120, 'order invitations'],
    <dynamic>[56, 'mail your invitations'],
    <dynamic>[28, 'your RSVP deadline'],
    <dynamic>[14, 'give your caterer the final headcount'],
    <dynamic>[7, 'send the final timeline to your vendors'],
    <dynamic>[1, 'the rehearsal'],
  ];

  List<dynamic>? _crMilestone(int daysOut) {
    for (final List<dynamic> m in _kCrMilestones) {
      final int at = m[0] as int;
      if (daysOut >= at) return <dynamic>[daysOut - at, m[1]];
    }
    return null;
  }

  Widget _cwNoticeOverlay() {
    final Map<String, dynamic>? n = _cwNotice;
    final bool phone = MediaQuery.of(context).size.width < 700;
    return Positioned(
      top: MediaQuery.of(context).padding.top + (phone ? 10 : 18),
      left: 0,
      right: 0,
      child: IgnorePointer(
        ignoring: n == null,
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 320),
          transitionBuilder: (Widget c, Animation<double> a) => FadeTransition(opacity: a, child: SlideTransition(position: Tween<Offset>(begin: const Offset(0, -.4), end: Offset.zero).animate(a), child: c)),
          child: n == null
              ? const SizedBox.shrink(key: ValueKey<String>('none'))
              : Center(
                  key: ValueKey<String>(n['text'] as String),
                  child: Container(
                    constraints: BoxConstraints(maxWidth: phone ? MediaQuery.of(context).size.width - 20 : 560),
                    margin: const EdgeInsets.symmetric(horizontal: 10),
                    padding: const EdgeInsets.fromLTRB(12, 10, 6, 10),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(colors: <Color>[Color(0xFF3D1C3B), Color(0xFF5A2D57)]),
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(color: gold.withOpacity(.75)),
                      boxShadow: const <BoxShadow>[BoxShadow(color: Color(0x55000000), blurRadius: 24, offset: Offset(0, 10))],
                    ),
                    child: Material(
                      color: Colors.transparent,
                      child: Row(children: <Widget>[
                        Container(
                          width: 34,
                          height: 34,
                          decoration: BoxDecoration(shape: BoxShape.circle, color: gold.withOpacity(.16), border: Border.all(color: gold.withOpacity(.5))),
                          child: Icon(n['icon'] as IconData, size: 18, color: gold),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: <Widget>[
                            const Text('JUNE', style: TextStyle(color: gold, fontSize: 9.5, letterSpacing: 1.6, fontWeight: FontWeight.w800)),
                            const SizedBox(height: 2),
                            Text(n['text'] as String, maxLines: 4, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Color(0xFFFAF6F0), fontSize: 13.5, height: 1.35, fontWeight: FontWeight.w500)),
                          ]),
                        ),
                        if ((n['thread'] ?? '').toString().isNotEmpty || n['go'] != null)
                          TextButton(
                            onPressed: () {
                              final String id = (n['thread'] ?? '').toString();
                              final _View? go = n['go'] as _View?;
                              _cwNext();
                              if (id.isNotEmpty) {
                                setState(() => _view = _View.messages);
                                final Map<String, dynamic> m = (_cwInq[id]?['data'] as Map<String, dynamic>?) ?? <String, dynamic>{};
                                _openCoupleThread(id, m);
                              } else if (go != null) {
                                setState(() => _view = go);
                              }
                            },
                            child: const Text('Open', style: TextStyle(color: gold, fontWeight: FontWeight.w800, fontSize: 13)),
                          ),
                        Tooltip(
                          message: _cwVoice ? 'Mute June\'s updates' : 'Let June read updates aloud',
                          child: IconButton(
                            visualDensity: VisualDensity.compact,
                            icon: Icon(_cwVoice ? Icons.volume_up_rounded : Icons.volume_off_rounded, size: 18, color: _cwVoice ? gold : const Color(0xFFB9A9BC)),
                            onPressed: () async {
                              setState(() => _cwVoice = !_cwVoice);
                              if (!_cwVoice) JuneNative.stopSpeaking();
                              try {
                                final SharedPreferences p = await SharedPreferences.getInstance();
                                await p.setBool('juneAnnounce', _cwVoice);
                              } catch (_) {}
                            },
                          ),
                        ),
                        IconButton(
                          visualDensity: VisualDensity.compact,
                          tooltip: 'Dismiss',
                          icon: const Icon(Icons.close_rounded, size: 18, color: Color(0xFFB9A9BC)),
                          onPressed: () {
                            JuneNative.stopSpeaking();
                            _cwNext();
                          },
                        ),
                      ]),
                    ),
                  ),
                ),
        ),
      ),
    );
  }

  // ===================================================================
  // v156: WIDGETS (couples)
  // ===================================================================
  static const List<List<String>> _kCrAll = <List<String>>[
    <String>['weather', 'Weather', 'Your wedding-day sky, or today'],
    <String>['countdown', 'Countdown', 'Days to go and the next milestone'],
    <String>['budget', 'Budget', 'Planned and committed against your total'],
    <String>['rsvp', 'RSVPs', 'Yes, no and still waiting'],
    <String>['team', 'Vendor team', 'Booked so far and who to book next'],
    <String>['payments', 'Payments due', 'What you owe your vendors, and when'],
    <String>['replies', 'Waiting on you', 'Vendors who wrote last'],
    <String>['website', 'Your website', 'RSVPs online and your link'],
    <String>['dayof', 'Your day', 'The first moments of your timeline'],
    <String>['shopping', 'Shopping list', 'What is left to buy'],
    <String>['notes', 'Notes', 'A private notepad for the two of you'],
  ];
  static const List<String> _kCrDefault = <String>['countdown', 'weather', 'rsvp', 'budget', 'team', 'payments', 'replies'];
  List<String> _cr = List<String>.from(_kCrDefault);
  String _crSynced = '';
  final TextEditingController _crNoteC = TextEditingController();
  bool _crNoteLoaded = false;
  Timer? _crNoteT;

  bool _crKnown(String id) => _kCrAll.any((List<String> r) => r[0] == id);
  List<String> _crTitle(String id) => _kCrAll.firstWhere((List<String> r) => r[0] == id, orElse: () => <String>[id, id, '']);

  void _crSync(Map<String, dynamic> d) {
    final Map<String, dynamic> lay = d['layout'] is Map ? Map<String, dynamic>.from(d['layout'] as Map) : <String, dynamic>{};
    if (lay['rail'] is! List) return;
    final List<String> l = (lay['rail'] as List).map((dynamic e) => e.toString()).where(_crKnown).toList();
    final String sig = l.join(',');
    if (sig == _crSynced) return;
    _crSynced = sig;
    _cr = l;
  }

  Future<void> _crSave() async {
    _crSynced = _cr.join(',');
    try {
      await _coupleRef.set(<String, dynamic>{'layout': <String, dynamic>{'rail': _cr}}, SetOptions(merge: true));
    } catch (e) {
      debugPrint('LAZO rail: ' + e.toString());
    }
  }

  Widget _crStack(Map<String, dynamic> couple, Map<String, Map<String, dynamic>> plan, List<QueryDocumentSnapshot<Map<String, dynamic>>> inqs, DateTime? wed, int? daysOut) {
    _crSync(couple);
    final List<String> ids = _cr.where(_crKnown).toList();
    Widget body(String id) {
      switch (id) {
        case 'weather':
          return Padding(padding: const EdgeInsets.only(bottom: 14), child: _fold('weather', 'Weather', _weatherFoldSummary(couple), _weatherHubWidget(couple)));
        case 'countdown':
          return _crCard('Countdown', Icons.hourglass_top_rounded, _crCountdown(wed, daysOut));
        case 'budget':
          return _crCard('Budget', Icons.account_balance_wallet_rounded, _crBudget(couple, plan));
        case 'rsvp':
          return _crCard('RSVPs', Icons.how_to_reg_rounded, _crRsvp(couple));
        case 'team':
          return _crCard('Vendor team', Icons.groups_rounded, _crTeam(plan));
        case 'payments':
          return _crCard('Payments due', Icons.payments_rounded, _crPayments());
        case 'replies':
          return _crCard('Waiting on you', Icons.mark_chat_unread_rounded, _crReplies(inqs));
        case 'website':
          return _crCard('Your website', Icons.language_rounded, _crWebsite());
        case 'dayof':
          return _crCard('Your day', Icons.schedule_rounded, _crDayOf());
        case 'shopping':
          return _crCard('Shopping list', Icons.shopping_bag_rounded, _crShopping());
        case 'notes':
          return _crCard('Notes', Icons.sticky_note_2_rounded, _crNotes(couple), sub: 'Just for the two of you');
      }
      return const SizedBox.shrink();
    }

    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
      ReorderableListView(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        buildDefaultDragHandles: false,
        padding: EdgeInsets.zero,
        proxyDecorator: (Widget child, int i, Animation<double> a) => Material(color: Colors.transparent, elevation: 10, shadowColor: const Color(0x55000000), borderRadius: BorderRadius.circular(20), child: child),
        onReorder: (int from, int to) {
          setState(() {
            if (to > from) to -= 1;
            final String x = ids.removeAt(from);
            ids.insert(to, x);
            _cr = List<String>.from(ids);
          });
          HapticFeedback.selectionClick();
          _crSave();
        },
        children: <Widget>[
          for (int i = 0; i < ids.length; i++)
            KeyedSubtree(
              key: ValueKey<String>('crail-${ids[i]}'),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
                Center(
                  child: ReorderableDragStartListener(
                    index: i,
                    child: MouseRegion(
                      cursor: SystemMouseCursors.grab,
                      child: Tooltip(
                        message: 'Drag to move',
                        child: Container(width: 54, height: 14, alignment: Alignment.center, child: Container(width: 30, height: 4, decoration: BoxDecoration(color: gold.withOpacity(.55), borderRadius: BorderRadius.circular(3)))),
                      ),
                    ),
                  ),
                ),
                ReorderableDelayedDragStartListener(index: i, child: body(ids[i])),
              ]),
            ),
        ],
      ),
      Center(
        child: TextButton.icon(
          onPressed: () => _crSheet(),
          icon: const Icon(Icons.dashboard_customize_rounded, size: 16, color: gold),
          label: Text(ids.isEmpty ? 'Add widgets' : 'Customize widgets', style: const TextStyle(color: gold, fontWeight: FontWeight.w700, fontSize: 12.5)),
        ),
      ),
    ]);
  }

  Widget _crCard(String title, IconData icon, Widget content, {String? sub}) => Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: _glass(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
          radius: 20,
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
            Row(children: <Widget>[
              Icon(icon, size: 16, color: gold),
              const SizedBox(width: 8),
              Expanded(child: Text(title, style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w800, fontSize: 13.5))),
              if (sub != null) Text(sub, style: TextStyle(color: _lzFg(muted), fontSize: 10.5)),
            ]),
            const SizedBox(height: 12),
            content,
          ]),
        ),
      );

  void _crSheet() {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (BuildContext c) => StatefulBuilder(builder: (BuildContext c2, StateSetter setS) {
        final List<String> on = _cr.where(_crKnown).toList();
        final List<String> off = _kCrAll.map((List<String> r) => r[0]).where((String id) => !on.contains(id)).toList();
        Widget row(String id, bool enabled, {int? index}) {
          final List<String> r = _crTitle(id);
          return ListTile(
            key: ValueKey<String>('crsheet-$id'),
            contentPadding: const EdgeInsets.symmetric(horizontal: 4),
            leading: index == null ? Icon(Icons.add_circle_outline_rounded, color: _lzFg(muted)) : ReorderableDragStartListener(index: index, child: Icon(Icons.drag_indicator_rounded, color: _lzFg(muted))),
            title: Text(r[1], style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w700, fontSize: 14)),
            subtitle: Text(r[2], style: TextStyle(color: _lzFg(muted), fontSize: 12)),
            trailing: Switch(
              value: enabled,
              activeColor: Colors.white,
              activeTrackColor: vGreen,
              onChanged: (bool v) {
                setS(() {});
                setState(() => _cr = v ? <String>[...on, id] : on.where((String x) => x != id).toList());
                _crSave();
              },
            ),
          );
        }

        return SafeArea(
          child: ConstrainedBox(
            constraints: BoxConstraints(maxHeight: MediaQuery.of(c2).size.height * .82),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(18, 14, 18, 8),
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
                Row(children: <Widget>[
                  Expanded(child: Text('Your widgets', style: TextStyle(color: _lzFg(plum), fontSize: 18, fontWeight: FontWeight.w800))),
                  TextButton(onPressed: () => Navigator.of(c2).pop(), child: Text('Done', style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w800))),
                ]),
                Text('Switch widgets on or off, and drag to put them in the order you like.', style: TextStyle(color: _lzFg(muted), fontSize: 12.5)),
                const SizedBox(height: 8),
                Flexible(
                  child: ListView(shrinkWrap: true, children: <Widget>[
                    ReorderableListView(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      buildDefaultDragHandles: false,
                      onReorder: (int from, int to) {
                        if (to > from) to -= 1;
                        final String x = on.removeAt(from);
                        on.insert(to, x);
                        setS(() {});
                        setState(() => _cr = List<String>.from(on));
                        _crSave();
                      },
                      children: <Widget>[for (int i = 0; i < on.length; i++) row(on[i], true, index: i)],
                    ),
                    if (off.isNotEmpty) ...<Widget>[
                      Padding(padding: const EdgeInsets.only(top: 12, bottom: 4), child: Text('MORE WIDGETS', style: TextStyle(color: _lzFg(muted), fontSize: 10.5, letterSpacing: 1.4, fontWeight: FontWeight.w800))),
                      for (final String id in off) row(id, false),
                    ],
                  ]),
                ),
              ]),
            ),
          ),
        );
      }),
    );
  }

  Widget _crStat(String big, String label) => Expanded(
        child: Container(
          padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
          decoration: BoxDecoration(color: _lzBg(plum.withOpacity(.04)), borderRadius: BorderRadius.circular(14), border: Border.all(color: _lzLine(goldLine))),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Text(big, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: _lzFg(plum), fontSize: 21, fontWeight: FontWeight.w800, height: 1)),
            const SizedBox(height: 4),
            Text(label, maxLines: 2, style: TextStyle(color: _lzFg(muted), fontSize: 11, height: 1.25)),
          ]),
        ),
      );

  Widget _crBar(String label, String right, double v, {Color? color}) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
          Row(children: <Widget>[
            Expanded(child: Text(label, style: TextStyle(color: _lzFg(ink), fontSize: 12.5, fontWeight: FontWeight.w600))),
            Text(right, style: TextStyle(color: _lzFg(plum), fontSize: 12.5, fontWeight: FontWeight.w800)),
          ]),
          const SizedBox(height: 5),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(value: v.isNaN ? 0 : v.clamp(0.0, 1.0), minHeight: 9, backgroundColor: _lzBg(plum.withOpacity(.07)), valueColor: AlwaysStoppedAnimation<Color>(color ?? gold)),
          ),
        ]),
      );

  Widget _crRow({required String title, required String sub, String right = '', Color? rightColor, VoidCallback? onTap}) => InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 2),
          child: Row(children: <Widget>[
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: _lzFg(ink), fontSize: 13, fontWeight: FontWeight.w700)),
                if (sub.isNotEmpty) Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: _lzFg(muted), fontSize: 11.5)),
              ]),
            ),
            if (right.isNotEmpty) Text(right, style: TextStyle(color: rightColor ?? _lzFg(plum), fontSize: 12.5, fontWeight: FontWeight.w800)),
            if (onTap != null) Icon(Icons.chevron_right_rounded, size: 18, color: _lzFg(muted)),
          ]),
        ),
      );

  Widget _crEmpty(String t) => Text(t, style: TextStyle(color: _lzFg(muted), fontSize: 12.5, height: 1.4));

  // ---- Countdown
  Widget _crCountdown(DateTime? wed, int? daysOut) {
    if (wed == null || daysOut == null) return _crEmpty('Set your wedding date and the countdown starts here.');
    if (daysOut < 0) return _crEmpty('Married ${-daysOut} day${daysOut == -1 ? '' : 's'}. Congratulations!');
    final List<dynamic>? ms = _crMilestone(daysOut);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
      Row(crossAxisAlignment: CrossAxisAlignment.end, children: <Widget>[
        Text('$daysOut', style: TextStyle(color: _lzFg(plum), fontSize: 40, fontWeight: FontWeight.w800, height: .95)),
        const SizedBox(width: 8),
        Padding(padding: const EdgeInsets.only(bottom: 4), child: Text(daysOut == 1 ? 'day to go' : 'days to go', style: TextStyle(color: _lzFg(muted), fontSize: 13))),
      ]),
      const SizedBox(height: 4),
      Text('${_kMoLong[wed.month - 1]} ${wed.day}, ${wed.year} - about ${(daysOut / 7).floor()} weeks', style: TextStyle(color: _lzFg(muted), fontSize: 12)),
      if (ms != null) ...<Widget>[
        const SizedBox(height: 10),
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          const Icon(Icons.flag_rounded, size: 15, color: gold),
          const SizedBox(width: 6),
          Expanded(child: Text(ms[0] == 0 ? 'Today: ${ms[1]}' : 'In ${ms[0]} day${ms[0] == 1 ? '' : 's'}: ${ms[1]}', style: TextStyle(color: _lzFg(ink), fontSize: 12.5, fontWeight: FontWeight.w600))),
        ]),
      ],
    ]);
  }

  // ---- Budget
  Widget _crBudget(Map<String, dynamic> couple, Map<String, Map<String, dynamic>> plan) {
    final num total = couple['budgetTotal'] is num ? couple['budgetTotal'] as num : 0;
    num planned = 0, committed = 0;
    for (final Map<String, dynamic> p in plan.values) {
      if (p['budgetPlanned'] is num) planned += p['budgetPlanned'] as num;
      if (p['budgetActual'] is num) committed += p['budgetActual'] as num;
    }
    num paid = 0;
    for (final List<Map<String, dynamic>> l in _cwInv.values) {
      for (final Map<String, dynamic> i in l) {
        if ((i['status'] ?? '') == 'paid' && i['total'] is num && i['demo'] != true) paid += i['total'] as num;
      }
    }
    if (total <= 0 && planned <= 0) return _crEmpty('Set a total budget and give each vendor a number, and this shows where you stand.');
    final double base = (total > 0 ? total : planned).toDouble();
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
      if (total > 0) Text('\$${_money(total)} total', style: TextStyle(color: _lzFg(plum), fontSize: 16, fontWeight: FontWeight.w800)),
      const SizedBox(height: 10),
      _crBar('Planned', '\$${_money(planned)}', planned / base, color: planned > base ? const Color(0xFFB4534B) : gold),
      _crBar('Committed to vendors', '\$${_money(committed)}', committed / base, color: committed > base ? const Color(0xFFB4534B) : const Color(0xFF8DA399)),
      _crBar('Paid so far', '\$${_money(paid)}', paid / base, color: vGreen),
      if (total > 0) Text(committed <= total ? '\$${_money(total - committed)} left to commit' : '\$${_money(committed - total)} over your total', style: TextStyle(color: committed <= total ? _lzFg(muted) : const Color(0xFFB4534B), fontSize: 12)),
    ]);
  }

  // ---- RSVPs
  Widget _crRsvp(Map<String, dynamic> couple) {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _liveQuery('guests:$_cid', () => _guestsRef),
      initialData: _liveQ['guests:$_cid']?.latest,
      builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
        int yes = 0, no = 0, wait = 0;
        for (final QueryDocumentSnapshot<Map<String, dynamic>> d in s.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[]) {
          final Map<String, dynamic> g = d.data();
          final int n = g['count'] is num ? math.max(1, (g['count'] as num).toInt()) : 1;
          final String r = (g['rsvp'] ?? '').toString().toLowerCase();
          if (g['rsvp'] == true || r.startsWith('yes') || r.startsWith('attend') || r.startsWith('accept')) {
            yes += n;
          } else if (g['rsvp'] == false || r.startsWith('no') || r.startsWith('declin') || r.startsWith('regret')) {
            no += n;
          } else {
            wait += n;
          }
        }
        final int all = yes + no + wait;
        final int est = couple['guestEstimate'] is num ? (couple['guestEstimate'] as num).toInt() : 0;
        if (all == 0) return _crEmpty('Add your guest list and RSVPs count up here as they come in.');
        return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
          Row(children: <Widget>[
            _crStat('$yes', 'Coming'),
            const SizedBox(width: 8),
            _crStat('$wait', 'Waiting'),
            const SizedBox(width: 8),
            _crStat('$no', 'Can\'t make it'),
          ]),
          const SizedBox(height: 10),
          _crBar('Answered', '${yes + no} of $all', (yes + no) / all, color: vGreen),
          if (est > 0) Text('You planned for about $est guests.', style: TextStyle(color: _lzFg(muted), fontSize: 12)),
          Align(alignment: Alignment.centerRight, child: TextButton(onPressed: () => setState(() => _view = _View.guests), child: const Text('Open guests', style: TextStyle(color: gold, fontWeight: FontWeight.w800, fontSize: 12)))),
        ]);
      },
    );
  }

  // ---- Vendor team
  Widget _crTeam(Map<String, Map<String, dynamic>> plan) {
    final List<MapEntry<String, Map<String, dynamic>>> need = plan.entries.where((MapEntry<String, Map<String, dynamic>> e) => (e.value['status'] ?? 'needed') != 'skipped').toList();
    if (need.isEmpty) return _crEmpty('Tell June which vendors you need and your team fills in here.');
    final int booked = need.where((MapEntry<String, Map<String, dynamic>> e) => e.value['status'] == 'booked').length;
    const List<String> order = <String>['wedding-venues', 'wedding-planners', 'wedding-photographers', 'wedding-caterers', 'wedding-videographers', 'wedding-djs', 'wedding-bands', 'wedding-florists', 'wedding-officiants', 'hair-and-makeup', 'wedding-cakes', 'wedding-invitations', 'wedding-rentals', 'wedding-transportation', 'day-of-coordination'];
    final List<String> open = need.where((MapEntry<String, Map<String, dynamic>> e) => e.value['status'] != 'booked').map((MapEntry<String, Map<String, dynamic>> e) => e.key).toList()
      ..sort((String a, String b) => (order.indexOf(a) + 100) % 100 - (order.indexOf(b) + 100) % 100);
    String label(String slug) => slug.replaceFirst('wedding-', '').replaceAll('-', ' ').replaceAll('djs', 'DJ').replaceAllMapped(RegExp(r'^\w'), (Match m) => m[0]!.toUpperCase());
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
      _crBar('Booked', '$booked of ${need.length}', booked / need.length, color: vGreen),
      if (open.isNotEmpty) ...<Widget>[
        Text('NEXT TO BOOK', style: TextStyle(color: _lzFg(muted), fontSize: 9.5, letterSpacing: 1.3, fontWeight: FontWeight.w800)),
        const SizedBox(height: 6),
        Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
          for (final String sl in open.take(4))
            Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5), decoration: BoxDecoration(color: _lzBg(plum.withOpacity(.05)), borderRadius: BorderRadius.circular(99), border: Border.all(color: _lzLine(goldLine))), child: Text(label(sl), style: TextStyle(color: _lzFg(plum), fontSize: 11.5, fontWeight: FontWeight.w700))),
        ]),
      ] else
        _crEmpty('Every vendor you need is booked. Lovely.'),
      Align(alignment: Alignment.centerRight, child: TextButton(onPressed: () => setState(() => _view = _View.vendors), child: const Text('Open team', style: TextStyle(color: gold, fontWeight: FontWeight.w800, fontSize: 12)))),
    ]);
  }

  // ---- Payments due
  Widget _crPayments() {
    final DateTime now = DateTime.now();
    final List<Map<String, dynamic>> due = <Map<String, dynamic>>[
      for (final List<Map<String, dynamic>> l in _cwInv.values)
        for (final Map<String, dynamic> i in l)
          if ((i['status'] ?? '') != 'paid' && (i['status'] ?? '') != 'void' && i['demo'] != true && i['dueDate'] is Timestamp) i
    ]..sort((Map<String, dynamic> a, Map<String, dynamic> b) => (a['dueDate'] as Timestamp).compareTo(b['dueDate'] as Timestamp));
    if (due.isEmpty) return _crEmpty('Nothing to pay right now. Invoices from your vendors show here with their due dates.');
    return Column(children: <Widget>[
      for (final Map<String, dynamic> i in due.take(5))
        Builder(builder: (BuildContext _) {
          final DateTime dd = (i['dueDate'] as Timestamp).toDate();
          final int days = DateTime(dd.year, dd.month, dd.day).difference(DateTime(now.year, now.month, now.day)).inDays;
          final String inq = (i['_inq'] ?? '').toString();
          return _crRow(
            title: (_cwInq[inq]?['vendor'] ?? 'Your vendor').toString(),
            sub: (i['title'] ?? 'Invoice').toString(),
            right: '${i['total'] is num ? '\$${_money(i['total'] as num)}' : ''}  ${days < 0 ? '${-days}d late' : days == 0 ? 'today' : 'in ${days}d'}',
            rightColor: days < 0 ? const Color(0xFFB4534B) : (days <= 7 ? gold : _lzFg(plum)),
            onTap: () {
              setState(() => _view = _View.messages);
              _openCoupleThread(inq, (_cwInq[inq]?['data'] as Map<String, dynamic>?) ?? <String, dynamic>{});
            },
          );
        }),
    ]);
  }

  // ---- Waiting on you
  Widget _crReplies(List<QueryDocumentSnapshot<Map<String, dynamic>>> inqs) {
    final List<QueryDocumentSnapshot<Map<String, dynamic>>> w = inqs.where((QueryDocumentSnapshot<Map<String, dynamic>> d) {
      final Map<String, dynamic> m = d.data();
      if ((m['lastMessageRole'] ?? '') != 'vendor' || (m['status'] ?? '') == 'lost' || m['blockedByCouple'] == true) return false;
      return m['lastMessageAt'] is Timestamp;
    }).toList()
      ..sort((QueryDocumentSnapshot<Map<String, dynamic>> a, QueryDocumentSnapshot<Map<String, dynamic>> b) => (a.data()['lastMessageAt'] as Timestamp).compareTo(b.data()['lastMessageAt'] as Timestamp));
    if (w.isEmpty) return _crEmpty('Nobody is waiting on you. Lovely.');
    final DateTime now = DateTime.now();
    return Column(children: <Widget>[
      for (final QueryDocumentSnapshot<Map<String, dynamic>> d in w.take(5))
        Builder(builder: (BuildContext _) {
          final Map<String, dynamic> m = d.data();
          final Duration age = now.difference((m['lastMessageAt'] as Timestamp).toDate());
          final String ago = age.inHours < 1 ? 'now' : age.inHours < 24 ? '${age.inHours}h' : '${age.inDays}d';
          return _crRow(
            title: _cwVendor(m),
            sub: (m['lastMessagePreview'] ?? 'Tap to reply').toString(),
            right: ago,
            rightColor: age.inDays >= 2 ? const Color(0xFFB4534B) : gold,
            onTap: () {
              setState(() => _view = _View.messages);
              _openCoupleThread(d.id, m);
            },
          );
        }),
    ]);
  }

  // ---- Your website
  Widget _crWebsite() {
    if (_cwSlug.isEmpty) {
      return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
        _crEmpty('A free website with RSVPs, your story, travel and your registry. June can write it with you.'),
        Align(alignment: Alignment.centerRight, child: TextButton(onPressed: () => setState(() => _view = _View.website), child: const Text('Build my website', style: TextStyle(color: gold, fontWeight: FontWeight.w800, fontSize: 12)))),
      ]);
    }
    final String url = 'https://meetlazo.com/w/$_cwSlug/';
    final int n = _liveQ['rsvp:$_cwSlug']?.latest?.docs.length ?? 0;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
      Row(children: <Widget>[
        _crStat('$n', 'RSVPs through your site'),
      ]),
      const SizedBox(height: 8),
      Text(url.replaceFirst('https://', ''), style: TextStyle(color: _lzFg(ink), fontSize: 12)),
      Row(children: <Widget>[
        TextButton.icon(
          onPressed: () async {
            await Clipboard.setData(ClipboardData(text: url));
            _toastC('Link copied.');
          },
          icon: const Icon(Icons.link_rounded, size: 15, color: gold),
          label: const Text('Copy link', style: TextStyle(color: gold, fontWeight: FontWeight.w800, fontSize: 12)),
        ),
        TextButton.icon(
          onPressed: () => setState(() => _view = _View.website),
          icon: const Icon(Icons.edit_rounded, size: 15, color: gold),
          label: const Text('Edit', style: TextStyle(color: gold, fontWeight: FontWeight.w800, fontSize: 12)),
        ),
      ]),
    ]);
  }

  // ---- Your day
  Widget _crDayOf() {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _liveQuery('dayof:$_cid', () => _dayofRef.orderBy('time')),
      initialData: _liveQ['dayof:$_cid']?.latest,
      builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
        final List<Map<String, dynamic>> ms = (s.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[]).map((QueryDocumentSnapshot<Map<String, dynamic>> d) => d.data()).where((Map<String, dynamic> m) => (m['label'] ?? '').toString().isNotEmpty).toList();
        if (ms.isEmpty) return _crEmpty('Your day-of timeline shows here once you build it. June can draft one around your ceremony time.');
        return Column(children: <Widget>[
          for (final Map<String, dynamic> m in ms.take(5))
            _crRow(title: (m['label'] ?? '').toString(), sub: (m['note'] ?? '').toString(), right: (m['time'] ?? '').toString()),
          Align(alignment: Alignment.centerRight, child: TextButton(onPressed: () => setState(() => _view = _View.dayof), child: Text(ms.length > 5 ? 'All ${ms.length} moments' : 'Open day-of', style: const TextStyle(color: gold, fontWeight: FontWeight.w800, fontSize: 12)))),
        ]);
      },
    );
  }

  // ---- Shopping list
  Widget _crShopping() {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _liveQuery('shop:$_cid', () => _shopRef.orderBy('order')),
      initialData: _liveQ['shop:$_cid']?.latest,
      builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
        final List<Map<String, dynamic>> all = (s.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[]).map((QueryDocumentSnapshot<Map<String, dynamic>> d) => d.data()).toList();
        final List<Map<String, dynamic>> left = all.where((Map<String, dynamic> m) => m['bought'] != true).toList();
        if (all.isEmpty) return _crEmpty('Favors, guest book, cake knife... add what you need to buy and track it here.');
        num est = 0;
        for (final Map<String, dynamic> m in left) {
          if (m['est'] is num) est += m['est'] as num;
        }
        return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
          _crBar('Bought', '${all.length - left.length} of ${all.length}', (all.length - left.length) / all.length, color: vGreen),
          for (final Map<String, dynamic> m in left.take(4)) _crRow(title: (m['name'] ?? '').toString(), sub: '', right: m['est'] is num && (m['est'] as num) > 0 ? '\$${_money(m['est'] as num)}' : ''),
          if (est > 0) Text('About \$${_money(est)} still to spend', style: TextStyle(color: _lzFg(muted), fontSize: 12)),
          Align(alignment: Alignment.centerRight, child: TextButton(onPressed: () => setState(() => _view = _View.shopping), child: const Text('Open list', style: TextStyle(color: gold, fontWeight: FontWeight.w800, fontSize: 12)))),
        ]);
      },
    );
  }

  // ---- Notes (the couple doc is private to the two of them)
  Widget _crNotes(Map<String, dynamic> couple) {
    if (!_crNoteLoaded && couple.isNotEmpty) {
      _crNoteLoaded = true;
      _crNoteC.text = (couple['deskNotes'] ?? '').toString();
    }
    return TextField(
      controller: _crNoteC,
      minLines: 4,
      maxLines: 10,
      style: TextStyle(color: _lzFg(ink), fontSize: 13.5, height: 1.4),
      decoration: InputDecoration(
        hintText: 'Song ideas, questions for the venue, who owes us a call...',
        hintStyle: TextStyle(color: _lzFg(muted), fontSize: 13),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: _lzLine(goldLine))),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: _lzLine(goldLine))),
        isDense: true,
      ),
      onChanged: (String v) {
        _crNoteT?.cancel();
        _crNoteT = Timer(const Duration(milliseconds: 900), () async {
          try {
            await _coupleRef.set(<String, dynamic>{'deskNotes': v}, SetOptions(merge: true));
          } catch (_) {}
        });
      },
    );
  }

  List<_TourStep> _coupleTourSteps({required bool needsSetup}) {""")

rep("""  void dispose() {
    _chimeSub?.cancel();
    _setTabBadge(0);
    _inqSub?.cancel();""", """  void dispose() {
    _chimeSub?.cancel();
    for (final StreamSubscription<dynamic> x in _cwSubs) {
      x.cancel();
    }
    for (final StreamSubscription<dynamic> x in _cwInvSubs.values) {
      x.cancel();
    }
    _cwNoticeT?.cancel();
    _cwSeenT?.cancel();
    _cwAwayT?.cancel();
    _crNoteT?.cancel();
    _setTabBadge(0);
    _inqSub?.cancel();""")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT.name} ({len(s):,} chars)")
