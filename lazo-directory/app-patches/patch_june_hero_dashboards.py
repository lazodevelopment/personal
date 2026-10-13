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
HERE = Path(__file__).resolve().parent


def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:80]!r}")
    return s.replace(old, new)


SWIPE = """SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              physics: const BouncingScrollPhysics(),
              clipBehavior: Clip.none,
              child: IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    for (int i = 0; i < tiles.length; i++) ...<Widget>[
                      if (i > 0) const SizedBox(width: 10),
                      SizedBox(width: 132, child: tiles[i]),
                    ],
                  ],
                ),
              ),
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
v = rep(v, "            : _twoUp(tiles);\n        return Container(\n          decoration: BoxDecoration(\n            borderRadius: BorderRadius.circular(22),\n            border: Border.all(color: gold),\n          ),",
        "            : " + SWIPE + ";\n        return Container(\n          decoration: BoxDecoration(\n            borderRadius: BorderRadius.circular(22),\n            border: Border.all(color: gold),\n          ),", "vendor swipe tiles")
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
        """                // JC-LAZO-JUNE-HERO-1013-001: June is the top of the dashboard - the business
                // and its badges as the eyebrow, her hero, then the live numbers.
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    nameBlock,
                    SizedBox(height: wide ? 18 : 14),
                    KeyedSubtree(
                        key: _kTourJune,
                        child: const JuneNative(role: 'vendor', layout: 'hero')),
                    SizedBox(height: wide ? 22 : 18),
                    wide
                        ? Align(alignment: Alignment.centerLeft, child: grid)
                        : grid,
                  ],
                ),""", "vendor layout")
v = v.replace("JC-LAZO-VDASH", "JC-LAZO-VDASH", 1)
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
        """            // JC-LAZO-JUNE-HERO-1013-001: June is the top of the dashboard - the day as
            // the eyebrow, her hero, then the numbers and this week's step.
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                nameBlock,
                KeyedSubtree(
                    key: _kTourJune,
                    child: const JuneNative(role: 'couple', layout: 'hero')),
                SizedBox(height: wide ? 22 : 18),
                wide
                    ? Align(alignment: Alignment.centerLeft, child: grid)
                    : grid,
                stepBlock,
              ],
            ),""", "couple layout")
# the eyebrow clears the wide "Add your photo" pill, not only the small camera button
c = rep(c, "              padding: const EdgeInsets.only(bottom: 8, right: 52),",
        "              padding: EdgeInsets.only(bottom: 8, right: photo.isEmpty ? 148 : 52),", "eyebrow clears pill")
(HERE / "Couple_master_v153.txt").write_text(c, encoding="utf-8")
print("wrote Couple_master_v153.txt", len(c))
