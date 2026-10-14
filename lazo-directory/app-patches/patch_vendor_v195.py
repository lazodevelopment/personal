r"""patch_vendor_v195.py - Vendor v194 -> v195 (JC-LAZO-VDASH-1014-195)
More widgets for the rail:
  speed      Reply speed: your average first reply and answer rate against the
             median for your category in your city (metroStats)
  quiet      Quiet leads: couples who went silent after your last message, oldest first
  deposits   Payments due this week: open invoices due in the next 7 days or overdue
  post       Today's post: June's Instagram caption for the day (june hub /api/post-idea),
             with the gallery photo she picked; Copy caption
  coming     Weddings coming up: the next 30 days with a countdown and what is still
             open (contract unsigned, balance unpaid)
  strength   Profile strength (the Profile tab card)
  share      Share your page: your public link, copy it, or open it
New vendors start with quiet and deposits on as well.

    python app-patches\patch_vendor_v195.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / "Vendor_master_v194.txt").read_text(encoding="utf-8")
OUT = HERE / "Vendor_master_v195.txt"


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"anchor found {n}x (want {count}): {old[:80]!r}")
    s = s.replace(old, new)


rep("// Build ID: JC-LAZO-VDASH-1014-194 (v194:", "// Build ID: JC-LAZO-VDASH-1014-195 (v195: more rail widgets - reply speed against the city, quiet leads, payments due this week, today's post from June, weddings coming up, profile strength, share your page. base v194) (v194:")

rep("""    <String>['notes', 'Notes', 'A private notepad'],
  ];
  static const List<String> _kRailDefault = <String>['weather', 'consults', 'analytics', 'calendar', 'funnel', 'goal'];""",
    """    <String>['notes', 'Notes', 'A private notepad'],
    <String>['speed', 'Reply speed', 'Your first replies against your city'],
    <String>['quiet', 'Quiet leads', 'Couples who went silent after your last message'],
    <String>['deposits', 'Payments due this week', 'Open invoices due in the next seven days'],
    <String>['post', 'Today\\'s post', 'June writes an Instagram caption for you each day'],
    <String>['coming', 'Weddings coming up', 'The next 30 days and anything still open'],
    <String>['strength', 'Profile strength', 'What to add to your page next'],
    <String>['share', 'Share your page', 'Your public link, ready to copy'],
  ];
  static const List<String> _kRailDefault = <String>['weather', 'consults', 'analytics', 'quiet', 'deposits', 'calendar', 'funnel', 'goal'];""")

rep("""        case 'notes':
          return _railCard('Notes', Icons.sticky_note_2_rounded, _railNotes(), sub: 'Only you see these');
      }""", """        case 'notes':
          return _railCard('Notes', Icons.sticky_note_2_rounded, _railNotes(), sub: 'Only you see these');
        case 'speed':
          return _railCard('Reply speed', Icons.bolt_rounded, _railSpeed(vendorId, vd));
        case 'quiet':
          return _railCard('Quiet leads', Icons.hourglass_bottom_rounded, _railQuiet(vendorId));
        case 'deposits':
          return _railCard('Payments due this week', Icons.request_quote_rounded, _railDeposits(vendorId));
        case 'post':
          return _railCard('Today\\'s post', Icons.photo_camera_back_rounded, _railPost(vendorId), sub: 'By June');
        case 'coming':
          return _railCard('Weddings coming up', Icons.event_rounded, _railComing(vendorId));
        case 'strength':
          return Padding(padding: const EdgeInsets.only(bottom: 14), child: _profileTodoCard(vendorId, vd));
        case 'share':
          return _railCard('Share your page', Icons.ios_share_rounded, _railShare(vd));
      }""")

rep("""  // ---- Notes (private: users/{uid}.vendorNotes)""", r"""  void _railOpen(String inquiryId) {
    if (inquiryId.isEmpty) return;
    setState(() {
      _showAccount = false;
      _editingProfile = false;
      _dashMode = 'leads';
      _setInboxThread(inquiryId);
      _showInbox = true;
    });
  }

  String _railMins(int m) {
    if (m < 60) return '$m min';
    if (m < 24 * 60) {
      final double h = m / 60;
      return h < 10 ? '${h.toStringAsFixed(1).replaceAll('.0', '')} hr' : '${h.round()} hr';
    }
    final double d = m / (24 * 60);
    return d < 10 ? '${d.toStringAsFixed(1).replaceAll('.0', '')} days' : '${d.round()} days';
  }

  Widget _railRow({required String title, required String sub, String right = '', Color? rightColor, VoidCallback? onTap}) => InkWell(
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

  // ---- Reply speed against the city
  Widget _railSpeed(String vendorId, Map<String, dynamic> vd) {
    final String metroId = (vd['metroId'] ?? '').toString();
    final String catId = vd['categories'] is List && (vd['categories'] as List).isNotEmpty ? (vd['categories'] as List).first.toString() : '';
    final String msKey = '${metroId}__$catId';
    return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
      stream: _liveDoc('ms:$msKey', () => FirebaseFirestore.instance.collection('metroStats').doc(msKey)),
      initialData: _liveD['ms:$msKey']?.latest,
      builder: (BuildContext c0, AsyncSnapshot<DocumentSnapshot<Map<String, dynamic>>> mss) {
        final Map<String, dynamic> ms = mss.data?.data() ?? <String, dynamic>{};
        return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
          stream: _leadsStream(vendorId),
          initialData: _leadsLatest(vendorId),
          builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
            final Map<String, num> rs = _replyStats(_leadDocs(s));
            final int replied = (rs['replied'] ?? 0).toInt();
            final int avg = (rs['avgMin'] ?? 0).toInt();
            final int rate = ((rs['rate'] ?? 0) * 100).round();
            final int bench = ms['medianReplyMin'] is num ? (ms['medianReplyMin'] as num).round() : 0;
            if (replied == 0) {
              return Text('Reply to your first inquiry and your speed shows here. The first vendor to answer usually gets the booking.', style: TextStyle(color: _lzFg(muted), fontSize: 12.5, height: 1.4));
            }
            final bool faster = bench > 0 && avg <= bench;
            final String verdict = bench <= 0
                ? 'No city figure yet for your category.'
                : faster
                    ? 'Faster than most ${_metroLabel(metroId)} ${_catLabelFor(catId).toLowerCase()}s (median ${_railMins(bench)}).'
                    : 'The ${_metroLabel(metroId)} median is ${_railMins(bench)}. Answering sooner wins more bookings.';
            return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
              Row(children: <Widget>[
                _railStat(_railMins(avg), 'Your average first reply'),
                const SizedBox(width: 8),
                _railStat('$rate%', 'Answered within a day'),
              ]),
              const SizedBox(height: 10),
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                Icon(faster ? Icons.trending_up_rounded : Icons.info_outline_rounded, size: 16, color: faster ? vGreen : gold),
                const SizedBox(width: 6),
                Expanded(child: Text(verdict, style: TextStyle(color: _lzFg(ink), fontSize: 12.5, height: 1.35))),
              ]),
            ]);
          },
        );
      },
    );
  }

  // ---- Quiet leads: you wrote last, no answer for 3+ days
  Widget _railQuiet(String vendorId) {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _leadsStream(vendorId),
      initialData: _leadsLatest(vendorId),
      builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
        final DateTime now = DateTime.now();
        final List<Map<String, dynamic>> q = _railLeads(vendorId).where((Map<String, dynamic> m) {
          final String stg = _railStage(m);
          if (stg == 'booked' || stg == 'lost') return false;
          if ((m['lastMessageRole'] ?? '') != 'vendor') return false;
          final dynamic t = m['lastMessageAt'];
          return t is Timestamp && now.difference(t.toDate()).inDays >= 3;
        }).toList()
          ..sort((Map<String, dynamic> a, Map<String, dynamic> b) => (a['lastMessageAt'] as Timestamp).compareTo(b['lastMessageAt'] as Timestamp));
        if (q.isEmpty) {
          return Text('Nobody has gone quiet. Couples who stop answering for three days show up here so you can nudge them.', style: TextStyle(color: _lzFg(muted), fontSize: 12.5, height: 1.4));
        }
        return Column(children: <Widget>[
          for (final Map<String, dynamic> m in q.take(5))
            Builder(builder: (BuildContext _) {
              final int days = now.difference((m['lastMessageAt'] as Timestamp).toDate()).inDays;
              final DateTime? w = _railWedding(m);
              return _railRow(
                title: (m['coupleName'] ?? 'A couple').toString(),
                sub: w == null ? 'Tap to send a nudge' : 'Wedding ${_jwDate(Timestamp.fromDate(w))} - tap to nudge',
                right: '$days days',
                rightColor: days >= 7 ? const Color(0xFFB4534B) : gold,
                onTap: () => _railOpen((m['_id'] ?? '').toString()),
              );
            }),
          if (q.length > 5) Padding(padding: const EdgeInsets.only(top: 4), child: Text('and ${q.length - 5} more', style: TextStyle(color: _lzFg(muted), fontSize: 11.5))),
        ]);
      },
    );
  }

  // ---- Payments due this week (and anything overdue)
  Widget _railDeposits(String vendorId) {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _invoicesAllStream(vendorId),
      initialData: _liveQ['invoices:$vendorId']?.latest,
      builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
        final DateTime now = DateTime.now();
        final DateTime end = DateTime(now.year, now.month, now.day).add(const Duration(days: 8));
        final Map<String, String> names = <String, String>{
          for (final Map<String, dynamic> m in _railLeads(vendorId)) (m['_id'] ?? '').toString(): (m['coupleName'] ?? 'A couple').toString()
        };
        final List<QueryDocumentSnapshot<Map<String, dynamic>>> due = (s.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[]).where((QueryDocumentSnapshot<Map<String, dynamic>> d) {
          final Map<String, dynamic> m = d.data();
          final String st = (m['status'] ?? '').toString();
          if (st == 'paid' || st == 'void' || m['demo'] == true) return false;
          final dynamic dd = m['dueDate'];
          return dd is Timestamp && dd.toDate().isBefore(end);
        }).toList()
          ..sort((QueryDocumentSnapshot<Map<String, dynamic>> a, QueryDocumentSnapshot<Map<String, dynamic>> b) => (a.data()['dueDate'] as Timestamp).compareTo(b.data()['dueDate'] as Timestamp));
        if (due.isEmpty) {
          return Text('Nothing due in the next seven days.', style: TextStyle(color: _lzFg(muted), fontSize: 12.5));
        }
        num total = 0;
        for (final QueryDocumentSnapshot<Map<String, dynamic>> d in due) {
          if (d.data()['total'] is num) total += d.data()['total'] as num;
        }
        return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
          Text('${_fmtMoney(total)} due across ${due.length} invoice${due.length == 1 ? '' : 's'}', style: TextStyle(color: _lzFg(plum), fontSize: 13, fontWeight: FontWeight.w800)),
          const SizedBox(height: 6),
          for (final QueryDocumentSnapshot<Map<String, dynamic>> d in due.take(6))
            Builder(builder: (BuildContext _) {
              final Map<String, dynamic> m = d.data();
              final String inq = d.reference.parent.parent?.id ?? '';
              final DateTime dd = (m['dueDate'] as Timestamp).toDate();
              final int days = DateTime(dd.year, dd.month, dd.day).difference(DateTime(now.year, now.month, now.day)).inDays;
              return _railRow(
                title: names[inq] ?? 'A couple',
                sub: (m['title'] ?? 'Invoice').toString(),
                right: '${_fmtMoney(m['total'])}  ${days < 0 ? '${-days}d late' : days == 0 ? 'today' : 'in ${days}d'}',
                rightColor: days < 0 ? const Color(0xFFB4534B) : _lzFg(plum),
                onTap: () => _railOpen(inq),
              );
            }),
        ]);
      },
    );
  }

  // ---- Today's post: June's caption of the day
  Map<String, dynamic>? _railPostData;
  String _railPostDay = '';
  bool _railPostBusy = false;

  Future<void> _railPostLoad() async {
    final String day = _ymd(DateTime.now());
    if (_railPostBusy || _railPostDay == day) return;
    _railPostBusy = true;
    try {
      final String? t = await FirebaseAuth.instance.currentUser?.getIdToken();
      if (t == null) return;
      final httpc.Response r = await httpc.get(Uri.parse('https://june.meetlazo.com/api/post-idea'), headers: <String, String>{'authorization': 'Bearer $t'}).timeout(const Duration(seconds: 45));
      final dynamic j = jsonDecode(r.body);
      if (j is Map && (j['caption'] ?? '').toString().isNotEmpty) {
        _railPostData = Map<String, dynamic>.from(j);
        _railPostDay = day;
      }
    } catch (_) {
    } finally {
      _railPostBusy = false;
      if (mounted) setState(() {});
    }
  }

  Widget _railPost(String vendorId) {
    final Map<String, dynamic>? p = _railPostData;
    if (p == null) {
      if (!_railPostBusy) WidgetsBinding.instance.addPostFrameCallback((_) => _railPostLoad());
      return Row(children: <Widget>[
        const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
        const SizedBox(width: 10),
        Expanded(child: Text(_railPostBusy ? 'June is writing today\'s caption...' : 'Today\'s caption will appear here.', style: TextStyle(color: _lzFg(muted), fontSize: 12.5))),
      ]);
    }
    final String cap = (p['caption'] ?? '').toString();
    final String photo = (p['photo'] ?? '').toString();
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
      if (photo.startsWith('http'))
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: AspectRatio(aspectRatio: 4 / 5, child: Image.network(photo, fit: BoxFit.cover, errorBuilder: (BuildContext c, Object e, StackTrace? st) => const SizedBox.shrink())),
        ),
      if (photo.startsWith('http')) const SizedBox(height: 10),
      Text(cap, style: TextStyle(color: _lzFg(ink), fontSize: 12.5, height: 1.45)),
      const SizedBox(height: 8),
      Row(children: <Widget>[
        TextButton.icon(
          onPressed: _h(() async {
            await Clipboard.setData(ClipboardData(text: cap));
            _toast('Caption copied. Paste it into Instagram with the photo.');
          }),
          icon: Icon(Icons.copy_rounded, size: 15, color: _lzFg(plum)),
          label: Text('Copy caption', style: TextStyle(color: _lzFg(plum), fontSize: 12, fontWeight: FontWeight.w800)),
        ),
        if (photo.startsWith('http'))
          TextButton.icon(
            onPressed: _h(() => launchUrl(Uri.parse(photo), mode: LaunchMode.externalApplication)),
            icon: Icon(Icons.download_rounded, size: 15, color: _lzFg(plum)),
            label: Text('Photo', style: TextStyle(color: _lzFg(plum), fontSize: 12, fontWeight: FontWeight.w800)),
          ),
      ]),
    ]);
  }

  // ---- Weddings coming up (30 days) and what is still open
  Widget _railComing(String vendorId) {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _leadsStream(vendorId),
      initialData: _leadsLatest(vendorId),
      builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
        final DateTime today = DateTime(DateTime.now().year, DateTime.now().month, DateTime.now().day);
        final List<Map<String, dynamic>> w = _railLeads(vendorId).where((Map<String, dynamic> m) {
          if (_railStage(m) != 'booked') return false;
          final DateTime? d = _railWedding(m);
          return d != null && !d.isBefore(today) && d.difference(today).inDays <= 30;
        }).toList()
          ..sort((Map<String, dynamic> a, Map<String, dynamic> b) => _railWedding(a)!.compareTo(_railWedding(b)!));
        if (w.isEmpty) {
          return Text('No weddings in the next 30 days.', style: TextStyle(color: _lzFg(muted), fontSize: 12.5));
        }
        return Column(children: <Widget>[
          for (final Map<String, dynamic> m in w.take(6))
            Builder(builder: (BuildContext _) {
              final DateTime d = _railWedding(m)!;
              final int days = DateTime(d.year, d.month, d.day).difference(today).inDays;
              final List<String> open = <String>[
                if ((m['contractStatus'] ?? '').toString() != 'signed') 'contract not signed',
                if ((m['invoiceStatus'] ?? '').toString().isNotEmpty && (m['invoiceStatus'] ?? '').toString() != 'paid') 'balance open',
              ];
              return _railRow(
                title: (m['coupleName'] ?? 'A couple').toString(),
                sub: open.isEmpty ? '${_jwDate(Timestamp.fromDate(d))} - all set' : '${_jwDate(Timestamp.fromDate(d))} - ${open.join(', ')}',
                right: days == 0 ? 'Today' : days == 1 ? 'Tomorrow' : '$days days',
                rightColor: open.isEmpty ? vGreen : gold,
                onTap: () => _railOpen((m['_id'] ?? '').toString()),
              );
            }),
        ]);
      },
    );
  }

  // ---- Share your page
  Widget _railShare(Map<String, dynamic> vd) {
    final String metro = (vd['metroId'] ?? '').toString();
    final String cat = vd['categories'] is List && (vd['categories'] as List).isNotEmpty ? (vd['categories'] as List).first.toString() : '';
    final String slug = (vd['slug'] ?? '').toString();
    if (metro.isEmpty || cat.isEmpty || slug.isEmpty) {
      return Text('Your public link appears here once your listing is live.', style: TextStyle(color: _lzFg(muted), fontSize: 12.5));
    }
    final String url = 'https://meetlazo.com/$metro/$cat/$slug/';
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(color: _lzBg(plum.withOpacity(.04)), borderRadius: BorderRadius.circular(10), border: Border.all(color: _lzLine(goldLine))),
        child: Text(url.replaceFirst('https://', ''), maxLines: 2, style: TextStyle(color: _lzFg(ink), fontSize: 12)),
      ),
      const SizedBox(height: 6),
      Text('Put it in your Instagram bio, your email signature and your inquiry replies. Couples who arrive from it can check your date in one tap.', style: TextStyle(color: _lzFg(muted), fontSize: 11.5, height: 1.35)),
      Row(children: <Widget>[
        TextButton.icon(
          onPressed: _h(() async {
            await Clipboard.setData(ClipboardData(text: url));
            _toast('Link copied.');
          }),
          icon: Icon(Icons.link_rounded, size: 15, color: _lzFg(plum)),
          label: Text('Copy link', style: TextStyle(color: _lzFg(plum), fontSize: 12, fontWeight: FontWeight.w800)),
        ),
        TextButton.icon(
          onPressed: _h(() => launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication)),
          icon: Icon(Icons.open_in_new_rounded, size: 15, color: _lzFg(plum)),
          label: Text('Open', style: TextStyle(color: _lzFg(plum), fontSize: 12, fontWeight: FontWeight.w800)),
        ),
      ]),
    ]);
  }

  // ---- Notes (private: users/{uid}.vendorNotes)""")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT.name} ({len(s):,} chars)")
