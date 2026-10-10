"""theme_rewrite.py - JC-LAZO-THEME-1009-001
Light and dark mode for the Lazo dashboards, done by role instead of by hand.

Every colour in a dashboard is read in place and given a role from the code around it:
  fg   - text, icons, foregroundColor ...           wrapped as _lzFg(x) when x is dark
  bg   - card / sheet / field / canvas fills        wrapped as _lzBg(x) when x is light
  line - borders, dividers, the gold hairline       wrapped as _lzLine(x) when x is light
In light mode the three functions return x untouched, so the light dashboard is byte-for-byte
the look it has today. In dark mode light surfaces become plum-black glass, dark text becomes
ivory, and gold, plum buttons and accents stay as they are.

A text colour is NOT flipped when the nearest fill around it (lexically: a Container, a
BoxDecoration, a button style ...) is a colour that stays in dark mode - plumDeep text on a gold
button keeps its contrast.

Any `const` that encloses a wrapped colour is dropped (the wrap is a runtime call).

  python theme_rewrite.py <in.dart> <out.dart> [report.txt]
"""
import re
import sys
from pathlib import Path

# ------------------------------------------------------------------ palette
PALETTE = {
    'plum': 0xFF52284F, 'plumDeep': 0xFF3D1C3B, 'gold': 0xFFD9B77C, 'gold2': 0xFFC9A45C,
    'ivory': 0xFFFAF6F0, 'ink': 0xFF241E2B, 'vGreen': 0xFF2E8B6B, 'muted': 0xFF6B5F72,
    'cardBg': 0xFFFFFDF9, 'card': 0xFFFFFDF9, 'goldLine': 0xFFE6D6B8, 'rose': 0xFFB04343,
}
COLORS = {
    'white': 0xFFFFFFFF, 'white70': 0xB3FFFFFF, 'white60': 0x99FFFFFF, 'white54': 0x8AFFFFFF,
    'white38': 0x62FFFFFF, 'white30': 0x4DFFFFFF, 'white24': 0x3DFFFFFF, 'white12': 0x1FFFFFFF,
    'white10': 0x1AFFFFFF, 'black': 0xFF000000, 'black87': 0xDD000000, 'black54': 0x8A000000,
    'black45': 0x73000000, 'black38': 0x61000000, 'black26': 0x42000000, 'black12': 0x1F000000,
    'transparent': 0x00000000,
}


def lum(argb):
    r, g, b = (argb >> 16) & 255, (argb >> 8) & 255, argb & 255
    mx, mn = max(r, g, b) / 255, min(r, g, b) / 255
    return (mx + mn) / 2


def alpha(argb):
    return ((argb >> 24) & 255) / 255


FG_ARGS = {'foregroundColor', 'iconColor', 'labelColor', 'unselectedLabelColor', 'checkmarkColor',
           'cursorColor', 'prefixIconColor', 'suffixIconColor', 'textColor', 'disabledForegroundColor'}
BG_ARGS = {'backgroundColor', 'fillColor', 'tileColor', 'dropdownColor', 'selectedTileColor',
           'canvasColor', 'scaffoldBackgroundColor', 'disabledBackgroundColor', 'surface'}
LINE_ARGS = {'borderColor', 'dividerColor', 'outlineColor'}
FG_CALLEES = {'TextStyle', 'Icon', 'IconThemeData', 'ImageIcon', 'Text', 'copyWith', 'IconButton',
              'TextSpan', 'DefaultTextStyle'}
BG_CALLEES = {'BoxDecoration', 'Container', 'Material', 'ColoredBox', 'Card', 'ShapeDecoration',
              'DecoratedBox', 'AnimatedContainer', 'Ink', 'Scaffold'}
LINE_CALLEES = {'Border.all', 'BorderSide', 'Divider', 'VerticalDivider', 'Border.fromBorderSide'}
SKIP_CALLEES = {'BoxShadow', 'Shadow', 'CircularProgressIndicator', 'LinearProgressIndicator',
                'AlwaysStoppedAnimation', 'SystemUiOverlayStyle', 'Paint', 'ColorFilter.mode'}
GRADIENTS = {'LinearGradient', 'RadialGradient', 'SweepGradient'}
FILL_PROPAGATE = {'BoxDecoration', 'ShapeDecoration', 'ButtonStyle'}  # + anything ending .styleFrom

# ------------------------------------------------------------------ lexer
IDENT = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')
NUM = re.compile(r'0[xX][0-9A-Fa-f]+|\d+(\.\d+)?([eE][+-]?\d+)?|\.\d+([eE][+-]?\d+)?')


def skip_string(s, i):
    """i at the opening quote (or the r prefix). Returns index after the string."""
    raw = False
    if s[i] == 'r':
        raw = True
        i += 1
    q = s[i]
    triple = s[i:i + 3] == q * 3
    i += 3 if triple else 1
    while i < len(s):
        c = s[i]
        if not raw and c == '\\':
            i += 2
            continue
        if triple and s[i:i + 3] == q * 3:
            return i + 3
        if not triple and c == q:
            return i + 1
        if not raw and c == '$' and i + 1 < len(s) and s[i + 1] == '{':
            i = skip_code_block(s, i + 1)
            continue
        i += 1
    return i


def skip_code_block(s, i):
    """i at '{'; returns index after the matching '}' (strings/comments aware)."""
    depth = 0
    while i < len(s):
        c = s[i]
        if c in '\'"' or (c == 'r' and i + 1 < len(s) and s[i + 1] in '\'"' and not IDENT.match(s[i - 1] if i else ' ')):
            i = skip_string(s, i)
            continue
        if s.startswith('//', i):
            j = s.find('\n', i)
            i = len(s) if j < 0 else j
            continue
        if s.startswith('/*', i):
            j = s.find('*/', i + 2)
            i = len(s) if j < 0 else j + 2
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return i


def tokenize(s):
    toks = []  # (kind, text, start, end)
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in ' \t\r\n':
            i += 1
            continue
        if s.startswith('//', i):
            j = s.find('\n', i)
            i = n if j < 0 else j
            continue
        if s.startswith('/*', i):
            j = s.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in '\'"' or (c == 'r' and i + 1 < n and s[i + 1] in '\'"'):
            j = skip_string(s, i)
            toks.append(('str', s[i:j], i, j))
            i = j
            continue
        m = IDENT.match(s, i)
        if m:
            toks.append(('id', m.group(), i, m.end()))
            i = m.end()
            continue
        m = NUM.match(s, i)
        if m and m.group():
            toks.append(('num', m.group(), i, m.end()))
            i = m.end()
            continue
        toks.append(('p', c, i, i + 1))
        i += 1
    return toks


# ------------------------------------------------------------------ colour expressions
def color_of_expr(txt):
    """Best-effort ARGB of a fill expression, honouring .withOpacity(x); None if unknown."""
    t = txt.strip()
    if '?' in t.replace('?.', '').replace('??', ''):
        return None  # a conditional fill is not a fill we can count on
    if t.startswith('const '):
        t = t[6:].strip()
    op = 1.0
    m = re.search(r'\.withOpacity\(\s*([0-9.]+)\s*\)\s*$', t) or re.search(r'\.withValues\(\s*alpha:\s*([0-9.]+)\s*\)\s*$', t)
    if m:
        op = float(m.group(1))
        t = t[:m.start()].strip()
    m = re.fullmatch(r'_lz(?:Fg|Bg|Line)\((.*)\)', t, re.S)
    if m:
        t = m.group(1).strip()
        if t.startswith('const '):
            t = t[6:].strip()
    v = None
    if t in PALETTE:
        v = PALETTE[t]
    elif t.startswith('Colors.') and t[7:] in COLORS:
        v = COLORS[t[7:]]
    else:
        m = re.fullmatch(r'Color\(\s*(0[xX][0-9A-Fa-f]{8})\s*\)', t)
        if m:
            v = int(m.group(1), 16)
    if v is None:
        m = re.search(r'colors:\s*(?:const\s*)?(?:<Color>)?\[\s*([^,\]]+)', t)  # a gradient: first stop
        if m:
            return color_of_expr(m.group(1))
        return None
    a = alpha(v) * op
    return (v & 0x00FFFFFF) | (int(round(a * 255)) << 24)


def flips_bg(argb):
    return argb is not None and lum(argb) > 0.75 and alpha(argb) > 0


def stays_fill(argb):
    """A fill that is still there, and still that colour, in dark mode."""
    return argb is not None and alpha(argb) >= 0.5 and lum(argb) <= 0.75


# ------------------------------------------------------------------ the pass
class Frame:
    __slots__ = ('kind', 'callee', 'const_span', 'arg', 'arg_start', 'args', 'fill', 'open')

    def __init__(self, kind, callee, const_span, open_):
        self.kind, self.callee, self.const_span, self.open = kind, callee, const_span, open_
        self.arg, self.arg_start, self.args, self.fill = None, None, {}, None


def callee_before(toks, k):
    """Dotted callee name ending just before toks[k] ('(' ), skipping a <...> type list.
    Returns (name, index of first token of the callee)."""
    j = k - 1
    if j >= 0 and toks[j][1] == '>':
        depth = 0
        while j >= 0:
            if toks[j][1] == '>':
                depth += 1
            elif toks[j][1] == '<':
                depth -= 1
                if depth == 0:
                    j -= 1
                    break
            j -= 1
    parts, first = [], j + 1
    while j >= 0 and toks[j][0] == 'id':
        parts.append(toks[j][1])
        first = j
        if j - 1 >= 0 and toks[j - 1][1] == '.' and j - 2 >= 0 and toks[j - 2][0] == 'id':
            j -= 2
            continue
        break
    return '.'.join(reversed(parts)), first


ROLE_ARGS_EXTRA_BG = {'inactiveTrackColor'}
FG_EXTRA = {'decorationColor'}


def role_of(fr):
    """Role of the current named arg of frame fr (a '(' frame)."""
    cal = fr.callee
    base = cal.split('.')[-1]
    if cal in SKIP_CALLEES or base in SKIP_CALLEES:
        return None
    a = fr.arg
    if a in FG_ARGS or a in FG_EXTRA:
        return 'fg'
    if a in BG_ARGS or a in ROLE_ARGS_EXTRA_BG:
        return 'bg'
    if a in LINE_ARGS:
        return 'line'
    if a == 'color':
        if cal in LINE_CALLEES or base in ('BorderSide', 'Divider', 'VerticalDivider'):
            return 'line'
        if base in BG_CALLEES:
            return 'bg'
        if base in FG_CALLEES or cal.startswith('GoogleFonts.') or cal in ('Image.network', 'Image.asset', 'Image') or base == '_serif':
            return 'fg'
    return None


def needs_wrap(role, val_txt, fill):
    v = color_of_expr(val_txt)
    t = val_txt.strip()
    if t in ('null', 'Colors.transparent') or t.startswith('_lz'):
        return False
    if role == 'fg':
        if stays_fill(fill):
            return False
        if v is not None:
            return lum(v) < 0.5 and alpha(v) > 0.3
        return True
    if role == 'bg':
        if v is not None:
            return flips_bg(v)
        return True
    if role == 'line':
        if v is not None:
            return lum(v) > 0.75
        return True
    return False


EXEMPT_FUNCS = ['_weatherHubWidget', '_weatherCard', '_vendorWeatherCard', '_goldDisc']


def exempt_spans(src):
    """Body spans of the EXEMPT_FUNCS method declarations."""
    out = []
    for name in EXEMPT_FUNCS:
        for m in re.finditer(r'^  [A-Za-z][\w<>?, ]*\s' + re.escape(name) + r'\(', src, re.M):
            i, depth = m.end() - 1, 0
            while i < len(src):  # the parameter list
                c = src[i]
                if c in '\'"':
                    i = skip_string(src, i)
                    continue
                if c == '(':
                    depth += 1
                elif c == ')':
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            j = src.find('{', i)
            if j < 0:
                continue
            out.append((m.start(), skip_code_block(src, j)))
    return out


def run(src):
    toks = tokenize(src)
    stack = [Frame('top', '', None, -1)]
    wraps = []      # (start, end, fn, frames)
    report = []

    def nearest_fill(frames):
        for f in reversed(frames):
            if f.fill is not None:
                v = color_of_expr(f.fill)
                if v is not None and alpha(v) >= 0.5:
                    return v
        return None

    def end_arg(fr, pos):
        """The current arg of fr ends at pos (a ',' or ')')."""
        if fr.arg is None:
            return
        st = fr.args.get('__s', pos)
        txt = src[st:pos]
        fr.args[fr.arg] = txt
        base = fr.callee.split('.')[-1]
        if fr.arg in ('color', 'backgroundColor') and (base in BG_CALLEES or base in ('styleFrom', 'FilledButton', 'ElevatedButton', 'Chip', 'CircleAvatar', 'ActionChip', 'FilterChip', 'ChoiceChip', 'Material')):
            if fr.fill is None:
                fr.fill = txt
        role = role_of(fr)
        if role and txt.strip():
            fill = nearest_fill(stack[:-1]) if role == 'fg' else None
            # the fill of this very frame counts for a foregroundColor beside a backgroundColor
            if role == 'fg' and fr.args.get('backgroundColor'):
                v = color_of_expr(fr.args['backgroundColor'])
                if v is not None and alpha(v) >= .5:
                    fill = v
            if needs_wrap(role, txt, fill):
                # trim whitespace
                a = st + (len(txt) - len(txt.lstrip()))
                b = st + len(txt.rstrip())
                ex = src[a:b]
                nullable = re.search(r'(?:^|[?:(,])\s*null\b|\?\.', ex) is not None and '??' not in ex
                fn = {'fg': '_lzFg', 'bg': '_lzBg', 'line': '_lzLine'}[role] + ('N' if nullable else '')
                wraps.append((a, b, fn, list(stack)))

    k, n = 0, len(toks)
    gradient_occ = []
    while k < n:
        kind, t, s0, e0 = toks[k]
        top = stack[-1]
        if kind == 'p' and t in '([{':
            callee, first = ('', k)
            if t == '(':
                callee, first = callee_before(toks, k)
            elif t == '[':
                j = k - 1
                if j >= 0 and toks[j][1] == '>':
                    depth = 0
                    while j >= 0:
                        if toks[j][1] == '>':
                            depth += 1
                        elif toks[j][1] == '<':
                            depth -= 1
                            if depth == 0:
                                break
                        j -= 1
                    first = j
            cspan = None
            if first - 1 >= 0 and toks[first - 1][1] == 'const':
                cspan = (toks[first - 1][2], toks[first - 1][3])
            fr = Frame(t, callee, cspan, s0)
            fr.arg_start = True
            stack.append(fr)
            k += 1
            continue
        if kind == 'p' and t in ')]}':
            if len(stack) > 1:
                fr = stack[-1]
                end_arg(fr, s0)
                stack.pop()
                parent = stack[-1]
                base = fr.callee.split('.')[-1]
                if fr.kind == '(' and (base in FILL_PROPAGATE or base == 'styleFrom'):
                    fill = fr.args.get('color') or fr.args.get('backgroundColor') or fr.args.get('gradient')
                    if fill and parent.fill is None:
                        parent.fill = fill
            k += 1
            continue
        if kind == 'p' and t == ',':
            end_arg(top, s0)
            top.arg = None
            top.arg_start = True
            k += 1
            continue
        if kind == 'id' and top.kind == '(' and top.arg_start and k + 1 < n and toks[k + 1][1] == ':':
            top.arg = t
            top.args['__s'] = toks[k + 2][2] if k + 2 < n else e0
            top.arg_start = False
            k += 2
            continue
        if top.kind == '(':
            top.arg_start = False
        # gradient stops: colors: [ ... ] inside a *Gradient
        if top.kind == '[' and len(stack) >= 2 and stack[-2].arg == 'colors' and stack[-2].callee.split('.')[-1] in GRADIENTS:
            prev = toks[k - 1][1] if k else ''
            o = None
            if kind == 'id' and t in PALETTE and prev != '.':
                o = (s0, e0, PALETTE[t])
            elif kind == 'id' and t == 'Color' and k + 3 < n and toks[k + 1][1] == '(' and toks[k + 3][1] == ')' and toks[k + 2][1].lower().startswith('0x'):
                st = toks[k - 1][2] if prev == 'const' else s0
                o = (st, toks[k + 3][3], int(toks[k + 2][1], 16))
                k += 3
            elif kind == 'id' and t == 'Colors' and k + 2 < n and toks[k + 2][1] in COLORS:
                o = (s0, toks[k + 2][3], COLORS[toks[k + 2][1]])
                k += 2
            if o and flips_bg(o[2]):
                wraps.append((o[0], o[1], '_lzBg', list(stack)))
        k += 1

    # functions that draw on their own fixed surface (the sky, a gold disc) keep their colours
    spans = exempt_spans(src)
    wraps = [w for w in wraps if not any(a <= w[0] < b for a, b in spans)]
    # drop wraps nested in another wrap
    wraps.sort(key=lambda w: (w[0], -w[1]))
    kept, last_end = [], -1
    for w in wraps:
        if w[0] < last_end:
            continue
        kept.append(w)
        last_end = w[1]
    counts, drop_const = {}, set()
    edits = []
    for a, b, fn, frames in kept:
        counts[fn] = counts.get(fn, 0) + 1
        edits.append((a, b, fn + '(' + src[a:b] + ')'))
        for f in frames:
            if f.const_span:
                drop_const.add(f.const_span)
    # a const that sits inside a wrapped span is fine; one before it is not
    for cs in drop_const:
        edits.append((cs[0], cs[1], ''))
    edits.sort(key=lambda e: e[0], reverse=True)
    out = src
    for st, en, rep in edits:
        out = out[:st] + rep + out[en:]
    return out, counts, len(drop_const), report


HELPERS = r'''
// ---------------------------------------------------------------- JC-LAZO-THEME-1009-001
// LIGHT AND DARK. Every colour that sits on a surface goes through one of three calls:
// _lzFg (text and icons), _lzBg (cards, sheets, fields, the canvas), _lzLine (borders and the
// gold hairline). In light mode they return the colour untouched - the dashboard you know.
// In dark mode (mission control) surfaces become plum-black glass, dark text becomes ivory,
// and gold, plum buttons and accents stay. The mode is 'system' | 'light' | 'dark' in
// SharedPreferences lazo_theme, shared by the couple and vendor dashboards.
bool _lzDark = false;
String _lzThemePref = 'system';
const Color _lzSurface = Color(0xFF1E1023); // dark card glass
const Color _lzCanvas = Color(0xFF140A17); // dark canvas
const Color _lzText = Color(0xFFF3ECE5);
const Color _lzMuted = Color(0xFFB7AABF);

Color _lzFg(Color c) {
  if (!_lzDark) return c;
  final int v = c.value & 0x00FFFFFF;
  if (v == 0x241E2B || v == 0x000000 || v == 0x141414) return _lzText.withOpacity(c.opacity);
  if (v == 0x6B5F72 || v == 0x8A7D90 || v == 0x8A7F90 || v == 0x5C5262) return _lzMuted.withOpacity(c.opacity);
  if (v == 0x52284F || v == 0x3D1C3B || v == 0x4A2147 || v == 0x6A3A66) return const Color(0xFFE2C6DE).withOpacity(c.opacity);
  final HSLColor h = HSLColor.fromColor(c);
  if (h.lightness >= 0.5) return c;
  return h.withLightness(0.74).withSaturation(h.saturation.clamp(0.0, 0.55)).toColor();
}

Color _lzBg(Color c) {
  if (!_lzDark) return c;
  final int v = c.value & 0x00FFFFFF;
  final double a = c.opacity;
  if (v == 0xFAF6F0) return (a > .97 ? _lzCanvas : _lzSurface).withOpacity(a);
  if (v == 0xFFFDF9 || v == 0xFFFFFF || v == 0xFFFDF8) return _lzSurface.withOpacity(a);
  final HSLColor h = HSLColor.fromColor(c);
  if (h.lightness <= 0.75) return c;
  // a tinted light surface (pale gold, pale red, pale green ...) keeps a whisper of its hue
  return Color.lerp(_lzSurface, h.withLightness(0.5).toColor(), 0.12)!.withOpacity(a);
}

Color _lzLine(Color c) {
  if (!_lzDark) return c;
  final HSLColor h = HSLColor.fromColor(c);
  if (h.lightness <= 0.75) return c;
  if ((c.value & 0x00FFFFFF) == 0xFFFFFF) return Colors.white.withOpacity(c.opacity * .14);
  return const Color(0xFFD9B77C).withOpacity(.26 * c.opacity);
}

Color? _lzFgN(Color? c) => c == null ? null : _lzFg(c);
Color? _lzBgN(Color? c) => c == null ? null : _lzBg(c);
Color? _lzLineN(Color? c) => c == null ? null : _lzLine(c);

bool _lzResolveDark(BuildContext context) {
  if (_lzThemePref == 'dark') return true;
  if (_lzThemePref == 'light') return false;
  return MediaQuery.platformBrightnessOf(context) == Brightness.dark;
}
// ---------------------------------------------------------------- end JC-LAZO-THEME-1009-001
'''


def insert_helpers(out):
    # after the last top-level import
    last = 0
    for m in re.finditer(r'^import [^\n]*\n', out, re.M):
        last = m.end()
    return out[:last] + HELPERS + out[last:]


if __name__ == '__main__':
    src = Path(sys.argv[1]).read_text(encoding='utf-8-sig')
    out, counts, nconst, report = run(src)
    out = insert_helpers(out)
    Path(sys.argv[2]).write_text(out, encoding='utf-8')
    print('wraps', counts, 'consts dropped', nconst, 'unclassified', len(report))
    if len(sys.argv) > 3:
        Path(sys.argv[3]).write_text('\n'.join(report), encoding='utf-8')
