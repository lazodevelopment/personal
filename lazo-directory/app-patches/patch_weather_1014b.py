"""patch_weather_1014b.py - JC-LAZO-WX-1014-002: the weather card, take two.
  - a past day is judged by what it was. Open-Meteo's archive daily weather_code is the WORST hour of the day,
    so one overcast hour made a 95%-sunshine day 'Cloudy' (Phoenix, Mar 27: five sunny years drawn as five
    clouds on a grey sky). _SkyCard.dayCode reads rain, then sunshine over daylight.
  - 'Avg H / L' when the card shows a typical day; the place loses the location arrow (Apple's means "you
    are here"); the when line may wrap.
  - stat tiles under the card (frosted, Apple's): the couple card shows rain, golden hour and sunset, says
    when the real forecast starts, and puts June's planning tip in the footer line.
Usage: python patch_weather_1014b.py   (Couple v153 -> v154; Vendor v190 patched by make_v190.py)
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def once(s, old, new):
    assert s.count(old) == 1, "anchor count %d: %s" % (s.count(old), old[:90])
    return s.replace(old, new)


DAY_CODE = r"""  // JC-LAZO-WX-1014-002: the archive's daily weather_code is the worst hour of the day, so a single
  // overcast hour made a sunny day 'Cloudy'. A past day is judged by what it was: rain or snow when
  // a millimetre or more fell, otherwise the share of daylight that was sunshine.
  static int dayCode(Map<String, dynamic> d) {
    num first(String k) {
      final dynamic v = d[k];
      return v is List && v.isNotEmpty && v.first is num ? v.first as num : -1;
    }

    final int raw = first('weather_code').toInt();
    final num precip = first('precipitation_sum');
    if (precip >= 1.0) return raw >= 51 ? raw : 61;
    final num sun = first('sunshine_duration');
    final num light = first('daylight_duration');
    if (sun < 0 || light <= 0) return raw < 0 ? 1 : (raw >= 51 ? 3 : raw);
    final double r = sun / light;
    if (r >= .85) return 0;
    if (r >= .7) return 1;
    if (r >= .45) return 2;
    if (raw == 45 || raw == 48) return 45;
    return 3;
  }

  // the hours of one day from an Open-Meteo forecast"""

STAT_TILES = r"""    // JC-LAZO-WX-1014-002: small frosted tiles, the way Apple lays out sunset and rain
    Widget statTiles() => Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          for (int i = 0; i < stats.length; i++) ...<Widget>[
            if (i > 0) const SizedBox(width: 8),
            Expanded(
              child: Container(
                padding: const EdgeInsets.fromLTRB(10, 8, 10, 9),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(.13),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.white.withOpacity(.16), width: .6),
                ),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: <Widget>[
                  Text(stats[i][0].toUpperCase(),
                      maxLines: 1, overflow: TextOverflow.ellipsis, style: t(9.5, wt: FontWeight.w700, color: fg2, ls: .8)),
                  const SizedBox(height: 3),
                  Text(stats[i][1], maxLines: 1, overflow: TextOverflow.ellipsis, style: t(14.5, wt: FontWeight.w600)),
                ]),
              ),
            ),
          ],
        ]);

    final List<Color> bg = sky(code, day);"""


def patch_sky(s):
    a = s.index("class _SkyCard extends StatelessWidget")
    c = s[a:]
    c = once(c, "    this.radius = 22,\n  });", "    this.radius = 22,\n    this.stats = const <List<String>>[],\n  });")
    c = once(c, "  final double radius;\n", "  final double radius;\n  final List<List<String>> stats; // [label, value] tiles under the card\n")
    c = once(c, "  // the hours of one day from an Open-Meteo forecast", DAY_CODE)
    c = once(c, "                const SizedBox(width: 5),\n                const Icon(Icons.navigation_rounded, size: 12, color: Colors.white),\n", "")
    c = once(c, "Text(when, maxLines: 1,", "Text(when, maxLines: 2,")
    c = once(c, "Text('H:${w['hi']}°  L:${w['lo']}°',", "Text('${w['mode'] == 'typical' ? 'Avg ' : ''}H:${w['hi']}°  L:${w['lo']}°',")
    c = once(c, "    final List<Color> bg = sky(code, day);", STAT_TILES)
    c = once(c, "        if (loaded && (note.isNotEmpty || action.isNotEmpty)) ...<Widget>[",
             "        if (loaded && stats.isNotEmpty) ...<Widget>[\n          const SizedBox(height: 12),\n          statTiles(),\n        ],\n"
             "        if (loaded && (note.isNotEmpty || action.isNotEmpty)) ...<Widget>[")
    return s[:a] + c


def patch_loader(s):
    s = once(s, "'&start_date=$ds&end_date=$ds&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,sunset'",
             "'&start_date=$ds&end_date=$ds&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,sunset,sunshine_duration,daylight_duration'")
    s = once(s, "          final dynamic c = (d['weather_code'] as List).first;\n          if (c is num) codes[c.toInt()] = (codes[c.toInt()] ?? 0) + 1;\n",
             "          final int c = _SkyCard.dayCode(d); // JC-LAZO-WX-1014-002\n          codes[c] = (codes[c] ?? 0) + 1;\n")
    s = once(s, "            'code': c is num ? c.toInt() : 1,\n", "            'code': c,\n")
    return s


COUPLE_HUB_OLD_START = "    // JC-LAZO-WX-1014-001: drawn the way Apple draws its weather widget\n"
COUPLE_HUB_OLD_END = "        action: 'All dates',\n        radius: 22,\n      ),\n    );\n  }\n"
COUPLE_HUB_NEW = r"""    // JC-LAZO-WX-1014-001: drawn the way Apple draws its weather widget
    // JC-LAZO-WX-1014-002: what a couple plans around - rain, golden hour, sunset - as tiles, when the
    // real forecast starts, and June's planning tip as the footer line
    final String sunsetIso = w == null ? '' : (w['sunset'] ?? '').toString();
    final String sunset = _sunsetClock(sunsetIso);
    final DateTime? sunsetAt = DateTime.tryParse(sunsetIso);
    final String golden = sunsetAt == null
        ? ''
        : _sunsetClock(
            sunsetAt.subtract(const Duration(hours: 1)).toIso8601String());
    final DateTime today0 = DateTime(
        DateTime.now().year, DateTime.now().month, DateTime.now().day);
    final DateTime day0 = DateTime(wedding.year, wedding.month, wedding.day);
    final String when;
    if (!hasDate) {
      when = 'Today · set your date to see your day';
    } else if (fc) {
      when = 'Forecast · ${_shortDate(wedding)}';
    } else if (day0.isAfter(today0)) {
      when =
          'Typical for ${_shortDate(wedding)} · forecast from ${_shortDate(day0.subtract(const Duration(days: 15)))}';
    } else {
      when = 'Your day · ${_shortDate(wedding)}';
    }
    final List<List<String>> stats = <List<String>>[
      if (w != null && fc) <String>['Rain', '${w['rainPct']}%'],
      if (w != null && !fc)
        <String>[
          'Rainy years',
          (w['rainYears'] == 0 ? 'None' : '${w['rainYears']}') +
              ' of ${w['years']}'
        ],
      if (golden.isNotEmpty) <String>['Golden hour', golden],
      if (sunset.isNotEmpty) <String>['Sunset', sunset],
    ];
    return _Press(
      scale: .985,
      dim: .92,
      onTap: () => setState(() => _view = _View.dayof),
      child: _SkyCard(
        place: city,
        when: when,
        w: w,
        status: _wxErr.isEmpty ? 'Reading the sky…' : _wxErr,
        fold: _foldBtn('weather', onDark: true),
        stats: stats,
        note: w == null || !hasDate ? '' : _weatherTip(w),
        action: 'All dates',
        radius: 22,
      ),
    );
  }
"""


def patch_couple_hub(s):
    a = s.index(COUPLE_HUB_OLD_START)
    b = s.index(COUPLE_HUB_OLD_END, a) + len(COUPLE_HUB_OLD_END)
    return s[:a] + COUPLE_HUB_NEW + s[b:]


def apply(s, kind):
    s = patch_loader(s)
    s = patch_sky(s)
    if kind == "couple":
        s = patch_couple_hub(s)
    return s


if __name__ == "__main__":
    src = HERE / "Couple_master_v153.txt"
    s = src.read_text(encoding="utf-8")
    s = s.replace("// Build ID: JC-LAZO-DASH-", "// Build ID: JC-LAZO-WX-1014-002 (v154: WEATHER, TAKE TWO - past days judged by their "
                  "sunshine (the archive's worst-hour code drew sunny Phoenix as five clouds), Avg H/L on a typical day, no location "
                  "arrow, rain / golden hour / sunset tiles, 'forecast from' date and June's tip on the couple card; base v153)\n"
                  "// Build ID: JC-LAZO-DASH-", 1)
    s = apply(s, "couple")
    dst = HERE / "Couple_master_v154.txt"
    dst.write_text(s, encoding="utf-8", newline="")
    print("wrote", dst)
