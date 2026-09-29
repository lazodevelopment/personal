"""patch_couple_v138.py - JC-LAZO-COUPLE-0929-V138
More for the site, from the dashboard:
  1. THE DAY-BEFORE NOTE. Live links gains "Send the day-before note": a sheet
     with a line in the couple's words, "Send a test to me", then Send to
     everyone (RSVP yes + guests marked attending, with an email). The worker
     builds the email (timeline, venue + map, parking, forecast, each guest's
     table) and sends through Resend; the call is signed with the partner's
     Firebase ID token (worker JC-LAZO-WORKER-0929-DAYB4-001).
  2. THE HOLD. "Approve photos before they show" (weddingSites.guestPhotosHold);
     the Manage sheet gains Waiting for approval - approve or decline each -
     and "Download all as a zip".
  3. THE WEEKEND. An events editor (name, date, time, venue, address, note,
     dress, ask on the RSVP) -> weddingSites.events; RSVP import keeps the
     events a guest picked; the guest row shows them.
  4. THE HOTEL. hotelAddress in the editor -> "Directions to the hotel".
  5. THE TABLE MAP. The seating mirror now carries the tables and the canvas,
     so the site can draw the room around the guest's table.
Applies on top of Couple_master_v137.txt -> Couple_master_v138.txt.
  python app-patches\\patch_couple_v138.py [src] [out]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v137.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "Couple_master_v138.txt"
s = SRC.read_text(encoding="utf-8")
if "JC-LAZO-COUPLE-0929-V138" in s:
    raise SystemExit("already applied")


def swap(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"ABORT [{label}]: anchor matched {n} times, expected {count}")
    s = s.replace(old, new)
    print(f"  ok  {label}")


swap("// (v137: THE SITE, LIVE",
     "// (v138: MORE FOR THE SITE - Send the day-before note (test to me, then everyone with an email; the worker builds it with the timeline, venue, parking, forecast and each guest's table, signed with the partner's ID token); Approve photos before they show (guestPhotosHold) with a Waiting-for-approval list in Manage and Download all as a zip; The weekend - an events editor (weddingSites.events) with per-event RSVP that import keeps; hotel address for directions; the seating mirror carries tables + canvas for the table map. JC-LAZO-COUPLE-0929-V138; base v137)\n// (v137: THE SITE, LIVE",
     "header")

# ---------------------------------------------------------------- 1. helpers
swap("""  // ---- v137: the site, live ----
  static const List<String> _tlVendorWords = <String>[
""", r'''  // ---- v138: signed calls to the worker (the partner's Firebase ID token) ----
  Future<Map<String, String>> _authHeaders() async {
    final String? t = await FirebaseAuth.instance.currentUser?.getIdToken();
    return <String, String>{
      'content-type': 'application/json',
      if (t != null && t.isNotEmpty) 'authorization': 'Bearer $t',
    };
  }

  Future<Map<String, dynamic>> _workerPost(
      String url, Map<String, dynamic> body) async {
    try {
      final httpc.Response r = await httpc
          .post(Uri.parse(url),
              headers: await _authHeaders(), body: jsonEncode(body))
          .timeout(const Duration(seconds: 90));
      final dynamic j = jsonDecode(r.body);
      if (j is Map) {
        return Map<String, dynamic>.from(j)..['_status'] = r.statusCode;
      }
    } catch (_) {}
    return <String, dynamic>{'ok': false, 'error': 'network'};
  }

  Future<Map<String, dynamic>> _workerGet(String url) async {
    try {
      final httpc.Response r = await httpc
          .get(Uri.parse(url), headers: await _authHeaders())
          .timeout(const Duration(seconds: 30));
      final dynamic j = jsonDecode(r.body);
      if (j is Map) {
        return Map<String, dynamic>.from(j);
      }
    } catch (_) {}
    return <String, dynamic>{'ok': false};
  }

  Future<void> _dayBeforeSheet(String slug, Map<String, dynamic> w) async {
    final TextEditingController noteC = TextEditingController(
        text: (w['dayBeforeNote'] ?? '').toString().isNotEmpty
            ? (w['dayBeforeNote'] ?? '').toString()
            : 'We can’t wait to see you tomorrow. Here’s everything you need for the day.');
    bool busy = false;
    String status = w['dayBeforeSentAt'] != null
        ? 'Sent once already to ${w['dayBeforeSentTo'] ?? '?'} guests.'
        : '';
    if (!mounted) {
      return;
    }
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: ivory,
      constraints: const BoxConstraints(maxWidth: 620),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          Future<void> send(bool test) async {
            setD(() => busy = true);
            final Map<String, dynamic> r = await _workerPost(
                'https://meetlazo.com/api/w/$slug/day-before', <String, dynamic>{
              'test': test,
              'note': noteC.text.trim(),
              'replyTo': FirebaseAuth.instance.currentUser?.email ?? '',
            });
            try {
              await FirebaseFirestore.instance
                  .collection('weddingSites')
                  .doc(slug)
                  .set(<String, dynamic>{'dayBeforeNote': noteC.text.trim()},
                      SetOptions(merge: true));
            } catch (_) {}
            setD(() {
              busy = false;
              status = r['ok'] == true
                  ? (test
                      ? 'Test sent to ${FirebaseAuth.instance.currentUser?.email ?? 'you'} ✓'
                      : 'Sent to ${r['sent']} guest${r['sent'] == 1 ? '' : 's'}${(r['failed'] ?? 0) != 0 ? ' (${r['failed']} failed)' : ''} ✓')
                  : (r['message'] ?? 'Could not send — ${r['error'] ?? 'try again'}.')
                      .toString();
            });
          }

          return Padding(
            padding: EdgeInsets.fromLTRB(
                20, 14, 20, 20 + MediaQuery.of(ctx2).viewInsets.bottom),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Center(
                  child: Container(
                      width: 40,
                      height: 4,
                      decoration: BoxDecoration(
                          color: plum.withOpacity(.25),
                          borderRadius: BorderRadius.circular(4))),
                ),
                const SizedBox(height: 14),
                Text('The day-before note',
                    style:
                        _serif(size: 24, weight: FontWeight.w600, color: plum)),
                const SizedBox(height: 4),
                const Text(
                    'One email to everyone coming who left an address: your line, the day hour by hour, the venue with a map, parking, the forecast, and each guest’s table if the seat finder is on. Replies come to you.',
                    style:
                        TextStyle(color: muted, fontSize: 13.5, height: 1.4)),
                const SizedBox(height: 14),
                TextField(
                    controller: noteC,
                    maxLines: 3,
                    maxLength: 600,
                    style: const TextStyle(color: ink, fontSize: 14),
                    decoration: _lightDeco('A line from the two of you')),
                const SizedBox(height: 6),
                if (status.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(status,
                        style: const TextStyle(
                            color: plum,
                            fontSize: 13,
                            fontWeight: FontWeight.w600)),
                  ),
                Row(children: <Widget>[
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                        foregroundColor: plum,
                        side: BorderSide(color: gold.withOpacity(.8))),
                    onPressed: _h(busy ? null : () => send(true)),
                    icon: const Icon(Icons.send_rounded, size: 15),
                    label: const Text('Send a test to me'),
                  ),
                  const Spacer(),
                  FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: gold, foregroundColor: plumDeep),
                    onPressed: _h(
                        busy
                            ? null
                            : () async {
                                final bool? sure = await showDialog<bool>(
                                  context: ctx2,
                                  builder: (BuildContext dc) => AlertDialog(
                                    backgroundColor: ivory,
                                    title: const Text('Send to everyone?',
                                        style: TextStyle(color: plum)),
                                    content: const Text(
                                        'Every guest who is coming and left an email gets it now.',
                                        style: TextStyle(
                                            color: ink, fontSize: 14)),
                                    actions: <Widget>[
                                      TextButton(
                                          onPressed: () =>
                                              Navigator.pop(dc, false),
                                          child: const Text('Not yet',
                                              style:
                                                  TextStyle(color: ink))),
                                      FilledButton(
                                          style: FilledButton.styleFrom(
                                              backgroundColor: gold,
                                              foregroundColor: plumDeep),
                                          onPressed: () =>
                                              Navigator.pop(dc, true),
                                          child: const Text('Send')),
                                    ],
                                  ),
                                );
                                if (sure == true) {
                                  await send(false);
                                }
                              },
                        _Tick.medium),
                    child: Text(busy ? 'Sending…' : 'Send to everyone',
                        style: const TextStyle(fontWeight: FontWeight.w700)),
                  ),
                ]),
              ],
            ),
          );
        },
      ),
    );
  }

  // the photos guests sent while the hold is on: approve or decline each
  Future<void> _pendingPhotosSheet(String slug) async {
    Map<String, dynamic> j = await _workerGet(
        'https://meetlazo.com/api/w/$slug/photos?pending=1&t=${DateTime.now().millisecondsSinceEpoch}');
    List<Map<String, dynamic>> list = ((j['photos'] as List?) ?? const <dynamic>[])
        .whereType<Map>()
        .map((Map e) => Map<String, dynamic>.from(e))
        .toList();
    if (!mounted) {
      return;
    }
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: ivory,
      constraints: const BoxConstraints(maxWidth: 720),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          Future<void> act(List<String> ids, bool decline) async {
            final Map<String, dynamic> r = await _workerPost(
                'https://meetlazo.com/api/w/$slug/photos/approve',
                <String, dynamic>{'ids': ids, 'decline': decline});
            if (r['ok'] == true) {
              setD(() => list.removeWhere(
                  (Map<String, dynamic> p) => ids.contains(p['id'])));
              _gpFuture = null;
              _toastC(decline
                  ? 'Declined ✓'
                  : 'On the wall ✓');
            } else {
              _toastC('Could not do that — try again.');
            }
          }

          return Padding(
            padding: const EdgeInsets.fromLTRB(20, 14, 20, 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Center(
                  child: Container(
                      width: 40,
                      height: 4,
                      decoration: BoxDecoration(
                          color: plum.withOpacity(.25),
                          borderRadius: BorderRadius.circular(4))),
                ),
                const SizedBox(height: 14),
                Row(children: <Widget>[
                  Expanded(
                      child: Text('Waiting for approval',
                          style: _serif(
                              size: 24,
                              weight: FontWeight.w600,
                              color: plum))),
                  if (list.isNotEmpty)
                    TextButton(
                        onPressed: _h(() => act(
                            list
                                .map((Map<String, dynamic> p) =>
                                    (p['id'] ?? '').toString())
                                .toList(),
                            false)),
                        child: const Text('Approve all',
                            style: TextStyle(
                                color: plum, fontWeight: FontWeight.w700))),
                ]),
                Text(
                    list.isEmpty
                        ? 'Nothing waiting. Photos guests send show up here first while the hold is on.'
                        : '${list.length} photo${list.length == 1 ? '' : 's'} — tap ✓ to put it on the wall, ✕ to decline.',
                    style: const TextStyle(
                        color: muted, fontSize: 13.5, height: 1.4)),
                const SizedBox(height: 12),
                Flexible(
                  child: list.isEmpty
                      ? const SizedBox(height: 30)
                      : GridView.builder(
                          shrinkWrap: true,
                          gridDelegate:
                              const SliverGridDelegateWithMaxCrossAxisExtent(
                                  maxCrossAxisExtent: 140,
                                  mainAxisSpacing: 8,
                                  crossAxisSpacing: 8),
                          itemCount: list.length,
                          itemBuilder: (BuildContext gc, int i) {
                            final Map<String, dynamic> p = list[i];
                            final String u = (p['url'] ?? '').toString();
                            final String id = (p['id'] ?? '').toString();
                            return ClipRRect(
                              borderRadius: BorderRadius.circular(12),
                              child: Stack(
                                  fit: StackFit.expand,
                                  children: <Widget>[
                                    GestureDetector(
                                      onTap: () => _openLink(u),
                                      child: Image.network(u,
                                          fit: BoxFit.cover,
                                          errorBuilder: (BuildContext c5,
                                                  Object e, StackTrace? st) =>
                                              Container(
                                                  color: gold.withOpacity(.08))),
                                    ),
                                    Positioned(
                                      left: 0,
                                      right: 0,
                                      bottom: 0,
                                      child: Container(
                                        color: plumDeep.withOpacity(.65),
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 4, vertical: 2),
                                        child: Row(children: <Widget>[
                                          Expanded(
                                            child: Text(
                                                (p['name'] ?? '').toString(),
                                                maxLines: 1,
                                                overflow: TextOverflow.ellipsis,
                                                style: const TextStyle(
                                                    color: ivory,
                                                    fontSize: 10)),
                                          ),
                                          IconButton(
                                              padding: EdgeInsets.zero,
                                              constraints:
                                                  const BoxConstraints(),
                                              onPressed: _h(() =>
                                                  act(<String>[id], true)),
                                              icon: const Icon(
                                                  Icons.close_rounded,
                                                  color: ivory,
                                                  size: 18)),
                                          const SizedBox(width: 6),
                                          IconButton(
                                              padding: EdgeInsets.zero,
                                              constraints:
                                                  const BoxConstraints(),
                                              onPressed: _h(() =>
                                                  act(<String>[id], false)),
                                              icon: const Icon(
                                                  Icons.check_rounded,
                                                  color: gold,
                                                  size: 20)),
                                        ]),
                                      ),
                                    ),
                                  ]),
                            );
                          },
                        ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  // ---- v137: the site, live ----
  static const List<String> _tlVendorWords = <String>[
''', "helpers")

# ---------------------------------------------------------------- 2. seating mirror carries the room
swap("""      await ref.set(<String, dynamic>{
        'guests': rows,
        'updatedAt': FieldValue.serverTimestamp(),
      });
    } catch (_) {}
  }
""", """      // v138: the room, so the site can draw the guest's table on a map
      final List<Map<String, dynamic>> tables = <Map<String, dynamic>>[];
      Map<String, dynamic> canvas = <String, dynamic>{'w': 1600, 'h': 1000};
      try {
        final DocumentSnapshot<Map<String, dynamic>> lay =
            await _coupleRef.collection('seating').doc('main').get();
        final Map<String, dynamic> ld = lay.data() ?? <String, dynamic>{};
        if (ld['canvas'] is Map) {
          canvas = Map<String, dynamic>.from(ld['canvas'] as Map);
        }
        for (final dynamic t in (ld['tables'] as List?) ?? const <dynamic>[]) {
          if (t is! Map) {
            continue;
          }
          tables.add(<String, dynamic>{
            'n': (t['name'] ?? '').toString(),
            'x': t['x'] is num ? (t['x'] as num).toDouble() : 0,
            'y': t['y'] is num ? (t['y'] as num).toDouble() : 0,
            'sh': (t['shape'] ?? 'round').toString(),
            'r': t['rotation'] is num ? (t['rotation'] as num).toDouble() : 0,
            's': t['seats'] is num ? (t['seats'] as num).toInt() : 8,
          });
        }
      } catch (_) {}
      await ref.set(<String, dynamic>{
        'guests': rows,
        'tables': tables,
        'canvas': canvas,
        'updatedAt': FieldValue.serverTimestamp(),
      });
    } catch (_) {}
  }
""", "seating mirror tables")

# ---------------------------------------------------------------- 3. live links: day-before
swap("""          row(Icons.tv_rounded, 'Slideshow for a TV',
""", """          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(children: <Widget>[
              const Icon(Icons.mark_email_read_outlined, color: plum, size: 18),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      const Text('The day-before note',
                          style: TextStyle(
                              color: plum,
                              fontSize: 13.5,
                              fontWeight: FontWeight.w700)),
                      Text(
                          w['dayBeforeSentAt'] != null
                              ? 'Sent to ${w['dayBeforeSentTo'] ?? '?'} guests'
                              : 'Timeline, map, parking, forecast, their table',
                          style: const TextStyle(fontSize: 11.5, color: muted)),
                    ]),
              ),
              FilledButton(
                  style: FilledButton.styleFrom(
                      backgroundColor: plum,
                      foregroundColor: ivory,
                      padding: const EdgeInsets.symmetric(horizontal: 14)),
                  onPressed: _h(() => _dayBeforeSheet(slug, w)),
                  child: const Text('Write it',
                      style: TextStyle(fontSize: 12.5))),
            ]),
          ),
          row(Icons.tv_rounded, 'Slideshow for a TV',
""", "live links day-before row")

# ---------------------------------------------------------------- 4. manage sheet: pending + zip
swap("""                  IconButton(
                    tooltip: 'Refresh',
                    onPressed: _h(() async {
                      final List<Map<String, dynamic>> l =
                          await _guestPhotos(slug, fresh: true);
                      setD(() => list = l);
                    }),
                    icon: const Icon(Icons.refresh_rounded, color: plum),
                  ),
                ]),
""", """                  TextButton.icon(
                    onPressed: _h(() => _pendingPhotosSheet(slug)),
                    icon: const Icon(Icons.pending_actions_rounded,
                        color: plum, size: 18),
                    label: const Text('Waiting',
                        style: TextStyle(
                            color: plum, fontWeight: FontWeight.w700)),
                  ),
                  IconButton(
                    tooltip: 'Refresh',
                    onPressed: _h(() async {
                      final List<Map<String, dynamic>> l =
                          await _guestPhotos(slug, fresh: true);
                      setD(() => list = l);
                    }),
                    icon: const Icon(Icons.refresh_rounded, color: plum),
                  ),
                ]),
""", "manage sheet pending button")
swap("""                    icon: const Icon(Icons.link_rounded, color: plum, size: 18),
                    label: const Text('Copy all links',
                        style: TextStyle(color: plum)),
                  ),
                  const Spacer(),
""", """                    icon: const Icon(Icons.link_rounded, color: plum, size: 18),
                    label: const Text('Copy all links',
                        style: TextStyle(color: plum)),
                  ),
                  TextButton.icon(
                    onPressed: _h(list.isEmpty
                        ? null
                        : () => _openLink(
                            'https://meetlazo.com/w/$slug/photos/download')),
                    icon: const Icon(Icons.download_rounded,
                        color: plum, size: 18),
                    label: const Text('Zip', style: TextStyle(color: plum)),
                  ),
                  const Spacer(),
""", "manage sheet zip")

# ---------------------------------------------------------------- 5. editor state
swap("""    final TextEditingController galleryC =
        TextEditingController(text: (w['galleryUrl'] ?? '').toString());
""", """    final TextEditingController galleryC =
        TextEditingController(text: (w['galleryUrl'] ?? '').toString());
    // v138: the hold, the hotel, the weekend
    bool guestHold = w['guestPhotosHold'] == true;
    final TextEditingController hotelAddrC =
        TextEditingController(text: (w['hotelAddress'] ?? '').toString());
    final List<Map<String, dynamic>> events = <Map<String, dynamic>>[
      for (final dynamic e in (w['events'] as List?) ?? const <dynamic>[])
        if (e is Map) Map<String, dynamic>.from(e)
    ];
""", "editor state")

# ---------------------------------------------------------------- 6. editor UI: hold + hotel + events
swap("""                            title: const Text('Let guests add photos',
                                style: TextStyle(fontSize: 13.5)),
                            value: guestOn,
                            onChanged:
                                _hb((bool v) => setD(() => guestOn = v)),
                          ),
""", """                            title: const Text('Let guests add photos',
                                style: TextStyle(fontSize: 13.5)),
                            value: guestOn,
                            onChanged:
                                _hb((bool v) => setD(() => guestOn = v)),
                          ),
                          if (guestOn)
                            SwitchListTile(
                              dense: true,
                              contentPadding: EdgeInsets.zero,
                              activeColor: Colors.white,
                              activeTrackColor: vGreen,
                              inactiveThumbColor: Colors.white,
                              inactiveTrackColor: muted.withOpacity(.4),
                              title: const Text(
                                  'Approve photos before they show',
                                  style: TextStyle(fontSize: 13.5)),
                              subtitle: const Text(
                                  'They wait under Manage › Waiting until you say yes',
                                  style: TextStyle(fontSize: 11, color: muted)),
                              value: guestHold,
                              onChanged:
                                  _hb((bool v) => setD(() => guestHold = v)),
                            ),
""", "editor hold switch")
swap("""                          _wbSection('LIVE ON THE DAY'),
""", """                          _wbSection('THE WEEKEND'),
                          const Padding(
                            padding: EdgeInsets.only(bottom: 8),
                            child: Text(
                                'More than one day? Add each event — welcome dinner, mehndi, sangeet, brunch — with its own place and time. Guests can say which they’ll join.',
                                style: TextStyle(fontSize: 11.5, color: muted)),
                          ),
                          ...events.asMap().entries.map(
                              (MapEntry<int, Map<String, dynamic>> en) =>
                                  Padding(
                                    padding: const EdgeInsets.only(bottom: 8),
                                    child: _Press(
                                      tick: _Tick.select,
                                      onTap: () async {
                                        final Map<String, dynamic>? r =
                                            await _eventEditor(
                                                ctx2, en.value);
                                        if (r == null) {
                                          return;
                                        }
                                        setD(() {
                                          if (r['_delete'] == true) {
                                            events.removeAt(en.key);
                                          } else {
                                            events[en.key] = r;
                                          }
                                        });
                                      },
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 12, vertical: 10),
                                        decoration: BoxDecoration(
                                          color: Colors.white,
                                          borderRadius:
                                              BorderRadius.circular(12),
                                          border: Border.all(
                                              color: gold.withOpacity(.5)),
                                        ),
                                        child: Row(children: <Widget>[
                                          const Icon(Icons.event_rounded,
                                              color: plum, size: 18),
                                          const SizedBox(width: 10),
                                          Expanded(
                                            child: Column(
                                                crossAxisAlignment:
                                                    CrossAxisAlignment.start,
                                                children: <Widget>[
                                                  Text(
                                                      (en.value['name'] ?? '')
                                                          .toString(),
                                                      style: const TextStyle(
                                                          color: plum,
                                                          fontSize: 13.5,
                                                          fontWeight:
                                                              FontWeight.w700)),
                                                  Text(
                                                      <String>[
                                                        (en.value['dateIso'] ??
                                                                '')
                                                            .toString(),
                                                        (en.value['time'] ?? '')
                                                            .toString(),
                                                        (en.value['venueName'] ??
                                                                '')
                                                            .toString(),
                                                        if (en.value['rsvp'] ==
                                                            true)
                                                          'asks on the RSVP',
                                                      ]
                                                          .where((String x) =>
                                                              x.isNotEmpty)
                                                          .join(' \\u00b7 '),
                                                      style: const TextStyle(
                                                          fontSize: 11,
                                                          color: muted)),
                                                ]),
                                          ),
                                          const Icon(Icons.edit_outlined,
                                              color: muted, size: 16),
                                        ]),
                                      ),
                                    ),
                                  )),
                          if (events.length < 12)
                            OutlinedButton.icon(
                              style: OutlinedButton.styleFrom(
                                  foregroundColor: plum,
                                  side: BorderSide(color: gold.withOpacity(.8))),
                              onPressed: _h(() async {
                                final Map<String, dynamic>? r =
                                    await _eventEditor(ctx2, null);
                                if (r != null && r['_delete'] != true) {
                                  setD(() => events.add(r));
                                }
                              }),
                              icon: const Icon(Icons.add_rounded, size: 16),
                              label: const Text('Add an event'),
                            ),
                          const SizedBox(height: 8),
                          TextField(
                              controller: hotelAddrC,
                              style: const TextStyle(color: ink, fontSize: 14),
                              decoration: _lightDeco(
                                  'Hotel address (for directions)',
                                  hint: '120 Main St, Sedona, AZ')),
                          _wbSection('LIVE ON THE DAY'),
""", "editor events + hotel")

# ---------------------------------------------------------------- 7. save
swap("""        'guestPhotosOn': guestOn,
        'guestPhotosNote': guestNoteC.text.trim(),
""", """        'guestPhotosOn': guestOn,
        'guestPhotosNote': guestNoteC.text.trim(),
        'guestPhotosHold': guestHold,
        'hotelAddress': hotelAddrC.text.trim(),
        'events': events,
""", "save fields")

# ---------------------------------------------------------------- 8. the event editor (a dialog)
swap("""  Future<void> _mirrorSeating(String slug, bool on) async {
""", r'''  // v138: one event of the weekend. Returns the map, {'_delete': true}, or null.
  Future<Map<String, dynamic>?> _eventEditor(
      BuildContext ctx, Map<String, dynamic>? cur) async {
    final Map<String, dynamic> c = cur ?? <String, dynamic>{};
    final TextEditingController nameC =
        TextEditingController(text: (c['name'] ?? '').toString());
    final TextEditingController dateC =
        TextEditingController(text: (c['dateIso'] ?? '').toString());
    final TextEditingController timeC =
        TextEditingController(text: (c['time'] ?? '').toString());
    final TextEditingController venC =
        TextEditingController(text: (c['venueName'] ?? '').toString());
    final TextEditingController addrC =
        TextEditingController(text: (c['venueAddress'] ?? '').toString());
    final TextEditingController noteC =
        TextEditingController(text: (c['note'] ?? '').toString());
    final TextEditingController dressC =
        TextEditingController(text: (c['dress'] ?? '').toString());
    bool ask = c['rsvp'] == true;
    final String? act = await showDialog<String>(
      context: ctx,
      builder: (BuildContext dc) => StatefulBuilder(
        builder: (BuildContext dc2, StateSetter setE) => AlertDialog(
          backgroundColor: ivory,
          title: Text(cur == null ? 'Add an event' : 'Edit event',
              style: const TextStyle(color: plum)),
          content: SizedBox(
            width: 420,
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
                TextField(
                    controller: nameC,
                    textCapitalization: TextCapitalization.words,
                    style: const TextStyle(color: ink, fontSize: 14),
                    decoration: _lightDeco('Event', hint: 'Welcome dinner')),
                const SizedBox(height: 10),
                Row(children: <Widget>[
                  Expanded(
                    child: TextField(
                        controller: dateC,
                        readOnly: true,
                        style: const TextStyle(color: ink, fontSize: 14),
                        decoration: _lightDeco('Date', hint: 'Tap to pick'),
                        onTap: () async {
                          final DateTime? d = await showDatePicker(
                              context: dc2,
                              initialDate: DateTime.tryParse(dateC.text) ??
                                  DateTime.now(),
                              firstDate: DateTime(2020),
                              lastDate: DateTime(2040));
                          if (d != null) {
                            setE(() => dateC.text =
                                '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}');
                          }
                        }),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                        controller: timeC,
                        style: const TextStyle(color: ink, fontSize: 14),
                        decoration: _lightDeco('Time', hint: '6:30 PM')),
                  ),
                ]),
                const SizedBox(height: 10),
                TextField(
                    controller: venC,
                    style: const TextStyle(color: ink, fontSize: 14),
                    decoration: _lightDeco('Place')),
                const SizedBox(height: 10),
                TextField(
                    controller: addrC,
                    style: const TextStyle(color: ink, fontSize: 14),
                    decoration: _lightDeco('Address')),
                const SizedBox(height: 10),
                TextField(
                    controller: dressC,
                    style: const TextStyle(color: ink, fontSize: 14),
                    decoration: _lightDeco('Dress (optional)')),
                const SizedBox(height: 10),
                TextField(
                    controller: noteC,
                    maxLines: 2,
                    style: const TextStyle(color: ink, fontSize: 14),
                    decoration: _lightDeco('A line for guests (optional)')),
                SwitchListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  activeColor: Colors.white,
                  activeTrackColor: vGreen,
                  inactiveThumbColor: Colors.white,
                  inactiveTrackColor: muted.withOpacity(.4),
                  title: const Text('Ask on the RSVP who’s joining',
                      style: TextStyle(fontSize: 13.5)),
                  value: ask,
                  onChanged: _hb((bool v) => setE(() => ask = v)),
                ),
              ]),
            ),
          ),
          actions: <Widget>[
            if (cur != null)
              TextButton(
                  onPressed: _h(() => Navigator.pop(dc2, 'delete')),
                  child: const Text('Remove',
                      style: TextStyle(color: Color(0xFF8A7D90)))),
            TextButton(
                onPressed: _h(() => Navigator.pop(dc2, null)),
                child: const Text('Cancel', style: TextStyle(color: ink))),
            FilledButton(
                style: FilledButton.styleFrom(
                    backgroundColor: gold, foregroundColor: plum),
                onPressed: _h(() => Navigator.pop(dc2, 'save')),
                child: const Text('Save')),
          ],
        ),
      ),
    );
    if (act == 'delete') {
      return <String, dynamic>{'_delete': true};
    }
    if (act != 'save' || nameC.text.trim().isEmpty) {
      return null;
    }
    return <String, dynamic>{
      'name': nameC.text.trim(),
      'dateIso': dateC.text.trim(),
      'time': timeC.text.trim(),
      'venueName': venC.text.trim(),
      'venueAddress': addrC.text.trim(),
      'note': noteC.text.trim(),
      'dress': dressC.text.trim(),
      'rsvp': ask,
    };
  }

  Future<void> _mirrorSeating(String slug, bool on) async {
''', "event editor")

# ---------------------------------------------------------------- 9. import keeps events; row shows them
swap("""      if ((r['song'] ?? '').toString().trim().isNotEmpty)
        'song': (r['song'] ?? '').toString().trim(),
      'updatedAt': FieldValue.serverTimestamp(),
    };
""", """      if ((r['song'] ?? '').toString().trim().isNotEmpty)
        'song': (r['song'] ?? '').toString().trim(),
      if (r['events'] is List)
        'events': List<String>.from(
            (r['events'] as List).map((dynamic e) => e.toString())),
      'updatedAt': FieldValue.serverTimestamp(),
    };
""", "import keeps events")
swap("""      if (g['thankYouAt'] != null) '\\u2709 thanked',
    ];
""", """      if (g['thankYouAt'] != null) '\\u2709 thanked',
      if (g['events'] is List && (g['events'] as List).isNotEmpty)
        (g['events'] as List).join(', '),
    ];
""", "row shows events")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT.name} ({len(s):,} chars)")
