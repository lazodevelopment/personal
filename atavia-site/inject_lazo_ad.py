# JC-ATV-LAZOAD-0914-002 - inject the Lazo ad into the Atavia page sources.
# Run from C:\Users\kurvh\atavia-site:  python inject_lazo_ad.py
# 002: strips the fragment's leading <!-- ... --> comment (it mentions the anchor
#      section, which tripped the exactly-one check) and removes any old copy
#      together with its comment.
import re, io, os, sys

ad_path = os.path.join('_src', 'lazo-ad.html')
if not os.path.exists(ad_path):
    sys.exit('missing _src\\lazo-ad.html - copy it from Downloads first')
ad = io.open(ad_path, encoding='utf-8').read().strip()
ad = re.sub(r'^\s*<!--.*?-->\s*', '', ad, flags=re.S)          # drop the header comment
if not ad.startswith('<section class="lazo-ad-wrap"'):
    sys.exit('fragment does not start with the lazo-ad-wrap section - tell Claude')

home = None
for cand in ('index.html', 'home.html'):
    p = os.path.join('_src', 'pages', cand)
    if os.path.exists(p):
        home = p
        break
if not home:
    sys.exit('could not find the home page source under _src\\pages')

targets = [
    (home, '<section class="cta-band'),
    (os.path.join('_src', 'pages', 'packages.html'), '<section class="closing"'),
]

OLD = re.compile(r'(?:<!--(?:(?!-->).)*LAZO AD(?:(?!-->).)*-->\s*)?<section class="lazo-ad-wrap".*?</section>\s*', re.S)

for path, anchor in targets:
    s = io.open(path, encoding='utf-8').read()
    s, n = OLD.subn('', s)
    if s.count(anchor) != 1:
        sys.exit('%s: expected exactly one %r, found %d - tell Claude' % (path, anchor, s.count(anchor)))
    s = s.replace(anchor, ad + '\n' + anchor)
    io.open(path, 'w', encoding='utf-8', newline='\n').write(s)
    print('injected into', path, '(replaced old copy)' if n else '')
print('done')
