import pathlib
p = pathlib.Path('seo_audit.py')
s = p.read_text(encoding='utf-8')
a = ("toks = [t for t in re.split(r'[-_]', f.stem.lower()) if len(t) > 2]",
     "toks = [t for t in re.split(r'[-_]', f.stem.lower()) if len(t) >= 2]")
b = ("for t in toks: norm = norm.replace(t, '')",
     "for t in toks: norm = re.sub(r'\\b%s\\b' % re.escape(t), ' ', norm)")
for old, new in (a, b):
    assert old in s, 'NOT FOUND: ' + old[:40]
    s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('seo_audit.py: word-boundary stripping + state codes')
