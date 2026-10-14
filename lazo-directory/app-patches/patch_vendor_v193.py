r"""patch_vendor_v193.py - Vendor v192 -> v193 (JC-LAZO-VDASH-1014-193)
JUNE KEEPS YOU POSTED. While the dashboard is open, June tells the vendor -
out loud and on a card at the top of the screen - when something that matters
happens:
  - a new inquiry (who, the date, the venue)        - a couple replies
  - a booking                                        - a contract signed
  - a payment (who, how much, what for)              - a new review (stars, a line)
  - a consult booked (who, what, when)
And once a day, the first time the dashboard opens: today's weather in their
city, and a heads-up if a booked wedding is today or tomorrow.
When they come back after being away, one sentence catches them up ("While
you were away: two new inquiries, Sarah and Mike paid $1,300, and a new
five-star review").
The card has Open (jumps to the thread) and a speaker that mutes June's
announcements (remembered); the card still shows when she is muted. Nothing
repeats: every event is remembered on the device. Quiet during the tour.

Needs JuneNative v8 (JuneNative.say / holdLine).

    python app-patches\patch_vendor_v193.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / "Vendor_master_v192.txt").read_text(encoding="utf-8")
OUT = HERE / "Vendor_master_v193.txt"


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"anchor found {n}x (want {count}): {old[:80]!r}")
    s = s.replace(old, new)


rep("// Build ID: JC-LAZO-VDASH-1012-188 (v188:", "// Build ID: JC-LAZO-VDASH-1014-193 (v193: JUNE KEEPS YOU POSTED - spoken + on-screen notices for new inquiries, replies, bookings, signed contracts, payments, reviews and consults, today's weather once a day, a catch-up line after time away; mute on the card. v192: June narrates the first-run tour. base v191) (v188:")

# start watching with the rest
rep("""    _ensureBookingWatch(vendorId);
    _ensureChimeWatch(vendorId);""", """    _ensureBookingWatch(vendorId);
    _ensureChimeWatch(vendorId);
    _juneWatch(vendorId);""")

# the card paints above the dashboard, under the tour
rep("""            // v168: the first-run tour paints over everything
            _tourOverlay(),""", """            // v193: June's notices
            _juneNoticeOverlay(),
            // v168: the first-run tour paints over everything
            _tourOverlay(),""")

rep("""    _chimeSub?.cancel();
    _setTabBadge(0);""", """    _chimeSub?.cancel();
    for (final StreamSubscription<dynamic> s in _jwSubs) {
      s.cancel();
    }
    _jwNoticeT?.cancel();
    _jwSeenT?.cancel();
    _setTabBadge(0);""")

rep("""  // Watches every thread for this vendor: chimes on a NEW couple message""", r"""  // ===================================================================
  // v193: JUNE KEEPS YOU POSTED
  // ===================================================================
  String _jwFor = '';
  final List<StreamSubscription<dynamic>> _jwSubs = <StreamSubscription<dynamic>>[];
  final Map<String, Map<String, dynamic>> _jwInq = <String, Map<String, dynamic>>{};
  final Set<String> _jwArmed = <String>{};
  Set<String> _jwSaid = <String>{};
  bool _jwVoice = true;
  DateTime? _jwLastSeen;
  final List<Map<String, dynamic>> _jwQueue = <Map<String, dynamic>>[];
  Map<String, dynamic>? _jwNotice;
  Timer? _jwNoticeT;
  Timer? _jwSeenT;
  final List<String> _jwAway = <String>[];
  Timer? _jwAwayT;

  String _jwCouple(Map<String, dynamic> m) {
    final String n = (m['coupleName'] ?? '').toString().trim();
    return n.isEmpty ? 'A couple' : n.replaceAll(' & ', ' and ');
  }

  String _jwDate(dynamic v) {
    DateTime? d;
    if (v is Timestamp) d = v.toDate();
    if (v is String) d = DateTime.tryParse(v);
    if (d == null) return '';
    const List<String> mo = <String>['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    return '${mo[d.month - 1]} ${d.day}${d.year != DateTime.now().year ? ', ${d.year}' : ''}';
  }

  String _jwWhen(DateTime d) {
    const List<String> wd = <String>['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    final int h12 = d.hour % 12 == 0 ? 12 : d.hour % 12;
    final String t = d.minute == 0 ? '$h12 ${d.hour < 12 ? 'am' : 'pm'}' : '$h12:${d.minute.toString().padLeft(2, '0')} ${d.hour < 12 ? 'am' : 'pm'}';
    final DateTime now = DateTime.now();
    final int days = DateTime(d.year, d.month, d.day).difference(DateTime(now.year, now.month, now.day)).inDays;
    final String day = days == 0 ? 'today' : days == 1 ? 'tomorrow' : days < 7 ? wd[d.weekday - 1] : _jwDate(d);
    return '$day at $t';
  }

  bool _jwFresh(dynamic v, {int minutes = 15}) {
    if (v is! Timestamp) return false;
    return DateTime.now().difference(v.toDate()).inMinutes.abs() <= minutes;
  }

  bool _jwSince(dynamic v) {
    final DateTime? ls = _jwLastSeen;
    if (ls == null || v is! Timestamp) return false;
    return v.toDate().isAfter(ls) && DateTime.now().difference(v.toDate()).inDays < 14;
  }

  Future<void> _jwLoadPrefs(String vendorId) async {
    try {
      final SharedPreferences p = await SharedPreferences.getInstance();
      _jwSaid = (p.getStringList('juneSaid_$vendorId') ?? <String>[]).toSet();
      _jwVoice = p.getBool('juneAnnounce') ?? true;
      final String ls = p.getString('juneSeen_$vendorId') ?? '';
      _jwLastSeen = DateTime.tryParse(ls);
    } catch (_) {}
  }

  Future<void> _jwRemember(String key) async {
    _jwSaid.add(key);
    try {
      final SharedPreferences p = await SharedPreferences.getInstance();
      final List<String> l = _jwSaid.toList();
      await p.setStringList('juneSaid_$_jwFor', l.length > 400 ? l.sublist(l.length - 400) : l);
    } catch (_) {}
  }

  Future<void> _jwMarkSeen() async {
    try {
      final SharedPreferences p = await SharedPreferences.getInstance();
      await p.setString('juneSeen_$_jwFor', DateTime.now().toIso8601String());
    } catch (_) {}
  }

  /// one notice: on the card, and spoken unless muted or the tour is talking
  void _juneSay(String key, String text, {String? threadId, IconData icon = Icons.auto_awesome_rounded, bool speak = true}) {
    if (key.isNotEmpty) {
      if (_jwSaid.contains(key)) return;
      _jwRemember(key);
    }
    _jwQueue.add(<String, dynamic>{'text': text, 'thread': threadId, 'icon': icon, 'speak': speak});
    if (_jwNotice == null) _jwNext();
  }

  void _jwNext() {
    _jwNoticeT?.cancel();
    if (_jwQueue.isEmpty) {
      if (mounted) setState(() => _jwNotice = null);
      return;
    }
    final Map<String, dynamic> n = _jwQueue.removeAt(0);
    if (mounted) setState(() => _jwNotice = n);
    if (n['speak'] == true && _jwVoice && !JuneNative.holdLine && _tourIdx < 0) {
      JuneNative.say(n['text'] as String);
    }
    final int words = (n['text'] as String).split(' ').length;
    _jwNoticeT = Timer(Duration(milliseconds: 4500 + words * 330), _jwNext);
  }

  // a burst of events while away (or at load) becomes one sentence
  void _jwAwayAdd(String key, String phrase) {
    if (_jwSaid.contains(key)) return;
    _jwRemember(key);
    _jwAway.add(phrase);
    _jwAwayKick();
  }

  void _jwAwayKick() {
    _jwAwayT?.cancel();
    _jwAwayT = Timer(const Duration(seconds: 3), () {
      if (_jwAway.isEmpty) return;
      final List<String> a = List<String>.from(_jwAway);
      _jwAway.clear();
      final String list = a.length == 1 ? a.first : a.sublist(0, a.length - 1).join(', ') + ', and ' + a.last;
      _juneSay('', 'While you were away: $list.', icon: Icons.history_rounded);
    });
  }

  String _jwCount(int n, String one, String many) => n == 1 ? 'a $one' : '${_jwWord(n)} $many';
  String _jwWord(int n) => n >= 0 && n < 11 ? <String>['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'][n] : '$n';

  Future<void> _juneWatch(String vendorId) async {
    if (_jwFor == vendorId) return;
    _jwFor = vendorId;
    for (final StreamSubscription<dynamic> s in _jwSubs) {
      s.cancel();
    }
    _jwSubs.clear();
    _jwArmed.clear();
    _jwInq.clear();
    await _jwLoadPrefs(vendorId);
    if (!mounted || _jwFor != vendorId) return;
    _jwSeenT?.cancel();
    _jwSeenT = Timer.periodic(const Duration(minutes: 1), (_) => _jwMarkSeen());

    // ---- threads: new inquiries, replies, bookings, contracts
    _jwSubs.add(_leadsStream(vendorId).listen((QuerySnapshot<Map<String, dynamic>> snap) {
      final bool first = !_jwArmed.contains('leads');
      int awayLeads = 0;
      for (final QueryDocumentSnapshot<Map<String, dynamic>> d in snap.docs) {
        final Map<String, dynamic> m = d.data();
        final Map<String, dynamic>? was = _jwInq[d.id];
        _jwInq[d.id] = <String, dynamic>{
          'status': m['status'], 'contract': m['contractStatus'], 'lastAt': m['lastMessageAt'],
          'role': m['lastMessageRole'], 'couple': _jwCouple(m)};
        final String who = _jwCouple(m);
        final bool practice = m['demo'] == true;
        final Map<String, dynamic> si = m['structuredIntent'] is Map ? Map<String, dynamic>.from(m['structuredIntent'] as Map) : <String, dynamic>{};
        final String date = _jwDate(si['weddingDate']);
        final String venue = (si['venue'] ?? '').toString().trim();
        if (first) {
          // catching up: what happened since the dashboard was last open
          if (_jwSince(m['createdAt']) && !practice) {
            awayLeads++;
            _jwRemember('lead:${d.id}');
          }
          if ((m['status'] ?? '') == 'booked' && _jwSince(m['bookedAt'])) {
            _jwAwayAdd('booked:${d.id}', '$who booked you');
          }
          continue;
        }
        if (was == null) {
          if (_jwFresh(m['createdAt'], minutes: 30)) {
            _juneSay('lead:${d.id}',
                practice
                    ? 'Your practice couple, $who, just wrote in. Have a go at replying.'
                    : 'New inquiry from $who${date.isNotEmpty ? ' for $date' : ''}${venue.isNotEmpty ? ' at $venue' : ''}.',
                threadId: d.id, icon: Icons.mark_email_unread_rounded);
          }
          continue;
        }
        if ((m['status'] ?? '') == 'booked' && (was['status'] ?? '') != 'booked') {
          _juneSay('booked:${d.id}', '$who booked you${date.isNotEmpty ? ' for $date' : ''}. Congratulations!', threadId: d.id, icon: Icons.celebration_rounded);
        } else if ((m['contractStatus'] ?? '') == 'signed' && (was['contract'] ?? '') != 'signed') {
          _juneSay('signed:${d.id}', '$who signed their contract.', threadId: d.id, icon: Icons.draw_rounded);
        } else if ((m['lastMessageRole'] ?? '') == 'couple' && m['lastMessageAt'] is Timestamp &&
            (was['lastAt'] is! Timestamp || (m['lastMessageAt'] as Timestamp).compareTo(was['lastAt'] as Timestamp) > 0) &&
            _jwFresh(m['lastMessageAt'], minutes: 5) && d.id != _inboxOpenId) {
          final String prev = (m['lastMessagePreview'] ?? '').toString().trim();
          final String line = prev.isEmpty ? '' : ' "${prev.length > 90 ? prev.substring(0, 87).trimRight() + '...' : prev}"';
          _juneSay('msg:${d.id}:${(m['lastMessageAt'] as Timestamp).seconds}', '$who just replied.$line', threadId: d.id, icon: Icons.chat_bubble_rounded, speak: !practice);
        }
      }
      if (first) {
        if (awayLeads > 0) {
          _jwAway.insert(0, _jwCount(awayLeads, 'new inquiry', 'new inquiries'));
          _jwAwayKick();
        }
        _jwArmed.add('leads');
        _jwMarkSeen();
      }
    }, onError: (Object _) {}));

    // ---- money: an invoice that turns paid
    _jwSubs.add(_invoicesAllStream(vendorId).listen((QuerySnapshot<Map<String, dynamic>> snap) {
      final bool first = !_jwArmed.contains('inv');
      for (final DocumentChange<Map<String, dynamic>> ch in snap.docChanges) {
        if (ch.type == DocumentChangeType.removed) continue;
        final Map<String, dynamic> m = ch.doc.data() ?? <String, dynamic>{};
        if ((m['status'] ?? '') != 'paid' || m['demo'] == true) continue;
        final String inqId = ch.doc.reference.parent.parent?.id ?? '';
        final String who = (_jwInq[inqId]?['couple'] ?? 'A couple').toString();
        final String amt = _fmtMoney(m['total']);
        final String what = (m['title'] ?? '').toString().trim();
        if (first) {
          if (_jwSince(m['paidAt'])) _jwAwayAdd('paid:${ch.doc.id}', '$who paid ${amt.isEmpty ? 'an invoice' : amt}');
          continue;
        }
        if (_jwFresh(m['paidAt'], minutes: 30)) {
          _juneSay('paid:${ch.doc.id}', '$who just paid${amt.isEmpty ? '' : ' $amt'}${what.isEmpty ? '' : ' for $what'}.', threadId: inqId.isEmpty ? null : inqId, icon: Icons.payments_rounded);
        }
      }
      _jwArmed.add('inv');
    }, onError: (Object _) {}));

    // ---- reviews
    _jwSubs.add(FirebaseFirestore.instance.collection('reviews').where('vendorId', isEqualTo: vendorId).snapshots().listen((QuerySnapshot<Map<String, dynamic>> snap) {
      final bool first = !_jwArmed.contains('rev');
      for (final DocumentChange<Map<String, dynamic>> ch in snap.docChanges) {
        if (ch.type != DocumentChangeType.added) continue;
        final Map<String, dynamic> m = ch.doc.data() ?? <String, dynamic>{};
        final int stars = (m['rating'] is num) ? (m['rating'] as num).round() : 0;
        final String who = (m['coupleName'] ?? '').toString().trim();
        final String txt = (m['text'] ?? '').toString().trim();
        final String starW = stars > 0 ? '${_jwWord(stars)}-star ' : '';
        if (first) {
          if (_jwSince(m['createdAt'])) _jwAwayAdd('rev:${ch.doc.id}', 'a new ${starW}review');
          continue;
        }
        final String quote = txt.isEmpty ? '' : ' "${txt.length > 110 ? txt.substring(0, 107).trimRight() + '...' : txt}"';
        _juneSay('rev:${ch.doc.id}', 'New ${starW}review${who.isEmpty ? '' : ' from $who'}.$quote', icon: Icons.star_rounded);
      }
      _jwArmed.add('rev');
    }, onError: (Object _) {}));

    // ---- consults booked through the scheduler
    _jwSubs.add(FirebaseFirestore.instance.collection('consults').where('vendorId', isEqualTo: vendorId).where('status', isEqualTo: 'booked').snapshots().listen((QuerySnapshot<Map<String, dynamic>> snap) {
      final bool first = !_jwArmed.contains('con');
      for (final DocumentChange<Map<String, dynamic>> ch in snap.docChanges) {
        if (ch.type != DocumentChangeType.added) continue;
        final Map<String, dynamic> m = ch.doc.data() ?? <String, dynamic>{};
        final dynamic st = m['startAt'];
        if (st is! Timestamp || st.toDate().isBefore(DateTime.now())) continue;
        final String who = (m['coupleName'] ?? m['name'] ?? m['guestName'] ?? 'Someone').toString().trim();
        final String kind = (m['typeLabel'] ?? 'a call').toString().trim();
        final String what = kind.isEmpty ? 'a call' : (RegExp(r'^[aeiou]', caseSensitive: false).hasMatch(kind) ? 'an ' : 'a ') + kind.toLowerCase();
        if (first) {
          if (_jwSince(m['createdAt'])) _jwAwayAdd('con:${ch.doc.id}', '$who booked $what for ${_jwWhen(st.toDate())}');
          continue;
        }
        _juneSay('con:${ch.doc.id}', '$who booked $what for ${_jwWhen(st.toDate())}.', threadId: (m['inquiryId'] ?? '').toString().isEmpty ? null : m['inquiryId'].toString(), icon: Icons.event_available_rounded);
      }
      _jwArmed.add('con');
    }, onError: (Object _) {}));

    // ---- the day: once a day, today's weather and any wedding today or tomorrow
    Future<void>.delayed(const Duration(seconds: 6), () => _jwWeather(vendorId));
  }

  Future<void> _jwWeather(String vendorId) async {
    if (!mounted || _jwFor != vendorId) return;
    final DateTime now = DateTime.now();
    final String key = 'wx:${_ymd(now)}';
    if (_jwSaid.contains(key) || now.hour < 5) return;
    final Map<String, dynamic> vd = _liveD['vendor:$vendorId']?.latest?.data() ?? <String, dynamic>{};
    final String metro = (vd['metroId'] ?? '').toString();
    if (metro.isEmpty || kMetroLatLng[metro] == null) return;
    await _loadWx(now, metro);
    final Map<String, dynamic>? w = _wxCache['${_ymd(now)}|$metro'];
    if (w == null || w['hi'] == null) return;
    final int code = (w['code'] is num) ? (w['code'] as num).toInt() : 0;
    final String sky = code == 0 ? 'clear skies' : code <= 2 ? 'sun and a few clouds' : code == 3 ? 'cloudy' : (code == 45 || code == 48) ? 'fog' : code >= 95 ? 'thunderstorms' : (code >= 71 && code <= 86 && code != 80 && code != 81 && code != 82) ? 'snow' : code >= 51 ? 'rain' : 'mixed skies';
    final int rain = (w['rainPct'] is num) ? (w['rainPct'] as num).round() : 0;
    final String city = metro.split('-').map((String p) => p.isEmpty ? p : p[0].toUpperCase() + p.substring(1)).join(' ');
    String line = 'Today in $city: $sky, a high of ${w['hi']} and a low of ${w['lo']}${rain >= 30 && !sky.contains('rain') && !sky.contains('thunder') ? ', with a $rain percent chance of rain' : ''}.';
    // a booked wedding today or tomorrow gets a mention
    final DateTime tom = now.add(const Duration(days: 1));
    final List<String> soon = <String>[];
    final QuerySnapshot<Map<String, dynamic>>? ls = _liveQ['leads:$vendorId']?.latest;
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in ls?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[]) {
      final Map<String, dynamic> m = d.data();
      if ((m['status'] ?? '') != 'booked' || m['demo'] == true) continue;
      final Map<String, dynamic> si = m['structuredIntent'] is Map ? Map<String, dynamic>.from(m['structuredIntent'] as Map) : <String, dynamic>{};
      final DateTime? wd = DateTime.tryParse((si['weddingDate'] ?? '').toString());
      if (wd == null) continue;
      if (_ymd(wd) == _ymd(now)) soon.add("${_jwCouple(m)}'s wedding is today");
      if (_ymd(wd) == _ymd(tom)) soon.add("${_jwCouple(m)}'s wedding is tomorrow");
    }
    if (soon.isNotEmpty) line += ' ' + soon.join(', and ') + '.';
    _juneSay(key, line, icon: Icons.wb_sunny_rounded);
  }

  Widget _juneNoticeOverlay() {
    final Map<String, dynamic>? n = _jwNotice;
    final bool phone = MediaQuery.of(context).size.width < 700;
    return Positioned(
      top: MediaQuery.of(context).padding.top + (phone ? 10 : 18),
      left: 0,
      right: 0,
      child: IgnorePointer(
        ignoring: n == null,
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 320),
          switchInCurve: Curves.easeOutCubic,
          switchOutCurve: Curves.easeInCubic,
          transitionBuilder: (Widget c, Animation<double> a) => FadeTransition(
              opacity: a, child: SlideTransition(position: Tween<Offset>(begin: const Offset(0, -.4), end: Offset.zero).animate(a), child: c)),
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
                        if ((n['thread'] ?? '').toString().isNotEmpty)
                          TextButton(
                            onPressed: () {
                              final String id = n['thread'].toString();
                              _jwNext();
                              setState(() {
                                _showAccount = false;
                                _editingProfile = false;
                                _setInboxThread(id);
                                _showInbox = true;
                              });
                            },
                            child: const Text('Open', style: TextStyle(color: gold, fontWeight: FontWeight.w800, fontSize: 13)),
                          ),
                        Tooltip(
                          message: _jwVoice ? 'Mute June\'s updates' : 'Let June read updates aloud',
                          child: IconButton(
                            visualDensity: VisualDensity.compact,
                            icon: Icon(_jwVoice ? Icons.volume_up_rounded : Icons.volume_off_rounded, size: 18, color: _jwVoice ? gold : const Color(0xFFB9A9BC)),
                            onPressed: () async {
                              setState(() => _jwVoice = !_jwVoice);
                              if (!_jwVoice) JuneNative.stopSpeaking();
                              try {
                                final SharedPreferences p = await SharedPreferences.getInstance();
                                await p.setBool('juneAnnounce', _jwVoice);
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
                            _jwNext();
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

  // Watches every thread for this vendor: chimes on a NEW couple message""")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT.name} ({len(s):,} chars)")
