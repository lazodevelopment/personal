"""patch_couple_v143.py - Couple dashboard v143
Couple_master_v142.txt -> Couple_master_v143.txt. Anchor-asserted.
  The wedding-website dialog's jump bar ("The two of you / Your story /
  The day ...") used Material ActionChips with a 16%-gold background. Under
  the app's Material 3 theme the chip composites that translucent colour over
  the theme surface, which on a phone came out as dark grey pills with plum
  text on top: unreadable. The pills are now plain ink-free containers with
  opaque cream fill, a gold hairline and plum text, same tap behaviour.
  python app-patches\\patch_couple_v143.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "Couple_master_v142.txt"
DST = HERE / "Couple_master_v143.txt"
s = SRC.read_text(encoding="utf-8")

old = """          return Padding(
            padding: const EdgeInsets.only(right: 6),
            child: ActionChip(
              label: Text(
                  label[0] + label.substring(1).toLowerCase(),
                  style: const TextStyle(
                      color: plum, fontSize: 11.5, fontWeight: FontWeight.w700)),
              backgroundColor: gold.withOpacity(.16),
              side: BorderSide(color: gold.withOpacity(.5)),
              padding: const EdgeInsets.symmetric(horizontal: 8),
              onPressed: () {
                HapticFeedback.selectionClick();
                final BuildContext? c = e.value.currentContext;
                if (c != null) {
                  Scrollable.ensureVisible(c,
                      duration: const Duration(milliseconds: 320),
                      alignment: 0.02,
                      curve: Curves.easeOutCubic);
                }
              },
            ),
          );"""
new = """          // v143: an opaque pill, not an ActionChip (M3 tinted the translucent
          // gold over the theme surface and the pills came out dark grey)
          return Padding(
            padding: const EdgeInsets.only(right: 6),
            child: Material(
              color: const Color(0xFFF7F0E1),
              shape: StadiumBorder(side: BorderSide(color: gold.withOpacity(.7))),
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: () {
                  HapticFeedback.selectionClick();
                  final BuildContext? c = e.value.currentContext;
                  if (c != null) {
                    Scrollable.ensureVisible(c,
                        duration: const Duration(milliseconds: 320),
                        alignment: 0.02,
                        curve: Curves.easeOutCubic);
                  }
                },
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  child: Text(
                      label[0] + label.substring(1).toLowerCase(),
                      style: const TextStyle(
                          color: plum,
                          fontSize: 11.5,
                          fontWeight: FontWeight.w700)),
                ),
              ),
            ),
          );"""
assert s.count(old) == 1, f"anchor x{s.count(old)}"
s = s.replace(old, new)
s = s.replace("// v142:", "// v143 (website dialog pills readable on phones) / v142:", 1) if "// v142:" in s else s
DST.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {DST.name}: {len(s):,} chars; brace balance {s.count('{') - s.count('}')}, paren balance {s.count('(') - s.count(')')}")
