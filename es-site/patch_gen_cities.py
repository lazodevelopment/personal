import pathlib
p = pathlib.Path('_src/gen_cities.py')
s = p.read_text(encoding='utf-8')

edits = [
 # 1. title: add state
 ('"%s Wedding Photographer &amp; Videographer | Elizabeth Scott" % h(name),',
  '"%s, %s Wedding Photographer &amp; Videographer | Elizabeth Scott" % (h(name), h(st)),'),
 # 2. h1: add state
 ('return (HERO % (h(name), h(r["sub"] % name))).replace("__HK__", _hk)',
  'return (HERO % ("%s, %s" % (h(name), h(st)), h(r["sub"] % name))).replace("__HK__", _hk)'),
 # 3. nearby-city links: add state
 ('% (slug("%s %s" % (n, s2)), h(n)) for n, s2 in nearby)',
  '% (slug("%s %s" % (n, s2)), "%s, %s" % (h(n), h(s2))) for n, s2 in nearby)'),
]

for old, new in edits:
    if new in s:
        print('SKIP (already applied):', old[:50]); continue
    assert old in s, 'NOT FOUND: ' + old[:60]
    s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('gen_cities.py: state added to title, H1, and nearby links')
