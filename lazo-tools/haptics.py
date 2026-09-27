"""v175 H2: wrap every Material button callback in a haptic helper.

  onPressed: X            ->  onPressed: _h(X)            (or _h(X, _Tick.medium))
  onSelected: X           ->  onSelected: _hb(X)          (chips)
  Switch(... onChanged: X ->  onChanged: _hb(X)           (Switch / SwitchListTile only)

X is the whole expression, found by a small Dart-aware scanner (strings with
${} interpolation, raw and triple-quoted strings, comments, nested brackets).
Literal `null` and already-wrapped sites are left alone, so the script is
idempotent.
"""
import re
import sys

SRC = sys.argv[1]
src = open(SRC, encoding='utf-8').read()

MEDIUM_MARKERS = [
    "'Send invoice'", "'Send proposal'", "'Send hello'", "'Send for signature'",
    "Text('Send')", "'Send to the couple'", "'Mark booked'", "'Choose $title'",
    "'Save profile'", "'Save brand'", "'Save scheduler'", "'Send the plan'",
    "'Send ${rows.length} payment", "'Recommend ${picked.length} pro",
    "'Send the report'", "'Send the plan'",
]


def skip_string(s, i):
    """i points at the opening quote (after any r prefix). Return index after close."""
    q = s[i]
    triple = s.startswith(q * 3, i)
    raw = i > 0 and s[i - 1] == 'r' and (i < 2 or not (s[i - 2].isalnum() or s[i - 2] == '_'))
    i += 3 if triple else 1
    n = len(s)
    while i < n:
        c = s[i]
        if not raw and c == '\\':
            i += 2
            continue
        if not raw and c == '$' and i + 1 < n and s[i + 1] == '{':
            i = skip_balanced(s, i + 1, '{', '}')
            continue
        if triple:
            if s.startswith(q * 3, i):
                return i + 3
        elif c == q:
            return i + 1
        i += 1
    raise ValueError('unterminated string at %d' % i)


def skip_comment(s, i):
    if s.startswith('//', i):
        j = s.find('\n', i)
        return len(s) if j < 0 else j
    if s.startswith('/*', i):
        j = s.find('*/', i + 2)
        return len(s) if j < 0 else j + 2
    return i


def skip_balanced(s, i, open_c, close_c):
    """i points at open_c. Return index after the matching close_c."""
    depth = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c in "'\"":
            i = skip_string(s, i)
            continue
        if s.startswith('//', i) or s.startswith('/*', i):
            i = skip_comment(s, i)
            continue
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError('unbalanced from %d' % i)


def expr_end(s, i):
    """i points at the first char of a named-argument expression. Return the
    index of the terminating ',' or ')' at depth 0."""
    n = len(s)
    while i < n:
        c = s[i]
        if c in "'\"":
            i = skip_string(s, i)
            continue
        if s.startswith('//', i) or s.startswith('/*', i):
            i = skip_comment(s, i)
            continue
        if c in '([{':
            i = skip_balanced(s, i, c, {'(': ')', '[': ']', '{': '}'}[c])
            continue
        if c in ',)]}':
            return i
        i += 1
    raise ValueError('no end')


def wrap_all(s, key, helper, tier_of=None, only_in=None):
    """Wrap every `key: expr` with helper(expr). only_in: regex for enclosing
    widget constructor; when given, only sites inside such a call are touched."""
    out = []
    pos = 0
    count = 0
    pat = re.compile(r'(?<![A-Za-z_])' + re.escape(key) + r'\s*')
    allowed = None
    if only_in is not None:
        allowed = []
        for m in re.finditer(only_in, s):
            start = m.end() - 1  # the '('
            end = skip_balanced(s, start, '(', ')')
            allowed.append((start, end))
    for m in pat.finditer(s):
        if m.start() < pos:
            continue
        # must be a named argument, not inside a string/comment: cheap check -
        # the key must be preceded by whitespace, '(' or ','
        prev = s[m.start() - 1] if m.start() > 0 else '\n'
        if prev not in ' \t\n(,':
            continue
        # not on a comment line
        ls = s.rfind('\n', 0, m.start()) + 1
        if '//' in s[ls:m.start()]:
            continue
        if allowed is not None and not any(a <= m.start() < b for a, b in allowed):
            continue
        e0 = m.end()
        e1 = expr_end(s, e0)
        expr = s[e0:e1]
        stripped = expr.strip()
        if stripped == 'null' or stripped.startswith(helper + '('):
            continue
        # trailing whitespace/newlines stay outside the wrapper
        body = expr.rstrip()
        trail = expr[len(body):]
        tier = tier_of(s, e1) if tier_of else None
        repl = '%s(%s%s)' % (helper, body, (', ' + tier) if tier else '')
        out.append(s[pos:e0])
        out.append(repl + trail)
        pos = e1
        count += 1
    out.append(s[pos:])
    return ''.join(out), count


def medium_tier(s, after):
    """Look at the rest of this widget's argument list for a medium marker."""
    # scan forward to the end of the enclosing constructor call
    depth = 0
    i = after
    n = len(s)
    while i < n:
        c = s[i]
        if c in "'\"":
            i = skip_string(s, i)
            continue
        if c in '([{':
            depth += 1
        elif c in ')]}':
            if depth == 0:
                break
            depth -= 1
        i += 1
    window = s[after:i]
    for mk in MEDIUM_MARKERS:
        if mk in window:
            return '_Tick.medium'
    return None


src, n1 = wrap_all(src, 'onPressed:', '_h', tier_of=medium_tier)
src, n2 = wrap_all(src, 'onSelected:', '_hb')
src, n3 = wrap_all(src, 'onChanged:', '_hb',
                   only_in=r'(?<![A-Za-z_])Switch(?:ListTile)?\(')

open(SRC, 'w', encoding='utf-8', newline='\n').write(src)
print('onPressed wrapped:', n1)
print('onSelected wrapped:', n2)
print('Switch onChanged wrapped:', n3)
