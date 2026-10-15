r"""patch_popups_1014.py - Couple v157 -> v158, Vendor v196 -> v197 (JC-LAZO-POPUP-1014)

Every popup in both dashboards, better:
  - ONE FRAME. Every showModalBottomSheet / showDialog now goes through _lzSheet /
    _lzDialog. Phones: a bottom sheet with a grab handle over a plum veil. Wide
    screens (760 px+): a centred card that rises and fades in, instead of a sheet
    stretched along the bottom of a monitor. Dialogs share one theme (ivory card,
    gold hairline, serif title, 44 px buttons) and the same entrance.
  - THE KIT (both widgets): _lzFrame (icon, serif title, one line under it, close
    and back buttons, scrolling body, a footer that never scrolls away, lifts above
    the keyboard), _lzActions, _lzConfirm, _lzBusy, _lzNote, _lzSection, _lzSteps.
  - COUPLE: "Switching from another planning site" is rebuilt as "Bring your
    wedding to Lazo": pick where you're coming from (the steps name that site's
    menus), five tiles that tick off as things come across, and each import runs
    inside the popup - June reads while you watch, guests show as counts plus the
    first rows, vendors are an editable list (name, what they do, amount, On Lazo
    match, remove, add another), website details are checkboxes, budget lines are
    rows - and every import ends on a done card. The old _askText / _previewOk
    text-dump dialogs are gone.

    python app-patches\patch_popups_1014.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = (HERE / "popup_kit_1014.dart.txt").read_text(encoding="utf-8")
IMPORT = (HERE / "import_v158.dart.txt").read_text(encoding="utf-8")


def popups(s, name):
    """Route every sheet and dialog through the shared frame, then add the kit."""
    n_sheet = s.count("showModalBottomSheet")
    n_dialog = s.count("showDialog")
    s = s.replace("showModalBottomSheet<", "_lzSheet<").replace("showModalBottomSheet(", "_lzSheet(")
    s = s.replace("showDialog<", "_lzDialog<").replace("showDialog(", "_lzDialog(")
    for call in ("showModalBottomSheet<", "showModalBottomSheet(", "showDialog<", "showDialog("):
        assert call not in s, (name, call)
    anchor = "  void _toast(String message) {\n"
    assert s.count(anchor) == 1, name
    s = s.replace(anchor, KIT + anchor)
    print(f"{name}: {n_sheet} sheets and {n_dialog} dialogs now use the shared frame")
    return s


# ---------------- couple ----------------
s = (HERE / "Couple_master_v157.txt").read_text(encoding="utf-8")
a = s.index("  Future<void> _importSheet(Map<String, dynamic> couple) async {\n")
b = s.index("  // ---------------- v97: SAVED VENDORS ----------------\n")
old = s[a:b]


def cut(text, start, end):
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]


parse_csv = cut(old, "  // -- CSV: a small RFC-4180 reader", "  Future<void> _importGuestsCsv(")
june = cut(old, "  Future<Map<String, dynamic>?> _juneImport(", "  Future<String?> _askText(")
june_new = june.replace(
    "  Future<Map<String, dynamic>?> _juneImport(Map<String, dynamic> args) async {",
    "  Future<Map<String, dynamic>?> _juneImport(Map<String, dynamic> args,\n"
    "      {void Function(String)? onError}) async {")
june_new = june_new.replace(
    "      _toast(e.message ?? 'June couldn\\u2019t read that.');",
    "      // a server-side failure arrives as 'internal' / 'unavailable' with a bare code for a message\n"
    "      final bool raw = const <String>['internal', 'unknown', 'unavailable', 'deadline-exceeded'].contains(e.code) ||\n"
    "          (e.message ?? '').trim().length < 16;\n"
    "      final String m = raw\n"
    "          ? 'June couldn\\u2019t read that right now. Try again in a moment.'\n"
    "          : (e.message ?? 'June couldn\\u2019t read that.');\n"
    "      if (onError != null) onError(m); else _toast(m);")
june_new = june_new.replace(
    "      _toast('June couldn\\u2019t read that: $e');",
    "      if (onError != null) onError('June couldn\\u2019t read that. Check your connection and try again.');\n"
    "      else _toast('June couldn\\u2019t read that: $e');")
assert june_new.count("onError") == 5, june_new
s = s[:a] + IMPORT + parse_csv + june_new + "\n" + s[b:]
for gone in ("_askText(", "_previewOk(", "_importRow(", "_importGuestsCsv(", "_importWebsite(", "_importBudget(", "_importVendors("):
    assert gone not in s, gone
s = popups(s, "couple v158")
s = s.replace("JC-LAZO-COUPLE-1014-157", "JC-LAZO-COUPLE-1014-157 / JC-LAZO-POPUP-1014 (v158)", 1)

# ---------------- vendor ----------------
v = (HERE / "Vendor_master_v196.txt").read_text(encoding="utf-8")
v = popups(v, "vendor v197")


def parts(text, base_name, names):
    """Each part rebuilt one region's popups against the frozen base (popup_parts/BRIEF.md)."""
    import importlib.util
    base = HERE / "popup_parts" / base_name
    if not base.exists():
        base.write_text(text, encoding="utf-8")
    assert base.read_text(encoding="utf-8") == text, f"{base_name} no longer matches this script's output"
    for n in names:
        f = HERE / "popup_parts" / f"{n}.py"
        if not f.exists():
            print(f"  part {n}: not there, skipped")
            continue
        sp = importlib.util.spec_from_file_location(n, f)
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        text = m.apply(text)
        print(f"  part {n}: applied")
    return text


s = parts(s, "base_couple.txt", ("cA", "cB", "cC"))
v = parts(v, "base_vendor.txt", ("v1", "v2", "v3", "v4"))
(HERE / "Couple_master_v158.txt").write_text(s, encoding="utf-8")
(HERE / "Vendor_master_v197.txt").write_text(v, encoding="utf-8")
print("wrote Couple_master_v158.txt and Vendor_master_v197.txt")
