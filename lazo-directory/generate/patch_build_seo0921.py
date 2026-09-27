"""patch_build_seo0921.py - JC-LAZO-SEO-0921-001
Three SEO additions to the build, applied once (idempotent, asserts on anchors):

 1. Slug write-back. build.py computes each vendor's URL slug (slugify + a
    per-metro de-conflict) and never stored it, so the couple app's "View full
    Lazo profile" button - which needs vendors/{id}.slug - never rendered for
    any of the 119,000 vendors. After the de-conflict pass the build now writes
    the final slug to Firestore for every vendor whose stored slug differs
    (batched, non-fatal). First run: every vendor. After that: only changes.
 2. Nearby-metro links. Metro pages get "Nearby cities" and category pages get
    "<Category> in nearby cities", both computed from config/metros centers
    (six nearest within 260 mi, category pages only where that metro lists the
    category). Internal links between the 108 metro clusters, which the 50
    metros added on 2026-09-21 otherwise lack entirely.
 3. deploy_site.py step 6: submit today's changed URLs to IndexNow after the
    sync (deploy/indexnow.py), so Bing/Yandex/DuckDuckGo index new pages in
    hours rather than weeks. Google ignores IndexNow; sitemaps cover it.

  python generate\\patch_build_seo0921.py
"""
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    return s.replace(old, new)

# ---------------------------------------------------------------- build.py
bp = ROOT / "generate" / "build.py"; b = bp.read_text(encoding="utf-8")
if "JC-LAZO-SEO-0921-001" in b:
    print("build.py: already patched")
else:
    b = rep(b, "_GONE = []  # JC-LAZO-GONE-0903",
            "_DB = None  # JC-LAZO-SEO-0921-001: the Firestore client, kept for the slug write-back\n_GONE = []  # JC-LAZO-GONE-0903", "db global")
    b = rep(b, "    db = firestore.client()\n    metro_ids = [m[\"id\"] for m in metros_for_tranche(tranche)]",
            "    db = firestore.client()\n    global _DB\n    _DB = db\n    metro_ids = [m[\"id\"] for m in metros_for_tranche(tranche)]", "db capture")
    b = rep(b, '        v["slug"] = slugify(v["name"])\n',
            '        v["_storedSlug"] = (v.get("slug") or "")  # JC-LAZO-SEO-0921-001\n        v["slug"] = slugify(v["name"])\n', "stored slug")
    b = rep(b, "            seen[v[\"slug\"]] = True\n    build_content(by_metro)\n",
            "            seen[v[\"slug\"]] = True\n    _writeback_slugs(by_metro)\n    build_content(by_metro)\n", "writeback call")
    helpers = '''
# JC-LAZO-SEO-0921-001: the couple app links to meetlazo.com/{metro}/{cat}/{slug}/
# from a vendor's sheet only when vendors/{id}.slug exists. The slug was only ever
# computed here, so the link never showed. Write the final (de-conflicted) slug
# back for every vendor whose stored value differs; batched, never fatal.
def _writeback_slugs(by_metro):
    if _DB is None:
        return
    todo = [(v["placeId"], v["slug"]) for vs in by_metro.values() for v in vs
            if v.get("placeId") and v.get("_storedSlug", "") != v["slug"]]
    if not todo:
        print("[build] slugs: all stored, nothing to write back")
        return
    done = 0
    try:
        col = _DB.collection("vendors")
        for i in range(0, len(todo), 400):
            batch = _DB.batch()
            for pid, slug in todo[i:i + 400]:
                batch.update(col.document(pid), {"slug": slug})
            batch.commit()
            done += len(todo[i:i + 400])
    except Exception as e:  # noqa: BLE001
        print(f"[build] slugs: write-back stopped after {done:,}/{len(todo):,}: {type(e).__name__}: {e}")
        return
    print(f"[build] slugs: wrote {done:,} slug(s) back to Firestore")


def _near_metros(metro, n=6, max_mi=260):
    """The n nearest other metros within max_mi, for the nearby-cities links."""
    a = {"lat": metro["center"][0], "lng": metro["center"][1]}
    out = []
    for m in METROS:
        if m["id"] == metro["id"]:
            continue
        d = _dist_mi(a, {"lat": m["center"][0], "lng": m["center"][1]})
        if d <= max_mi:
            out.append((d, m))
    out.sort(key=lambda t: t[0])
    return [dict(id=m["id"], name=m["name"], display=m["display"], miles=int(round(d))) for d, m in out[:n]]

'''
    b = rep(b, "\ndef build(vendors: list[dict]):\n", helpers + "\ndef build(vendors: list[dict]):\n", "helpers")
    b = rep(b, "    live_metros = [BY_ID[mid] for mid in by_metro if mid in BY_ID]\n",
            "    live_metros = [BY_ID[mid] for mid in by_metro if mid in BY_ID]\n"
            "    _cats_of = {mid: {c for v in vs for c in v[\"categories\"]} for mid, vs in by_metro.items()}  # JC-LAZO-SEO-0921-001\n", "cats_of")
    b = rep(b, "            t_metro.render(metro=metro, categories=cats_here, total=len(vs), base=BASE_URL,\n                           featured=pick_featured((mid, v) for v in vs)),",
            "            t_metro.render(metro=metro, categories=cats_here, total=len(vs), base=BASE_URL,\n                           featured=pick_featured((mid, v) for v in vs),\n                           near=[m for m in _near_metros(metro) if m[\"id\"] in by_metro]),", "metro render")
    b = rep(b, "                t_cat.render(metro=metro, cat=cat, vendors=cvs, base=BASE_URL, cat_intro=cat_intro,\n                             cost_typical=_COST_TYPICAL.get(cat[\"slug\"])), encoding=\"utf-8\")",
            "                t_cat.render(metro=metro, cat=cat, vendors=cvs, base=BASE_URL, cat_intro=cat_intro,\n                             cost_typical=_COST_TYPICAL.get(cat[\"slug\"]),\n                             near=[m for m in _near_metros(metro) if cat[\"slug\"] in _cats_of.get(m[\"id\"], ())]), encoding=\"utf-8\")", "cat render")
    bp.write_text(b, encoding="utf-8", newline="\n"); print("build.py: slug write-back + nearby metros")

# ---------------------------------------------------------------- templates
mp = ROOT / "generate" / "templates" / "metro.html"; m = mp.read_text(encoding="utf-8")
if "lz-near" in m:
    print("metro.html: already patched")
else:
    block = '''<!-- lz-near -->
{% if near %}
<section class="band" style="padding-top:0">
  <h2 class="band-title" style="font-size:28px">Nearby cities</h2>
  <p class="band-sub">Getting married near {{ metro.name }}? Vendors from these cities travel for weddings here.</p>
  <div class="cat-grid">
    {% for m in near %}
    <a class="cat-card" href="/{{ m.id }}/"><span class="cat-name">Wedding vendors in {{ m.name }}</span><span class="cat-count">{{ m.miles }} miles from {{ metro.name }}</span></a>
    {% endfor %}
  </div>
</section>
{% endif %}
<!-- /lz-near -->
'''
    m = rep(m, '<section class="june" style="background-image:linear-gradient(120deg,rgba(46,21,48,.9),rgba(61,28,59,.82)),url(\'/assets/photos/atmo-candlelight.jpg\')">',
            block + '<section class="june" style="background-image:linear-gradient(120deg,rgba(46,21,48,.9),rgba(61,28,59,.82)),url(\'/assets/photos/atmo-candlelight.jpg\')">', "metro near")
    mp.write_text(m, encoding="utf-8", newline="\n"); print("metro.html: nearby cities")

cp = ROOT / "generate" / "templates" / "category.html"; c = cp.read_text(encoding="utf-8")
if "lz-near" in c:
    print("category.html: already patched")
else:
    block = '''<!-- lz-near -->
{% if near %}
<section class="band" style="padding-top:0">
  <h2 class="band-title" style="font-size:28px">{{ cat.label }} in nearby cities</h2>
  <p class="band-sub">Many {{ cat.label|lower }} travel. If {{ metro.name }} is short on dates, these cities are close enough to book.</p>
  <div class="cat-grid">
    {% for m in near %}
    <a class="cat-card" href="/{{ m.id }}/{{ cat.slug }}/"><span class="cat-name">{{ cat.label }} in {{ m.name }}</span><span class="cat-count">{{ m.miles }} miles away</span></a>
    {% endfor %}
  </div>
</section>
{% endif %}
<!-- /lz-near -->
'''
    i = c.rindex("{% endblock %}")
    c = c[:i] + block + c[i:]
    cp.write_text(c, encoding="utf-8", newline="\n"); print("category.html: category in nearby cities")

# ---------------------------------------------------------------- deploy_site.py
dp = ROOT / "deploy" / "deploy_site.py"; d = dp.read_text(encoding="utf-8")
if "indexnow" in d:
    print("deploy_site.py: already patched")
else:
    d = rep(d, 'def purge():\n    print("== 5/5 cache purge ==")',
            '''def indexnow():
    """JC-LAZO-SEO-0921-001: tell IndexNow (Bing, Yandex, DuckDuckGo, Naver) which
    URLs changed today, straight after the sync. Non-fatal; Google ignores it."""
    print("== 6/6 IndexNow ==")
    import datetime as _dt, subprocess as _sp
    try:
        r = _sp.run([sys.executable, str(ROOT / "deploy" / "indexnow.py"), "--since",
                     _dt.date.today().isoformat()], capture_output=True, text=True, timeout=600)
        print((r.stdout or "").strip()[-1500:])
        if r.returncode:
            print("  indexnow failed (non-fatal):", (r.stderr or "").strip()[-400:])
    except Exception as e:  # noqa: BLE001
        print("  indexnow skipped (non-fatal):", e)


def purge():
    print("== 5/6 cache purge ==")''', "indexnow def")
    # call it after purge in main flow
    n = len(re.findall(r"^\s*purge\(\)\s*$", d, re.M))
    if n != 1:
        raise SystemExit(f"deploy_site.py: expected one bare purge() call, found {n}")
    d = re.sub(r"^(\s*)purge\(\)\s*$", r"\1purge()\n\1indexnow()", d, count=1, flags=re.M)
    dp.write_text(d, encoding="utf-8", newline="\n"); print("deploy_site.py: IndexNow step after purge")
