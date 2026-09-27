"""patch_build_license.py - JC-LAZO-LICENSE-0920-001
build.py renders /marriage-license/ (every state), /marriage-license/<state>/
(51 pages) and /marriage-license/data.json (what the couple app's Marriage
license card reads), all from config/marriage_license.py. Refuses to run twice.
  python generate\\patch_build_license.py
"""
from pathlib import Path

P = Path(__file__).resolve().parent / "build.py"
s = P.read_text(encoding="utf-8")
if "JC-LAZO-LICENSE-0920-001" in s:
    raise SystemExit("already applied")

old = '    urls.append(f"{BASE_URL}/planning/")\n'
if s.count(old) != 1:
    raise SystemExit("anchor for planning hub not found once")
new = old + '''
    # JC-LAZO-LICENSE-0920-001: marriage licenses, every state, plus the county
    # offices for our metros and a data.json for the couple app's license card.
    from config.marriage_license import STATES as _LS, COUNTIES as _LC, BY_ABBR as _LA, fee_text as _lft, wait_text as _lwt, valid_text as _lvt
    import json as _lj
    from datetime import date as _ld
    _ldir = DIST / "marriage-license"
    _ldir.mkdir(exist_ok=True)
    _lyear = _ld.today().year
    _lstates = []
    _lmetros_by_state = {}
    for _m in METROS:
        _lmetros_by_state.setdefault(_LA.get(_m["state"], ""), []).append(_m)
    for _slug, _st in _LS.items():
        _row = dict(_st, slug=_slug, fee_text=_lft(_st["fee"]), wait_text=_lwt(_st["wait_days"]), valid_text=_lvt(_st["valid_days"]))
        _lstates.append(_row)
    _lstates.sort(key=lambda r: r["name"])
    (_ldir / "index.html").write_text(env.get_template("license_index.html").render(
        base=BASE_URL, states=_lstates, year=_lyear, metros=live_metros, categories=CATEGORIES,
        vendor_total_display=vendor_total_display, metro_count=len(live_metros), first_metro=_first), encoding="utf-8")
    urls.append(f"{BASE_URL}/marriage-license/")
    _t_ls = env.get_template("license_state.html")
    _ldata = {"updated": _ld.today().isoformat(), "states": {}, "metros": {}}
    for _row in _lstates:
        _ms = [m for m in _lmetros_by_state.get(_row["slug"], []) if m in live_metros] or _lmetros_by_state.get(_row["slug"], [])
        _offices = []
        for _m in _ms:
            for (_county, _office, _site, _fee, _note) in _LC.get(_m["id"], []):
                _offices.append({"metro": _m["name"], "metro_id": _m["id"], "county": _county, "office": _office, "site": _site, "fee": _fee, "note": _note})
        _d = _ldir / _row["slug"]
        _d.mkdir(exist_ok=True)
        (_d / "index.html").write_text(_t_ls.render(
            base=BASE_URL, s=_row, offices=_offices, year=_lyear, metros=_ms, categories=CATEGORIES,
            vendor_total_display=vendor_total_display, metro_count=len(live_metros), first_metro=_first), encoding="utf-8")
        urls.append(f"{BASE_URL}/marriage-license/{_row['slug']}/")
        _ldata["states"][_row["slug"]] = {k: _row[k] for k in ("name", "abbr", "issuer", "fee", "fee_text", "wait_days", "wait_text", "valid_days", "valid_text", "witnesses", "min_age", "course", "notes")}
    for _m in METROS:
        _ldata["metros"][_m["id"]] = {"state": _LA.get(_m["state"], ""), "offices": [
            {"county": c, "office": o, "site": u, "fee": f, "note": n} for (c, o, u, f, n) in _LC.get(_m["id"], [])]}
    (_ldir / "data.json").write_text(_lj.dumps(_ldata, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
'''
s = s.replace(old, new)
P.write_text(s, encoding="utf-8", newline="\n")
print("generate/build.py patched (marriage license)")
