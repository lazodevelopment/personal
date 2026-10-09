"""City guide blocks for the top metro x category hubs.  JC-LAZO-GUIDE-1008

See config/city_guides.py for what may and may not go on a guide. Everything here is
computed (sunset, counts) or read from config (license, lead time, cost); the only
prose is the per-metro note and sentences that wrap those facts.
"""
import datetime as dt
from collections import Counter, defaultdict

from config.city_guides import GUIDE_CATS, GUIDE_METROS
from config.booking import WHEN_LABEL, ONE_PER_DAY
from config.marriage_license import STATES, BY_ABBR
import solar

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
SUNSET_CATS = {"wedding-venues", "wedding-photographers", "wedding-videographers", "wedding-planners"}
PICKS = 12
PER_TOWN = 2

# one sentence per category, after the metro note. {n} vendors, {towns} town count.
CAT_LINE = {
    "wedding-venues": "Lazo lists {n} wedding venues across {towns} towns in the area; the short list below spreads across the metro so you can compare settings before you tour.",
    "wedding-photographers": "Lazo lists {n} wedding photographers working across {towns} towns. Light is the thing that changes most by month here, so the sunset table below is worth reading before you set a ceremony time.",
    "wedding-videographers": "Lazo lists {n} wedding videographers across {towns} towns. Ask each one how they handle sound at your ceremony site and how long delivery takes.",
    "wedding-planners": "Lazo lists {n} wedding planners and coordinators across {towns} towns. A planner who knows the area's venues and drive times earns their fee on a spread-out metro.",
    "wedding-florists": "Lazo lists {n} wedding florists across {towns} towns. What is in season in your month sets the price of your flowers more than anything else.",
    "wedding-djs": "Lazo lists {n} wedding DJs across {towns} towns. Ask about MC experience and venue sound limits as well as the playlist.",
}


def _a(word):
    return "an" if word[:1].lower() in "aeiou" else "a"


def is_guide(metro_id, cat_slug):
    return metro_id in GUIDE_METROS and cat_slug in GUIDE_CATS


def _month_span(months):
    """[10,11,12,1,2] -> 'October to February'; [4,5,6,9,10] -> 'April to June and September to October'."""
    runs, cur = [], [months[0]]
    for m in months[1:]:
        if (cur[-1] % 12) + 1 == m:
            cur.append(m)
        else:
            runs.append(cur); cur = [m]
    runs.append(cur)
    parts = [MONTHS[r[0] - 1] if len(r) == 1 else f"{MONTHS[r[0] - 1]} to {MONTHS[r[-1] - 1]}" for r in runs]
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def _issuer(s):
    """'County auditor' -> 'county auditor'; keep proper names like 'Marriage Bureau, DC Superior Court'."""
    return s if any(c.isupper() for c in s[1:]) else s[:1].lower() + s[1:]


def _sunsets(metro, months):
    lat, lng = metro["center"]
    year = dt.date.today().year + 1
    rows = []
    for m in sorted(months):
        info = solar.day_info(dt.date(year, m, 15), lat, lng, metro["state"])
        if not info["sunset"]:
            continue
        rows.append(dict(month=MONTHS[m - 1], golden=solar.hhmm(info["golden_start"]),
                         sunset=solar.hhmm(info["sunset"]), dusk=solar.hhmm(info["dusk"]),
                         ceremony=solar.hhmm(info["sunset"] - dt.timedelta(hours=2, minutes=45))))
    return rows


def _license(state_abbr):
    key = BY_ABBR.get(state_abbr)
    s = STATES.get(key) if key else None
    if not s:
        return None
    fee = str(s.get("fee") or "").strip()
    fee_text = (f"${fee.replace('-', '&ndash;$')}" if fee and fee[0].isdigit() else fee) or "varies by county"
    wait = int(s.get("wait_days") or 0)
    valid = int(s.get("valid_days") or 0)
    wit = int(s.get("witnesses") or 0)
    return dict(state=s.get("name") or key, slug=key,
                issuer=_issuer(s.get("issuer") or "county clerk"), fee=fee_text,
                wait=(f"a {wait}-day waiting period" if wait else "no waiting period"),
                valid=(f"valid for {valid} days" if valid else ""),
                witnesses=("no witnesses are needed" if not wit else f"you need {wit} witness{'es' if wit > 1 else ''}"))


def _picks(cvs, locality):
    """Verified / claimed vendors based here first, then vendors with their own website,
    at most PER_TOWN per town, taking towns round-robin so the list spans the metro."""
    local = [v for v in cvs if not v.get("travelFrom")]
    first = [v for v in local if v.get("verified") or v.get("claimedBy")]
    _first = {id(v) for v in first}
    rest = [v for v in local if id(v) not in _first and (v.get("website") or "").strip()]
    out, per_town = list(first[:PICKS]), Counter()
    for v in out:
        per_town[locality(v)] += 1
    by_town = defaultdict(list)
    for v in rest:
        by_town[locality(v)].append(v)
    towns = sorted(by_town, key=lambda t: -len(by_town[t]))
    while len(out) < PICKS and any(by_town[t] for t in towns):
        for t in towns:
            if len(out) >= PICKS:
                break
            if by_town[t] and per_town[t] < PER_TOWN:
                out.append(by_town[t].pop(0))
                per_town[t] += 1
        if all(per_town[t] >= PER_TOWN or not by_town[t] for t in towns):
            break
    return [dict(name=v["name"], slug=v["slug"], town=locality(v),
                 verified=bool(v.get("verified")), claimed=bool(v.get("claimedBy")),
                 website=bool((v.get("website") or "").strip()),
                 thumb=v.get("thumbUrl") or "") for v in out]


def build_guide(metro, cat, cvs, locality, cost_typical=None):
    g = GUIDE_METROS[metro["id"]]
    towns = Counter(locality(v) for v in cvs if not v.get("travelFrom"))
    lead = WHEN_LABEL.get(cat["slug"])
    lic = _license(metro["state"])
    peak = g["peak"]
    sunsets = _sunsets(metro, peak) if cat["slug"] in SUNSET_CATS else []
    season = _month_span(peak)
    singular = cat["singular"].lower()

    faqs = [(f"When is wedding season in {metro['name']}?",
             f"Peak season in {metro['name']} runs {season}. "
             + g["weather"].replace("&deg;", "°").replace("&ndash;", "–"))]
    if lead:
        faqs.append((f"How far ahead should we book a {singular} in {metro['name']}?",
                     f"Plan on {lead} for a peak-season Saturday."
                     + (" A " + singular + " can only take one wedding a day, so popular dates go first."
                        if cat["slug"] in ONE_PER_DAY else "")))
    if cost_typical:
        faqs.append((f"How much does a {singular} cost in {metro['name']}?",
                     f"Most couples spend {cost_typical}. Lazo does not yet hold verified booking prices "
                     f"for {metro['name']}, so treat this as a national range and ask each {singular} for their packages."))
    if sunsets:
        mid = sunsets[len(sunsets) // 2]
        faqs.append((f"What time is sunset for {_a(mid['month'])} {mid['month']} wedding in {metro['name']}?",
                     f"Around {mid['sunset']} on {mid['month']} 15, with golden hour from about {mid['golden']}. "
                     f"For portraits in that light, a ceremony near {mid['ceremony']} works."))
    if lic:
        faqs.append((f"How do we get a marriage license in {lic['state']}?",
                     f"Apply with the {lic['issuer']}. The fee is {lic['fee'].replace('&ndash;', '-')} and there is {lic['wait']}. "
                     + (f"The license is {lic['valid']}, and " if lic['valid'] else "")
                     + (lic['witnesses'][0].upper() + lic['witnesses'][1:] if not lic['valid'] else lic['witnesses']) + "."))

    other_cities = sorted(((mid_, m) for mid_, m in GUIDE_METROS.items() if mid_ != metro["id"]),
                          key=lambda x: x[0])
    return dict(
        intro=g["setting"],
        cat_line=CAT_LINE.get(cat["slug"], "").format(n=len(cvs), towns=len(towns)),
        weather=g["weather"], season=season,
        towns=[(t, n) for t, n in towns.most_common(8)],
        sunsets=sunsets, lead=lead, license=lic,
        picks=_picks(cvs, locality),
        faqs=faqs,
        other_cats=[c for c in GUIDE_CATS if c != cat["slug"]],
        other_cities=[mid_ for mid_, _ in other_cities],
    )
