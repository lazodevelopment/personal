"""Couple v179: a Visibility card on the Website screen (JC-LAZO-VISIBILITY-1019-COUPLE).

    python app-patches\\patch_couple_v179.py [base.txt]   # base defaults to Couple_master_v178.txt
                                                          # writes Couple_master_v179.txt
Zola gives couples two switches we did not have: "Allow search engines to link to your site" and
"Appear in guest search". The Website screen gains a Visibility card next to Invitations / Collect
addresses with four rows:
  - Visible to guests: the live link (tap to copy) + Edit website - read-only status, the site is
    always reachable by link;
  - Allow search engines to link to your site: switch -> weddingSites.noindex = !on (the worker adds
    the noindex,nofollow robots meta and drops the site from the couples sitemap; note that search
    engines can take days to update);
  - Appear in Find a couple on Lazo: switch -> weddingSites.unlisted = !on (the worker leaves the site
    out of /api/couples and the couples sitemap);
  - Password: the existing passcode field - "No password needed. Anyone with the link can open it."
    when empty, else "Guests need the password on the invitation." - with Change / Add a password
    opening the website editor where the field lives.
Writes go to weddingSites/{slug} with set(merge). No rules change (the couple already writes these
docs); worker side deployed separately (JC-LAZO-VISIBILITY-1019 in worker/src/index.js).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v178.txt"
DST = HERE / "Couple_master_v179.txt"
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
    "// Build ID: JC-LAZO-VISIBILITY-1019-COUPLE (v179: VISIBILITY CARD on the Website screen - Visible to guests "
    "(live link + Edit website), Allow search engines to link to your site (weddingSites.noindex), Appear in Find a "
    "couple on Lazo (weddingSites.unlisted), and the password row pointing at the existing passcode field; "
    "set(merge) on weddingSites/{slug}; worker honours both flags; base v178)\n"
) + s[first_build:]

# the card sits under Collect addresses, in the same Website screen builder (couple / doc / defNames in scope)
rep("              _collectorCard(slug, w), // v177\n",
    "              _collectorCard(slug, w), // v177\n"
    "              _visibilityCard(slug, w, () => _editWebsite(couple, doc, defNames)), // v179\n")

HELPERS = r"""  // ---- v179: who can find the site -------------------------------------------------------
  /// Website screen: the two Zola-style switches (search engines, Find a couple) plus the link and
  /// password rows. Flags are stored inverted (noindex / unlisted) so a missing field means public.
  Widget _visibilityCard(String slug, Map<String, dynamic> w, VoidCallback editSite) {
    final String link = 'https://meetlazo.com/w/$slug/';
    final bool searchOn = w['noindex'] != true;
    final bool findOn = w['unlisted'] != true;
    final bool hasPass = ((w['passcode'] ?? '') as String).trim().isNotEmpty;

    Future<void> save(Map<String, dynamic> patch, String okMsg) async {
      try {
        await FirebaseFirestore.instance.collection('weddingSites').doc(slug).set(patch, SetOptions(merge: true));
        _toastC(okMsg);
      } catch (_) {
        _toastC('Couldn’t save that - try again.');
      }
    }

    Widget row(IconData ic, String title, String sub, {Widget? trailing}) => Padding(
          padding: const EdgeInsets.only(top: 12),
          child: Row(crossAxisAlignment: CrossAxisAlignment.center, children: <Widget>[
            Icon(ic, size: 18, color: _lzFg(plum)),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                Text(title, style: TextStyle(color: _lzFg(ink), fontSize: 13.5, fontWeight: FontWeight.w700)),
                Text(sub, style: TextStyle(fontSize: 11.5, color: _lzFg(muted), height: 1.35)),
              ]),
            ),
            if (trailing != null) ...<Widget>[const SizedBox(width: 8), trailing],
          ]),
        );

    Widget small(IconData ic, String label, VoidCallback onTap) => ActionChip(
          avatar: Icon(ic, size: 15, color: _lzFg(plum)),
          label: Text(label, style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: _lzFg(plum))),
          backgroundColor: _lzBg(Colors.white.withOpacity(.7)),
          side: BorderSide(color: gold.withOpacity(.6)),
          visualDensity: VisualDensity.compact,
          onPressed: onTap,
        );

    Widget sw(bool v, ValueChanged<bool> onChanged) =>
        Switch(value: v, activeColor: plum, activeTrackColor: gold, onChanged: onChanged);

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
              child: Icon(Icons.visibility_outlined, color: _lzFg(plum), size: 22),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                Text('Visibility', style: TextStyle(color: _lzFg(plum), fontSize: 15.5, fontWeight: FontWeight.w700)),
                Text('Who can find your site, and how.', style: TextStyle(fontSize: 12, color: _lzFg(muted), height: 1.35)),
              ]),
            ),
          ]),
          row(Icons.people_alt_outlined, 'Visible to guests',
              hasPass ? 'Anyone with the link and the password can open it.' : 'Anyone with the link can open it.'),
          Padding(
            padding: const EdgeInsets.only(top: 8, left: 28),
            child: Wrap(spacing: 6, runSpacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: <Widget>[
              SelectableText(link, style: TextStyle(fontSize: 12, color: _lzFg(ink), fontWeight: FontWeight.w600)),
              small(Icons.link_rounded, 'Copy link', () async {
                await Clipboard.setData(ClipboardData(text: link));
                _toastC('Link copied.');
              }),
              small(Icons.edit_outlined, 'Edit website', editSite),
            ]),
          ),
          row(Icons.travel_explore_rounded, 'Allow search engines to link to your site',
              searchOn
                  ? 'Guests can find it by searching your names. Search engines can take days to update.'
                  : 'Search engines are asked not to list it. Changes can take days to show.',
              trailing: sw(searchOn, (bool v) => save(<String, dynamic>{'noindex': !v},
                  v ? 'Search engines may link to your site. Give them a few days.' : 'Search engines are asked to skip your site. It can take days to drop out of results.'))),
          row(Icons.favorite_border_rounded, 'Appear in Find a couple on Lazo',
              findOn
                  ? 'Guests can look you up by name on meetlazo.com.'
                  : 'Only people with the link will find it.',
              trailing: sw(findOn, (bool v) => save(<String, dynamic>{'unlisted': !v},
                  v ? 'You’re back in Find a couple.' : 'Taken out of Find a couple.'))),
          row(Icons.lock_outline_rounded, 'Password',
              hasPass
                  ? 'Guests need the password on the invitation.'
                  : 'No password needed. Anyone with the link can open it.',
              trailing: small(Icons.key_rounded, hasPass ? 'Change' : 'Add a password', editSite)),
        ]),
      ),
    );
  }

"""
rep("  // ---- invitations\n  String _siteUrl(String slug)", HELPERS + "  // ---- invitations\n  String _siteUrl(String slug)")

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8")
print("wrote", DST, len(s.splitlines()), "lines")
