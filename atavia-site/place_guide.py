# JC-ATV-GUIDE-VET-0914-002 - place the "How to Vet a Wedding Vendor" guide
# into the Atavia source tree by mirroring how the existing guide
# "wedding-videography-cost" is stored.  Run from C:\Users\kurvh\atavia-site:
#     python place_guide.py
import io, os, re, sys, glob, json, shutil

SLUG_OLD = 'wedding-videography-cost'
SLUG_NEW = 'how-to-vet-wedding-vendors'
TITLE    = 'How to Vet a Wedding Vendor Before You Pay a Deposit'
DESC     = ('How to vet a wedding vendor in 2026 \u2014 the five checks that catch fake reviews, '
            'hidden fees and vendors who won\u2019t show, and where to find prices before you ever send a message.')
KEYWORDS = ('how to vet wedding vendors, wedding vendor red flags, are wedding vendor reviews real, '
            'verified wedding vendor reviews, wedding vendor pricing, questions to ask wedding vendors, '
            'wedding vendor contract')
CARD_SUB = 'Five checks, ten minutes, and the question most couples forget.'

frag_path = os.path.join(os.environ.get('USERPROFILE', ''), 'Downloads', 'guide-how-to-vet-wedding-vendors.html')
if not os.path.exists(frag_path):
    sys.exit('Downloads\\guide-how-to-vet-wedding-vendors.html not found')
frag = io.open(frag_path, encoding='utf-8').read()
frag = re.sub(r'^\s*<!--.*?-->\s*', '', frag, flags=re.S)  # drop the meta comment

def rd(p): return io.open(p, encoding='utf-8').read()
def wr(p, s):
    os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

# 1) find where the existing guide's body lives under _src
hits = []
for p in glob.glob('_src/**/*', recursive=True):
    if os.path.isfile(p) and p.lower().endswith(('.html', '.htm', '.md', '.json', '.py')):
        try: t = rd(p)
        except Exception: continue
        if 'The honest ranges' in t: hits.append(p)
if not hits:
    sys.exit('Could not find the source of /guides/wedding-videography-cost under _src - tell Claude what _src\\pages contains')
print('existing guide source:', hits)

src = [h for h in hits if not h.endswith('.py')]
if not src:
    sys.exit('The guide body is inside a .py file (%s) - send that file to Claude to patch' % hits[0])
old = src[0]
new = old.replace(SLUG_OLD, SLUG_NEW)
if new == old:
    sys.exit('Source file %s is not named by slug - send it to Claude' % old)
t = rd(old)

if '<html' in t.lower():
    # full-page source: swap <main>, title, description, canonical, ld+json headline/keywords
    m0 = t.find('<main'); m0 = t.find('>', m0) + 1; m1 = t.find('</main>')
    body = frag.strip()
    t2 = t[:m0] + '\n' + body + '\n' + t[m1:]
    t2 = re.sub(r'<title>.*?</title>', '<title>%s | Atavia Weddings</title>' % TITLE, t2, count=1, flags=re.S)
    t2 = re.sub(r'(<meta name="description" content=")[^"]*', lambda m: m.group(1) + DESC.replace('"', '&quot;'), t2, count=1)
    t2 = t2.replace(SLUG_OLD, SLUG_NEW)
    t2 = re.sub(r'"headline": "[^"]*"', '"headline": "%s"' % TITLE, t2)
    t2 = re.sub(r'"description": "[^"]*"', '"description": "%s"' % DESC.replace('"', '\\"'), t2)
    t2 = re.sub(r'"keywords": "[^"]*"', '"keywords": "%s"' % KEYWORDS, t2)
    t2 = re.sub(r'"name": "What Wedding Photography & Videography Actually Cost"', '"name": "%s"' % TITLE, t2)
    wr(new, t2); print('wrote full page', new)
else:
    # fragment source: replace the body wholesale; meta is set elsewhere (build.py list) - report it
    wr(new, frag.strip() + '\n'); print('wrote fragment', new)
    print('NOTE: meta (title/description) for guides is not in this file - check build.py for a guides list and add:')
    print(json.dumps({'slug': SLUG_NEW, 'title': TITLE, 'description': DESC, 'keywords': KEYWORDS}, indent=2))

# 2) guides index card: clone the first fcard and put the new guide at position 01
idx_candidates = [p for p in glob.glob('_src/**/*.html', recursive=True) if 'fcard__idx' in rd(p) and '/guides/' + SLUG_OLD in rd(p)]
if idx_candidates:
    ip = idx_candidates[0]; s = rd(ip)
    if SLUG_NEW not in s:
        m = re.search(r'<a href="/guides/[^"]+" class="fcard reveal"[^>]*>.*?</a>', s, re.S)
        card = m.group(0)
        card = re.sub(r'href="/guides/[^"]+"', 'href="/guides/%s"' % SLUG_NEW, card)
        card = re.sub(r'<h3>.*?</h3>', '<h3>%s</h3>' % TITLE, card, flags=re.S)
        card = re.sub(r'<p>.*?</p>', '<p>%s</p>' % CARD_SUB, card, count=1, flags=re.S)
        card = re.sub(r'<div class="fcard__idx">\d+</div>', '<div class="fcard__idx">01</div>', card)
        s = s[:m.start()] + card + s[m.start():]
        # renumber the rest
        n = [0]
        def renum(mm):
            n[0] += 1; return '<div class="fcard__idx">%02d</div>' % n[0]
        s = re.sub(r'<div class="fcard__idx">\d+</div>', renum, s)
        wr(ip, s); print('added index card to', ip)
else:
    print('guides index source not found - add the card by hand or tell Claude')

# 3) "More guides" lists on the other guides (only if they are static per-file)
for p in glob.glob('_src/**/*.html', recursive=True):
    if p == new: continue
    s = rd(p)
    if 'class="guide-more' in s and '/guides/' + SLUG_OLD in s and SLUG_NEW not in s and '<div class="loc-grid">' in s:
        s = s.replace('<div class="loc-grid">', '<div class="loc-grid"><a href="/guides/%s">%s</a>' % (SLUG_NEW, TITLE), 1)
        wr(p, s); print('cross-linked', p)
print('done')
