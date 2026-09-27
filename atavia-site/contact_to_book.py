# JC-ATV-BOOKCTA-0914-001 - every CTA that pointed at /contact now goes to /book/.
# Edits the generators and page sources under _src (so rebuilds keep it) and adds
# a 301 in _redirects so old links and Google land on the booking page.
# Run from C:\Users\kurvh\atavia-site:   python contact_to_book.py
import io, os, re, glob

ROOT = os.getcwd()
exts = ('.html', '.htm', '.py', '.js')
pat = re.compile(r'''(href=["'])(?:https://(?:www\.)?ataviaweddings\.com)?/contact/?(?=["'#?])''')
touched = {}
for p in glob.glob('_src/**/*', recursive=True):
    if not os.path.isfile(p) or not p.lower().endswith(exts) or '.bak' in p: continue
    if os.path.basename(p) in ('contact.html',): continue          # the page itself - retired below
    try: s = io.open(p, encoding='utf-8').read()
    except UnicodeDecodeError: continue
    s2, n = pat.subn(r'\g<1>/book/', s)
    # Jinja/f-string style href in the generators, e.g. href=\"/contact\"
    s2, m = re.subn(r'href=\\"/contact/?\\"', r'href=\\"/book/\\"', s2)
    if n + m:
        io.open(p, 'w', encoding='utf-8', newline='\n').write(s2)
        touched[p] = n + m

for p, n in sorted(touched.items()):
    print('%4d  %s' % (n, p))
print('files changed:', len(touched))

# retire the contact page source so it is no longer built or listed in the sitemap
cp = os.path.join('_src', 'pages', 'contact.html')
if os.path.exists(cp):
    os.makedirs(os.path.join('_src', 'retired'), exist_ok=True)
    os.replace(cp, os.path.join('_src', 'retired', 'contact.html'))
    print('moved _src\\pages\\contact.html -> _src\\retired\\contact.html')

# 301 so /contact keeps working for anyone holding the old link
rp = '_redirects'
lines = io.open(rp, encoding='utf-8').read().splitlines() if os.path.exists(rp) else []
if not any(l.split() and l.split()[0] in ('/contact', '/contact/') for l in lines):
    lines = ['/contact  /book/  301', '/contact/  /book/  301'] + lines
    io.open(rp, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    print('added /contact -> /book/ 301 to _redirects')
else:
    print('_redirects already routes /contact')
