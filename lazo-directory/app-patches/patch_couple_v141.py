"""patch_couple_v141.py - JC-LAZO-COUPLE-0929-V141
PEONY - the twenty-first website design (blush, peony & champagne; pairs with
wedding-websites/themes_peony.py and worker TEMPLATES). The editor's design
list gains it with its four palettes, and the two "known template" lists
accept it (the marketing page's ?template=peony and a saved doc).
Applies on top of Couple_master_v140.txt -> Couple_master_v141.txt.
  python app-patches\\patch_couple_v141.py [src] [out]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v140.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "Couple_master_v141.txt"
s = SRC.read_text(encoding="utf-8")
if "JC-LAZO-COUPLE-0929-V141" in s:
    raise SystemExit("already applied")


def swap(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"ABORT [{label}]: anchor matched {n} times, expected {count}")
    s = s.replace(old, new)
    print(f"  ok  {label}")


swap("// (v140: THE OPEN ITEMS",
     "// (v141: PEONY - a twenty-first website design (blush, peony & champagne, Playfair type) in the editor's picker with four palettes; pairs with wedding-websites/themes_peony.py. JC-LAZO-COUPLE-0929-V141; base v140)\n// (v140: THE OPEN ITEMS",
     "header")
swap("""      'marigold',
      'papel'
    ];
    if (!known.contains(tpl)) return;
""", """      'marigold',
      'papel',
      'peony'
    ];
    if (!known.contains(tpl)) return;
""", "known list (deep link)")
swap("""      'marigold',
      'papel'
    ].contains(template)) {
      template = 'fete';
    }
""", """      'marigold',
      'papel',
      'peony'
    ].contains(template)) {
      template = 'fete';
    }
""", "known list (editor)")
swap("""      'papel': <List<dynamic>>[
        <dynamic>['fiesta', 0xFFE0512F, 0xFFFFF9F2],
        <dynamic>['cobalt', 0xFF1F4FB8, 0xFFF4F7FC],
        <dynamic>['terracotta', 0xFFB8542E, 0xFFFBF5EF],
        <dynamic>['jade', 0xFF159A72, 0xFFF3FAF7],
      ],
    };
""", """      'papel': <List<dynamic>>[
        <dynamic>['fiesta', 0xFFE0512F, 0xFFFFF9F2],
        <dynamic>['cobalt', 0xFF1F4FB8, 0xFFF4F7FC],
        <dynamic>['terracotta', 0xFFB8542E, 0xFFFBF5EF],
        <dynamic>['jade', 0xFF159A72, 0xFFF3FAF7],
      ],
      'peony': <List<dynamic>>[
        <dynamic>['peony', 0xFFC2506F, 0xFFFDF7F8],
        <dynamic>['champagne', 0xFFB9924E, 0xFFFCF8F2],
        <dynamic>['dusk', 0xFF8B62A8, 0xFFFAF7FB],
        <dynamic>['ivory', 0xFFA9766A, 0xFFFCFBF8],
      ],
    };
""", "palettes")
swap("""                            <dynamic>[
                              'papel',
                              'Papel',
                              'Latin fiesta \\u00b7 papel picado',
                              const Color(0xFFE0512F)
                            ],
                          ].map((List<dynamic> t) {
""", """                            <dynamic>[
                              'papel',
                              'Papel',
                              'Latin fiesta \\u00b7 papel picado',
                              const Color(0xFFE0512F)
                            ],
                            <dynamic>[
                              'peony',
                              'Peony',
                              'Blush \\u00b7 peony & champagne \\u00b7 petals in the air',
                              const Color(0xFFC2506F)
                            ],
                          ].map((List<dynamic> t) {
""", "picker row")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT.name} ({len(s):,} chars)")
