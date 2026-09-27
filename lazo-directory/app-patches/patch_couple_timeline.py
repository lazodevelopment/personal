"""patch_couple_timeline.py - JC-LAZO-COUPLE-0920-TL-001
The day-of timeline, anchored to the ceremony, with durations and owners:
  - Every moment can carry a duration (dur, minutes) and owners (tags:
    planner, photo, video, dj, caterer, venue, florist, officiant, cake,
    party). The editor gets chips for both, and a "this is the ceremony"
    chip that marks the anchor.
  - The ceremony is the anchor. The builder header shows "Ceremony at 4:00 PM";
    tap it, pick a new time, and every moment shifts by the same amount.
    The classic day seeds with durations and owners, and its time picker
    starts from the wedding website's ceremony time when there is one. The
    Day-Of card's starter button now builds around the ceremony too (it used
    to seed a fixed 4 pm day).
  - The list shows ranges (4:00 - 4:30 PM), owner chips, and a hint between
    moments: "overlaps the last one by 15 min" in rose, "90 min open" when
    the gap is long.
  - Per-vendor sends: each booked vendor gets a page that opens with "Your
    moments" (the ones that name their role, with times and durations) and
    then the whole day with their moments marked. Same send sheet, same
    thread, one attachment each; the planner gets everything.
Anchor-and-assert; nothing is written unless every anchor matches once.

  python app-patches\\patch_couple_timeline.py [src] [out]
Default src: app-patches\\Couple_master_templates20.txt (the templates patch
goes first, both are needed live); out ..._timeline.txt.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_templates20.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else SRC.with_name(SRC.stem.replace("_templates20", "") + "_timeline.txt")
s = SRC.read_text(encoding="utf-8")
if "JC-LAZO-COUPLE-0920-TL-001" in s:
    raise SystemExit("already applied")


def swap(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"ABORT [{label}]: anchor matched {n} times, expected {count}")
    s = s.replace(old, new)
    print(f"  ok  {label}")


# ---------------------------------------------------------------- 1. the editor: duration, owners, anchor
swap("""    TimeOfDay time = TimeOfDay(
        hour: int.tryParse(t0[0]) ?? 16,
        minute: t0.length > 1 ? int.tryParse(t0[1]) ?? 0 : 0);
    final bool? ok = await showDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => StatefulBuilder(
          builder: (BuildContext ctx2, StateSetter setD) => AlertDialog(
                backgroundColor: ivory,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(20)),
                title: Text(d == null ? 'Add a moment' : 'Edit moment',""",
     """    TimeOfDay time = TimeOfDay(
        hour: int.tryParse(t0[0]) ?? 16,
        minute: t0.length > 1 ? int.tryParse(t0[1]) ?? 0 : 0);
    // JC-LAZO-COUPLE-0920-TL-001: how long it runs, whose moment it is, and
    // whether it is the ceremony - the anchor the whole day shifts around.
    int dur = ev['dur'] is num ? (ev['dur'] as num).toInt() : 0;
    final Set<String> owners = <String>{
      if (ev['owners'] is List)
        for (final dynamic o in ev['owners'] as List) o.toString()
    };
    bool anchor = ev['anchor'] == true;
    final bool? ok = await showDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => StatefulBuilder(
          builder: (BuildContext ctx2, StateSetter setD) => AlertDialog(
                backgroundColor: ivory,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(20)),
                scrollable: true,
                title: Text(d == null ? 'Add a moment' : 'Edit moment',""",
     "editor state")

swap("""                      icon: const Icon(Icons.schedule_rounded, size: 16),
                      label: Text(time.format(ctx2),
                          style: const TextStyle(fontWeight: FontWeight.w700)),
                    ),
                  ],
                ),
                actions: <Widget>[
                  TextButton(
                      onPressed: _h(() => Navigator.pop(ctx2, false)),
                      child:
                          const Text('Cancel', style: TextStyle(color: muted))),""",
     """                      icon: const Icon(Icons.schedule_rounded, size: 16),
                      label: Text(time.format(ctx2),
                          style: const TextStyle(fontWeight: FontWeight.w700)),
                    ),
                    const SizedBox(height: 12),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: const Text('HOW LONG',
                          style: TextStyle(
                              fontSize: 10.5,
                              letterSpacing: 2,
                              color: plum,
                              fontWeight: FontWeight.w700)),
                    ),
                    const SizedBox(height: 6),
                    Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                      for (final int m in const <int>[0, 15, 30, 45, 60, 90, 120, 180])
                        _tlChip(m == 0 ? 'A moment' : _tlDur(m), dur == m,
                            () => setD(() => dur = m)),
                    ]),
                    const SizedBox(height: 12),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: const Text('WHOSE MOMENT',
                          style: TextStyle(
                              fontSize: 10.5,
                              letterSpacing: 2,
                              color: plum,
                              fontWeight: FontWeight.w700)),
                    ),
                    const SizedBox(height: 6),
                    Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                      for (final List<String> o in kTlOwners)
                        _tlChip(o[1], owners.contains(o[0]), () => setD(() {
                              if (!owners.remove(o[0])) owners.add(o[0]);
                            })),
                    ]),
                    const SizedBox(height: 12),
                    _tlChip('This is the ceremony \\u00b7 the day is built around it',
                        anchor, () => setD(() => anchor = !anchor)),
                  ],
                ),
                actions: <Widget>[
                  TextButton(
                      onPressed: _h(() => Navigator.pop(ctx2, false)),
                      child:
                          const Text('Cancel', style: TextStyle(color: muted))),""",
     "editor chips")

swap("""    final Map<String, dynamic> payload = <String, dynamic>{
      'time': hh,
      'label': labelC.text.trim(),
      'note': noteC.text.trim(),
      'updatedAt': FieldValue.serverTimestamp(),
    };
    if (d == null) {
      await _dayofRef.add(payload);
    } else {
      await d.reference.set(payload, SetOptions(merge: true));
    }
  }
""", """    final Map<String, dynamic> payload = <String, dynamic>{
      'time': hh,
      'label': labelC.text.trim(),
      'note': noteC.text.trim(),
      'dur': dur,
      'owners': owners.toList()..sort(),
      'anchor': anchor,
      'updatedAt': FieldValue.serverTimestamp(),
    };
    if (d == null) {
      await _dayofRef.add(payload);
    } else {
      await d.reference.set(payload, SetOptions(merge: true));
    }
    if (anchor) {
      // One anchor only: the ceremony.
      try {
        final QuerySnapshot<Map<String, dynamic>> others =
            await _dayofRef.where('anchor', isEqualTo: true).get();
        final WriteBatch b = FirebaseFirestore.instance.batch();
        bool any = false;
        for (final QueryDocumentSnapshot<Map<String, dynamic>> o in others.docs) {
          if (d != null && o.id == d.id) continue;
          if (d == null && (o.data()['label'] ?? '') == labelC.text.trim() && (o.data()['time'] ?? '') == hh) continue;
          b.set(o.reference, <String, dynamic>{'anchor': false}, SetOptions(merge: true));
          any = true;
        }
        if (any) await b.commit();
      } catch (_) {}
    }
  }

  // ---- JC-LAZO-COUPLE-0920-TL-001: the anchored timeline ----

  // Owner tags match _catTag on booked vendors, plus the wedding party.
  static const List<List<String>> kTlOwners = <List<String>>[
    <String>['planner', 'Planner'],
    <String>['photo', 'Photographer'],
    <String>['video', 'Videographer'],
    <String>['dj', 'DJ / band'],
    <String>['caterer', 'Caterer'],
    <String>['venue', 'Venue'],
    <String>['florist', 'Florist'],
    <String>['officiant', 'Officiant'],
    <String>['cake', 'Cake'],
    <String>['party', 'Wedding party'],
  ];

  static String _tlOwnerLabel(String tag) {
    for (final List<String> o in kTlOwners) {
      if (o[0] == tag) return o[1];
    }
    return tag;
  }

  static String _tlDur(int m) {
    if (m <= 0) return '';
    if (m < 60) return '$m min';
    final int h = m ~/ 60;
    final int r = m % 60;
    return r == 0 ? '$h hr' : '$h hr $r min';
  }

  static int _tlMin(String hhmm) {
    final List<String> p = hhmm.split(':');
    return (int.tryParse(p[0]) ?? 0) * 60 +
        (p.length > 1 ? int.tryParse(p[1]) ?? 0 : 0);
  }

  static String _tlHm(int m) {
    final int x = ((m % 1440) + 1440) % 1440;
    return '${(x ~/ 60).toString().padLeft(2, '0')}:${(x % 60).toString().padLeft(2, '0')}';
  }

  // "4:00 - 4:30 PM" when the moment has a length, "4:00 PM" when not.
  String _tlRange(Map<String, dynamic> ev) {
    final String t = (ev['time'] ?? '').toString();
    final int dur = ev['dur'] is num ? (ev['dur'] as num).toInt() : 0;
    if (dur <= 0) return _fmtClock(t);
    final String a = _fmtClock(t);
    final String b = _fmtClock(_tlHm(_tlMin(t) + dur));
    final String apA = a.substring(a.length - 2);
    final String apB = b.substring(b.length - 2);
    return apA == apB
        ? '${a.substring(0, a.length - 3)} \\u2013 $b'
        : '$a \\u2013 $b';
  }

  List<String> _tlOwners(Map<String, dynamic> ev) => <String>[
        if (ev['owners'] is List)
          for (final dynamic o in ev['owners'] as List) o.toString()
      ];

  // The hint that sits between two moments: an overlap, or a long gap.
  String _tlHint(Map<String, dynamic> prev, Map<String, dynamic> next) {
    final int pd = prev['dur'] is num ? (prev['dur'] as num).toInt() : 0;
    if (pd <= 0) return '';
    final int end = _tlMin((prev['time'] ?? '').toString()) + pd;
    final int start = _tlMin((next['time'] ?? '').toString());
    if (start < end) {
      return 'Overlaps ${(prev['label'] ?? 'the last one').toString().toLowerCase()} by ${_tlDur(end - start)}';
    }
    if (start - end >= 60) return '${_tlDur(start - end)} open';
    return '';
  }

  Widget _tlChip(String label, bool on, VoidCallback go) {
    return _Press(
      tick: _Tick.select,
      onTap: go,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
        decoration: BoxDecoration(
          color: on ? plum : Colors.white,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: on ? plum : goldLine),
        ),
        child: Text(label,
            style: TextStyle(
                color: on ? gold : plum,
                fontSize: 12,
                fontWeight: FontWeight.w700)),
      ),
    );
  }

  Widget _tlOwnerRow(Map<String, dynamic> ev, {double size = 10}) {
    final List<String> os = _tlOwners(ev);
    if (os.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Wrap(spacing: 4, runSpacing: 4, children: <Widget>[
        for (final String o in os)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
            decoration: BoxDecoration(
                color: gold.withOpacity(.18),
                borderRadius: BorderRadius.circular(999)),
            child: Text(_tlOwnerLabel(o),
                style: TextStyle(
                    color: const Color(0xFF8A6A2F),
                    fontSize: size,
                    fontWeight: FontWeight.w800)),
          ),
      ]),
    );
  }

  // The anchor: the moment flagged as the ceremony, else the first one
  // called Ceremony.
  QueryDocumentSnapshot<Map<String, dynamic>>? _tlAnchor(
      List<QueryDocumentSnapshot<Map<String, dynamic>>> evs) {
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in evs) {
      if (d.data()['anchor'] == true) return d;
    }
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in evs) {
      if ((d.data()['label'] ?? '').toString().trim().toLowerCase() == 'ceremony') {
        return d;
      }
    }
    return null;
  }

  // The website's ceremony time ("4:00 pm", "16:00", "4pm") as a TimeOfDay.
  TimeOfDay? _tlSiteCeremony() {
    try {
      final QuerySnapshot<Map<String, dynamic>>? q = _liveQ['site:$_cid']?.latest;
      if (q == null || q.docs.isEmpty) return null;
      final String raw = (q.docs.first.data()['ceremonyTime'] ?? '').toString().trim().toLowerCase();
      final RegExpMatch? m = RegExp(r'(\\d{1,2})(?::(\\d{2}))?\\s*(am|pm)?').firstMatch(raw);
      if (m == null) return null;
      int h = int.parse(m.group(1)!);
      final int mi = int.tryParse(m.group(2) ?? '') ?? 0;
      final String? ap = m.group(3);
      if (ap == 'pm' && h < 12) h += 12;
      if (ap == 'am' && h == 12) h = 0;
      if (ap == null && h < 8) h += 12; // "4:00" on a wedding site means afternoon
      if (h > 23 || mi > 59) return null;
      return TimeOfDay(hour: h, minute: mi);
    } catch (_) {
      return null;
    }
  }

  // Move the ceremony and everything moves with it.
  Future<void> _tlReanchor(BuildContext ctx,
      List<QueryDocumentSnapshot<Map<String, dynamic>>> evs) async {
    final QueryDocumentSnapshot<Map<String, dynamic>>? a = _tlAnchor(evs);
    if (a == null) {
      _toast('Mark the ceremony first - open it and tap \\u201cThis is the ceremony\\u201d.');
      return;
    }
    final int was = _tlMin((a.data()['time'] ?? '16:00').toString());
    final TimeOfDay? p = await showTimePicker(
        context: ctx,
        initialTime: TimeOfDay(hour: was ~/ 60, minute: was % 60),
        helpText: 'CEREMONY TIME - EVERYTHING SHIFTS WITH IT');
    if (p == null) return;
    final int delta = p.hour * 60 + p.minute - was;
    if (delta == 0) return;
    final WriteBatch b = FirebaseFirestore.instance.batch();
    final Map<DocumentReference<Map<String, dynamic>>, String> before =
        <DocumentReference<Map<String, dynamic>>, String>{};
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in evs) {
      final String t = (d.data()['time'] ?? '').toString();
      before[d.reference] = t;
      b.set(d.reference, <String, dynamic>{
        'time': _tlHm(_tlMin(t) + delta),
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
    }
    await b.commit();
    _toastUndo(
        'Ceremony at ${_fmtClock(_tlHm(p.hour * 60 + p.minute))} - ${evs.length} moments moved ${delta > 0 ? 'later' : 'earlier'} by ${_tlDur(delta.abs())}.',
        () async {
      final WriteBatch u = FirebaseFirestore.instance.batch();
      before.forEach((DocumentReference<Map<String, dynamic>> r, String t) {
        u.set(r, <String, dynamic>{'time': t}, SetOptions(merge: true));
      });
      await u.commit();
    });
  }

  // One vendor's page: their moments first, then the whole day with theirs
  // marked. The planner (and anyone with no tag) gets the whole day plain.
  String _tlVendorHtml(List<QueryDocumentSnapshot<Map<String, dynamic>>> evs,
      List<List<String>> team, Map<String, dynamic> couple, String tag,
      String vendorName) {
    final String who = _coupleLabel(couple);
    final String when = _weddingDateLine(couple);
    final bool scoped = tag.isNotEmpty && tag != 'planner';
    final StringBuffer h = StringBuffer();
    if (scoped) {
      final List<QueryDocumentSnapshot<Map<String, dynamic>>> mine = evs
          .where((QueryDocumentSnapshot<Map<String, dynamic>> d) =>
              _tlOwners(d.data()).contains(tag))
          .toList();
      h.write('<h2>Your moments</h2>');
      if (mine.isEmpty) {
        h.write('<p style="color:#6B5F72">Nothing is marked as yours yet - the whole day is below. Tell us where you need to be and when.</p>');
      } else {
        h.write('<table>');
        for (final QueryDocumentSnapshot<Map<String, dynamic>> d in mine) {
          final Map<String, dynamic> ev = d.data();
          final String note = (ev['note'] ?? '').toString();
          h.write('<tr><td class="time">${_esc(_tlRange(ev))}</td><td><b>${_esc((ev['label'] ?? '').toString())}</b>'
              '${note.isEmpty ? '' : '<br><span style="color:#6B5F72">${_esc(note)}</span>'}</td></tr>');
        }
        h.write('</table>');
      }
      h.write('<h2>The whole day</h2>');
    }
    h.write('<table>');
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in evs) {
      final Map<String, dynamic> ev = d.data();
      final String note = (ev['note'] ?? '').toString();
      final List<String> os = _tlOwners(ev);
      final bool mine = scoped && os.contains(tag);
      h.write('<tr${mine ? ' style="background:#FBF3E4"' : ''}><td class="time">${_esc(_tlRange(ev))}</td><td><b>${_esc((ev['label'] ?? '').toString())}</b>'
          '${mine ? ' <span style="color:#8A6A2F;font-size:11px;font-weight:700">YOURS</span>' : ''}'
          '${note.isEmpty ? '' : '<br><span style="color:#6B5F72">${_esc(note)}</span>'}'
          '${os.isEmpty ? '' : '<br><span style="color:#8A6A2F;font-size:11px">${_esc(os.map(_tlOwnerLabel).join(' \\u00b7 '))}</span>'}'
          '</td></tr>');
    }
    h.write('</table>');
    if (team.isNotEmpty) {
      h.write('<h2>The team</h2><table>');
      for (final List<String> x in team) {
        h.write('<tr><td>${_esc(x[0])}</td><td><b>${_esc(x[1].isEmpty ? 'Booked' : x[1])}</b></td></tr>');
      }
      h.write('</table>');
    }
    return _printShell(
        scoped ? 'Day-of timeline for $vendorName' : 'Day-of timeline',
        <String>[if (who.isNotEmpty) who, if (when.isNotEmpty) when].join(' \\u00b7 '),
        h.toString());
  }

  String _tlVendorText(List<QueryDocumentSnapshot<Map<String, dynamic>>> evs,
      Map<String, dynamic> couple, String tag) {
    final String when = _weddingDateLine(couple);
    final bool scoped = tag.isNotEmpty && tag != 'planner';
    final StringBuffer t = StringBuffer();
    t.writeln('DAY-OF TIMELINE${when.isEmpty ? '' : ' - $when'}');
    if (scoped) {
      t.writeln('');
      t.writeln('YOUR MOMENTS');
      bool any = false;
      for (final QueryDocumentSnapshot<Map<String, dynamic>> d in evs) {
        final Map<String, dynamic> ev = d.data();
        if (!_tlOwners(ev).contains(tag)) continue;
        any = true;
        t.writeln('${_tlRange(ev)}  ${ev['label'] ?? ''}');
      }
      if (!any) t.writeln('(nothing marked yet - see the whole day)');
      t.writeln('');
      t.writeln('THE WHOLE DAY');
    } else {
      t.writeln('');
    }
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in evs) {
      final Map<String, dynamic> ev = d.data();
      final String note = (ev['note'] ?? '').toString();
      final bool mine = scoped && _tlOwners(ev).contains(tag);
      t.writeln('${_tlRange(ev)}  ${ev['label'] ?? ''}${mine ? '  [yours]' : ''}${note.isEmpty ? '' : ' - $note'}');
    }
    return t.toString();
  }
""", "editor save + timeline helpers")

# ---------------------------------------------------------------- 2. classic seed: durations + owners, website ceremony time
swap("""  Future<void> _seedClassicDay(BuildContext ctx) async {
    final TimeOfDay? cer = await showTimePicker(
        context: ctx,
        initialTime: const TimeOfDay(hour: 16, minute: 0),
        helpText: 'WHAT TIME IS THE CEREMONY?');""",
     """  Future<void> _seedClassicDay(BuildContext ctx) async {
    // JC-LAZO-COUPLE-0920-TL-001: start from the website's ceremony time.
    final TimeOfDay? cer = await showTimePicker(
        context: ctx,
        initialTime: _tlSiteCeremony() ?? const TimeOfDay(hour: 16, minute: 0),
        helpText: 'WHAT TIME IS THE CEREMONY?');""",
     "classic seed picker")

swap("""    final List<List<dynamic>> classic = <List<dynamic>>[
      <dynamic>[
        -240,
        'Hair & makeup',
        'Getting-ready photos start about an hour before you\\u2019re dressed'
      ],
      <dynamic>[
        -120,
        'Getting dressed',
        'Details: rings, invitation suite, shoes, perfume'
      ],
      <dynamic>[-90, 'First look', 'Private moment, then wedding-party photos'],
      <dynamic>[
        -30,
        'Guests arrive',
        'Ceremony music starts; wedding party tucked away'
      ],
      <dynamic>[0, 'Ceremony', ''],
      <dynamic>[
        30,
        'Cocktail hour',
        'Family photos first 20 minutes, then couple portraits at golden light'
      ],
      <dynamic>[
        90,
        'Grand entrance',
        'Into the reception - straight into the first dance'
      ],
      <dynamic>[95, 'First dance', ''],
      <dynamic>[
        105,
        'Welcome & toasts',
        'Parents\\u2019 welcome, then dinner is served'
      ],
      <dynamic>[120, 'Dinner', ''],
      <dynamic>[
        180,
        'Speeches',
        'Maid of honor, best man - 3 minutes each is plenty'
      ],
      <dynamic>[195, 'Parent dances', ''],
      <dynamic>[205, 'Cake cutting', 'Then the dance floor opens'],
      <dynamic>[210, 'Open dancing', ''],
      <dynamic>[300, 'Last dance', 'Private last dance, or everyone in'],
      <dynamic>[310, 'Send-off', 'Sparklers, bubbles, or a quiet exit'],
    ];
    final WriteBatch batch = FirebaseFirestore.instance.batch();
    for (final List<dynamic> row in classic) {
      batch.set(_dayofRef.doc(), <String, dynamic>{
        'time': hm(base + (row[0] as int)),
        'label': row[1],
        'note': row[2],
        'updatedAt': FieldValue.serverTimestamp(),
      });
    }""",
     """    // offset from the ceremony, label, note, duration, owners
    final List<List<dynamic>> classic = <List<dynamic>>[
      <dynamic>[
        -240,
        'Hair & makeup',
        'Getting-ready photos start about an hour before you\\u2019re dressed',
        120,
        <String>['party']
      ],
      <dynamic>[
        -120,
        'Getting dressed',
        'Details: rings, invitation suite, shoes, perfume',
        30,
        <String>['photo', 'video', 'party']
      ],
      <dynamic>[-90, 'First look', 'Private moment, then wedding-party photos', 45, <String>['photo', 'video']],
      <dynamic>[
        -30,
        'Guests arrive',
        'Ceremony music starts; wedding party tucked away',
        30,
        <String>['venue', 'dj', 'planner']
      ],
      <dynamic>[0, 'Ceremony', '', 30, <String>['officiant', 'photo', 'video', 'dj', 'florist']],
      <dynamic>[
        30,
        'Cocktail hour',
        'Family photos first 20 minutes, then couple portraits at golden light',
        60,
        <String>['caterer', 'photo', 'dj']
      ],
      <dynamic>[
        90,
        'Grand entrance',
        'Into the reception - straight into the first dance',
        5,
        <String>['dj', 'photo', 'video']
      ],
      <dynamic>[95, 'First dance', '', 5, <String>['dj', 'photo', 'video']],
      <dynamic>[
        105,
        'Welcome & toasts',
        'Parents\\u2019 welcome, then dinner is served',
        15,
        <String>['dj', 'caterer']
      ],
      <dynamic>[120, 'Dinner', '', 60, <String>['caterer', 'venue']],
      <dynamic>[
        180,
        'Speeches',
        'Maid of honor, best man - 3 minutes each is plenty',
        15,
        <String>['dj', 'video', 'party']
      ],
      <dynamic>[195, 'Parent dances', '', 10, <String>['dj', 'photo', 'video']],
      <dynamic>[205, 'Cake cutting', 'Then the dance floor opens', 5, <String>['cake', 'caterer', 'photo']],
      <dynamic>[210, 'Open dancing', '', 90, <String>['dj']],
      <dynamic>[300, 'Last dance', 'Private last dance, or everyone in', 5, <String>['dj', 'photo', 'video']],
      <dynamic>[310, 'Send-off', 'Sparklers, bubbles, or a quiet exit', 10, <String>['planner', 'photo', 'video', 'venue']],
    ];
    final WriteBatch batch = FirebaseFirestore.instance.batch();
    for (final List<dynamic> row in classic) {
      batch.set(_dayofRef.doc(), <String, dynamic>{
        'time': hm(base + (row[0] as int)),
        'label': row[1],
        'note': row[2],
        'dur': row[3],
        'owners': row[4],
        'anchor': (row[0] as int) == 0,
        'updatedAt': FieldValue.serverTimestamp(),
      });
    }""",
     "classic seed rows")

# The Day-Of card's starter seeded a fixed 4 pm day; it builds around the ceremony now.
swap("""                      onPressed: _h(_seedStarterTimeline),
                      icon: const Icon(Icons.auto_awesome_rounded, size: 16),
                      label: const Text('Start with a classic timeline',""",
     """                      onPressed: _h(() => _seedClassicDay(context)),
                      icon: const Icon(Icons.auto_awesome_rounded, size: 16),
                      label: const Text('Start with a classic timeline',""",
     "Day-Of card seed")

# ---------------------------------------------------------------- 3. builder: anchor chip in the header
swap("""                            Text('Day-of timeline', style: _serif(size: 26)),
                            Text(
                                evs.isEmpty
                                    ? 'Start from a classic day and adjust, or add moments one at a time.'
                                    : '${evs.length} moment${evs.length == 1 ? '' : 's'} \\u00b7 tap one to change it',
                                style: const TextStyle(
                                    fontSize: 12.5, color: muted, height: 1.4)),
                          ]),
                    ),""",
     """                            Text('Day-of timeline', style: _serif(size: 26)),
                            Text(
                                evs.isEmpty
                                    ? 'Start from a classic day and adjust, or add moments one at a time.'
                                    : '${evs.length} moment${evs.length == 1 ? '' : 's'} \\u00b7 tap one to change it',
                                style: const TextStyle(
                                    fontSize: 12.5, color: muted, height: 1.4)),
                            if (evs.isNotEmpty)
                              Padding(
                                padding: const EdgeInsets.only(top: 6),
                                child: _tlChip(
                                    _tlAnchor(evs) == null
                                        ? 'Mark the ceremony to shift the whole day'
                                        : 'Ceremony at ${_fmtClock((_tlAnchor(evs)!.data()['time'] ?? '').toString())} \\u00b7 change',
                                    _tlAnchor(evs) != null,
                                    () => _tlReanchor(ctx, evs)),
                              ),
                          ]),
                    ),""",
     "builder anchor chip")

# ---------------------------------------------------------------- 4. builder rows: range, owners, hints
swap("""                            final Map<String, dynamic> ev = evs[i].data();
                            final bool last = i == evs.length - 1;
                            return _Press(
                              onTap: () => _editTimelineEvent(evs[i]),
                              child: IntrinsicHeight(""",
     """                            final Map<String, dynamic> ev = evs[i].data();
                            final bool last = i == evs.length - 1;
                            final String hint =
                                i == 0 ? '' : _tlHint(evs[i - 1].data(), ev);
                            final bool clash = hint.startsWith('Overlaps');
                            return _Press(
                              onTap: () => _editTimelineEvent(evs[i]),
                              child: IntrinsicHeight(""",
     "builder row hint state")

swap("""                                          child: Text(
                                              _fmtClock((ev['time'] ?? '')
                                                  .toString()),
                                              style: const TextStyle(
                                                  color: plum,
                                                  fontSize: 13,
                                                  fontWeight: FontWeight.w800)),
                                        ),
                                      ),""",
     """                                          child: Text(_tlRange(ev),
                                              style: TextStyle(
                                                  color: clash ? rose : plum,
                                                  fontSize: 12,
                                                  height: 1.25,
                                                  fontWeight: FontWeight.w800)),
                                        ),
                                      ),""",
     "builder row time")

swap("""                                                if ((ev['note'] ?? '')
                                                    .toString()
                                                    .isNotEmpty)
                                                  Text(
                                                      (ev['note'] ?? '')
                                                          .toString(),
                                                      style: const TextStyle(
                                                          fontSize: 12.5,
                                                          color: muted,
                                                          height: 1.35)),
                                              ]),
                                        ),
                                      ),
                                      IconButton(""",
     """                                                if ((ev['note'] ?? '')
                                                    .toString()
                                                    .isNotEmpty)
                                                  Text(
                                                      (ev['note'] ?? '')
                                                          .toString(),
                                                      style: const TextStyle(
                                                          fontSize: 12.5,
                                                          color: muted,
                                                          height: 1.35)),
                                                _tlOwnerRow(ev),
                                                if (hint.isNotEmpty)
                                                  Padding(
                                                    padding:
                                                        const EdgeInsets.only(
                                                            top: 4),
                                                    child: Text(hint,
                                                        style: TextStyle(
                                                            fontSize: 11,
                                                            color: clash
                                                                ? rose
                                                                : const Color(
                                                                    0xFF8A6A2F),
                                                            fontWeight:
                                                                FontWeight
                                                                    .w700)),
                                                  ),
                                              ]),
                                        ),
                                      ),
                                      IconButton(""",
     "builder row owners + hint")

# ---------------------------------------------------------------- 5. Day-Of card rows: range + owners
swap("""                                  child: Text(
                                      _fmtClock(
                                          (ev['time'] ?? '12:00').toString()),
                                      textAlign: TextAlign.center,
                                      style: const TextStyle(
                                          color: Color(0xFF8A6A2F),
                                          fontSize: 11,
                                          fontWeight: FontWeight.w800)),
                                ),""",
     """                                  child: Text(
                                      _fmtClock(
                                          (ev['time'] ?? '12:00').toString()),
                                      textAlign: TextAlign.center,
                                      style: const TextStyle(
                                          color: Color(0xFF8A6A2F),
                                          fontSize: 11,
                                          fontWeight: FontWeight.w800)),
                                ),""",
     "Day-Of card time (unchanged anchor check)")

swap("""                                        if (((ev['note'] ?? '').toString())
                                            .isNotEmpty)
                                          Text((ev['note'] ?? '').toString(),
                                              style: const TextStyle(
                                                  fontSize: 11, color: muted)),
                                      ]),
                                ),
                              ]),
                        ),
                      );
                    }),""",
     """                                        if (((ev['note'] ?? '').toString())
                                            .isNotEmpty)
                                          Text((ev['note'] ?? '').toString(),
                                              style: const TextStyle(
                                                  fontSize: 11, color: muted)),
                                        if (ev['dur'] is num &&
                                            (ev['dur'] as num) > 0)
                                          Text(
                                              '${_tlDur((ev['dur'] as num).toInt())} \\u00b7 until ${_fmtClock(_tlHm(_tlMin((ev['time'] ?? '12:00').toString()) + (ev['dur'] as num).toInt()))}',
                                              style: const TextStyle(
                                                  fontSize: 10.5,
                                                  color: Color(0xFF8A6A2F),
                                                  fontWeight: FontWeight.w700)),
                                        _tlOwnerRow(ev, size: 9),
                                      ]),
                                ),
                              ]),
                        ),
                      );
                    }),""",
     "Day-Of card rows")

# ---------------------------------------------------------------- 6. per-vendor sends
swap("""  Future<void> _sendToVendors({
    required String kind,
    required String title,
    required String fileName,
    required String page,
    required String text,
    required List<String> tags,
    String note = '',
    String preview = '',
  }) async {""",
     """  Future<void> _sendToVendors({
    required String kind,
    required String title,
    required String fileName,
    required String page,
    required String text,
    required List<String> tags,
    String note = '',
    String preview = '',
    // JC-LAZO-COUPLE-0920-TL-001: a page and text built for one vendor
    // (their role's moments first). Null keeps one page for everyone.
    String Function(Map<String, dynamic> vendor)? pageFor,
    String Function(Map<String, dynamic> vendor)? textFor,
  }) async {""",
     "sendToVendors signature")

swap("""                                  final bool ok = await _sendArtifact(
                                      v['id'].toString(),
                                      fileName,
                                      page,
                                      noteC.text.trim(),
                                      text,
                                      title);""",
     """                                  final bool ok = await _sendArtifact(
                                      v['id'].toString(),
                                      fileName,
                                      pageFor == null ? page : pageFor(v),
                                      noteC.text.trim(),
                                      textFor == null ? text : textFor(v),
                                      title);""",
     "sendToVendors per-vendor page")

swap("""    await _sendToVendors(
      kind: 'timeline',
      title: 'day-of timeline',
      fileName: 'Day-of timeline.html',
      page: _printShell(
          'Day-of timeline',
          <String>[if (who.isNotEmpty) who, if (when.isNotEmpty) when]
              .join(' \\u00b7 '),
          h.toString()),
      text: t.toString(),
      tags: <String>[],
      note:
          'Here\\u2019s our day-of timeline as it stands. Tell us if any of your times need to shift.',""",
     """    await _sendToVendors(
      kind: 'timeline',
      title: 'day-of timeline',
      fileName: 'Day-of timeline.html',
      page: _printShell(
          'Day-of timeline',
          <String>[if (who.isNotEmpty) who, if (when.isNotEmpty) when]
              .join(' \\u00b7 '),
          h.toString()),
      text: t.toString(),
      tags: <String>[],
      // JC-LAZO-COUPLE-0920-TL-001: each vendor's page opens with their moments.
      pageFor: (Map<String, dynamic> v) => _tlVendorHtml(
          evs, team, couple, (v['tag'] ?? '').toString(), v['name'].toString()),
      textFor: (Map<String, dynamic> v) =>
          _tlVendorText(evs, couple, (v['tag'] ?? '').toString()),
      note:
          'Here\\u2019s our day-of timeline as it stands - your moments are at the top. Tell us if any of your times need to shift.',""",
     "timeline send per vendor")

# the shared (non-vendor) timeline page and text show ranges too
swap("""      final String clock = _fmtClock((ev['time'] ?? '').toString());
      final String label = (ev['label'] ?? '').toString();
      final String note = (ev['note'] ?? '').toString();
      t.writeln('$clock  $label${note.isEmpty ? '' : ' - $note'}');""",
     """      final String clock = _tlRange(ev);
      final String label = (ev['label'] ?? '').toString();
      final String note = (ev['note'] ?? '').toString();
      t.writeln('$clock  $label${note.isEmpty ? '' : ' - $note'}');""",
     "shared timeline ranges")

# ---------------------------------------------------------------- 6b. the overlap colour (the page had no rose)
swap("  static const Color goldLine = Color(0xFFE6D6B8);\n",
     "  static const Color goldLine = Color(0xFFE6D6B8);\n"
     "  static const Color rose = Color(0xFFB04343); // JC-LAZO-COUPLE-0920-TL-001: overlaps\n",
     "rose colour")

# ---------------------------------------------------------------- 7. header history line
swap("// (v130.1: the view switch",
     "// (v131: THE TIMELINE, ANCHORED - every moment can carry a duration and owners (planner, photo, video, DJ, caterer, venue, florist, officiant, cake, wedding party) set with chips in the editor; the ceremony is the anchor - tap 'Ceremony at 4:00 PM' in the builder, pick a new time, and every moment shifts with it (undo in the toast); the classic day seeds with durations and owners and starts its picker from the website's ceremony time, and the Day-Of card's starter builds around the ceremony instead of a fixed 4 pm day; rows show ranges, owner chips and a hint between moments (overlap in rose, long gaps); Send to vendors builds one page per vendor - their moments first, then the whole day with theirs marked - through the same send sheet. JC-LAZO-COUPLE-0920-TL-001; base v130.1) (v130.1: the view switch",
     "header")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT} ({len(s):,} chars)")
