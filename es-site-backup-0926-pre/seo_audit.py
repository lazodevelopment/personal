import pathlib, re, hashlib
from collections import Counter, defaultdict

ROOT = pathlib.Path('.')
PAGE_DIRS = ['wedding-photographer', 'locations']

def strip_tags(h):
    h = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.S|re.I)
    h = re.sub(r'<[^>]+>', ' ', h)
    h = re.sub(r'&#?\w+;', ' ', h)
    return re.sub(r'\s+', ' ', h).strip()

def meta(html, name):
    for tag in re.findall(r'<meta\b[^>]*>', html, re.I):
        if re.search(r'name\s*=\s*["\']%s["\']' % name, tag, re.I):
            m = re.search(r'content\s*=\s*["\'](.*?)["\']', tag, re.I|re.S)
            if m: return m.group(1).strip()
    return ''

def canon(html):
    for tag in re.findall(r'<link\b[^>]*>', html, re.I):
        if re.search(r'rel\s*=\s*["\']canonical["\']', tag, re.I):
            m = re.search(r'href\s*=\s*["\'](.*?)["\']', tag, re.I)
            if m: return m.group(1).strip()
    return ''

pages = []
for d in PAGE_DIRS:
    base = ROOT / d
    if not base.exists(): continue
    for f in sorted(base.rglob('*.html')):
        html = f.read_text(encoding='utf-8', errors='replace')
        toks = [t for t in re.split(r'[-_]', f.stem.lower()) if len(t) >= 2]
        body = strip_tags(html)
        norm = body.lower()
        for t in toks: norm = re.sub(r'\b%s\b' % re.escape(t), ' ', norm)
        norm = re.sub(r'[^a-z ]+', ' ', norm)
        norm = re.sub(r'\s+', ' ', norm).strip()
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S|re.I)
        pages.append(dict(
            path=str(f.relative_to(ROOT)).replace('\\','/'),
            title=(re.search(r'<title[^>]*>(.*?)</title>', html, re.S|re.I) or [None,''])[1].strip()
                  if re.search(r'<title[^>]*>(.*?)</title>', html, re.S|re.I) else '',
            desc=meta(html,'description'), robots=meta(html,'robots'),
            h1=strip_tags(m.group(1)) if m else '',
            canon=canon(html), words=len(body.split()),
            schema=sorted(set(re.findall(r'"@type"\s*:\s*"([^"]+)"', html))),
            skel=hashlib.md5(norm.encode()).hexdigest()[:10],
            links=len(set(re.findall(r'href=["\'](/[^"\'#?]*)', html))),
            imgs=len(re.findall(r'<img\b', html)))) 

n = len(pages)
print(f"=== {n} LOCATION PAGES SCANNED ===\n")

def dupe(field, label):
    c = Counter(p[field] for p in pages)
    blank = c.pop('', 0)
    dupes = {k:v for k,v in c.items() if v > 1}
    print(f"{label}: {len(c)} unique / {n} pages | missing: {blank} | duplicated: {sum(dupes.values())}")
    for k,v in sorted(dupes.items(), key=lambda x:-x[1])[:3]:
        print(f"    x{v}  {k[:90]}")

dupe('title','TITLE'); dupe('desc','META DESC'); dupe('h1','H1')

dl = [len(p['desc']) for p in pages if p['desc']]
if dl: print(f"    desc length: min {min(dl)} / med {sorted(dl)[len(dl)//2]} / max {max(dl)}  (target 120-158)")

print()
skel = defaultdict(list)
for p in pages: skel[p['skel']].append(p['path'])
groups = sorted((v for v in skel.values() if len(v) > 1), key=len, reverse=True)
identical = sum(len(g) for g in groups)
print(f"TEMPLATE SKELETON: {len(skel)} distinct / {n} pages")
print(f"  -> {identical} pages ({100*identical//max(n,1)}%) are byte-identical after city names removed")
for g in groups[:3]:
    print(f"    cluster of {len(g)}: {', '.join(x.split('/')[-1] for x in g[:4])}...")

print()
w = sorted(p['words'] for p in pages)
if w:
    print(f"WORD COUNT: min {w[0]} / med {w[len(w)//2]} / max {w[-1]}")
    print(f"  under 300 words: {sum(1 for x in w if x < 300)} pages")
print(f"CANONICAL: {sum(1 for p in pages if p['canon'])} present / {n}")
print(f"NOINDEX:   {sum(1 for p in pages if 'noindex' in p['robots'].lower())} pages")
il = sorted(p['links'] for p in pages)
print(f"INTERNAL LINKS/page: min {il[0]} / med {il[len(il)//2]} / max {il[-1]}")
im = sorted(p['imgs'] for p in pages)
print(f"IMAGES/page: min {im[0]} / med {im[len(im)//2]} / max {im[-1]}")
sc = Counter(t for p in pages for t in p['schema'])
print(f"SCHEMA TYPES: {dict(sc)}")

locs = set()
for sm in ROOT.glob('sitemap*.xml'):
    locs |= set(re.findall(r'<loc>(.*?)</loc>', sm.read_text(encoding='utf-8', errors='replace')))
print(f"\nSITEMAPS: {len(list(ROOT.glob('sitemap*.xml')))} files, {len(locs)} total <loc> entries")
missing = [p['path'] for p in pages if not any(p['path'].rsplit('.html',1)[0] in l for l in locs)]
print(f"  location pages absent from sitemaps: {len(missing)}")
for x in missing[:5]: print(f"    {x}")
