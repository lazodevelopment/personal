"""patch_theme.py - JC-LAZO-THEME-1009-001
Light and dark mode for both dashboards: Couple_master_v148 -> v149, Vendor_master_v184 -> v185.
  python app-patches\\patch_theme.py
Runs theme_rewrite.py (every colour placed by role: text, surface, line) and theme_wire.py (the
mode, the Appearance control, the status bar), then stamps the build notes.
Light is the dashboards exactly as they were. Dark is mission control: plum-black canvas and glass
cards, ivory text, gold hairlines; gold buttons, plum fills, accents and the weather sky keep their
colours. Account > Appearance: Light / Dark / Auto (follows the device; the default). Remembered per
device in SharedPreferences lazo_theme, shared by both dashboards. JuneNative is unchanged (always dark).
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable


def run(*a):
    subprocess.run([PY, *a], check=True, cwd=HERE)


def rep(s, old, new, label):
    if s.count(old) != 1:
        raise SystemExit(f"{label}: anchor found {s.count(old)}x")
    return s.replace(old, new)


NOTE = ("THEME - LIGHT AND DARK: Account > Appearance (Light / Dark / Auto, default Auto = the device); dark is mission "
        "control - plum-black canvas and glass cards, ivory text, gold hairlines, with gold, plum fills, accents and the "
        "weather sky unchanged; light is the dashboard as before. Every colour goes through _lzFg / _lzBg / _lzLine "
        "(placed by app-patches/theme_rewrite.py); lazo_theme in SharedPreferences. JC-LAZO-THEME-1009-001")

for kind, src, dst in (('couple', 'Couple_master_v148.txt', 'Couple_master_v149.txt'),
                       ('vendor', 'Vendor_master_v184.txt', 'Vendor_master_v185.txt')):
    tmp = HERE / ('_theme_' + kind + '.tmp')
    run('theme_rewrite.py', src, str(tmp))
    run('theme_wire.py', kind, str(tmp), str(tmp))
    s = tmp.read_text(encoding='utf-8')
    tmp.unlink()
    if kind == 'couple':
        s = rep(s, "// (v148: JUNE, NATIVE", "// (v149: " + NOTE + "; base v148)\n// (v148: JUNE, NATIVE", 'couple note')
        s = rep(s, "// END OF FILE - JC-LAZO-COUPLE-1008-V148", "// END OF FILE - JC-LAZO-COUPLE-1009-V149", 'couple end')
    else:
        s = rep(s, "// Build ID: JC-LAZO-VDASH-1008-184 (v184:",
                "// Build ID: JC-LAZO-VDASH-1009-185 (v185: " + NOTE + "; base v184) (v184:", 'vendor note')
        s = rep(s, "// END OF FILE - JC-LAZO-VDASH-1008-184", "// END OF FILE - JC-LAZO-VDASH-1009-185", 'vendor end')
    (HERE / dst).write_text(s, encoding='utf-8')
    print('wrote', dst, len(s))
