"""patch_vendor_v188.py - JC-LAZO-VDASH-1012-188
Vendor_master_v187 -> v188:
  HOW DID YOU HEAR ABOUT LAZO? A vendor who is not in the directory yet (Add your business -> listingRequests)
  now picks a source before submitting (Google search, ChatGPT or another AI assistant, Instagram, Facebook,
  TikTok, a couple or client, another vendor, Zola / The Knot / WeddingWire, an email or text from Lazo,
  word of mouth, other + a free-text line). Saved as listingRequests.heardAbout / heardAboutDetail, shown on
  the admin card, and copied onto the vendor doc at approval so attribution stays with the listing.
  (2026-10-12: TickTickBoom's source had to be reconstructed from site sessions by hand; it was ChatGPT.)
  python app-patches\\patch_vendor_v188.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent


def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    return s.replace(old, new)


src = (HERE / "Vendor_master_v187.txt").read_text(encoding="utf-8")
s = src

# build tag
s = rep(s, "// Build ID: JC-LAZO-VDASH-1011-187 (",
        "// Build ID: JC-LAZO-VDASH-1012-188 (v188: HOW DID YOU HEAR ABOUT LAZO - the Add your business form asks for the source (required) and stores listingRequests.heardAbout / heardAboutDetail; the admin card shows it and approval copies it onto the vendor doc. JC-LAZO-VDASH-1012-188; base v187) (", "build tag")

# 1. state for the listing form
s = rep(s, """    final TextEditingController legalEntityC = TextEditingController();
    final Set<String> picked = <String>{};""",
"""    final TextEditingController legalEntityC = TextEditingController();
    final TextEditingController heardOtherC = TextEditingController();
    String? heardAbout; // JC-LAZO-VDASH-1012-188
    final Set<String> picked = <String>{};""", "state")

# 2. required before submit
s = rep(s, """                picked.isNotEmpty &&
                pb != null;""",
"""                picked.isNotEmpty &&
                heardAbout != null &&
                pb != null;""", "canSubmit")

# 3. saved with the request
s = rep(s, """                  'legalEntityName': legalEntityC.text.trim(),
                  'proofPath': proofPath,
                });""",
"""                  'legalEntityName': legalEntityC.text.trim(),
                  'proofPath': proofPath,
                  'heardAbout': heardAbout ?? '',
                  'heardAboutDetail': heardOtherC.text.trim(),
                });""", "submit")

# 4. the field, after the legal entity name
s = rep(s, """                          decoration:
                              ldeco('Legal entity name (if different)')),
                      const SizedBox(height: 16),
                       Text('WHAT DO YOU DO?',""",
"""                          decoration:
                              ldeco('Legal entity name (if different)')),
                      const SizedBox(height: 12),
                      // JC-LAZO-VDASH-1012-188: where they came from
                      DropdownButtonFormField<String>(
                        value: heardAbout,
                        isExpanded: true,
                        decoration: ldeco('How did you hear about Lazo?'),
                        style: TextStyle(
                            color: _lzFg(ink),
                            fontSize: 15,
                            fontWeight: FontWeight.w500),
                        dropdownColor: _lzBg(ivory),
                        items: const [
                          DropdownMenuItem<String>(
                              value: 'Google search',
                              child: Text('Google search')),
                          DropdownMenuItem<String>(
                              value: 'ChatGPT or another AI assistant',
                              child: Text('ChatGPT or another AI assistant')),
                          DropdownMenuItem<String>(
                              value: 'Instagram', child: Text('Instagram')),
                          DropdownMenuItem<String>(
                              value: 'Facebook', child: Text('Facebook')),
                          DropdownMenuItem<String>(
                              value: 'TikTok', child: Text('TikTok')),
                          DropdownMenuItem<String>(
                              value: 'A couple or client',
                              child: Text('A couple or client')),
                          DropdownMenuItem<String>(
                              value: 'Another vendor',
                              child: Text('Another vendor')),
                          DropdownMenuItem<String>(
                              value: 'Zola, The Knot or WeddingWire',
                              child: Text('Zola, The Knot or WeddingWire')),
                          DropdownMenuItem<String>(
                              value: 'An email or text from Lazo',
                              child: Text('An email or text from Lazo')),
                          DropdownMenuItem<String>(
                              value: 'Word of mouth',
                              child: Text('Word of mouth')),
                          DropdownMenuItem<String>(
                              value: 'Other', child: Text('Other')),
                        ],
                        onChanged: busy
                            ? null
                            : (String? val) {
                                setD(() {
                                  heardAbout = val;
                                });
                              },
                      ),
                      if (heardAbout == 'Other') ...[
                        const SizedBox(height: 12),
                        TextField(
                            controller: heardOtherC,
                            enabled: !busy,
                            cursorColor: _lzFg(plum),
                            style: TextStyle(color: _lzFg(ink), fontSize: 15),
                            decoration: ldeco('Where exactly? (optional)')),
                      ],
                      const SizedBox(height: 16),
                       Text('WHAT DO YOU DO?',""", "field")

# 5. admin card line
s = rep(s, """    if (req['metroId'] != null) {
      lines.add('Metro: ' + _metroLabel(req['metroId'].toString()));
    }""",
"""    if (req['metroId'] != null) {
      lines.add('Metro: ' + _metroLabel(req['metroId'].toString()));
    }
    if (req['heardAbout'] != null && req['heardAbout'].toString().isNotEmpty) {
      lines.add('Heard about Lazo: ' +
          req['heardAbout'].toString() +
          (req['heardAboutDetail'] != null &&
                  req['heardAboutDetail'].toString().isNotEmpty
              ? ' (' + req['heardAboutDetail'].toString() + ')'
              : ''));
    }""", "admin card")

# 6. keep the source on the vendor doc at approval
s = rep(s, """            'serviceArea': true,
            'seededAt': FieldValue.serverTimestamp(),""",
"""            'serviceArea': true,
            'heardAbout': req['heardAbout'] == null ? '' : req['heardAbout'].toString(),
            'seededAt': FieldValue.serverTimestamp(),""", "approval")

out = HERE / "Vendor_master_v188.txt"
out.write_text(s, encoding="utf-8", newline="")
print("wrote", out.name, len(s), "chars;", s.count("heardAbout"), "heardAbout refs")
