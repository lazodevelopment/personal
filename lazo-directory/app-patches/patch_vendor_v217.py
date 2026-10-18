"""Vendor v217: a lead says where it really came from (JC-LAZO-LEADSOURCE-1018-VENDOR).

    python app-patches\\patch_vendor_v217.py [base.txt]   # base defaults to Vendor_master_v216.txt
                                                          # writes Vendor_master_v217.txt
- the thread's lead strip said "From your website" for every off-platform lead. Now it reads the
  lead's source: "From Zola" / "From The Knot" / "From WeddingWire" / "From Joy" / "From Instagram"
  / "From a forwarded email" (leads@meetlazo.com forwards, sourceRef.platform), "From your booking
  link" (source 'book'), "Added by you" (Add a client), or "From your website" / the page's host
  for the lead form. The icon follows (forward_to_inbox for forwards, event for the booking link,
  person_add for added clients, language for the form).
- the inbox card shows the same source as a small tag next to the name instead of a bare globe.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Vendor_master_v216.txt"
DST = HERE / "Vendor_master_v217.txt"
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
    "// Build ID: JC-LAZO-LEADSOURCE-1018-VENDOR (v217: WHERE A LEAD CAME FROM - the thread strip and the inbox card say "
    "Zola, The Knot, WeddingWire, Joy, Instagram, a forwarded email, your booking link, added by you, or your website, "
    "from the lead's source and sourceRef.platform, instead of 'From your website' for everything; base v216)\n"
) + s[first_build:]

HELPERS = r'''
  // v217: the lead's origin, from source + sourceRef.platform (leads@ forwards), as a label and an icon
  static const Map<String, String> _kLeadPlatforms = <String, String>{
    'theknot': 'The Knot', 'zola': 'Zola', 'weddingwire': 'WeddingWire', 'joy': 'Joy', 'instagram': 'Instagram',
  };
  String _leadSourceLabel(Map<String, dynamic> inq) {
    final String source = (inq['source'] ?? '').toString();
    final Map<String, dynamic> src = inq['sourceRef'] is Map ? Map<String, dynamic>.from(inq['sourceRef'] as Map) : <String, dynamic>{};
    if (source == 'email-forward') {
      return _kLeadPlatforms[(src['platform'] ?? '').toString()] ?? 'a forwarded email';
    }
    if (source == 'book') return 'your booking link';
    if (source == 'addClient' || source == 'manual') return 'added by you';
    final String page = (src['page'] ?? '').toString();
    if (page.isNotEmpty) {
      try {
        final String host = Uri.parse(page).host.replaceFirst('www.', '');
        if (host.isNotEmpty) return host;
      } catch (_) {}
    }
    return 'your website';
  }
  IconData _leadSourceIcon(Map<String, dynamic> inq) {
    final String source = (inq['source'] ?? '').toString();
    if (source == 'email-forward') return Icons.forward_to_inbox_rounded;
    if (source == 'book') return Icons.event_available_rounded;
    if (source == 'addClient' || source == 'manual') return Icons.person_add_alt_1_rounded;
    return Icons.language_rounded;
  }

  Widget _leadSourceStrip(String inquiryId, Map<String, dynamic> inq) {'''

rep("\n  Widget _leadSourceStrip(String inquiryId, Map<String, dynamic> inq) {", HELPERS)

rep("""    String where = 'your website';
    final String page = (src['page'] ?? '').toString();
    try {
      if (page.isNotEmpty)
        where = Uri.parse(page).host.replaceFirst('www.', '');
    } catch (_) {}""",
    """    // v217: Zola, The Knot, a forwarded email, the booking link, added by you, or the website
    final String where = _leadSourceLabel(inq);
    final bool addedByYou = where == 'added by you';""")
rep("""             Icon(Icons.language_rounded, size: 15, color: _lzFg(plum)),
            const SizedBox(width: 7),
            Expanded(
              child: Text('From $where$camp',""",
    """             Icon(_leadSourceIcon(inq), size: 15, color: _lzFg(plum)),
            const SizedBox(width: 7),
            Expanded(
              child: Text(addedByYou ? 'Added by you$camp' : 'From $where$camp',""")

# inbox card: a small source tag instead of the bare globe
rep("""            if (m['offPlatform'] == true)
               Icon(Icons.language_rounded, size: 12, color: _lzFg(muted)),""",
    """            if (m['offPlatform'] == true)
              Padding(
                padding: const EdgeInsets.only(left: 4),
                child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                  Icon(_leadSourceIcon(m), size: 12, color: _lzFg(muted)),
                  if ((m['source'] ?? '') == 'email-forward' || (m['source'] ?? '') == 'book') ...<Widget>[
                    const SizedBox(width: 3),
                    Text(_leadSourceLabel(m) == 'your booking link' ? 'Booking link' : _leadSourceLabel(m),
                        style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: _lzFg(muted))),
                  ],
                ]),
              ),""")

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8")
print("wrote", DST.name, len(s.splitlines()), "lines")
