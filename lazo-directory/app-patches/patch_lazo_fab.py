"""patch_lazo_fab.py - JC-LAZO-FAB-1014-001: the desk button can be moved, and gets out of the way.
Applied by patch_june_hero_dashboards.py to Vendor_master_v189 / Couple_master_v153 (imported, not run alone).
  - drag it anywhere; on release it glides to the nearer side edge (never parked over the middle of the page)
    at the height it was dropped, and the spot is remembered per device (SharedPreferences)
  - like iPhone's AssistiveTouch: after a few seconds untouched it tucks partly behind the edge and dims, so
    it covers almost nothing; a touch or a drag wakes it; a plain tap still opens the desk
  - honours Reduce Motion (no glide, no tuck animation)
"""

FAB_CLASS = r"""
// JC-LAZO-FAB-1014-001: the desk button, movable. Drag it anywhere; it settles against the nearer side edge
// at the height it was dropped and remembers the spot on this device. Left alone for a few seconds it tucks
// partly behind the edge and dims (AssistiveTouch style), so it covers almost nothing until it is touched.
class _MovableFab extends StatefulWidget {
  const _MovableFab({required this.prefKey, required this.child, this.size = 56, this.defaultBottom = 18});
  final String prefKey;
  final Widget child;
  final double size;
  final double defaultBottom;
  @override
  State<_MovableFab> createState() => _MovableFabState();
}

class _MovableFabState extends State<_MovableFab> {
  bool _left = false;
  double? _yFrac;
  Offset? _drag;
  bool _awake = true;
  Timer? _sleep;
  Offset _grab = Offset.zero; // where on the disc the finger went down
  final GlobalKey _area = GlobalKey();

  // the finger's real position in the button's area, so a fast flick lands exactly where it is let go
  Offset _at(Offset global) {
    final RenderObject? ro = _area.currentContext?.findRenderObject();
    if (ro is! RenderBox) return global - _grab;
    return ro.globalToLocal(global) - _grab;
  }

  @override
  void initState() {
    super.initState();
    SharedPreferences.getInstance().then((SharedPreferences p) {
      final String? s = p.getString(widget.prefKey);
      if (s == null || !mounted) return;
      final List<String> parts = s.split('|');
      setState(() {
        _left = parts[0] == 'L';
        _yFrac = parts.length > 1 ? double.tryParse(parts[1]) : null;
      });
    }).catchError((Object _) {});
    _wake();
  }

  @override
  void dispose() {
    _sleep?.cancel();
    super.dispose();
  }

  void _wake() {
    _sleep?.cancel();
    if (!_awake && mounted) setState(() => _awake = true);
    _sleep = Timer(const Duration(seconds: 4), () {
      if (mounted && _drag == null) setState(() => _awake = false);
    });
  }

  void _save() {
    final String v = '${_left ? 'L' : 'R'}|${(_yFrac ?? -1).toStringAsFixed(4)}';
    SharedPreferences.getInstance().then((SharedPreferences p) => p.setString(widget.prefKey, v)).catchError((Object _) => false);
  }

  @override
  Widget build(BuildContext context) {
    final bool reduce = MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    return LayoutBuilder(builder: (BuildContext c, BoxConstraints box) {
      final double s = widget.size;
      const double edge = 14;
      const double minY = 12;
      final double maxY = math.max(minY, box.maxHeight - s - widget.defaultBottom);
      final double span = math.max(1, box.maxHeight - s);
      double y = (_yFrac == null || _yFrac! < 0) ? maxY : (_yFrac! * span).clamp(minY, maxY).toDouble();
      // tucked: 40% of the disc behind the edge
      final double tuck = _awake ? 0 : s * .4;
      double x = _left ? edge - tuck : box.maxWidth - s - edge + tuck;
      final Offset? d = _drag;
      if (d != null) {
        x = d.dx.clamp(0, math.max(0, box.maxWidth - s)).toDouble();
        y = d.dy.clamp(minY, maxY).toDouble();
      }
      return Stack(key: _area, children: <Widget>[
        AnimatedPositioned(
          duration: Duration(milliseconds: d != null || reduce ? 0 : 340),
          curve: Curves.easeOutCubic,
          left: x,
          top: y,
          child: Listener(
            onPointerDown: (PointerDownEvent e) {
              _grab = e.localPosition;
              _wake();
            },
            child: GestureDetector(
              onPanStart: (DragStartDetails st) {
                HapticFeedback.selectionClick();
                _sleep?.cancel();
                setState(() {
                  _awake = true;
                  _drag = _at(st.globalPosition);
                });
              },
              onPanUpdate: (DragUpdateDetails u) => setState(() => _drag = _at(u.globalPosition)),
              onPanEnd: (DragEndDetails _) {
                final Offset p = _drag ?? Offset(x, y);
                HapticFeedback.lightImpact();
                setState(() {
                  _left = p.dx + s / 2 < box.maxWidth / 2;
                  _yFrac = p.dy.clamp(minY, maxY).toDouble() / span;
                  _drag = null;
                });
                _save();
                _wake();
              },
              child: AnimatedOpacity(
                duration: Duration(milliseconds: reduce ? 0 : 260),
                opacity: _awake ? 1 : .55,
                child: AnimatedScale(
                  duration: const Duration(milliseconds: 150),
                  scale: d != null ? 1.08 : 1,
                  child: Semantics(
                    hint: 'Drag to move it',
                    child: widget.child,
                  ),
                ),
              ),
            ),
          ),
        ),
      ]);
    });
  }
}
"""


def apply_fab(s, fn_name, right, bottom, size, pref_key, rep):
    """Wrap the dashboard's Positioned desk button in _MovableFab and append the class."""
    start = s.index(f"  Widget {fn_name}() {{")
    end = s.index("\n  }\n", start) + len("\n  }\n")
    body = s[start:end]
    head_old = f"    return Positioned(\n      right: {right},\n      bottom: {bottom},"
    if body.count(head_old) != 1:
        raise SystemExit(f"{fn_name}: Positioned head not found")
    # keep any trailing comment on the bottom line (the couple's says why it sits above the Ask June bar)
    body = body.replace(head_old, f"    return Positioned.fill(\n      child: _MovableFab(\n      prefKey: '{pref_key}',\n      size: {size},\n      defaultBottom: {bottom},", 1)
    tail_old = "\n    );\n  }\n"
    if not body.endswith(tail_old):
        raise SystemExit(f"{fn_name}: unexpected tail")
    body = body[: -len(tail_old)] + "\n    ));\n  }\n"
    s = s[:start] + body + s[end:]
    if "class _MovableFab extends StatefulWidget" not in s:
        s = s.rstrip("\n") + "\n" + FAB_CLASS
    return s
