"""patch_lazo_weather.py - JC-LAZO-WX-1014-001: the weather card, drawn the way Apple draws its weather widget.
Applied by patch_june_hero_dashboards.py to Vendor_master_v189 / Couple_master_v153 (imported, not run alone).
  - the sky is the card: a gradient chosen by the condition and by day or night (clear blue, night navy, cloud
    grey, rain slate, storm violet, snow pale), white type, no gold frame, a hairline and light on the top edge
  - the place, what day it is about (and for vendors whose wedding), a large thin temperature, and on the right
    the condition icon in colour, the condition and H / L - Apple's medium widget
  - underneath, what helps: in forecast range an hour strip (the next six hours today, 2 PM to 7 PM on a wedding
    day) with colour icons and rain chances; further out, this date in each of the last five years as Apple's
    day rows - year, icon, low, a cool-to-warm range bar on a shared scale, high
  - one quiet line for rain and sunset, and the couple card keeps its All dates way into the day-of plan
The loaders now keep what they already fetch: the forecast asks for the hours of that day (and sunrise), the
history keeps each year's row instead of only the average.
"""

SKY_CLASS = r"""
// JC-LAZO-WX-1014-001: the weather card, drawn the way Apple draws its weather widget. The sky is the card
// (a gradient picked by the condition and by day or night), type is white, the temperature large and thin,
// the condition and H / L on the right, and underneath either the hours of the day or, further out, this
// date in each of the last five years as range bars on one scale.
class _SkyCard extends StatelessWidget {
  const _SkyCard({
    required this.place,
    required this.when,
    required this.w,
    required this.status,
    required this.fold,
    this.who = '',
    this.note = '',
    this.action = '',
    this.radius = 22,
  });
  final String place;
  final String when;
  final String who;
  final Map<String, dynamic>? w;
  final String status;
  final Widget fold;
  final String note;
  final String action;
  final double radius;

  static String label(int c) {
    if (c == 0) return 'Clear';
    if (c == 1) return 'Mostly Clear';
    if (c == 2) return 'Partly Cloudy';
    if (c == 3) return 'Cloudy';
    if (c == 45 || c == 48) return 'Foggy';
    if (c >= 51 && c <= 57) return 'Drizzle';
    if (c >= 61 && c <= 67) return c >= 65 ? 'Heavy Rain' : 'Rain';
    if (c >= 71 && c <= 77) return 'Snow';
    if (c >= 80 && c <= 82) return 'Showers';
    if (c == 85 || c == 86) return 'Snow Showers';
    if (c >= 95) return 'Thunderstorms';
    return 'Cloudy';
  }

  static IconData icon(int c, bool day) {
    if (c <= 1) return day ? Icons.wb_sunny_rounded : Icons.nightlight_round;
    if (c == 2) return day ? Icons.wb_cloudy_rounded : Icons.cloud_rounded;
    if (c == 3 || c == 45 || c == 48) return Icons.cloud_rounded;
    if (c >= 95) return Icons.thunderstorm_rounded;
    if ((c >= 71 && c <= 77) || c == 85 || c == 86) return Icons.ac_unit_rounded;
    return Icons.water_drop_rounded;
  }

  // Apple colours its glyphs: a yellow sun, white moon and cloud, blue rain, a yellow bolt
  static Color iconColor(int c, bool day) {
    if (c <= 1) return day ? const Color(0xFFFFD60A) : Colors.white;
    if (c >= 95) return const Color(0xFFFFD60A);
    if ((c >= 51 && c <= 67) || (c >= 80 && c <= 82)) return const Color(0xFF64D2FF);
    return Colors.white;
  }

  static List<Color> sky(int c, bool day) {
    if (c < 0) return const <Color>[Color(0xFF3B4A63), Color(0xFF1F2A3D)];
    if (!day) {
      if (c <= 2) return const <Color>[Color(0xFF0B1230), Color(0xFF1E2C57), Color(0xFF34477A)];
      return const <Color>[Color(0xFF1B2232), Color(0xFF2E3850), Color(0xFF45506A)];
    }
    if (c <= 1) return const <Color>[Color(0xFF2A6FDB), Color(0xFF4C93EE), Color(0xFF7DB8F5)];
    if (c == 2) return const <Color>[Color(0xFF3C74C4), Color(0xFF6B97CF), Color(0xFF9DB9DB)];
    if (c >= 95) return const <Color>[Color(0xFF2B2745), Color(0xFF443D6B), Color(0xFF615A8A)];
    if ((c >= 71 && c <= 77) || c == 85 || c == 86) return const <Color>[Color(0xFF6E86A8), Color(0xFF97ABC6), Color(0xFFC3D0E1)];
    if ((c >= 51 && c <= 67) || (c >= 80 && c <= 82)) return const <Color>[Color(0xFF3E4D61), Color(0xFF5A6A80), Color(0xFF7C8B9E)];
    return const <Color>[Color(0xFF55667F), Color(0xFF75859B), Color(0xFF97A4B6)];
  }

  // the hours of one day from an Open-Meteo forecast: the next six today, 2 PM to 7 PM on another day
  static List<Map<String, dynamic>> hoursFrom(Map<String, dynamic> j, int daysOut) {
    final List<Map<String, dynamic>> out = <Map<String, dynamic>>[];
    try {
      final Map<String, dynamic> h = Map<String, dynamic>.from(j['hourly'] as Map);
      final List<dynamic> t = h['time'] as List<dynamic>;
      final List<dynamic> temp = h['temperature_2m'] as List<dynamic>;
      final List<dynamic> code = h['weather_code'] as List<dynamic>;
      final List<dynamic> pop = (h['precipitation_probability'] as List<dynamic>?) ?? <dynamic>[];
      final List<dynamic> isDay = (h['is_day'] as List<dynamic>?) ?? <dynamic>[];
      final int startHour = daysOut == 0 ? DateTime.now().hour : 14;
      int start = 0;
      for (int i = 0; i < t.length; i++) {
        final DateTime? d = DateTime.tryParse(t[i].toString());
        if (d != null && d.hour >= startHour) {
          start = i;
          break;
        }
      }
      for (int i = start; i < t.length && out.length < 6; i++) {
        final DateTime? d = DateTime.tryParse(t[i].toString());
        if (d == null || temp[i] is! num) continue;
        final int h12 = d.hour % 12 == 0 ? 12 : d.hour % 12;
        out.add(<String, dynamic>{
          'label': daysOut == 0 && out.isEmpty ? 'Now' : '$h12${d.hour < 12 ? 'AM' : 'PM'}',
          't': (temp[i] as num).round(),
          'code': code[i] is num ? (code[i] as num).toInt() : 1,
          'pop': i < pop.length && pop[i] is num ? (pop[i] as num).round() : 0,
          'day': i < isDay.length ? isDay[i] == 1 : (d.hour >= 7 && d.hour < 19),
        });
      }
    } catch (_) {}
    return out;
  }

  @override
  Widget build(BuildContext context) {
    final Map<String, dynamic>? w = this.w;
    final bool loaded = w != null;
    final int code = loaded ? (w['code'] as int) : -1;
    final int daysOut = loaded && w['daysOut'] is int ? w['daysOut'] as int : 1;
    // night only matters for today: after sunset or before seven
    bool day = true;
    if (loaded && daysOut == 0) {
      final DateTime now = DateTime.now();
      final DateTime? ss = DateTime.tryParse((w['sunset'] ?? '').toString());
      day = now.hour >= 7 && (ss == null || now.isBefore(ss));
    }
    final List<Map<String, dynamic>> hours = loaded && w['hours'] is List
        ? (w['hours'] as List).whereType<Map>().map((Map m) => Map<String, dynamic>.from(m)).toList()
        : <Map<String, dynamic>>[];
    final List<Map<String, dynamic>> years = loaded && w['yearsRows'] is List
        ? (w['yearsRows'] as List).whereType<Map>().map((Map m) => Map<String, dynamic>.from(m)).toList()
        : <Map<String, dynamic>>[];
    const Color fg = Colors.white;
    final Color fg2 = Colors.white.withOpacity(.78);
    TextStyle t(double size, {FontWeight wt = FontWeight.w500, Color color = fg, double h = 1.2, double ls = 0}) =>
        TextStyle(color: color, fontSize: size, fontWeight: wt, height: h, letterSpacing: ls,
            shadows: const <Shadow>[Shadow(color: Color(0x33000000), blurRadius: 6, offset: Offset(0, 1))]);
    final Widget divider = Container(height: .6, color: Colors.white.withOpacity(.22));

    Widget hourStrip() => Row(children: <Widget>[
          for (final Map<String, dynamic> hr in hours)
            Expanded(
              child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
                Text(hr['label'].toString(), style: t(12, wt: FontWeight.w600, color: fg2)),
                const SizedBox(height: 7),
                Icon(icon(hr['code'] as int, hr['day'] == true), size: 20, color: iconColor(hr['code'] as int, hr['day'] == true)),
                SizedBox(
                  height: 14,
                  child: (hr['pop'] as int) >= 20
                      ? Text('${hr['pop']}%', style: t(10.5, wt: FontWeight.w700, color: const Color(0xFF8FDBFF)))
                      : const SizedBox.shrink(),
                ),
                Text('${hr['t']}°', style: t(15, wt: FontWeight.w600)),
              ]),
            ),
        ]);

    Widget yearRows() {
      int lo = 999, hi = -999;
      for (final Map<String, dynamic> y in years) {
        lo = math.min(lo, y['lo'] as int);
        hi = math.max(hi, y['hi'] as int);
      }
      final double span = math.max(1, hi - lo).toDouble();
      return Column(children: <Widget>[
        for (final Map<String, dynamic> y in years)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(children: <Widget>[
              SizedBox(width: 44, child: Text(y['y'].toString(), style: t(14, wt: FontWeight.w600))),
              SizedBox(
                width: 30,
                child: Icon(y['rain'] == true ? Icons.water_drop_rounded : icon(y['code'] as int, true),
                    size: 18, color: y['rain'] == true ? const Color(0xFF64D2FF) : iconColor(y['code'] as int, true)),
              ),
              SizedBox(width: 38, child: Text('${y['lo']}°', textAlign: TextAlign.right, style: t(14, wt: FontWeight.w600, color: fg2))),
              const SizedBox(width: 10),
              Expanded(
                child: LayoutBuilder(builder: (BuildContext c, BoxConstraints b) {
                  final double a = ((y['lo'] as int) - lo) / span * b.maxWidth;
                  final double z = ((y['hi'] as int) - lo) / span * b.maxWidth;
                  return SizedBox(
                    height: 5,
                    child: Stack(children: <Widget>[
                      Positioned.fill(child: DecoratedBox(decoration: BoxDecoration(color: Colors.black.withOpacity(.16), borderRadius: BorderRadius.circular(3)))),
                      Positioned(
                        left: a,
                        width: math.max(5, z - a),
                        top: 0,
                        bottom: 0,
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(3),
                            gradient: const LinearGradient(colors: <Color>[Color(0xFF5AC8FA), Color(0xFFFFD60A), Color(0xFFFF9F0A)]),
                          ),
                        ),
                      ),
                    ]),
                  );
                }),
              ),
              const SizedBox(width: 10),
              SizedBox(width: 34, child: Text('${y['hi']}°', style: t(14, wt: FontWeight.w600))),
            ]),
          ),
      ]);
    }

    final List<Color> bg = sky(code, day);
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(radius),
        gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: bg),
        boxShadow: <BoxShadow>[BoxShadow(color: Colors.black.withOpacity(.22), blurRadius: 18, offset: const Offset(0, 8))],
      ),
      foregroundDecoration: BoxDecoration(
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: Colors.white.withOpacity(.14), width: .8),
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: <Color>[Colors.white.withOpacity(.12), Colors.white.withOpacity(0)],
          stops: const <double>[0, .35],
        ),
      ),
      clipBehavior: Clip.antiAlias,
      padding: const EdgeInsets.fromLTRB(18, 16, 14, 16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                Flexible(child: Text(place, maxLines: 1, overflow: TextOverflow.ellipsis, style: t(17, wt: FontWeight.w600))),
                const SizedBox(width: 5),
                const Icon(Icons.navigation_rounded, size: 12, color: Colors.white),
              ]),
              const SizedBox(height: 1),
              Text(when, maxLines: 1, overflow: TextOverflow.ellipsis, style: t(12.5, wt: FontWeight.w500, color: fg2)),
              if (who.isNotEmpty) Text(who, maxLines: 1, overflow: TextOverflow.ellipsis, style: t(12.5, wt: FontWeight.w600)),
            ]),
          ),
          fold,
        ]),
        const SizedBox(height: 4),
        if (!loaded)
          Padding(padding: const EdgeInsets.symmetric(vertical: 14), child: Text(status, style: t(15, color: fg2)))
        else
          Row(crossAxisAlignment: CrossAxisAlignment.end, children: <Widget>[
            // today the big number is the temperature now, as Apple's is; another day shows that day's high
            Text('${daysOut == 0 && hours.isNotEmpty ? hours.first['t'] : w['hi']}°', style: t(64, wt: FontWeight.w200, h: 1, ls: -2.5)),
            const Spacer(),
            Padding(
              padding: const EdgeInsets.only(bottom: 8, right: 4),
              child: Column(crossAxisAlignment: CrossAxisAlignment.end, children: <Widget>[
                Icon(icon(code, day), size: 24, color: iconColor(code, day)),
                const SizedBox(height: 4),
                Text(label(code), style: t(14, wt: FontWeight.w600)),
                Text('H:${w['hi']}°  L:${w['lo']}°', style: t(14, wt: FontWeight.w600)),
              ]),
            ),
          ]),
        if (loaded && (hours.isNotEmpty || years.isNotEmpty)) ...<Widget>[
          const SizedBox(height: 12),
          divider,
          const SizedBox(height: 10),
          if (hours.isNotEmpty) hourStrip() else ...<Widget>[
            Text('THIS DATE, THE LAST ${years.length} YEARS', style: t(10.5, wt: FontWeight.w700, color: fg2, ls: 1.2)),
            const SizedBox(height: 6),
            yearRows(),
          ],
        ],
        if (loaded && (note.isNotEmpty || action.isNotEmpty)) ...<Widget>[
          const SizedBox(height: 10),
          divider,
          const SizedBox(height: 9),
          Row(children: <Widget>[
            Expanded(child: Text(note, maxLines: 2, overflow: TextOverflow.ellipsis, style: t(12.5, wt: FontWeight.w500, color: fg2))),
            if (action.isNotEmpty) Text('$action ›', style: t(12.5, wt: FontWeight.w700)),
          ]),
        ],
      ]),
    );
  }
}
"""


def apply_weather(s, kind, rep):
    """Extend the loader and replace the card. kind: 'couple' or 'vendor'."""
    # the forecast also brings the hours of that day (and sunrise)
    s = rep(s, "precipitation_probability_max,wind_speed_10m_max,sunset'",
            "precipitation_probability_max,wind_speed_10m_max,sunset,sunrise'\n"
            "            '&hourly=temperature_2m,weather_code,precipitation_probability,is_day'", f"{kind} wx hourly url")
    s = rep(s, "'sunset': (d['sunset'] as List).first.toString(),",
            "'sunset': (d['sunset'] as List).first.toString(),\n"
            "          'hours': _SkyCard.hoursFrom(j, daysOut), // JC-LAZO-WX-1014-001", f"{kind} wx hours")
    # the history keeps each year's row, not only the average
    s = rep(s, "        double hi = 0, lo = 0;",
            "        double hi = 0, lo = 0;\n"
            "        final List<Map<String, dynamic>> yearsRows = <Map<String, dynamic>>[]; // JC-LAZO-WX-1014-001", f"{kind} wx rows decl")
    precip = "p" if kind == "couple" else "pr"
    s = rep(s, "if (c is num) codes[c.toInt()] = (codes[c.toInt()] ?? 0) + 1;",
            "if (c is num) codes[c.toInt()] = (codes[c.toInt()] ?? 0) + 1;\n"
            "          yearsRows.add(<String, dynamic>{\n"
            "            'y': (d['time'] is List && (d['time'] as List).isNotEmpty) ? (d['time'] as List).first.toString().substring(0, 4) : '',\n"
            "            'hi': h.round(),\n"
            "            'lo': l.round(),\n"
            "            'code': c is num ? c.toInt() : 1,\n"
            f"            'rain': {precip} is num && {precip} >= 1.0,\n"
            "          });", f"{kind} wx rows add")
    s = rep(s, "'mode': 'typical',", "'mode': 'typical',\n          'yearsRows': yearsRows,", f"{kind} wx rows keep")

    if kind == "couple":
        a = s.index("    // sky tint by condition\n")
        b = s.index("\n  }\n", s.index("tile('All dates \\u203a'),", a)) + len("\n  }\n")
        new = r"""    // JC-LAZO-WX-1014-001: drawn the way Apple draws its weather widget
    final String sunset =
        w == null ? '' : _sunsetClock((w['sunset'] ?? '').toString());
    final String rain = w == null
        ? ''
        : fc
            ? '${w['rainPct']}% chance of rain'
            : (w['rainYears'] == 0
                ? 'Dry ${w['years']} of ${w['years']} years'
                : 'Rain ${w['rainYears']} of ${w['years']} years');
    return _Press(
      scale: .985,
      dim: .92,
      onTap: () => setState(() => _view = _View.dayof),
      child: _SkyCard(
        place: city,
        when: hasDate
            ? '${fc ? 'Forecast' : 'Usually'} · ${_shortDate(wedding)}'
            : 'Today · set your date to see your day',
        w: w,
        status: _wxErr.isEmpty ? 'Reading the sky…' : _wxErr,
        fold: _foldBtn('weather', onDark: true),
        note: <String>[
          if (rain.isNotEmpty) rain,
          if (sunset.isNotEmpty) 'Sunset $sunset',
        ].join(' · '),
        action: 'All dates',
        radius: 22,
      ),
    );
  }
"""
        s = s[:a] + new + s[b:]
    else:
        a = s.index("        List<Color> sky;\n", s.index("  Widget _vendorWeatherCard("))
        b = s.index("\n  Widget _vendorFab() {", a)
        new = r"""        const List<String> mo = <String>['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const List<String> wk = <String>['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        final String metroName = metro
            .split('-')
            .map((String p) =>
                p.isEmpty ? p : p[0].toUpperCase() + p.substring(1))
            .join(' ');
        final String sunset =
            w == null ? '' : _sunsetClock((w['sunset'] ?? '').toString());
        final String rain = w == null
            ? ''
            : fc
                ? '${w['rainPct']}% chance of rain'
                : (w['rainYears'] == 0
                    ? 'Dry ${w['years']} of ${w['years']} years'
                    : 'Rain ${w['rainYears']} of ${w['years']} years');
        // JC-LAZO-WX-1014-001: drawn the way Apple draws its weather widget
        return Padding(
          padding: const EdgeInsets.only(bottom: 14),
          child: _Press(
            scale: .985,
            dim: .94,
            onTap: threadId.isEmpty
                ? null
                : () => setState(() {
                      _dashMode = 'leads';
                      _setInboxThread(threadId);
                      _showInbox = true;
                    }),
            child: _SkyCard(
              place: metroName,
              when: next == null
                  ? 'Today'
                  : '${fc ? 'Forecast' : 'Usually'} · ${wk[day.weekday - 1]}, ${mo[day.month - 1]} ${day.day}',
              who: who.isEmpty ? '' : '$who’s wedding',
              w: w,
              status: _wxErr.isEmpty ? 'Reading the sky…' : _wxErr,
              fold: _foldBtn('weather', onDark: true),
              note: <String>[
                if (rain.isNotEmpty) rain,
                if (sunset.isNotEmpty) 'Sunset $sunset',
              ].join(' · '),
              radius: 18,
            ),
          ),
        );
      },
    );
  }
"""
        s = s[:a] + new + s[b:]
    if "class _SkyCard extends StatelessWidget" not in s:
        s = s.rstrip("\n") + "\n" + SKY_CLASS
    return s
