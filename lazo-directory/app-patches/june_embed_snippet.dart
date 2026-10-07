// JC-LAZO-JUNE-EMBED-1008-001: June inside the dashboard.
// On the web app the June hub (june.meetlazo.com) is a real <iframe> laid over
// the Flutter canvas exactly where this widget sits (position re-synced every
// frame tick, hidden whenever a sheet or dialog is on top), signed in through
// the juneToken hand-off, with the mic and autoplay allowed. On the phone apps
// the same URL opens in the in-app browser from a card. Nothing in Firestore
// changes; the hub is one codebase for couples and vendors.
class _JuneEmbed extends StatefulWidget {
  const _JuneEmbed({
    super.key,
    required this.urlFuture,
    this.height,
    required this.openExternal,
    this.blurb = '',
  });
  final Future<String> urlFuture; // the signed-in hub URL (with ?embed=1)
  final double? height; // null = fill the parent
  final Future<void> Function() openExternal; // phone: open in the in-app browser
  final String blurb;
  @override
  State<_JuneEmbed> createState() => _JuneEmbedState();
}

class _JuneEmbedState extends State<_JuneEmbed> {
  static const Color _plum = Color(0xFF52284F);
  static const Color _plumDeep = Color(0xFF3D1C3B);
  static const Color _gold = Color(0xFFD9B77C);
  static const Color _ivory = Color(0xFFFAF6F0);
  final GlobalKey _anchor = GlobalKey();
  html.IFrameElement? _frame;
  Timer? _sync;
  String _url = '';
  bool _failed = false;

  @override
  void initState() {
    super.initState();
    widget.urlFuture.then((String u) {
      if (!mounted) return;
      setState(() => _url = u);
      if (kIsWeb) _mount();
    }).catchError((Object e) {
      if (mounted) setState(() => _failed = true);
    });
  }

  void _mount() {
    try {
      final html.IFrameElement f = html.IFrameElement();
      f.src = _url;
      f.setAttribute('allow', 'microphone; autoplay; clipboard-write');
      f.setAttribute('allowtransparency', 'true');
      f.style
        ..position = 'fixed'
        ..border = '0'
        ..zIndex = '30'
        ..display = 'none'
        ..borderRadius = '22px'
        ..background = '#24101F'
        ..boxShadow = '0 24px 60px -24px rgba(0,0,0,.6)';
      html.document.body?.append(f);
      _frame = f;
      _sync = Timer.periodic(const Duration(milliseconds: 60), (_) => _place());
    } catch (e) {
      debugPrint('LAZO june embed: ' + e.toString());
      if (mounted) setState(() => _failed = true);
    }
  }

  void _place() {
    final html.IFrameElement? f = _frame;
    if (f == null) return;
    final BuildContext? c = _anchor.currentContext;
    final RenderObject? ro = c?.findRenderObject();
    final bool onTop = c != null && (ModalRoute.of(c)?.isCurrent ?? true);
    if (ro is! RenderBox || !ro.attached || !ro.hasSize || !onTop) {
      if (f.style.display != 'none') f.style.display = 'none';
      return;
    }
    final Offset o = ro.localToGlobal(Offset.zero);
    final Size s = ro.size;
    if (s.width < 40 || s.height < 40) {
      if (f.style.display != 'none') f.style.display = 'none';
      return;
    }
    f.style
      ..left = '${o.dx.round()}px'
      ..top = '${o.dy.round()}px'
      ..width = '${s.width.round()}px'
      ..height = '${s.height.round()}px';
    if (f.style.display != 'block') f.style.display = 'block';
  }

  @override
  void dispose() {
    _sync?.cancel();
    _frame?.remove();
    _frame = null;
    super.dispose();
  }

  Widget _mark(double size) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[_plumDeep, Color(0xFF6A3A66)]),
          borderRadius: BorderRadius.circular(size * .34),
          border: Border.all(color: _gold.withOpacity(.85), width: 1.4),
          boxShadow: <BoxShadow>[
            BoxShadow(color: _gold.withOpacity(.3), blurRadius: 40, spreadRadius: 2)
          ],
        ),
        child: Icon(Icons.graphic_eq_rounded,
            color: const Color(0xFFE8CFA0), size: size * .46),
      );

  Widget _card({required Widget child}) => Container(
        width: double.infinity,
        padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[Color(0xFF241022), Color(0xFF3D1C3B)]),
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: _gold.withOpacity(.55)),
        ),
        child: child,
      );

  @override
  Widget build(BuildContext context) {
    Widget body;
    if (!kIsWeb) {
      // phones: the hub opens in the in-app browser (voice, brief, radio all work there)
      body = _card(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(children: <Widget>[
              _mark(54),
              const SizedBox(width: 14),
              const Expanded(
                child: Text('June',
                    style: TextStyle(
                        color: _ivory, fontSize: 22, fontWeight: FontWeight.w800)),
              ),
            ]),
            const SizedBox(height: 12),
            Text(
                widget.blurb.isEmpty
                    ? 'Talk to her out loud, hear your brief, and let her act for you. One tap, already signed in.'
                    : widget.blurb,
                style: TextStyle(color: _ivory.withOpacity(.82), fontSize: 13.5, height: 1.4)),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: () => widget.openExternal(),
              icon: const Icon(Icons.graphic_eq_rounded, size: 18),
              label: const Text('Open June',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
              style: FilledButton.styleFrom(
                  backgroundColor: _gold,
                  foregroundColor: _plumDeep,
                  padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999))),
            ),
          ],
        ),
      );
    } else if (_failed) {
      body = _card(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          const Text('June couldn’t load here.',
              style: TextStyle(color: _ivory, fontSize: 16, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          TextButton(
            onPressed: () => widget.openExternal(),
            style: TextButton.styleFrom(foregroundColor: _gold),
            child: const Text('Open June in a new tab'),
          ),
        ]),
      );
    } else {
      // the iframe is laid over this box; the box itself just reserves the space (and shows a soft loading frame)
      body = Container(
        key: _anchor,
        width: double.infinity,
        height: widget.height,
        decoration: BoxDecoration(
          color: const Color(0xFF24101F),
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: _gold.withOpacity(.35)),
        ),
        child: _url.isEmpty
            ? const Center(
                child: SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2, color: _gold)))
            : const SizedBox.expand(),
      );
      if (widget.height == null) return body;
    }
    return SizedBox(height: widget.height, child: body);
  }
}
