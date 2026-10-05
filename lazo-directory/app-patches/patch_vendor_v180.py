"""patch_vendor_v180.py - JC-LAZO-VDASH-1004-180
Talk to June: a gold "Talk to June" button in the Ask June card header opens the
June hub (june-hub worker: the brief read aloud in her voice, the living core,
weather, local news, who is waiting, money, confirm-first actions). The vendor
signs in there once with the same Lazo login. The in-card text chat stays as it is.

Anchor-and-assert against Vendor_master_v179.txt; writes Vendor_master_v180.txt.
  python app-patches\\patch_vendor_v180.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent
src = HERE / "Vendor_master_v179.txt"; dst = HERE / "Vendor_master_v180.txt"
s = src.read_text(encoding="utf-8")
if "VDASH-1004-180" in s:
    raise SystemExit("already patched")

def rep(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    s = s.replace(old, new)

# ---- build id line
rep("// Build ID: JC-LAZO-VDASH-0924-179 (v179:",
    "// Build ID: JC-LAZO-VDASH-1004-180 (v180: TALK TO JUNE - a gold button in the Ask June card header opens the June hub (kJuneHubUrl) in the browser: the day's brief read aloud, voice chat, weather, local news, money, confirm-first actions; same Lazo login. base v179)\n// (v179:",
    "build id")

# ---- the hub address, next to the metro table
rep("  static const Map<String, List<double>> kMetroLatLng = <String, List<double>>{",
    "  // v180: the June hub (june-hub worker). Swap for june.meetlazo.com once the custom domain is on.\n"
    "  static const String kJuneHubUrl = 'https://june-hub.floral-credit-e4f0.workers.dev/';\n\n"
    "  static const Map<String, List<double>> kMetroLatLng = <String, List<double>>{",
    "hub url")

# ---- the button in the Ask June card header
rep('''          Row(children: <Widget>[
            _cardIconChip(Icons.auto_awesome_rounded),
            const Expanded(
              child: Text('Ask June',
                  style: TextStyle(
                      color: plum, fontSize: 15, fontWeight: FontWeight.w700)),
            ),
            _foldBtn('june'),
          ]),
          const SizedBox(height: 4),
          const Text(
              'She reads your real leads, money and dates - and drafts, tags and adds tasks when you say so.',
              style: TextStyle(fontSize: 11.5, color: muted, height: 1.35)),''',
'''          Row(children: <Widget>[
            _cardIconChip(Icons.auto_awesome_rounded),
            const Expanded(
              child: Text('Ask June',
                  style: TextStyle(
                      color: plum, fontSize: 15, fontWeight: FontWeight.w700)),
            ),
            // v180: the full June - voice, brief, weather, news - lives in the hub
            TextButton.icon(
              onPressed: _h(() => _openUrl(kJuneHubUrl)),
              icon: const Icon(Icons.graphic_eq_rounded,
                  size: 16, color: plumDeep),
              label: const Text('Talk to June',
                  style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: plumDeep)),
              style: TextButton.styleFrom(
                backgroundColor: gold,
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                minimumSize: const Size(0, 30),
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(999)),
              ),
            ),
            const SizedBox(width: 6),
            _foldBtn('june'),
          ]),
          const SizedBox(height: 4),
          const Text(
              'She reads your real leads, money and dates - and drafts, tags and adds tasks when you say so. Talk to June opens her hub: today\\'s brief read aloud, weather, local news and more.',
              style: TextStyle(fontSize: 11.5, color: muted, height: 1.35)),''',
    "ask june header")

dst.write_text(s, encoding="utf-8")
print("wrote", dst.name, len(s), "chars")
