# JC-ATV-BADGE-0914-001 - add the Lazo Verified badge after the Zola badge
# in the "As Featured On" row.  Run from C:\Users\kurvh\atavia-site:
#     python add_lazo_badge.py
import io, glob, sys

BADGE = ('<a class="badge-logo" href="https://meetlazo.com/phoenix/wedding-videographers/atavia-weddings/'
         '?utm_source=ataviaweddings&amp;utm_medium=badge&amp;utm_campaign=featured-on" target="_blank" '
         'rel="noopener" aria-label="View Atavia Weddings on Lazo" title="Atavia Weddings on Lazo">'
         '<img src="https://meetlazo.com/badges/lazo-verified-plum.png" alt="Lazo Verified &mdash; Atavia Weddings" '
         'width="140" height="140" loading="lazy"></a>')

ANCHOR = 'alt="Featured on Zola" loading="lazy"></a>'
done = []
for p in glob.glob('_src/**/*.html', recursive=True):
    s = io.open(p, encoding='utf-8').read()
    if ANCHOR in s and 'lazo-verified-plum' not in s:
        s = s.replace(ANCHOR, ANCHOR + '\n      ' + BADGE, 1)
        io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
        done.append(p)
if not done:
    sys.exit('Zola badge anchor not found under _src (or the Lazo badge is already there)')
print('added Lazo badge to:', done)
