r"""patch_links_1018.py - TAPS THAT DID NOTHING (Lazo profile, website, license and site links).  JC-LAZO-LINKS-1018

Every link in the dashboards asked canLaunchUrl() first and silently did nothing when it said no. On Android 11+
canLaunchUrl() answers no for web links unless the app's manifest declares a <queries> entry, which FlutterFlow
builds don't add, so the couple's "Lazo profile" button on a vendor (and six other couple links, one vendor link)
were dead taps. Now web, phone, email and text links always go to launchUrl (which needs no <queries>); only other
schemes are still pre-checked.

    python app-patches\patch_links_1018.py couple Couple_master_v166.txt Couple_master_v169.txt
    python app-patches\patch_links_1018.py vendor Vendor_master_v206.txt Vendor_master_v209.txt
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
which, src, dst = sys.argv[1], sys.argv[2], sys.argv[3]
SRC, DST = HERE / src, HERE / dst
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")

CLASS = {"couple": "class LazoCoupleDashboard extends StatefulWidget", "vendor": "class LazoVendorDashboard extends StatefulWidget"}[which]
COUNT = {"couple": 7, "vendor": 1}[which]
SIDE = {"couple": "COUPLE", "vendor": "VENDOR"}[which]


def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, f"expected {n} match(es), found {c}: {old[:90]!r}"
    s = s.replace(old, new)


i = s.index("// Build ID:")
s = (s[:i] + f"// Build ID: JC-LAZO-LINKS-1018-{SIDE} ({DST.stem.split('_v')[-1] and 'v' + DST.stem.split('_v')[-1]}: "
     "TAPS THAT DID NOTHING - web, phone, email and text links no longer wait on canLaunchUrl, which says no on "
     f"Android without a manifest <queries> entry; base {SRC.stem.split('_master_')[-1]})\n" + s[i:])

rep("await canLaunchUrl(", "await _lzCanLaunch(", COUNT)

rep(CLASS, """// JC-LAZO-LINKS-1018: canLaunchUrl() needs a <queries> entry on Android 11+ that FlutterFlow
// builds don't add, so it said no to every web link and the tap did nothing. Web, phone,
// email and text links always go to launchUrl (which needs no <queries>); other schemes
// are still asked.
Future<bool> _lzCanLaunch(Uri u) async {
  const Set<String> always = <String>{'http', 'https', 'tel', 'mailto', 'sms'};
  if (always.contains(u.scheme.toLowerCase())) return true;
  try {
    return await canLaunchUrl(u);
  } catch (_) {
    return false;
  }
}

""" + CLASS)

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8", newline="")
print(f"wrote {DST.name} from {SRC.name} ({len(s):,} chars)")
