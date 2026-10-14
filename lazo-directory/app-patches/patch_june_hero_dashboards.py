"""patch_june_hero_dashboards.py - JC-LAZO-JUNE-HERO-1013-001
Vendor_master_v188.txt -> Vendor_master_v189.txt and Couple_master_v152.txt -> Couple_master_v153.txt:
June's hero (JuneNative build 006, layout 'hero') becomes the top of both dashboards, on the dashboard's
own cover photo and scrim. What changes inside the hero card:
  vendor: the big business name becomes a small caps line that keeps the verified pill, the badges and
          the verify action; June's hero follows; the live stat tiles (waiting, average reply, next
          wedding, views) sit beneath it - a swipeable row on phones, the row they already were on wide.
  couple: the tappable eyebrow (names, date, city -> the setup sheet) and the camera pill stay; the big
          countdown and the local "June's read" line give way to June's hero (her line comes from the
          brief); the countdown becomes the first tile, in gold; "This week:" setup step stays under
          the tiles; the tiles become a swipeable row on phones.
JuneNative must be build 006 or later in the project first.
  python app-patches\\patch_june_hero_dashboards.py
"""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from patch_lazo_fab import apply_fab
from patch_lazo_weather import apply_weather
from patch_vendor_couple_view import apply_couple_view


def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:80]!r}")
    return s.replace(old, new)


# JC-LAZO-JUNE-HERO-1013-002: on phones every tile is visible in a grid - nothing scrolls off, nothing is
# clipped; with an odd count the first tile (the countdown, or who is waiting) spans the width, so no row is half empty
SWIPE = """Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                if (tiles.length.isOdd) ...<Widget>[
                  tiles.first,
                  if (tiles.length > 1) const SizedBox(height: 10),
                ],
                _twoUp(tiles.length.isOdd ? tiles.sublist(1) : tiles),
              ],
            )"""

# wide screens: the tiles as a two-column block on the right of the hero, filling the card instead of
# leaving its right half empty (the couple dashboard already builds its wide grid this way)
PAIRS = """IntrinsicHeight(
                child: Row(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: <Widget>[
                      for (int i = 0; i < tiles.length; i += 2)
                        Padding(
                          padding: EdgeInsets.only(left: i == 0 ? 0 : 10),
                          child: SizedBox(
                            width: 168,
                            // a column with one tile lets it fill the height: no empty slot
                            child: Column(children: <Widget>[
                              Expanded(child: tiles[i]),
                              if (i + 1 < tiles.length) ...<Widget>[
                                const SizedBox(height: 10),
                                Expanded(child: tiles[i + 1]),
                              ],
                            ]),
                          ),
                        ),
                    ]),
              )"""

# ---------------------------------------------------------------- vendor
v = (HERE / "Vendor_master_v188.txt").read_text(encoding="utf-8-sig")
v = rep(v, """            Text(name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: _serif(
                    size: wide ? 34 : 28,
                    weight: FontWeight.w500,
                    color: ivory)),
            const SizedBox(height: 8),""",
        """            // JC-LAZO-JUNE-HERO-1013-001: the business name is the eyebrow now; June's greeting leads
            Text(name.toUpperCase(),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                    color: ivory,
                    fontSize: 11.5,
                    letterSpacing: 2,
                    fontWeight: FontWeight.w600,
                    shadows: <Shadow>[
                      Shadow(
                          color: Color(0x99000000),
                          blurRadius: 6,
                          offset: Offset(0, 1)),
                    ])),
            const SizedBox(height: 8),""", "vendor name -> eyebrow")
v = rep(v, """        final Widget grid = wide
            ? IntrinsicHeight(
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    for (int i = 0; i < tiles.length; i++) ...<Widget>[
                      if (i > 0) const SizedBox(width: 10),
                      SizedBox(width: 158, child: tiles[i]),
                    ],
                  ],
                ),
              )
            : _twoUp(tiles);
        return Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: gold),
          ),""",
        """        final Widget grid = wide
            ? """ + PAIRS + """
            : """ + SWIPE + """;
        // JC-LAZO-JUNE-HERO-1013-002: the gold border is painted on top (as the couple card does since
        // v117), so the cover gradient can no longer cover it at the corners and along the dark bottom
        return Container(
          decoration: const BoxDecoration(
              borderRadius: BorderRadius.all(Radius.circular(22)), color: plum),
          foregroundDecoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: gold),
          ),""", "vendor grid + border")
v = rep(v, """                // JC-LAZO-VDASH-1010-186: the deck - the name and the numbers along
                // the top, June across it.
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    wide
                        ? Row(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: <Widget>[
                              Expanded(child: nameBlock),
                              const SizedBox(width: 20),
                              grid,
                            ],
                          )
                        : Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              nameBlock,
                              const SizedBox(height: 16),
                              grid,
                            ],
                          ),
                    SizedBox(height: wide ? 22 : 18),
                    Container(height: 1, color: gold.withOpacity(.38)),
                    SizedBox(height: wide ? 22 : 18),
                    KeyedSubtree(
                        key: _kTourJune,
                        child: const JuneNative(role: 'vendor', layout: 'deck')),
                  ],
                ),""",
        """                // JC-LAZO-JUNE-HERO-1013-001/002: June is the top of the dashboard - the business
                // and its badges as the eyebrow, her hero, then the live numbers (beside her on wide
                // screens, so the card has no empty half; under her on phones).
                // Beside her only when the card has room for both (>= 1040): narrower wide cards stack the
                // tiles under her in one even row, so June is never squeezed into a strip.
                child: LayoutBuilder(builder: (BuildContext hc, BoxConstraints hb) {
                  final Widget june = KeyedSubtree(
                      key: _kTourJune,
                      child: const JuneNative(role: 'vendor', layout: 'hero'));
                  if (wide && hb.maxWidth >= 1040) {
                    return Row(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: <Widget>[
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            mainAxisSize: MainAxisSize.min,
                            children: <Widget>[
                              nameBlock,
                              const SizedBox(height: 18),
                              june,
                            ],
                          ),
                        ),
                        const SizedBox(width: 28),
                        grid,
                      ],
                    );
                  }
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: <Widget>[
                      nameBlock,
                      const SizedBox(height: 14),
                      june,
                      const SizedBox(height: 18),
                      wide
                          ? IntrinsicHeight(
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: <Widget>[
                                  for (int i = 0; i < tiles.length; i++) ...<Widget>[
                                    if (i > 0) const SizedBox(width: 10),
                                    Expanded(child: tiles[i]),
                                  ],
                                ],
                              ),
                            )
                          : grid,
                    ],
                  );
                }),""", "vendor layout")

# JC-LAZO-JUNE-HERO-1013-002: the Today / Pipeline / Money / Studio / Profile switch spans the width - equal
# segments that always fit (icon over label on phones, side by side when there is room), so nothing is
# cut mid-word on a phone and nothing is left empty beside it on a desktop
v = rep(v, """  static const double _kSegW = 116;
  static const double _kSegH = 38;

  // v175: one plum pill glides between positions; the labels stay put.
  Widget _dashModeToggle() {
    int idx = _kModes.indexWhere((List<dynamic> m) => m[0] == _dashMode);
    if (idx < 0) idx = 0;
    final bool reduced = _reducedMotion(context);
    return Align(
      key: _kTourModes,
      alignment: Alignment.centerLeft,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Container(
          padding: const EdgeInsets.all(4),
          decoration: BoxDecoration(
            color: _lzBg(const Color(0xFFF1E9E1)),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: _lzLine(goldLine)),
          ),
          child: SizedBox(
            width: _kSegW * _kModes.length,
            height: _kSegH,
            child: Stack(children: <Widget>[
              AnimatedPositioned(
                duration: Duration(milliseconds: reduced ? 0 : 280),
                curve: Curves.easeOutCubic,
                left: idx * _kSegW,
                top: 0,
                bottom: 0,
                width: _kSegW,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                      color: plum, borderRadius: BorderRadius.circular(9)),
                ),
              ),
              Row(children: <Widget>[
                for (int i = 0; i < _kModes.length; i++) _modeSeg(i),
              ]),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _modeSeg(int i) {""",
        """  // v175: one plum pill glides between positions; the labels stay put.
  Widget _dashModeToggle() {
    int idx = _kModes.indexWhere((List<dynamic> m) => m[0] == _dashMode);
    if (idx < 0) idx = 0;
    final bool reduced = _reducedMotion(context);
    return LayoutBuilder(
      key: _kTourModes,
      builder: (BuildContext c, BoxConstraints box) {
        final double segW = (box.maxWidth - 10) / _kModes.length;
        final bool compact = segW < 104; // phones: icon over label
        final double segH = compact ? 52 : 40;
        return Container(
          padding: const EdgeInsets.all(4),
          decoration: BoxDecoration(
            color: _lzBg(const Color(0xFFF1E9E1)),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: _lzLine(goldLine)),
          ),
          child: SizedBox(
            height: segH,
            child: Stack(children: <Widget>[
              AnimatedPositioned(
                duration: Duration(milliseconds: reduced ? 0 : 280),
                curve: Curves.easeOutCubic,
                left: idx * segW,
                top: 0,
                bottom: 0,
                width: segW,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                      color: plum, borderRadius: BorderRadius.circular(9)),
                ),
              ),
              Row(children: <Widget>[
                for (int i = 0; i < _kModes.length; i++)
                  _modeSeg(i, segW, segH, compact),
              ]),
            ]),
          ),
        );
      },
    );
  }

  Widget _modeSeg(int i, double segW, double segH, bool compact) {""", "mode toggle full width")
v = rep(v, """      child: SizedBox(
        width: _kSegW,
        height: _kSegH,
        child:
            Row(mainAxisAlignment: MainAxisAlignment.center, children: <Widget>[
          Icon(_kModes[i][2] as IconData, size: 15, color: _lzFg(sel ? gold : muted)),
          const SizedBox(width: 7),
          AnimatedDefaultTextStyle(
            duration: const Duration(milliseconds: 200),
            curve: Curves.easeOut,
            style: TextStyle(
                color: _lzFg(sel ? ivory : muted),
                fontSize: 13.5,
                fontWeight: sel ? FontWeight.w700 : FontWeight.w600),
            child: Text(_kModes[i][1] as String),
          ),
          if (locked) ...<Widget>[
            const SizedBox(width: 6),
            Icon(Icons.lock_rounded,
                size: 12, color: _lzFg(sel ? gold : muted.withOpacity(.7))),
          ],
        ]),
      ),""",
        """      child: SizedBox(
        width: segW,
        height: segH,
        child: compact
            ? Column(mainAxisAlignment: MainAxisAlignment.center, children: <Widget>[
                Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                  Icon(_kModes[i][2] as IconData, size: 18, color: _lzFg(sel ? gold : muted)),
                  if (locked) ...<Widget>[
                    const SizedBox(width: 3),
                    Icon(Icons.lock_rounded,
                        size: 10, color: _lzFg(sel ? gold : muted.withOpacity(.7))),
                  ],
                ]),
                const SizedBox(height: 3),
                AnimatedDefaultTextStyle(
                  duration: const Duration(milliseconds: 200),
                  curve: Curves.easeOut,
                  style: TextStyle(
                      color: _lzFg(sel ? ivory : muted),
                      fontSize: 11,
                      fontWeight: sel ? FontWeight.w700 : FontWeight.w600),
                  child: Text(_kModes[i][1] as String, maxLines: 1, overflow: TextOverflow.fade, softWrap: false),
                ),
              ])
            : Row(mainAxisAlignment: MainAxisAlignment.center, children: <Widget>[
                Icon(_kModes[i][2] as IconData, size: 15, color: _lzFg(sel ? gold : muted)),
                const SizedBox(width: 7),
                AnimatedDefaultTextStyle(
                  duration: const Duration(milliseconds: 200),
                  curve: Curves.easeOut,
                  style: TextStyle(
                      color: _lzFg(sel ? ivory : muted),
                      fontSize: 13.5,
                      fontWeight: sel ? FontWeight.w700 : FontWeight.w600),
                  child: Text(_kModes[i][1] as String),
                ),
                if (locked) ...<Widget>[
                  const SizedBox(width: 6),
                  Icon(Icons.lock_rounded,
                      size: 12, color: _lzFg(sel ? gold : muted.withOpacity(.7))),
                ],
              ]),
      ),""", "mode segment compact")
v = v.replace("JC-LAZO-VDASH", "JC-LAZO-VDASH", 1)
# JC-LAZO-JUNE-HERO-1013-002: a tile's small print may take two lines (a half-width tile cut "Timed from your fi...")
v = rep(v, """          Text(sub,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 12, color: ivory.withOpacity(.78))),""",
        """          Text(sub,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 12, height: 1.3, color: ivory.withOpacity(.78))),""", "vendor tile footnote")
v = apply_fab(v, "_vendorFab", 16, 18, 54, "lazo_fab_vendor", rep)
v = apply_weather(v, "vendor", rep)
v = apply_couple_view(v, rep)
(HERE / "Vendor_master_v189.txt").write_text(v, encoding="utf-8")
print("wrote Vendor_master_v189.txt", len(v))

# ---------------------------------------------------------------- couple
c = (HERE / "Couple_master_v152.txt").read_text(encoding="utf-8-sig")
# the countdown becomes the first tile
c = rep(c, """    final List<Widget> tiles = <Widget>[
      _heroTile(
          'Vendor team',""",
        """    final List<Widget> tiles = <Widget>[
      // JC-LAZO-JUNE-HERO-1013-001: the countdown, now the first tile
      _heroTile(
          daysOut == null ? 'Your day' : (daysOut < 0 ? 'Married' : 'Countdown'),
          daysOut == null ? 'Set' : (daysOut == 0 ? 'Today' : '${daysOut.abs()}'),
          daysOut == null || daysOut == 0 ? '' : (daysOut < 0 ? 'days since' : 'days to go'),
          wedding == null ? 'Tap your names above to add it' : _longDate(wedding),
          accent: gold),
      _heroTile(
          'Vendor team',""", "couple countdown tile")
# the big countdown and the local read give way to June's hero
a = c.index("        Row(\n            crossAxisAlignment: CrossAxisAlignment.baseline,\n            textBaseline: TextBaseline.alphabetic,\n            children: <Widget>[\n              Text(\n                  daysOut == null")
b = c.index("        if (steps.isNotEmpty) ...<Widget>[", a)
seg = c[a:b]
if "_juneRead(" not in seg:
    raise SystemExit("couple: the countdown/read segment is not where expected")
c = c[:a] + c[b:]
# lift "This week:" out of the name block so it sits under the tiles, not between the eyebrow and June
NL = "\n"
sa = c.index("        if (steps.isNotEmpty) ...<Widget>[", a - 10)
close_steps = "        ]," + NL
end_marker = close_steps + "      ]," + NL + "    );" + NL
sb = c.index(end_marker, sa)
step_seg = c[sa:sb + len(close_steps)]
c = c[:sa] + c[sb + len(close_steps):]
nb_end = c.index("    );" + NL, sa - 40) + len("    );" + NL)
step_block = (
    "    // JC-LAZO-JUNE-HERO-1013-001: this week's step, under the tiles" + NL
    + "    final Widget stepBlock = Column(" + NL
    + "      crossAxisAlignment: CrossAxisAlignment.start," + NL
    + "      mainAxisSize: MainAxisSize.min," + NL
    + "      children: <Widget>[" + NL
    + step_seg
    + "      ]," + NL
    + "    );" + NL
)
c = c[:nb_end] + step_block + c[nb_end:]
# the hero card: eyebrow, June, tiles, then the step
c = rep(c, "          : _twoUp(tiles);\n      return Container(",
        "          : " + SWIPE.replace("\n            ", "\n              ") + ";\n      return Container(", "couple swipe tiles")
c = rep(c, """            // JC-LAZO-COUPLE-1010-V150: the deck - the day along the top,
            // June across it.
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                wide
                    ? Row(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: <Widget>[
                            Expanded(child: nameBlock),
                            const SizedBox(width: 22),
                            grid,
                          ])
                    : Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                            nameBlock,
                            const SizedBox(height: 16),
                            grid,
                          ]),
                SizedBox(height: wide ? 22 : 18),
                Container(height: 1, color: gold.withOpacity(.38)),
                SizedBox(height: wide ? 22 : 18),
                KeyedSubtree(
                    key: _kTourJune,
                    child: const JuneNative(role: 'couple', layout: 'deck')),
              ],
            ),""",
        """            // JC-LAZO-JUNE-HERO-1013-001/002: June is the top of the dashboard - the day as
            // the eyebrow, her hero, then the numbers (beside her when the card has room for both, >= 1100;
            // a narrower wide card - beside the sidebar - stacks them under her in one even row) and this week's step.
            child: wide && cons.maxWidth >= 1100
                ? Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: <Widget>[
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          mainAxisSize: MainAxisSize.min,
                          children: <Widget>[
                            nameBlock,
                            KeyedSubtree(
                                key: _kTourJune,
                                child: const JuneNative(
                                    role: 'couple', layout: 'hero')),
                            stepBlock,
                          ],
                        ),
                      ),
                      const SizedBox(width: 28),
                      grid,
                    ],
                  )
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: <Widget>[
                      nameBlock,
                      KeyedSubtree(
                          key: _kTourJune,
                          child: const JuneNative(role: 'couple', layout: 'hero')),
                      const SizedBox(height: 18),
                      wide
                          ? IntrinsicHeight(
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: <Widget>[
                                  for (int i = 0; i < tiles.length; i++) ...<Widget>[
                                    if (i > 0) const SizedBox(width: 10),
                                    Expanded(child: tiles[i]),
                                  ],
                                ],
                              ),
                            )
                          : grid,
                      stepBlock,
                    ],
                  ),""", "couple layout")
# JC-LAZO-JUNE-HERO-1013-002: the eyebrow breaks on purpose - the names on one line, the date and the city on
# the next - instead of wrapping wherever it lands and leaving a "·" at the start or end of a line
c = rep(c, r"""    final String eyebrow = <String>[
      if (names.isNotEmpty) glue(names),
      if (names.isEmpty && !_hasRail && greetFirst.isNotEmpty)
        glue('HI, $greetFirst'),
      if (wedding != null) glue(_longDate(wedding)),
      if (metro.isNotEmpty) glue(metro),
    ].join(' \u00b7 ');""",
        r"""    final String eyeTop = <String>[
      if (names.isNotEmpty) glue(names),
      if (names.isEmpty && !_hasRail && greetFirst.isNotEmpty)
        glue('HI, $greetFirst'),
    ].join(' \u00b7 ');
    final String eyeBottom = <String>[
      if (wedding != null) glue(_longDate(wedding)),
      if (metro.isNotEmpty) glue(metro),
    ].join(' \u00b7 ');
    final String eyebrow = <String>[
      if (eyeTop.isNotEmpty) eyeTop,
      if (eyeBottom.isNotEmpty) eyeBottom,
    ].join('\n');""", "eyebrow two lines")
# JC-LAZO-JUNE-HERO-1013-002: June greets them in the hero now, so the page title stops saying "Hi, Avery"
# right above "Good evening, Avery & Jordan." - one greeting, hers
c = rep(c, """                        : Text(
                            firstName.isEmpty
                                ? 'Your wedding'
                                : 'Hi, $firstName',""",
        """                        : Text(
                            'Your wedding',""", "one greeting")
# JC-LAZO-JUNE-HERO-1013-002: on phones the photo pill is just its camera (the tooltip still says what it
# does), so the eyebrow keeps the narrow inset and the date line no longer wraps into a dangling dot
c = rep(c, "                    if (photo.isEmpty) ...<Widget>[",
        "                    if (photo.isEmpty && MediaQuery.of(context).size.width >= 600) ...<Widget>[", "photo pill label")
c = rep(c, "                      horizontal: photo.isEmpty ? 12 : 8, vertical: 7),",
        "                      horizontal: photo.isEmpty && MediaQuery.of(context).size.width >= 600 ? 12 : 8, vertical: 7),", "photo pill padding")
c = rep(c, "              padding: const EdgeInsets.only(bottom: 8, right: 52),",
        "              padding: EdgeInsets.only(bottom: 8, right: photo.isEmpty && MediaQuery.of(context).size.width >= 600 ? 148 : 52),", "eyebrow clears pill")
c = rep(c, """                          child: Column(children: <Widget>[
                            Expanded(child: tiles[i]),
                            const SizedBox(height: 10),
                            Expanded(
                                child: i + 1 < tiles.length
                                    ? tiles[i + 1]
                                    : const SizedBox.shrink()),
                          ]),""", """                          // a column with one tile lets it fill the height: no empty slot
                          child: Column(children: <Widget>[
                            Expanded(child: tiles[i]),
                            if (i + 1 < tiles.length) ...<Widget>[
                              const SizedBox(height: 10),
                              Expanded(child: tiles[i + 1]),
                            ],
                          ]),""", "couple wide pairs")
c = apply_fab(c, "_deskFab", 18, 86, 58, "lazo_fab_couple", rep)
c = apply_weather(c, "couple", rep)
(HERE / "Couple_master_v153.txt").write_text(c, encoding="utf-8")
print("wrote Couple_master_v153.txt", len(c))
