"""Saturday enrichment: video embeds, serviceMetros multi-metro listing emit,
preferred-vendor resolution, metro-name chips. Run once from lazo-directory root."""
from pathlib import Path

bp = Path("generate/build.py")
src = bp.read_text(encoding="utf-8")
if "saturday_enrich" in src:
    print("Already patched.")
    raise SystemExit

anchor = '''    vendors = load_vendors_mock(Path(a.mock)) if a.mock else load_vendors_firestore(a.tranche)
    build(vendors)'''
assert anchor in src, "main anchor not found — send Claude the last 15 lines of build.py"

enrich = '''
def saturday_enrich(vendors):
    """Compute claimed-profile display fields + emit traveling-vendor copies."""
    by_pid = {}
    for v in vendors:
        pid = v.get("placeId")
        if pid:
            by_pid[pid] = v

    def slug_of(v):
        return slugify(v.get("name", ""))

    def home_path(v):
        cats = v.get("categories") or []
        cat0 = cats[0] if cats else None
        if not cat0 or cat0 not in BY_SLUG:
            return None
        return f"/{v.get('metroId')}/{cat0}/{slug_of(v)}/"

    extra = []
    for v in vendors:
        # video embed
        vu = (v.get("videoUrl") or "").strip()
        emb = None
        if "youtu.be/" in vu:
            emb = "https://www.youtube.com/embed/" + vu.split("youtu.be/")[1].split("?")[0].split("&")[0]
        elif "youtube.com/watch" in vu and "v=" in vu:
            emb = "https://www.youtube.com/embed/" + vu.split("v=")[1].split("&")[0]
        elif "youtube.com/shorts/" in vu:
            emb = "https://www.youtube.com/embed/" + vu.split("shorts/")[1].split("?")[0]
        elif "vimeo.com/" in vu:
            vid = vu.split("vimeo.com/")[1].split("?")[0].split("/")[0]
            if vid.isdigit():
                emb = "https://player.vimeo.com/video/" + vid
        if emb:
            v["videoEmbed"] = emb

        # serviceMetros -> display names + traveling copies
        sm = [m for m in (v.get("serviceMetros") or []) if m in BY_ID]
        home = v.get("metroId")
        if sm:
            ordered = [m for m in sm if m != home]
            v["serviceMetroNames"] = [BY_ID[home]["display"]] + [BY_ID[m]["display"] for m in ordered] if home in BY_ID else [BY_ID[m]["display"] for m in ordered]
            hp = home_path(v)
            for m in ordered:
                cp = dict(v)
                cp["metroId"] = m
                cp["travelFrom"] = BY_ID[home]["name"] if home in BY_ID else ""
                if hp:
                    cp["homeCanonical"] = BASE_URL + hp
                cp.pop("serviceMetroNames", None)
                extra.append(cp)

        # preferred vendors -> resolved links
        prefs = v.get("preferredVendors") or []
        resolved = []
        for p in prefs:
            pid = p.get("placeId") if isinstance(p, dict) else None
            t = by_pid.get(pid)
            if t:
                tp = home_path(t)
                if tp:
                    resolved.append({"name": t.get("name", ""), "path": tp})
        if resolved:
            v["preferredResolved"] = resolved

    vendors.extend(extra)
    print(f"saturday_enrich: +{len(extra)} traveling-vendor listings")
    return vendors

'''
src = src.replace(anchor,
    enrich.strip("\\n") + "\\n\\n" +
    '''    vendors = load_vendors_mock(Path(a.mock)) if a.mock else load_vendors_firestore(a.tranche)
    vendors = saturday_enrich(vendors)
    build(vendors)''')
bp.write_text(src, encoding="utf-8")
print("PATCHED: build.py enriches profiles + emits traveling-vendor listings.")
