"""Couple v177: three guest tools Zola has and Lazo lacked (JC-LAZO-ZOLAGAPS-1019-COUPLE).

    python app-patches\\patch_couple_v177.py [base.txt]   # base defaults to Couple_master_v176.txt
                                                          # writes Couple_master_v177.txt
Found by walking Zola's couple account on 2026-10-19 (Guest list > Contact Collector, Guest
Messaging, Instant Thank Yous). Everything else on Zola's couple side (budget, checklist, events,
seating, website, hotels, guest photos, registry link, partner invite) Lazo already has.
- Website screen: a "Collect addresses" card (after Invitations). A switch opens a link + QR
  (meetlazo.com/w/{slug}/contact?k=...) that guests fill in themselves; their details land on the
  guest list (weddingSites.collectorOn / collectorKey; worker JC-LAZO-GUESTCOMMS-1019; rules
  1019-COLLECT). Copy link, copy a ready-to-send text, open it.
- Guests screen: a tools row under the title - Message guests (one email to Everyone / Coming /
  Still to reply / Sent regrets / a group, four templates, test to me, sent through the worker
  like the day-before note; copies in couples/{id}/guestMessages), Thank-you notes (a draft per
  guest in a warm / formal / playful tone from the guest list, Copy, Mark sent -> thankYouAt),
  Collect addresses (jumps to the Website card), and a line counting guests who came in from the
  link (guests.source == 'collector').
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v176.txt"
DST = HERE / "Couple_master_v177.txt"
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
    "// Build ID: JC-LAZO-ZOLAGAPS-1019-COUPLE (v177: COLLECT ADDRESSES, MESSAGE GUESTS, THANK-YOU NOTES - a Collect "
    "addresses card on the Website screen (link + QR guests fill in; weddingSites.collectorOn/collectorKey; worker "
    "/w/{slug}/contact writes guests with source collector); a Guests tools row: Message guests (one email to a group, "
    "templates, test to me, /api/w/{slug}/guest-message), Thank-you notes (a draft per guest, three tones, Copy, Mark "
    "sent), Collect addresses; base v176)\n"
) + s[first_build:]

# ---- Website screen: the collector card after Invitations
rep("              _invitationsCard(slug, w), // v174",
    "              _invitationsCard(slug, w), // v174\n              _collectorCard(slug, w), // v177")

# ---- Guests screen: the tools row under the title
rep("""            _subHeader('Guest list'),
            _thankYouLine(docs),""",
    """            _subHeader('Guest list'),
            _thankYouLine(docs),
            _guestToolsRow(docs), // v177""")

HELPERS = r"""  // ---- v177: the guest tools Zola had and we didn't -------------------------------------
  String _newCollectorKey() {
    const String a = 'abcdefghjkmnpqrstuvwxyz23456789';
    final math.Random r = math.Random.secure();
    return List<String>.generate(12, (int _) => a[r.nextInt(a.length)]).join();
  }

  /// Website screen: a link (and QR) guests open to type in their own name and address.
  Widget _collectorCard(String slug, Map<String, dynamic> w) {
    final bool on = w['collectorOn'] == true;
    final String key = (w['collectorKey'] ?? '').toString();
    final String link = 'https://meetlazo.com/w/$slug/contact?k=$key';
    final String shareText = 'Can you tap and share your address for our wedding? \u{1F60A} $link';
    Future<void> flip(bool v) async {
      try {
        await FirebaseFirestore.instance.collection('weddingSites').doc(slug).set(<String, dynamic>{
          'collectorOn': v,
          'collectorKey': key.isNotEmpty ? key : _newCollectorKey(),
        }, SetOptions(merge: true));
        _toastC(v ? 'Your address link is open. Send it to anyone whose address you need.' : 'Address link closed.');
      } catch (_) {
        _toastC('Couldn’t save that - try again.');
      }
    }

    Widget small(IconData ic, String label, VoidCallback onTap) => ActionChip(
          avatar: Icon(ic, size: 15, color: _lzFg(plum)),
          label: Text(label, style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: _lzFg(plum))),
          backgroundColor: _lzBg(Colors.white.withOpacity(.7)),
          side: BorderSide(color: gold.withOpacity(.6)),
          visualDensity: VisualDensity.compact,
          onPressed: onTap,
        );
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: _glass(
        tint: .6,
        borderColor: gold.withOpacity(.6),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          Row(children: <Widget>[
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(borderRadius: BorderRadius.circular(12), color: _lzBg(plum.withOpacity(.1))),
              child: Icon(Icons.contact_mail_rounded, color: _lzFg(plum), size: 22),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                Text('Collect addresses', style: TextStyle(color: _lzFg(plum), fontSize: 15.5, fontWeight: FontWeight.w700)),
                Text(
                    on
                        ? 'Text or email this link. Guests type in their name, address and email, and they appear on your guest list.'
                        : 'One link guests fill in themselves - no chasing addresses one by one.',
                    style: TextStyle(fontSize: 12, color: _lzFg(muted), height: 1.35)),
              ]),
            ),
            Switch(value: on, activeColor: plum, activeTrackColor: gold, onChanged: (bool v) => flip(v)),
          ]),
          if (on && key.isNotEmpty) ...<Widget>[
            const SizedBox(height: 12),
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: Image.network(_qrUrl(link), width: 88, height: 88,
                    errorBuilder: (BuildContext c, Object e, StackTrace? st) => const SizedBox(width: 88, height: 88)),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                  SelectableText(link, style: TextStyle(fontSize: 12, color: _lzFg(ink), fontWeight: FontWeight.w600)),
                  const SizedBox(height: 8),
                  Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                    small(Icons.link_rounded, 'Copy link', () async {
                      await Clipboard.setData(ClipboardData(text: link));
                      _toastC('Link copied.');
                    }),
                    small(Icons.sms_outlined, 'Copy a text to send', () async {
                      await Clipboard.setData(ClipboardData(text: shareText));
                      _toastC('Copied - paste it into a text, a DM or an email.');
                    }),
                    small(Icons.open_in_new_rounded, 'Open', () => _openLink(link)),
                  ]),
                ]),
              ),
            ]),
          ],
        ]),
      ),
    );
  }

  /// Guests screen: the tools row under the title.
  Widget _guestToolsRow(List<QueryDocumentSnapshot<Map<String, dynamic>>> docs) {
    final int fromLink = docs.where((QueryDocumentSnapshot<Map<String, dynamic>> d) => d.data()['source'] == 'collector').length;
    Widget pill(IconData ic, String label, VoidCallback onTap) => ActionChip(
          avatar: Icon(ic, size: 16, color: _lzFg(plum)),
          label: Text(label, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: _lzFg(plum))),
          backgroundColor: _lzBg(Colors.white.withOpacity(.7)),
          side: BorderSide(color: gold.withOpacity(.6)),
          onPressed: onTap,
        );
    return Padding(
      padding: const EdgeInsets.only(left: 6, bottom: 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        if (fromLink > 0)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text('✦ $fromLink guest${fromLink == 1 ? '' : 's'} came in from your address link',
                style: TextStyle(fontSize: 12.5, color: _lzFg(muted), fontWeight: FontWeight.w600)),
          ),
        Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
          pill(Icons.forward_to_inbox_rounded, 'Message guests', () => _guestMessageSheet(docs)),
          pill(Icons.volunteer_activism_rounded, 'Thank-you notes', () => _thankYouSheet(docs)),
          pill(Icons.contact_mail_outlined, 'Collect addresses', () => setState(() => _view = _View.website)),
        ]),
      ]),
    );
  }

  /// One email to a group of guests, sent by the worker as the couple (like the day-before note).
  Future<void> _guestMessageSheet(List<QueryDocumentSnapshot<Map<String, dynamic>>> docs) async {
    final String slug = await _siteSlug();
    if (slug.isEmpty) {
      _toastC('Create your wedding website first — it’s under Website.');
      return;
    }
    if (!mounted) return;
    final List<String> groups = <String>[];
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in docs) {
      final String g = (d.data()['group'] ?? '').toString();
      if (g.isNotEmpty && !groups.contains(g)) groups.add(g);
    }
    int countFor(String a) => docs.where((QueryDocumentSnapshot<Map<String, dynamic>> d) {
          final Map<String, dynamic> g = d.data();
          if ((g['email'] ?? '').toString().trim().isEmpty) return false;
          final String r = (g['rsvp'] ?? 'pending').toString();
          if (a == 'all') return true;
          if (a == 'yes') return r == 'yes';
          if (a == 'no') return r == 'no';
          if (a == 'pending') return r != 'yes' && r != 'no';
          if (a.startsWith('group:')) return (g['group'] ?? '') == a.substring(6);
          return false;
        }).length;
    const List<List<String>> templates = <List<String>>[
      <String>['RSVP reminder', 'A little nudge from us', 'We’re finalizing numbers with our caterer and would love your RSVP. It takes a minute on our wedding site - just tap the button below. Can’t wait to celebrate with you.'],
      <String>['Where to stay', 'Where to stay for our wedding', 'A few hotels near the venue are on our wedding site, with the room block and the booking deadline. Book early if you can - rooms go fast on a holiday weekend.'],
      <String>['Week-of details', 'This week: what to know', 'It’s almost here! Ceremony time, parking, the dress code and the weekend’s timeline are on our site. Reply here if you have a question - we’ll answer the night before at the latest.'],
      <String>['After the wedding', 'Thank you for celebrating with us', 'We’re still smiling. Thank you for being there - it meant everything to have you with us. Photos from the day are going up on our site as they come in.'],
    ];
    String audience = 'all';
    final TextEditingController subjC = TextEditingController();
    final TextEditingController bodyC = TextEditingController();
    bool busy = false;
    bool open = true;
    bool ok = false;
    String status = '';
    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 620),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          void up(VoidCallback f) {
            if (open) setD(f);
          }

          Future<void> send(bool test) async {
            if (subjC.text.trim().isEmpty || bodyC.text.trim().isEmpty) {
              up(() => status = 'Give it a subject and a message.');
              return;
            }
            up(() {
              busy = true;
              status = '';
            });
            final Map<String, dynamic> r = await _workerPost(
                'https://meetlazo.com/api/w/$slug/guest-message', <String, dynamic>{
              'test': test,
              'subject': subjC.text.trim(),
              'message': bodyC.text.trim(),
              'audience': audience,
              'replyTo': FirebaseAuth.instance.currentUser?.email ?? '',
            });
            up(() {
              busy = false;
              ok = r['ok'] == true;
              status = ok
                  ? (test
                      ? 'Test sent to ${FirebaseAuth.instance.currentUser?.email ?? 'you'}.'
                      : 'Sent to ${r['sent']} guest${r['sent'] == 1 ? '' : 's'}${(r['failed'] ?? 0) != 0 ? ' (${r['failed']} didn’t go through)' : ''}.')
                  : (r['message'] ?? 'Couldn’t send - ${r['error'] ?? 'try again'}.').toString();
            });
          }

          Widget who(String a, String label) {
            final int n = countFor(a);
            return ChoiceChip(
              label: Text('$label ($n)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: audience == a ? Colors.white : _lzFg(plum))),
              selected: audience == a,
              selectedColor: plum,
              backgroundColor: _lzBg(Colors.white.withOpacity(.7)),
              side: BorderSide(color: gold.withOpacity(.6)),
              showCheckmark: false,
              onSelected: busy ? null : (bool _) => up(() => audience = a),
            );
          }

          final int n = countFor(audience);
          return _lzFrame(ctx2,
              icon: Icons.forward_to_inbox_rounded,
              title: 'Message your guests',
              subtitle: 'One email to the guests you pick. Replies come to you.',
              children: <Widget>[
                _lzSection('Who'),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  who('all', 'Everyone'),
                  who('yes', 'Coming'),
                  who('pending', 'Still to reply'),
                  who('no', 'Sent regrets'),
                  for (final String g in groups) who('group:$g', g),
                ]),
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text('Guests without an email on file are skipped.', style: TextStyle(fontSize: 11.5, color: _lzFg(muted))),
                ),
                _lzSection('Start from'),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  for (final List<String> t in templates)
                    ActionChip(
                      label: Text(t[0], style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: _lzFg(plum))),
                      backgroundColor: _lzBg(Colors.white.withOpacity(.7)),
                      side: BorderSide(color: gold.withOpacity(.6)),
                      onPressed: busy
                          ? null
                          : () => up(() {
                                subjC.text = t[1];
                                bodyC.text = t[2];
                              }),
                    ),
                ]),
                const SizedBox(height: 14),
                TextField(
                    controller: subjC,
                    enabled: !busy,
                    maxLength: 140,
                    textCapitalization: TextCapitalization.sentences,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Subject')),
                const SizedBox(height: 8),
                TextField(
                    controller: bodyC,
                    enabled: !busy,
                    minLines: 4,
                    maxLines: 12,
                    maxLength: 4000,
                    textCapitalization: TextCapitalization.sentences,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14, height: 1.4),
                    decoration: _lightDeco('Your message')),
                Text('Each email opens with the guest’s first name and ends with a button to your site.',
                    style: TextStyle(fontSize: 11.5, color: _lzFg(muted))),
                if (status.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 10),
                    child: Text(status, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: _lzFg(ok ? vGreen : rose))),
                  ),
                const SizedBox(height: 16),
                Wrap(spacing: 10, runSpacing: 10, children: <Widget>[
                  OutlinedButton.icon(
                    onPressed: busy ? null : () => send(true),
                    icon: const Icon(Icons.science_outlined, size: 16),
                    label: const Text('Send a test to me'),
                    style: OutlinedButton.styleFrom(foregroundColor: _lzFg(plum), side: BorderSide(color: gold.withOpacity(.8))),
                  ),
                  FilledButton.icon(
                    onPressed: busy || n == 0 ? null : () => send(false),
                    icon: busy
                        ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                        : const Icon(Icons.send_rounded, size: 16),
                    label: Text('Send to $n guest${n == 1 ? '' : 's'}'),
                    style: FilledButton.styleFrom(backgroundColor: plum, foregroundColor: Colors.white),
                  ),
                ]),
              ]);
        },
      ),
    );
    open = false;
  }

  /// A thank-you draft for every guest who answered, from the guest list; Copy and Mark sent.
  Future<void> _thankYouSheet(List<QueryDocumentSnapshot<Map<String, dynamic>>> docs) async {
    if (!mounted) return;
    String tone = 'warm';
    bool open = true;
    String draft(Map<String, dynamic> g) {
      final String name = (g['name'] ?? '').toString().trim();
      final String first = name.isEmpty ? 'friend' : name.split(' ').first;
      final String party = (g['party'] ?? '').toString().trim();
      final String gift = (g['gift'] ?? '').toString().trim();
      final bool came = (g['rsvp'] ?? '') == 'yes';
      final String you = party.isNotEmpty ? 'you both' : 'you';
      final String dear = tone == 'formal' ? 'Dear $name${party.isNotEmpty ? ' and $party' : ''},' : (tone == 'playful' ? 'Hey $first${party.isNotEmpty ? ' and $party' : ''}!' : 'Dear $first${party.isNotEmpty ? ' and $party' : ''},');
      final String giftLine = gift.isEmpty
          ? ''
          : (tone == 'formal'
              ? ' Thank you as well for the $gift; it was most generous and we will think of you each time we use it.'
              : (tone == 'playful' ? ' And the $gift?! You know us too well. It’s already in use.' : ' And thank you for the $gift - it was so thoughtful, and it already feels like part of our home.'));
      String body;
      if (came) {
        body = tone == 'formal'
            ? 'Thank you for joining us on our wedding day. Your presence made the celebration complete, and we are grateful $you travelled to share it with us.'
            : (tone == 'playful'
                ? 'Thank you for coming to celebrate with us - seeing $you on the dance floor is one of our favorite memories of the whole day.'
                : 'Thank you for sharing our wedding day with us. Having $you there made it feel complete, and we’ll always treasure the memories we made together.');
      } else {
        body = tone == 'formal'
            ? 'We missed you on our wedding day, and we are grateful for your kind wishes. We hope to celebrate with $you in person before long.'
            : (tone == 'playful'
                ? 'We missed $you on the big day! Your note meant a lot - next celebration, you’re not getting out of it.'
                : 'We missed $you on our wedding day, but your warm wishes meant so much. We can’t wait to celebrate with $you soon.');
      }
      final String close = tone == 'formal' ? 'With our sincere thanks,' : (tone == 'playful' ? 'Love you lots,' : 'With love,');
      return '$dear\n\n$body$giftLine\n\n$close';
    }

    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 640),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          void up(VoidCallback f) {
            if (open) setD(f);
          }

          final List<QueryDocumentSnapshot<Map<String, dynamic>>> list = docs
              .where((QueryDocumentSnapshot<Map<String, dynamic>> d) => d.data()['rsvp'] == 'yes' || d.data()['rsvp'] == 'no')
              .toList()
            ..sort((QueryDocumentSnapshot<Map<String, dynamic>> a, QueryDocumentSnapshot<Map<String, dynamic>> b) {
              final int sa = a.data()['thankYouAt'] == null ? 0 : 1, sb = b.data()['thankYouAt'] == null ? 0 : 1;
              if (sa != sb) return sa - sb;
              return (a.data()['name'] ?? '').toString().compareTo((b.data()['name'] ?? '').toString());
            });
          final int done = list.where((QueryDocumentSnapshot<Map<String, dynamic>> d) => d.data()['thankYouAt'] != null).length;
          Widget toneChip(String t, String label) => ChoiceChip(
                label: Text(label, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: tone == t ? Colors.white : _lzFg(plum))),
                selected: tone == t,
                selectedColor: plum,
                backgroundColor: _lzBg(Colors.white.withOpacity(.7)),
                side: BorderSide(color: gold.withOpacity(.6)),
                showCheckmark: false,
                onSelected: (bool _) => up(() => tone = t),
              );
          return _lzFrame(ctx2,
              icon: Icons.volunteer_activism_rounded,
              title: 'Thank-you notes',
              subtitle: 'A draft for every guest who answered, from your guest list. Copy it, make it yours, tick it off.',
              children: <Widget>[
                _lzSection('Tone'),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[toneChip('warm', 'Warm'), toneChip('formal', 'Formal'), toneChip('playful', 'Playful')]),
                Padding(
                  padding: const EdgeInsets.only(top: 10, bottom: 4),
                  child: Text(list.isEmpty ? 'Once guests RSVP, their notes appear here.' : '$done of ${list.length} sent. Add a gift to a guest and the note mentions it.',
                      style: TextStyle(fontSize: 12.5, color: _lzFg(done == list.length && list.isNotEmpty ? vGreen : muted), fontWeight: FontWeight.w600)),
                ),
                for (final QueryDocumentSnapshot<Map<String, dynamic>> d in list)
                  Builder(builder: (BuildContext bc) {
                    final Map<String, dynamic> g = d.data();
                    final bool sent = g['thankYouAt'] != null;
                    final String text = draft(g);
                    return Container(
                      margin: const EdgeInsets.only(top: 10),
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: _lzBg(Colors.white.withOpacity(sent ? .45 : .8)),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: _lzLine(sent ? goldLine : gold.withOpacity(.6))),
                      ),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                        Row(children: <Widget>[
                          Expanded(
                            child: Text((g['name'] ?? '').toString(),
                                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: _lzFg(plum))),
                          ),
                          Text(g['rsvp'] == 'yes' ? 'Came' : 'Sent regrets', style: TextStyle(fontSize: 11.5, color: _lzFg(muted))),
                          if (sent) ...<Widget>[const SizedBox(width: 8), Icon(Icons.check_circle_rounded, size: 16, color: _lzFg(vGreen))],
                        ]),
                        const SizedBox(height: 6),
                        SelectableText(text, style: TextStyle(fontSize: 13, height: 1.45, color: _lzFg(ink))),
                        const SizedBox(height: 6),
                        Wrap(spacing: 4, children: <Widget>[
                          TextButton.icon(
                            onPressed: () async {
                              await Clipboard.setData(ClipboardData(text: text));
                              _toastC('Copied - paste it into a card, a text or an email.');
                            },
                            icon: const Icon(Icons.copy_rounded, size: 15),
                            label: const Text('Copy'),
                            style: TextButton.styleFrom(foregroundColor: _lzFg(plum), visualDensity: VisualDensity.compact),
                          ),
                          TextButton.icon(
                            onPressed: () async {
                              try {
                                await d.reference.set(<String, dynamic>{'thankYouAt': sent ? null : FieldValue.serverTimestamp()}, SetOptions(merge: true));
                              } catch (_) {
                                _toastC('Couldn’t save that - try again.');
                              }
                            },
                            icon: Icon(sent ? Icons.undo_rounded : Icons.check_rounded, size: 15),
                            label: Text(sent ? 'Not sent yet' : 'Mark sent'),
                            style: TextButton.styleFrom(foregroundColor: _lzFg(sent ? muted : vGreen), visualDensity: VisualDensity.compact),
                          ),
                        ]),
                      ]),
                    );
                  }),
              ]);
        },
      ),
    );
    open = false;
  }

"""
rep("  Widget _thankYouLine(\n", HELPERS + "  Widget _thankYouLine(\n")

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8")
print("wrote", DST, len(s.splitlines()), "lines")
