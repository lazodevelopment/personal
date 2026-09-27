"""Per-line paren/bracket balance for a JS file, ignoring string contents. Usage: python _src/parens.py file [from] [to]"""
import sys, re
path = sys.argv[1]; a = int(sys.argv[2]) if len(sys.argv) > 2 else 1; b = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
lines = open(path, encoding="utf-8").read().split("\n")
strip = re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`")
depth = 0
for i, line in enumerate(lines, 1):
    s = strip.sub("''", line)
    o, c = s.count("("), s.count(")")
    depth += o - c
    if a <= i <= b:
        print(f"{i}: ( {o}  ) {c}  cumulative {depth}")
print("final depth", depth)
