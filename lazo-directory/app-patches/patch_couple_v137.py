"""patch_couple_v137.py - JC-LAZO-COUPLE-0929-V137
The site, live - what the couple dashboard feeds it:
  1. PUBLISH MIRRORS. Saving the website also writes weddingSites.timeline
     (the Day-of moments guests should see - vendor-only moments filtered out),
     weddingSites/{slug}/seating/main (name, party, table, seat for every
     seated guest) when "Find your seat" is on, weddingSites/{slug}/playlist/
     main (song requests + RSVP songs) for the DJ page, and vendorTeam entries
     now carry vendorId + the vendor's Lazo URL.
  2. EDITOR: "LIVE ON THE DAY" - switches for the hour-by-hour list, the seat
     finder and translation; dinner choices (comma-separated) for the RSVP
     form; the photographer's gallery link.
  3. PERSONAL RSVP LINKS. The guest editor gains "Personal RSVP link": it
     writes weddingSites/{slug}/invites/{guestId} (name, party, plus-ones,
     meals) and copies meetlazo.com/w/{slug}/?i={guestId}. RSVP import
     matches on that id before falling back to the name.
  4. THANK-YOU TRACKER. A "Thank-you note sent" switch per guest
     (guests.thankYouAt), a mark on the row, and a count under the header.
  5. WEBSITE SCREEN: "Live links" card - table cards (QR), the DJ page, the
     slideshow for a TV, seat finder preview, with a Refresh for the DJ page.
Pairs with worker JC-LAZO-WORKER-0929-LIVE-001, template patch
JC-LAZO-WWS-0929-LIVE and rules JC-LAZO-LIVE-0929. Applies on top of
Couple_master_v136.txt -> Couple_master_v137.txt. Anchor-and-assert.
  python app-patches\\patch_couple_v137.py [src] [out]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v136.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "Couple_master_v137.txt"
s = SRC.read_text(encoding="utf-8")
if "JC-LAZO-COUPLE-0929-V137" in s:
    raise SystemExit("already applied")


def swap(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"ABORT [{label}]: anchor matched {n} times, expected {count}")
    s = s.replace(old, new)
    print(f"  ok  {label}")


# ---------------------------------------------------------------- 0. header
swap("// (v136: PHOTOS, PLACED + GUEST PHOTOS",
     "// (v137: THE SITE, LIVE - publishing the website also mirrors the Day-of timeline (weddingSites.timeline), the seating chart (weddingSites/{slug}/seating/main) and the song requests (weddingSites/{slug}/playlist/main) so the site shows the day hour by hour with Now/Next on the day, lets guests find their table, and gives the DJ a live page; vendor credits carry vendorId + Lazo URL; the editor's LIVE ON THE DAY section (timeline / seat finder / translation switches, dinner choices, gallery link); personal RSVP links per guest (weddingSites/{slug}/invites/{guestId}, ?i= on the site) with import matching on the id; a Thank-you note sent switch per guest (guests.thankYouAt) with a count; a Live links card on the Website screen (table cards with QR, DJ page, slideshow, seat finder). JC-LAZO-COUPLE-0929-V137; base v136)\n// (v136: PHOTOS, PLACED + GUEST PHOTOS",
     "header")

# ---------------------------------------------------------------- 1. helpers
swap("""  // ---- v136: photos from the guests (read through the worker's API) ----
  Future<List<Map<String, dynamic>>>? _gpFuture;
""", r'''  // ---- v137: the site, live ----
  static const List<String> _tlVendorWords = <String>[
    'arriv', 'load', 'setup', 'set-up', 'set up', 'vendor', 'deliver',
    'breakdown', 'strike', 'pickup', 'pick-up', 'tear', 'sound check',
    'getting ready', 'hair', 'makeup', 'make-up', 'first look', 'photos with'
  ];

  // the Day-of moments a guest should see: the ceremony and everything a
  // guest is part of; not the vendor calls, the load-in or getting ready
  Future<List<Map<String, dynamic>>> _guestTimeline() async {
    final List<Map<String, dynamic>> out = <Map<String, dynamic>>[];
    try {
      final QuerySnapshot<Map<String, dynamic>> evs =
          await _dayofRef.orderBy('time').get();
      for (final QueryDocumentSnapshot<Map<String, dynamic>> d in evs.docs) {
        final Map<String, dynamic> m = d.data();
        final String label = (m['label'] ?? '').toString().trim();
        final String time = (m['time'] ?? '').toString().trim();
        if (label.isEmpty || time.isEmpty) {
          continue;
        }
        final String low = label.toLowerCase();
        final bool anchor = m['anchor'] == true;
        if (!anchor && _tlVendorWords.any((String w) => low.contains(w))) {
          continue;
        }
        out.add(<String, dynamic>{
          'time': time,
          'label': label,
          'note': (m['note'] ?? '').toString().trim(),
          'dur': (m['dur'] is num) ? (m['dur'] as num).toInt() : 0,
        });
        if (out.length >= 40) {
          break;
        }
      }
    } catch (_) {}
    return out;
  }

  Future<void> _mirrorSeating(String slug, bool on) async {
    final DocumentReference<Map<String, dynamic>> ref = FirebaseFirestore
        .instance
        .collection('weddingSites')
        .doc(slug)
        .collection('seating')
        .doc('main');
    if (!on) {
      try {
        await ref.delete();
      } catch (_) {}
      return;
    }
    try {
      final QuerySnapshot<Map<String, dynamic>> gs = await _guestsRef.get();
      final List<Map<String, dynamic>> rows = <Map<String, dynamic>>[];
      for (final QueryDocumentSnapshot<Map<String, dynamic>> d in gs.docs) {
        final Map<String, dynamic> g = d.data();
        final String n = (g['name'] ?? '').toString().trim();
        if (n.isEmpty || (g['rsvp'] ?? '') == 'no') {
          continue;
        }
        rows.add(<String, dynamic>{
          'n': n,
          'p': (g['party'] ?? '').toString().trim(),
          't': (g['tableName'] ?? '').toString().trim(),
          's': g['seat'] is num ? (g['seat'] as num).toInt() : -1,
        });
      }
      await ref.set(<String, dynamic>{
        'guests': rows,
        'updatedAt': FieldValue.serverTimestamp(),
      });
    } catch (_) {}
  }

  Future<int> _mirrorPlaylist(String slug) async {
    final List<Map<String, dynamic>> songs = <Map<String, dynamic>>[];
    try {
      final QuerySnapshot<Map<String, dynamic>> rq =
          await _coupleRef.collection('musicRequests').get();
      for (final QueryDocumentSnapshot<Map<String, dynamic>> d in rq.docs) {
        final Map<String, dynamic> m = d.data();
        if ((m['status'] ?? '') == 'declined') {
          continue;
        }
        final String song = (m['song'] ?? '').toString().trim();
        if (song.isEmpty) {
          continue;
        }
        songs.add(<String, dynamic>{
          'song': song,
          'artist': (m['artist'] ?? '').toString().trim(),
          'guest': (m['guest'] ?? '').toString().trim(),
          'note': (m['note'] ?? '').toString().trim(),
          'must': m['status'] == 'must',
        });
      }
    } catch (_) {}
    try {
      final QuerySnapshot<Map<String, dynamic>> rs = await FirebaseFirestore
          .instance
          .collection('weddingSites')
          .doc(slug)
          .collection('rsvps')
          .get();
      for (final QueryDocumentSnapshot<Map<String, dynamic>> d in rs.docs) {
        final String song = (d.data()['song'] ?? '').toString().trim();
        if (song.isEmpty) {
          continue;
        }
        songs.add(<String, dynamic>{
          'song': song,
          'artist': '',
          'guest': (d.data()['name'] ?? '').toString().trim(),
          'note': '',
          'must': false,
        });
      }
    } catch (_) {}
    try {
      final QuerySnapshot<Map<String, dynamic>> gs = await _guestsRef.get();
      for (final QueryDocumentSnapshot<Map<String, dynamic>> d in gs.docs) {
        final String song = (d.data()['song'] ?? '').toString().trim();
        if (song.isEmpty) {
          continue;
        }
        songs.add(<String, dynamic>{
          'song': song,
          'artist': '',
          'guest': (d.data()['name'] ?? '').toString().trim(),
          'note': '',
          'must': false,
        });
      }
    } catch (_) {}
    try {
      await FirebaseFirestore.instance
          .collection('weddingSites')
          .doc(slug)
          .collection('playlist')
          .doc('main')
          .set(<String, dynamic>{
        'songs': songs.take(300).toList(),
        'updatedAt': DateTime.now().toUtc().toIso8601String(),
      });
    } catch (_) {}
    return songs.length;
  }

  Future<String> _siteSlug() async {
    try {
      final QuerySnapshot<Map<String, dynamic>> q = await FirebaseFirestore
          .instance
          .collection('weddingSites')
          .where('coupleUid', isEqualTo: _cid)
          .limit(1)
          .get();
      if (q.docs.isNotEmpty) {
        return q.docs.first.id;
      }
    } catch (_) {}
    return '';
  }

  // a link that opens the site with this guest's RSVP form already filled in
  Future<void> _personalLink(String guestId, Map<String, dynamic> g) async {
    final String slug = await _siteSlug();
    if (slug.isEmpty) {
      _toastC('Create your wedding website first — it’s under Website.');
      return;
    }
    try {
      final DocumentSnapshot<Map<String, dynamic>> site = await FirebaseFirestore
          .instance
          .collection('weddingSites')
          .doc(slug)
          .get();
      final List<String> meals = List<String>.from(
          (site.data()?['mealOptions'] as List?)
                  ?.map((dynamic e) => e.toString()) ??
              const <String>[]);
      await FirebaseFirestore.instance
          .collection('weddingSites')
          .doc(slug)
          .collection('invites')
          .doc(guestId)
          .set(<String, dynamic>{
        'name': (g['name'] ?? '').toString(),
        'party': (g['party'] ?? '').toString(),
        'plusOnes': ((g['plusOnes'] ?? 0) as num).toInt(),
        'meals': meals,
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
      final String link = 'https://meetlazo.com/w/$slug/?i=$guestId';
      await Clipboard.setData(ClipboardData(text: link));
      _toastC('Personal link copied — their RSVP arrives already matched ✓');
    } catch (_) {
      _toastC('Could not make the link — try again.');
    }
  }

  Widget _thankYouLine(
      List<QueryDocumentSnapshot<Map<String, dynamic>>> docs) {
    int yes = 0, done = 0;
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in docs) {
      final Map<String, dynamic> g = d.data();
      if ((g['rsvp'] ?? '') == 'yes') {
        yes++;
        if (g['thankYouAt'] != null) {
          done++;
        }
      }
    }
    if (yes == 0) {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.only(left: 6, bottom: 10),
      child: Text('✉ Thank-you notes: $done of $yes sent',
          style: TextStyle(
              fontSize: 12.5,
              color: done == yes ? vGreen : muted,
              fontWeight: FontWeight.w600)),
    );
  }

  Widget _liveLinksCard(String slug, Map<String, dynamic> w) {
    Widget row(IconData ic, String title, String sub, String url,
        {VoidCallback? extra, String? extraLabel}) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(children: <Widget>[
          Icon(ic, color: plum, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(title,
                      style: const TextStyle(
                          color: plum,
                          fontSize: 13.5,
                          fontWeight: FontWeight.w700)),
                  Text(sub,
                      style: const TextStyle(fontSize: 11.5, color: muted)),
                ]),
          ),
          if (extra != null)
            TextButton(
                onPressed: _h(extra),
                child: Text(extraLabel ?? 'Refresh',
                    style: const TextStyle(
                        color: plum,
                        fontSize: 12,
                        fontWeight: FontWeight.w700))),
          IconButton(
              tooltip: 'Open',
              onPressed: _h(() => _openLink(url)),
              icon:
                  const Icon(Icons.open_in_new_rounded, color: plum, size: 18)),
        ]),
      );
    }

    return _glass(
      padding: const EdgeInsets.fromLTRB(16, 14, 8, 8),
      radius: 20,
      tint: .6,
      borderColor: gold.withOpacity(.6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text('Live on the day',
              style: TextStyle(
                  color: plum, fontSize: 15.5, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          row(Icons.qr_code_2_rounded, 'Table cards',
              'Print six per page: share photos, request a song',
              'https://meetlazo.com/w/$slug/cards'),
          row(Icons.queue_music_rounded, 'DJ page',
              'Every request, refreshed on publish or here',
              'https://meetlazo.com/w/$slug/playlist',
              extra: () async {
                final int n = await _mirrorPlaylist(slug);
                _toastC('DJ page updated — $n song${n == 1 ? '' : 's'} ✓');
              }),
          row(Icons.tv_rounded, 'Slideshow for a TV',
              'Guests’ photos, full screen, refreshes itself',
              'https://meetlazo.com/w/$slug/?wall=1'),
          if (w['seatingOn'] == true)
            row(Icons.event_seat_rounded, 'Find your seat',
                'Guests type their name and get their table',
                'https://meetlazo.com/w/$slug/#rsvpSec',
                extra: () async {
                  await _mirrorSeating(slug, true);
                  _toastC('Seating on the site updated ✓');
                }),
        ],
      ),
    );
  }

  // ---- v136: photos from the guests (read through the worker's API) ----
  Future<List<Map<String, dynamic>>>? _gpFuture;
''', "helpers")

# ---------------------------------------------------------------- 2. editor state
swap("""    bool guestOn = w['guestPhotosOn'] != false;
    final TextEditingController guestNoteC =
        TextEditingController(text: (w['guestPhotosNote'] ?? '').toString());
""", """    bool guestOn = w['guestPhotosOn'] != false;
    final TextEditingController guestNoteC =
        TextEditingController(text: (w['guestPhotosNote'] ?? '').toString());
    // v137: the site, live
    bool timelineOn = w['timelineOn'] != false;
    bool seatingOn = w['seatingOn'] == true;
    bool translateOn = w['translateOn'] != false;
    final TextEditingController mealsC = TextEditingController(
        text: ((w['mealOptions'] as List?) ?? const <dynamic>[])
            .map((dynamic e) => e.toString())
            .join(', '));
    final TextEditingController galleryC =
        TextEditingController(text: (w['galleryUrl'] ?? '').toString());
""", "editor state")

# ---------------------------------------------------------------- 3. editor UI
swap("""                          _wbSection('PHOTOS FROM YOUR GUESTS'),
""", """                          _wbSection('LIVE ON THE DAY'),
                          const Padding(
                            padding: EdgeInsets.only(bottom: 4),
                            child: Text(
                                'Publishing copies your Day-of timeline and seating chart to the site. On the wedding day the schedule marks what\\u2019s happening now; guests can look up their table.',
                                style: TextStyle(fontSize: 11.5, color: muted)),
                          ),
                          SwitchListTile(
                            dense: true,
                            contentPadding: EdgeInsets.zero,
                            activeColor: Colors.white,
                            activeTrackColor: vGreen,
                            inactiveThumbColor: Colors.white,
                            inactiveTrackColor: muted.withOpacity(.4),
                            title: const Text('Show the day hour by hour',
                                style: TextStyle(fontSize: 13.5)),
                            value: timelineOn,
                            onChanged:
                                _hb((bool v) => setD(() => timelineOn = v)),
                          ),
                          SwitchListTile(
                            dense: true,
                            contentPadding: EdgeInsets.zero,
                            activeColor: Colors.white,
                            activeTrackColor: vGreen,
                            inactiveThumbColor: Colors.white,
                            inactiveTrackColor: muted.withOpacity(.4),
                            title: const Text('Let guests find their seat',
                                style: TextStyle(fontSize: 13.5)),
                            subtitle: const Text(
                                'Name, table and tablemates from your seating chart',
                                style: TextStyle(fontSize: 11, color: muted)),
                            value: seatingOn,
                            onChanged:
                                _hb((bool v) => setD(() => seatingOn = v)),
                          ),
                          SwitchListTile(
                            dense: true,
                            contentPadding: EdgeInsets.zero,
                            activeColor: Colors.white,
                            activeTrackColor: vGreen,
                            inactiveThumbColor: Colors.white,
                            inactiveTrackColor: muted.withOpacity(.4),
                            title: const Text('Offer the site in other languages',
                                style: TextStyle(fontSize: 13.5)),
                            value: translateOn,
                            onChanged:
                                _hb((bool v) => setD(() => translateOn = v)),
                          ),
                          const SizedBox(height: 8),
                          TextField(
                              controller: mealsC,
                              style: const TextStyle(color: ink, fontSize: 14),
                              decoration: _lightDeco(
                                  'Dinner choices on the RSVP (comma-separated)',
                                  hint: 'Chicken, Salmon, Garden risotto')),
                          const SizedBox(height: 10),
                          TextField(
                              controller: galleryC,
                              keyboardType: TextInputType.url,
                              style: const TextStyle(color: ink, fontSize: 14),
                              decoration: _lightDeco(
                                  'Photo gallery link (after the wedding)',
                                  hint: 'https://meetlazo.com/g/your-gallery')),
                          _wbSection('PHOTOS FROM YOUR GUESTS'),
""", "editor UI")

# ---------------------------------------------------------------- 4. vendorTeam with ids + urls
swap("""      final List<Map<String, String>> vendorTeam = <Map<String, String>>[];
""", """      final List<Map<String, dynamic>> vendorTeam = <Map<String, dynamic>>[];
""", "vendorTeam type")
swap("""          vendorTeam.add(<String, String>{'category': label, 'name': vn});
""", """          // v137: the credit links to the vendor's Lazo page and carries the
          // id for a "Check your date" lead link
          final Map<String, dynamic> credit = <String, dynamic>{
            'category': label,
            'name': vn
          };
          final String vid = (p.data()['vendorId'] ?? '').toString();
          if (vid.isNotEmpty) {
            credit['vendorId'] = vid;
            try {
              final DocumentSnapshot<Map<String, dynamic>> ven =
                  await FirebaseFirestore.instance
                      .collection('vendors')
                      .doc(vid)
                      .get();
              final String metro = (ven.data()?['metroId'] ?? '').toString();
              final String vslug = (ven.data()?['slug'] ?? '').toString();
              if (metro.isNotEmpty && vslug.isNotEmpty) {
                credit['url'] = 'https://meetlazo.com/$metro/${p.id}/$vslug/';
              }
            } catch (_) {}
          }
          vendorTeam.add(credit);
""", "vendorTeam credit")

# ---------------------------------------------------------------- 5. save + mirrors
swap("""        'guestPhotosOn': guestOn,
        'guestPhotosNote': guestNoteC.text.trim(),
""", """        'guestPhotosOn': guestOn,
        'guestPhotosNote': guestNoteC.text.trim(),
        // v137: the site, live
        'timelineOn': timelineOn,
        'timeline': await _guestTimeline(),
        'seatingOn': seatingOn,
        'translateOn': translateOn,
        'mealOptions': mealsC.text
            .split(',')
            .map((String e) => e.trim())
            .where((String e) => e.isNotEmpty)
            .take(8)
            .toList(),
        'galleryUrl': galleryC.text.trim().startsWith('https://')
            ? galleryC.text.trim()
            : '',
""", "save fields")
swap("""      if (mounted) {
        _siteLiveShareSheet(joinedNames(), slug);
      }
""", """      // v137: the seating lookup and the DJ page read mirrored copies
      await _mirrorSeating(slug, seatingOn);
      await _mirrorPlaylist(slug);
      if (mounted) {
        _siteLiveShareSheet(joinedNames(), slug);
      }
""", "mirrors on publish")

# ---------------------------------------------------------------- 6. website screen card
swap("""              _guestPhotosCard(slug, w),
""", """              _guestPhotosCard(slug, w),
              const SizedBox(height: 14),
              _liveLinksCard(slug, w),
""", "live links card")

# ---------------------------------------------------------------- 7. guest editor: link + thank-you
swap("""    String meal = (c['meal'] ?? '') as String;
""", """    String meal = (c['meal'] ?? '') as String;
    bool thanked = c['thankYouAt'] != null; // v137
""", "guest editor state")
swap("""                  TextField(
                      controller: emailC,
                      keyboardType: TextInputType.emailAddress,
                      style: const TextStyle(color: ink, fontSize: 14),
                      decoration: _lightDeco('Email (optional)')),
""", """                  TextField(
                      controller: emailC,
                      keyboardType: TextInputType.emailAddress,
                      style: const TextStyle(color: ink, fontSize: 14),
                      decoration: _lightDeco('Email (optional)')),
                  if (rsvp == 'yes')
                    SwitchListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      activeColor: Colors.white,
                      activeTrackColor: vGreen,
                      inactiveThumbColor: Colors.white,
                      inactiveTrackColor: muted.withOpacity(.4),
                      title: const Text('Thank-you note sent',
                          style: TextStyle(fontSize: 13.5)),
                      value: thanked,
                      onChanged: _hb((bool v) => setD(() => thanked = v)),
                    ),
""", "guest editor thank-you switch")
swap("""          actions: <Widget>[
            if (id != null)
              TextButton(
                onPressed: _h(() async {
                  await _guestsRef.doc(id).delete();
""", """          actions: <Widget>[
            if (id != null)
              TextButton.icon(
                onPressed: _h(() => _personalLink(id, <String, dynamic>{
                      'name': nameC.text.trim(),
                      'party': partyC.text.trim(),
                      'plusOnes': int.tryParse(plusC.text.trim()) ?? 0,
                    })),
                icon: const Icon(Icons.link_rounded, size: 16, color: plum),
                label: const Text('Personal RSVP link',
                    style: TextStyle(color: plum, fontSize: 12.5)),
              ),
            if (id != null)
              TextButton(
                onPressed: _h(() async {
                  await _guestsRef.doc(id).delete();
""", "guest editor personal link")
swap("""      'allergies': allergyC.text.trim(),
      'email': emailC.text.trim(),
      'address': addrC.text.trim(),
      'updatedAt': FieldValue.serverTimestamp(),
    };
""", """      'allergies': allergyC.text.trim(),
      'email': emailC.text.trim(),
      'address': addrC.text.trim(),
      'thankYouAt': thanked
          ? (c['thankYouAt'] ?? FieldValue.serverTimestamp())
          : null,
      'updatedAt': FieldValue.serverTimestamp(),
    };
""", "guest editor save thank-you")

# ---------------------------------------------------------------- 8. guest row + header
swap("""      if ((g['tableName'] ?? '').toString().trim().isNotEmpty)
        '${g['tableName']}${g['seat'] is num && (g['seat'] as num) >= 0 ? ' \\u00b7 seat ${(g['seat'] as num).toInt() + 1}' : ''}',
    ];
""", """      if ((g['tableName'] ?? '').toString().trim().isNotEmpty)
        '${g['tableName']}${g['seat'] is num && (g['seat'] as num) >= 0 ? ' \\u00b7 seat ${(g['seat'] as num).toInt() + 1}' : ''}',
      if (g['thankYouAt'] != null) '\\u2709 thanked',
    ];
""", "guest row thanked")
swap("""            _subHeader('Guest list'),
            if (docs.isNotEmpty)
""", """            _subHeader('Guest list'),
            _thankYouLine(docs),
            if (docs.isNotEmpty)
""", "guests header thank-you count")

# ---------------------------------------------------------------- 9. RSVP import by invite
swap("""    final QuerySnapshot<Map<String, dynamic>> ex =
        await _guestsRef.where('name', isEqualTo: nm).limit(1).get();
    final Map<String, dynamic> data = <String, dynamic>{
      'name': nm,
      'rsvp': (r['attending'] ?? 'yes') == 'yes' ? 'yes' : 'no',
      'meal': (r['meal'] ?? '') as String,
      'plusOnes': ((r['plusOnes'] ?? 0) as num).toInt(),
      'updatedAt': FieldValue.serverTimestamp(),
    };
    if (ex.docs.isNotEmpty) {
      await _guestsRef.doc(ex.docs.first.id).set(data, SetOptions(merge: true));
    } else {
""", """    // v137: a personal link carries the guest's id, so the reply lands on
    // the right row even when they typed the household name
    final String inv = (r['invite'] ?? '').toString();
    String matchId = '';
    if (inv.isNotEmpty) {
      try {
        final DocumentSnapshot<Map<String, dynamic>> gd =
            await _guestsRef.doc(inv).get();
        if (gd.exists) {
          matchId = inv;
        }
      } catch (_) {}
    }
    final QuerySnapshot<Map<String, dynamic>>? ex = matchId.isNotEmpty
        ? null
        : await _guestsRef.where('name', isEqualTo: nm).limit(1).get();
    final Map<String, dynamic> data = <String, dynamic>{
      if (matchId.isEmpty) 'name': nm,
      'rsvp': (r['attending'] ?? 'yes') == 'yes' ? 'yes' : 'no',
      'meal': (r['meal'] ?? '') as String,
      'plusOnes': ((r['plusOnes'] ?? 0) as num).toInt(),
      if ((r['song'] ?? '').toString().trim().isNotEmpty)
        'song': (r['song'] ?? '').toString().trim(),
      'updatedAt': FieldValue.serverTimestamp(),
    };
    if (matchId.isNotEmpty) {
      await _guestsRef.doc(matchId).set(data, SetOptions(merge: true));
    } else if (ex != null && ex.docs.isNotEmpty) {
      await _guestsRef.doc(ex.docs.first.id).set(data, SetOptions(merge: true));
    } else {
""", "rsvp import by invite")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT.name} ({len(s):,} chars)")
