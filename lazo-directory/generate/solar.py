#!/usr/bin/env python3
"""solar.py - NOAA solar position engine. Pure stdlib, no network, no API key.

Produces exact sunset / civil-dusk / golden-hour times for any lat/lng/date.
These are computed astronomical facts, not generated copy - which is precisely
why they make legitimate per-city page content.
"""
import math, datetime as dt
from zoneinfo import ZoneInfo

# ---- state -> IANA timezone. Split states resolved by longitude threshold. ----
_TZ = {
 'AL':'America/Chicago','AR':'America/Chicago','AZ':'America/Phoenix','CA':'America/Los_Angeles',
 'CO':'America/Denver','CT':'America/New_York','DC':'America/New_York','DE':'America/New_York',
 'GA':'America/New_York','IA':'America/Chicago','IL':'America/Chicago','LA':'America/Chicago',
 'MA':'America/New_York','MD':'America/New_York','ME':'America/New_York','MN':'America/Chicago',
 'MO':'America/Chicago','MS':'America/Chicago','MT':'America/Denver','NC':'America/New_York',
 'NH':'America/New_York','NJ':'America/New_York','NM':'America/Denver','NV':'America/Los_Angeles',
 'NY':'America/New_York','OH':'America/New_York','OK':'America/Chicago','PA':'America/New_York',
 'RI':'America/New_York','SC':'America/New_York','UT':'America/Denver','VA':'America/New_York',
 'VT':'America/New_York','WA':'America/Los_Angeles','WI':'America/Chicago','WV':'America/New_York',
 'WY':'America/Denver','HI':'Pacific/Honolulu','AK':'America/Anchorage',
}
# states straddling a timezone line: (western_tz, eastern_tz, longitude_boundary)
_SPLIT = {
 'FL': ('America/Chicago','America/New_York',-85.0),
 'TX': ('America/Denver','America/Chicago',-104.9),
 'KS': ('America/Denver','America/Chicago',-101.5),
 'NE': ('America/Denver','America/Chicago',-101.5),
 'ND': ('America/Denver','America/Chicago',-100.5),
 'SD': ('America/Denver','America/Chicago',-100.5),
 'TN': ('America/Chicago','America/New_York',-85.5),
 'KY': ('America/Chicago','America/New_York',-85.5),
 'IN': ('America/Chicago','America/New_York',-87.3),
 'MI': ('America/Chicago','America/New_York',-87.0),
 'OR': ('America/Los_Angeles','America/Boise',-117.5),
 'ID': ('America/Los_Angeles','America/Boise',-116.0),
}

def tz_for(st, lng):
    st = (st or '').upper()
    if st in _SPLIT:
        west, east, bound = _SPLIT[st]
        return ZoneInfo(west if lng < bound else east)
    return ZoneInfo(_TZ.get(st, 'America/New_York'))

# ---------------- NOAA solar equations ----------------
def _jday(d):
    y, m = d.year, d.month
    if m <= 2: y, m = y - 1, m + 12
    a = y // 100
    b = 2 - a + a // 4
    return math.floor(365.25*(y+4716)) + math.floor(30.6001*(m+1)) + d.day + b - 1524.5

def _solar_events(date, lat, lng, zenith, _jc_offset_days=0.0):
    """Return (rise_utc_minutes, set_utc_minutes) for a given solar zenith angle."""
    jc = (_jday(date) + _jc_offset_days - 2451545.0) / 36525.0
    gml = (280.46646 + jc*(36000.76983 + jc*0.0003032)) % 360
    gma = 357.52911 + jc*(35999.05029 - 0.0001537*jc)
    ecc = 0.016708634 - jc*(0.000042037 + 0.0000001267*jc)
    ctr = (math.sin(math.radians(gma))*(1.914602 - jc*(0.004817 + 0.000014*jc))
         + math.sin(math.radians(2*gma))*(0.019993 - 0.000101*jc)
         + math.sin(math.radians(3*gma))*0.000289)
    tl = gml + ctr
    al = tl - 0.00569 - 0.00478*math.sin(math.radians(125.04 - 1934.136*jc))
    oblq = 23 + (26 + ((21.448 - jc*(46.815 + jc*(0.00059 - jc*0.001813))))/60)/60
    oc = oblq + 0.00256*math.cos(math.radians(125.04 - 1934.136*jc))
    decl = math.degrees(math.asin(math.sin(math.radians(oc))*math.sin(math.radians(al))))
    vy = math.tan(math.radians(oc/2))**2
    eqt = 4*math.degrees(vy*math.sin(2*math.radians(gml))
          - 2*ecc*math.sin(math.radians(gma))
          + 4*ecc*vy*math.sin(math.radians(gma))*math.cos(2*math.radians(gml))
          - 0.5*vy*vy*math.sin(4*math.radians(gml))
          - 1.25*ecc*ecc*math.sin(2*math.radians(gma)))
    try:
        ha = math.degrees(math.acos(
            math.cos(math.radians(zenith))/(math.cos(math.radians(lat))*math.cos(math.radians(decl)))
            - math.tan(math.radians(lat))*math.tan(math.radians(decl))))
    except ValueError:
        return None, None          # sun never reaches that angle (polar cases)
    noon = 720 - 4*lng - eqt
    return noon - 4*ha, noon + 4*ha

def solar_events(date, lat, lng, zenith):
    """Iterated form: re-evaluates solar position at the event time itself.
    Without this the whole day is approximated from midnight UTC and every
    result lands ~1-4 minutes early."""
    rise, sett = _solar_events(date, lat, lng, zenith)
    for _ in range(3):
        if rise is None: break
        r2, s2 = _solar_events(date, lat, lng, zenith, _jc_offset_days=(rise/1440.0))
        _,  s3 = _solar_events(date, lat, lng, zenith, _jc_offset_days=(sett/1440.0))
        if r2 is None: break
        rise, sett = r2, s3
    return rise, sett

def _fmt(minutes_utc, date, tz):
    if minutes_utc is None: return None
    base = dt.datetime(date.year, date.month, date.day, tzinfo=dt.timezone.utc)
    return (base + dt.timedelta(minutes=minutes_utc)).astimezone(tz)

def day_info(date, lat, lng, st):
    """All timing a wedding timeline actually needs, for one date."""
    tz = tz_for(st, lng)
    sunrise, sunset = solar_events(date, lat, lng, 90.833)  # refraction-corrected horizon
    _, dusk         = solar_events(date, lat, lng, 96.0)    # civil twilight ends
    _, golden_start = solar_events(date, lat, lng, 84.0)    # sun at +6 deg
    return dict(
        sunrise=_fmt(sunrise, date, tz),
        golden_start=_fmt(golden_start, date, tz),
        sunset=_fmt(sunset, date, tz),
        dusk=_fmt(dusk, date, tz),
        tz=str(tz))

def hhmm(d):
    return (d.strftime('%I:%M %p').lstrip('0') or d.strftime('%I:%M %p')) if d else '--'   # Windows has no %-I

def wedding_season(year, lat, lng, st, months=(5,6,7,8,9,10)):
    """Sunset + golden-hour window on the 15th of each peak-season month."""
    out = []
    for m in months:
        d = dt.date(year, m, 15)
        info = day_info(d, lat, lng, st)
        if not info['sunset']: continue
        daylen = (info['sunset'] - info['sunrise']).total_seconds()/3600
        out.append(dict(month=d.strftime('%B'), abbr=d.strftime('%b'),
                        golden=info['golden_start'], sunset=info['sunset'],
                        dusk=info['dusk'], daylight=round(daylen, 1),
                        ceremony=info['sunset'] - dt.timedelta(hours=2, minutes=45)))
    return out

if __name__ == '__main__':
    for nm, la, ln, st in [('Nashville',36.1627,-86.7816,'TN'), ('Seattle',47.6062,-122.3321,'WA')]:
        print(f"\n{nm}")
        for r in wedding_season(2027, la, ln, st):
            print(f"  {r['abbr']}  golden {hhmm(r['golden'])}  sunset {hhmm(r['sunset'])}"
                  f"  dusk {hhmm(r['dusk'])}  {r['daylight']}h  ceremony ~{hhmm(r['ceremony'])}")
