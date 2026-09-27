import io
p = '_src/gen_guides.py'
s = io.open(p, encoding='utf-8').read()
n = s.count('href="/contact" class="btn btn--copper"')
s = s.replace('href="/contact" class="btn btn--copper"', 'href="/book/" class="btn btn--copper"')
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('replaced', n)
