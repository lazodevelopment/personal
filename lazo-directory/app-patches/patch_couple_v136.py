"""patch_couple_v136.py - JC-LAZO-COUPLE-0929-V136
Two moves on the couple dashboard's website editor:
  1. PHOTOS, PLACED. The header and the story slot each take a photo the
     couple positions - drag it into place, zoom around that point, check it
     in a desktop and a phone frame - and every gallery tile gets the same
     sheet. Saved as weddingSites.heroPhoto / storyPhoto {url, x, y, zoom}
     and siteGalleryFocus [{x, y, zoom}]; the site applies exactly these
     numbers (object-position + transform-origin), so the sheet is honest.
     The header falls back to the home photo (coverUrl + a new coverFocus).
  2. GUEST PHOTOS. A switch and a line for guests (weddingSites.guestPhotosOn
     / guestPhotosNote); on the Website screen a card with the count, "See
     the wall" and Manage - a sheet that lists what guests shared, removes a
     photo (weddingSites.guestPhotosRemoved; the worker deletes the file on
     its next listing) and copies every link.
Pairs with worker JC-LAZO-WORKER-0929-GUESTPHOTOS-001 and the template patch
JC-LAZO-WWS-0929-PHOTOS. Applies on top of Couple_master_v135.txt (the
dart-formatted export) -> Couple_master_v136.txt. Anchor-and-assert.
  python app-patches\\patch_couple_v136.py [src] [out]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v135.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "Couple_master_v136.txt"
s = SRC.read_text(encoding="utf-8")
if "JC-LAZO-COUPLE-0929-V136" in s:
    raise SystemExit("already applied")


def swap(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"ABORT [{label}]: anchor matched {n} times, expected {count}")
    s = s.replace(old, new)
    print(f"  ok  {label}")


# ---------------------------------------------------------------- 0. header
swap("// (v135: COMMENTS + ALLOCATION",
     "// (v136: PHOTOS, PLACED + GUEST PHOTOS - the website editor's header and story slots take a photo the couple drags into place and zooms (desktop and phone frames), and every gallery tile opens the same sheet; saved as weddingSites.heroPhoto / storyPhoto {url, x, y, zoom} and siteGalleryFocus, applied 1:1 by the site (the header falls back to the home photo + coverFocus). A switch and a line let guests add photos from their phones from the wedding day on (guestPhotosOn / guestPhotosNote); the Website screen shows the count with See the wall and Manage - remove a photo (guestPhotosRemoved) or copy every link. JC-LAZO-COUPLE-0929-V136; base v135)\n// (v135: COMMENTS + ALLOCATION",
     "header")

# ---------------------------------------------------------------- 1. state + helpers
swap("""  List<String> _siteGal = <String>[];
  bool _siteGalBusy = false;
""", r'''  List<String> _siteGal = <String>[];
  bool _siteGalBusy = false;

  // v136: PHOTOS, PLACED. A slot is {url, x, y, zoom}: x/y (0..1) is the
  // point of the picture that stays in view, zoom (1..3) scales around it.
  // The site applies exactly this (object-position + transform-origin), so
  // the sheet below shows what guests will see.
  Map<String, dynamic>? _siteHero;
  Map<String, dynamic>? _siteStory;
  List<Map<String, dynamic>> _siteGalFocus = <Map<String, dynamic>>[];

  Map<String, dynamic>? _slotFrom(dynamic v) {
    if (v is! Map) {
      return null;
    }
    final String url = (v['url'] ?? '').toString();
    double d(dynamic x, double def, double lo, double hi) =>
        x is num ? x.toDouble().clamp(lo, hi).toDouble() : def;
    return <String, dynamic>{
      if (url.isNotEmpty) 'url': url,
      'x': d(v['x'], .5, 0, 1),
      'y': d(v['y'], .5, 0, 1),
      'zoom': d(v['zoom'], 1, 1, 3),
    };
  }

  // the picture's real size, so a drag moves the focus point by exactly the
  // distance the finger travelled
  Future<Size?> _imgSize(String url) {
    final Completer<Size?> c = Completer<Size?>();
    final ImageStream st =
        NetworkImage(url).resolve(const ImageConfiguration());
    late ImageStreamListener l;
    l = ImageStreamListener((ImageInfo i, bool sync) {
      if (!c.isCompleted) {
        c.complete(Size(i.image.width.toDouble(), i.image.height.toDouble()));
      }
      st.removeListener(l);
    }, onError: (Object e, StackTrace? st2) {
      if (!c.isCompleted) {
        c.complete(null);
      }
      st.removeListener(l);
    });
    st.addListener(l);
    return c.future
        .timeout(const Duration(seconds: 8), onTimeout: () => null);
  }

  // the picture as the site shows it: cover-fit, the focus point aligned,
  // scaled around that same point
  Widget _placed(Map<String, dynamic> p, {int resize = 1400}) {
    final double x = ((p['x'] as num?) ?? .5).toDouble();
    final double y = ((p['y'] as num?) ?? .5).toDouble();
    final double z = ((p['zoom'] as num?) ?? 1).toDouble();
    final Alignment a = Alignment(x * 2 - 1, y * 2 - 1);
    return ClipRect(
      child: Transform.scale(
        scale: z,
        alignment: a,
        child: Image(
          image: ResizeImage(NetworkImage((p['url'] ?? '').toString()),
              width: resize),
          fit: BoxFit.cover,
          alignment: a,
          width: double.infinity,
          height: double.infinity,
          errorBuilder: (BuildContext c, Object e, StackTrace? st) =>
              const ColoredBox(
                  color: plumDeep,
                  child: Icon(Icons.broken_image_outlined, color: ivory)),
        ),
      ),
    );
  }

  Future<String?> _uploadSlotPhoto(String slot) async {
    try {
      final FilePickerResult? res = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: <String>['jpg', 'jpeg', 'png', 'webp'],
        withData: true,
      );
      if (res == null || res.files.isEmpty) {
        return null;
      }
      final PlatformFile f = res.files.first;
      final Uint8List? bytes = f.bytes;
      if (bytes == null) {
        return null;
      }
      if (bytes.length > 12 * 1024 * 1024) {
        _toastC('That photo is over 12 MB — pick a smaller one.');
        return null;
      }
      final String ext = f.name.contains('.')
          ? f.name.substring(f.name.lastIndexOf('.')).toLowerCase()
          : '.jpg';
      final String ctype = ext == '.png'
          ? 'image/png'
          : ext == '.webp'
              ? 'image/webp'
              : 'image/jpeg';
      _toastC('Uploading photo…');
      final Reference ref = FirebaseStorage.instance.ref(
          'couples/$_uid/site/$slot-${DateTime.now().millisecondsSinceEpoch}$ext');
      await ref.putData(bytes, SettableMetadata(contentType: ctype));
      return await ref.getDownloadURL();
    } catch (e) {
      _toastC(e.toString().contains('unauthorized') ||
              e.toString().contains('permission')
          ? 'Photo upload isn’t permitted yet — storage rules need the couples/site path.'
          : 'Could not upload photo — try again.');
      return null;
    }
  }

  // The sheet: drag the picture until what matters is in view, zoom around
  // that point, check it in each frame the site will show. Returns the new
  // {url, x, y, zoom}; {'choose': true} to pick a different photo;
  // {'remove': true} to take it off; null when cancelled.
  Future<Map<String, dynamic>?> _positionSheet({
    required Map<String, dynamic> photo,
    required String title,
    required String hint,
    required List<List<dynamic>> frames, // [label, width/height]
    bool canChoose = true,
    bool canRemove = true,
  }) async {
    final String url = (photo['url'] ?? '').toString();
    double fx = ((photo['x'] as num?) ?? .5).toDouble();
    double fy = ((photo['y'] as num?) ?? .5).toDouble();
    double fz =
        ((photo['zoom'] as num?) ?? 1).toDouble().clamp(1.0, 3.0).toDouble();
    int frame = 0;
    Size? nat;
    _imgSize(url).then((Size? v) => nat = v);
    if (!mounted) {
      return null;
    }
    return showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      backgroundColor: ivory,
      constraints: const BoxConstraints(maxWidth: 620),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          final double aspect = (frames[frame][1] as num).toDouble();
          return Padding(
            padding: EdgeInsets.fromLTRB(
                20, 14, 20, 20 + MediaQuery.of(ctx2).viewInsets.bottom),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Center(
                  child: Container(
                      width: 40,
                      height: 4,
                      decoration: BoxDecoration(
                          color: plum.withOpacity(.25),
                          borderRadius: BorderRadius.circular(4))),
                ),
                const SizedBox(height: 14),
                Text(title,
                    style:
                        _serif(size: 24, weight: FontWeight.w600, color: plum)),
                const SizedBox(height: 4),
                Text(hint,
                    style: const TextStyle(
                        color: muted, fontSize: 13.5, height: 1.4)),
                if (frames.length > 1) ...<Widget>[
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    children: frames.asMap().entries.map(
                        (MapEntry<int, List<dynamic>> e) {
                      final bool sel = e.key == frame;
                      return ChoiceChip(
                        label: Text(e.value[0] as String,
                            style: TextStyle(
                                color: sel ? plum : ivory,
                                fontSize: 12,
                                fontWeight: FontWeight.w700)),
                        selected: sel,
                        selectedColor: gold,
                        backgroundColor: plum,
                        showCheckmark: false,
                        onSelected: (bool v) {
                          HapticFeedback.selectionClick();
                          setD(() => frame = e.key);
                        },
                      );
                    }).toList(),
                  ),
                ],
                const SizedBox(height: 14),
                LayoutBuilder(builder: (BuildContext lc, BoxConstraints cons) {
                  double w = cons.maxWidth;
                  double h = w / aspect;
                  final double maxH =
                      MediaQuery.of(ctx2).size.height * .42;
                  if (h > maxH) {
                    h = maxH;
                    w = h * aspect;
                  }
                  return Center(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(18),
                      child: GestureDetector(
                        behavior: HitTestBehavior.opaque,
                        onPanUpdate: (DragUpdateDetails d) {
                          // how far the picture can slide inside the frame at
                          // this zoom; the finger moves it that far, so the
                          // focus point moves the opposite way in proportion
                          double px, py;
                          final Size? n = nat;
                          if (n != null && n.width > 0 && n.height > 0) {
                            final double sc =
                                math.max(w / n.width, h / n.height);
                            px = n.width * sc * fz - w;
                            py = n.height * sc * fz - h;
                          } else {
                            px = w * fz * .6;
                            py = h * fz * .6;
                          }
                          setD(() {
                            if (px > 2) {
                              fx = (fx - d.delta.dx / px).clamp(0.0, 1.0).toDouble();
                            }
                            if (py > 2) {
                              fy = (fy - d.delta.dy / py).clamp(0.0, 1.0).toDouble();
                            }
                          });
                        },
                        child: SizedBox(
                          width: w,
                          height: h,
                          child: Stack(fit: StackFit.expand, children: <Widget>[
                            const ColoredBox(color: plumDeep),
                            _placed(<String, dynamic>{
                              'url': url,
                              'x': fx,
                              'y': fy,
                              'zoom': fz
                            }),
                            Positioned(
                              left: 14,
                              bottom: 12,
                              child: Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 9, vertical: 5),
                                decoration: BoxDecoration(
                                    color: plumDeep.withOpacity(.55),
                                    borderRadius: BorderRadius.circular(999)),
                                child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: <Widget>[
                                      const Icon(Icons.open_with_rounded,
                                          color: ivory, size: 14),
                                      const SizedBox(width: 6),
                                      Text('Drag to move',
                                          style: TextStyle(
                                              color: ivory.withOpacity(.9),
                                              fontSize: 12,
                                              fontWeight: FontWeight.w600)),
                                    ]),
                              ),
                            ),
                          ]),
                        ),
                      ),
                    ),
                  );
                }),
                const SizedBox(height: 8),
                Row(children: <Widget>[
                  const Icon(Icons.zoom_out_rounded, color: muted, size: 18),
                  Expanded(
                    child: SliderTheme(
                      data: SliderTheme.of(ctx2).copyWith(
                          activeTrackColor: gold,
                          inactiveTrackColor: gold.withOpacity(.25),
                          thumbColor: plum,
                          overlayColor: gold.withOpacity(.2),
                          trackHeight: 3),
                      child: Slider(
                        value: fz,
                        min: 1,
                        max: 3,
                        onChanged: (double v) => setD(() => fz = v),
                        onChangeEnd: (double v) =>
                            HapticFeedback.selectionClick(),
                      ),
                    ),
                  ),
                  const Icon(Icons.zoom_in_rounded, color: muted, size: 18),
                ]),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 2,
                  runSpacing: 2,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: <Widget>[
                    TextButton.icon(
                      onPressed: _h(() => setD(() {
                            fx = .5;
                            fy = .5;
                            fz = 1;
                          })),
                      icon: const Icon(Icons.center_focus_strong_rounded,
                          color: plum, size: 18),
                      label:
                          const Text('Center', style: TextStyle(color: plum)),
                    ),
                    if (canChoose)
                      TextButton.icon(
                        onPressed: _h(() => Navigator.pop(
                            ctx2, <String, dynamic>{'choose': true})),
                        icon: const Icon(Icons.photo_camera_rounded,
                            color: plum, size: 18),
                        label: const Text('Different photo',
                            style: TextStyle(color: plum)),
                      ),
                    if (canRemove)
                      TextButton.icon(
                        onPressed: _h(() => Navigator.pop(
                            ctx2, <String, dynamic>{'remove': true})),
                        icon: const Icon(Icons.delete_outline_rounded,
                            color: rose, size: 18),
                        label: const Text('Remove',
                            style: TextStyle(color: rose)),
                      ),
                  ],
                ),
                const SizedBox(height: 6),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: gold,
                        foregroundColor: plumDeep,
                        padding: const EdgeInsets.symmetric(vertical: 13),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12))),
                    onPressed: _h(
                        () => Navigator.pop(ctx2, <String, dynamic>{
                              'url': url,
                              'x': fx,
                              'y': fy,
                              'zoom': double.parse(fz.toStringAsFixed(2)),
                            }),
                        _Tick.medium),
                    child: const Text('Use this',
                        style: TextStyle(fontWeight: FontWeight.w700)),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  // pick (if there is nothing yet) then position; loops through "Different
  // photo" until the couple settles on one
  Future<void> _slotFlow({
    required StateSetter setD,
    required String slot,
    required Map<String, dynamic>? current,
    Map<String, dynamic>? fallback,
    required String title,
    required String hint,
    required List<List<dynamic>> frames,
    required void Function(Map<String, dynamic>?) apply,
  }) async {
    Map<String, dynamic>? p = current ?? fallback;
    if (p == null || (p['url'] ?? '').toString().isEmpty) {
      final String? u = await _uploadSlotPhoto(slot);
      if (u == null) {
        return;
      }
      p = <String, dynamic>{'url': u, 'x': .5, 'y': .5, 'zoom': 1.0};
    }
    while (true) {
      final Map<String, dynamic>? r = await _positionSheet(
          photo: p!,
          title: title,
          hint: hint,
          frames: frames,
          canRemove: current != null);
      if (r == null) {
        return;
      }
      if (r['choose'] == true) {
        final String? u = await _uploadSlotPhoto(slot);
        if (u != null) {
          p = <String, dynamic>{'url': u, 'x': .5, 'y': .5, 'zoom': 1.0};
        }
        continue;
      }
      if (r['remove'] == true) {
        setD(() => apply(null));
        _toastC('Photo removed — publish to update the site.');
        return;
      }
      setD(() => apply(r));
      return;
    }
  }

  static const List<List<dynamic>> _heroFrames = <List<dynamic>>[
    <dynamic>['Desktop', 1.7],
    <dynamic>['Phone', .58],
  ];

  Widget _slotTile({
    required String label,
    required Map<String, dynamic>? current,
    Map<String, dynamic>? fallback,
    required VoidCallback onTap,
  }) {
    final Map<String, dynamic>? shown = current ?? fallback;
    final bool has = shown != null && (shown['url'] ?? '').toString().isNotEmpty;
    return _Press(
      tick: _Tick.select,
      onTap: onTap,
      child: SizedBox(
        width: 150,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Container(
              height: 104,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                color: gold.withOpacity(.06),
                border: Border.all(
                    color: has ? gold : gold.withOpacity(.8),
                    width: has ? 1.2 : 1),
              ),
              clipBehavior: Clip.antiAlias,
              child: has
                  ? Stack(fit: StackFit.expand, children: <Widget>[
                      _placed(shown, resize: 600),
                      Positioned(
                        right: 6,
                        bottom: 6,
                        child: Container(
                          padding: const EdgeInsets.all(5),
                          decoration: const BoxDecoration(
                              color: plumDeep, shape: BoxShape.circle),
                          child: const Icon(Icons.crop_free_rounded,
                              color: ivory, size: 13),
                        ),
                      ),
                    ])
                  : const Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: <Widget>[
                        Icon(Icons.add_photo_alternate_outlined,
                            color: plum, size: 24),
                        SizedBox(height: 3),
                        Text('Add a photo',
                            style: TextStyle(
                                color: plum,
                                fontSize: 10.5,
                                fontWeight: FontWeight.w700)),
                      ]),
            ),
            const SizedBox(height: 6),
            Text(label,
                style: const TextStyle(
                    color: plum, fontSize: 12.5, fontWeight: FontWeight.w800)),
            Text(
                !has
                    ? 'Tap to add'
                    : current == null
                        ? 'Your home photo · tap to position'
                        : 'Tap to position',
                style: const TextStyle(fontSize: 10.5, color: muted)),
          ],
        ),
      ),
    );
  }

  Future<void> _galPosition(StateSetter setD, int i) async {
    if (i < 0 || i >= _siteGal.length) {
      return;
    }
    while (_siteGalFocus.length < _siteGal.length) {
      _siteGalFocus.add(<String, dynamic>{'x': .5, 'y': .5, 'zoom': 1.0});
    }
    final Map<String, dynamic> cur = <String, dynamic>{
      'url': _siteGal[i],
      ..._siteGalFocus[i]
    };
    final Map<String, dynamic>? r = await _positionSheet(
        photo: cur,
        title: 'Position this photo',
        hint: i == 0
            ? 'The first photo leads the gallery as a tall tile on desktop.'
            : 'Gallery tiles are landscape on desktop and full-width on phones.',
        frames: i == 0
            ? const <List<dynamic>>[
                <dynamic>['Desktop', .75],
                <dynamic>['Phone', 1.33]
              ]
            : const <List<dynamic>>[
                <dynamic>['Tile', 1.33]
              ],
        canChoose: false,
        canRemove: false);
    if (r == null || r['url'] == null) {
      return;
    }
    setD(() => _siteGalFocus[i] = <String, dynamic>{
          'x': r['x'],
          'y': r['y'],
          'zoom': r['zoom']
        });
  }

  // ---- v136: photos from the guests (read through the worker's API) ----
  Future<List<Map<String, dynamic>>>? _gpFuture;
  String _gpFutureSlug = '';

  Future<List<Map<String, dynamic>>> _guestPhotosFetch(String slug) async {
    try {
      final httpc.Response r = await httpc
          .get(Uri.parse(
              'https://meetlazo.com/api/w/$slug/photos?t=${DateTime.now().millisecondsSinceEpoch}'))
          .timeout(const Duration(seconds: 12));
      if (r.statusCode != 200) {
        return <Map<String, dynamic>>[];
      }
      final dynamic j = jsonDecode(r.body);
      final List<dynamic> ph =
          (j is Map ? j['photos'] as List? : null) ?? const <dynamic>[];
      return ph
          .whereType<Map>()
          .map((Map e) => Map<String, dynamic>.from(e))
          .toList();
    } catch (_) {
      return <Map<String, dynamic>>[];
    }
  }

  Future<List<Map<String, dynamic>>> _guestPhotos(String slug,
      {bool fresh = false}) {
    if (fresh || _gpFuture == null || _gpFutureSlug != slug) {
      _gpFutureSlug = slug;
      _gpFuture = _guestPhotosFetch(slug);
    }
    return _gpFuture!;
  }

  Widget _guestPhotosCard(String slug, Map<String, dynamic> w) {
    final bool on = w['guestPhotosOn'] != false;
    return _glass(
      padding: const EdgeInsets.all(16),
      radius: 20,
      tint: .6,
      borderColor: gold.withOpacity(.6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(children: <Widget>[
            const Icon(Icons.photo_library_outlined, color: plum, size: 20),
            const SizedBox(width: 8),
            const Expanded(
              child: Text('Photos from your guests',
                  style: TextStyle(
                      color: plum,
                      fontSize: 15.5,
                      fontWeight: FontWeight.w700)),
            ),
            if (!on)
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                    color: muted.withOpacity(.15),
                    borderRadius: BorderRadius.circular(999)),
                child: const Text('OFF',
                    style: TextStyle(
                        color: muted,
                        fontSize: 9.5,
                        letterSpacing: 1,
                        fontWeight: FontWeight.w800)),
              ),
          ]),
          const SizedBox(height: 6),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _guestPhotos(slug),
            builder: (BuildContext c,
                AsyncSnapshot<List<Map<String, dynamic>>> sn) {
              final int n = sn.data?.length ?? 0;
              final String line = !on
                  ? 'Guests can’t add photos right now — turn it on under Edit.'
                  : sn.connectionState != ConnectionState.done
                      ? 'Checking the wall…'
                      : n == 0
                          ? 'From the wedding day, guests tap “Add photos from your phone” on your site and they show up here.'
                          : '$n photo${n == 1 ? '' : 's'} shared so far.';
              return Text(line,
                  style: const TextStyle(fontSize: 12.5, color: muted));
            },
          ),
          const SizedBox(height: 10),
          Row(children: <Widget>[
            Expanded(
              child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                    foregroundColor: plum,
                    side: BorderSide(color: gold.withOpacity(.8))),
                onPressed: _h(() => _openLink(
                    'https://meetlazo.com/w/$slug/?photos=1#photos')),
                icon: const Icon(Icons.open_in_new_rounded, size: 15),
                label: const Text('See the wall'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: FilledButton.icon(
                style: FilledButton.styleFrom(
                    backgroundColor: plum, foregroundColor: ivory),
                onPressed: _h(() => _guestPhotosSheet(slug)),
                icon: const Icon(Icons.tune_rounded, size: 15),
                label: const Text('Manage'),
              ),
            ),
          ]),
        ],
      ),
    );
  }

  Future<void> _guestPhotosSheet(String slug) async {
    List<Map<String, dynamic>> list = await _guestPhotos(slug, fresh: true);
    if (!mounted) {
      return;
    }
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: ivory,
      constraints: const BoxConstraints(maxWidth: 720),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          Future<void> remove(Map<String, dynamic> p) async {
            final bool? sure = await showDialog<bool>(
              context: ctx2,
              builder: (BuildContext dc) => AlertDialog(
                backgroundColor: ivory,
                title: const Text('Remove this photo?',
                    style: TextStyle(color: plum)),
                content: const Text(
                    'It comes off the wall for everyone and the file is deleted. This can’t be undone.',
                    style: TextStyle(color: ink, fontSize: 14)),
                actions: <Widget>[
                  TextButton(
                      onPressed: () => Navigator.pop(dc, false),
                      child: const Text('Keep', style: TextStyle(color: ink))),
                  FilledButton(
                      style: FilledButton.styleFrom(
                          backgroundColor: rose, foregroundColor: ivory),
                      onPressed: () => Navigator.pop(dc, true),
                      child: const Text('Remove')),
                ],
              ),
            );
            if (sure != true) {
              return;
            }
            try {
              await FirebaseFirestore.instance
                  .collection('weddingSites')
                  .doc(slug)
                  .update(<String, dynamic>{
                'guestPhotosRemoved': FieldValue.arrayUnion(<dynamic>[p['id']]),
              });
              setD(() => list.removeWhere(
                  (Map<String, dynamic> x) => x['id'] == p['id']));
              _gpFuture = Future<List<Map<String, dynamic>>>.value(
                  List<Map<String, dynamic>>.from(list));
              // the worker deletes the file on its next listing
              Future<void>.delayed(const Duration(seconds: 2), () {
                _guestPhotosFetch(slug);
              });
              _toastC('Removed — it’s off the wall within a minute.');
            } catch (_) {
              _toastC('Could not remove — try again.');
            }
          }

          return Padding(
            padding: EdgeInsets.fromLTRB(
                20, 14, 20, 20 + MediaQuery.of(ctx2).viewInsets.bottom),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Center(
                  child: Container(
                      width: 40,
                      height: 4,
                      decoration: BoxDecoration(
                          color: plum.withOpacity(.25),
                          borderRadius: BorderRadius.circular(4))),
                ),
                const SizedBox(height: 14),
                Row(children: <Widget>[
                  Expanded(
                    child: Text('Photos from your guests',
                        style: _serif(
                            size: 24, weight: FontWeight.w600, color: plum)),
                  ),
                  IconButton(
                    tooltip: 'Refresh',
                    onPressed: _h(() async {
                      final List<Map<String, dynamic>> l =
                          await _guestPhotos(slug, fresh: true);
                      setD(() => list = l);
                    }),
                    icon: const Icon(Icons.refresh_rounded, color: plum),
                  ),
                ]),
                Text(
                    list.isEmpty
                        ? 'Nothing shared yet. From the wedding day, guests add photos from their phones on your site.'
                        : '${list.length} photo${list.length == 1 ? '' : 's'} · tap to open, hold to remove.',
                    style: const TextStyle(
                        color: muted, fontSize: 13.5, height: 1.4)),
                const SizedBox(height: 12),
                Flexible(
                  child: list.isEmpty
                      ? const SizedBox(height: 40)
                      : GridView.builder(
                          shrinkWrap: true,
                          gridDelegate:
                              const SliverGridDelegateWithMaxCrossAxisExtent(
                                  maxCrossAxisExtent: 120,
                                  mainAxisSpacing: 8,
                                  crossAxisSpacing: 8),
                          itemCount: list.length,
                          itemBuilder: (BuildContext gc, int i) {
                            final Map<String, dynamic> p = list[i];
                            final String u = (p['url'] ?? '').toString();
                            return GestureDetector(
                              onTap: () => _openLink(u),
                              onLongPress: () => remove(p),
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(12),
                                child: Stack(
                                    fit: StackFit.expand,
                                    children: <Widget>[
                                      Image.network(
                                        'https://wsrv.nl/?url=${Uri.encodeComponent(u)}&w=300&q=70',
                                        fit: BoxFit.cover,
                                        errorBuilder: (BuildContext c5,
                                                Object e, StackTrace? st) =>
                                            Container(
                                                color: gold.withOpacity(.08),
                                                child: const Icon(
                                                    Icons
                                                        .broken_image_outlined,
                                                    color: muted)),
                                      ),
                                      if ((p['name'] ?? '')
                                          .toString()
                                          .isNotEmpty)
                                        Positioned(
                                          left: 0,
                                          right: 0,
                                          bottom: 0,
                                          child: Container(
                                            padding:
                                                const EdgeInsets.symmetric(
                                                    horizontal: 6,
                                                    vertical: 3),
                                            color: plumDeep.withOpacity(.6),
                                            child: Text(
                                                (p['name'] ?? '').toString(),
                                                maxLines: 1,
                                                overflow:
                                                    TextOverflow.ellipsis,
                                                style: const TextStyle(
                                                    color: ivory,
                                                    fontSize: 10,
                                                    fontWeight:
                                                        FontWeight.w700)),
                                          ),
                                        ),
                                      Positioned(
                                        top: 4,
                                        right: 4,
                                        child: _Press(
                                          tick: _Tick.select,
                                          onTap: () => remove(p),
                                          child: Container(
                                            width: 22,
                                            height: 22,
                                            decoration: const BoxDecoration(
                                                color: plumDeep,
                                                shape: BoxShape.circle),
                                            child: const Icon(
                                                Icons.close_rounded,
                                                color: ivory,
                                                size: 14),
                                          ),
                                        ),
                                      ),
                                    ]),
                              ),
                            );
                          },
                        ),
                ),
                const SizedBox(height: 12),
                Row(children: <Widget>[
                  TextButton.icon(
                    onPressed: _h(list.isEmpty
                        ? null
                        : () async {
                            await Clipboard.setData(ClipboardData(
                                text: list
                                    .map((Map<String, dynamic> p) =>
                                        (p['url'] ?? '').toString())
                                    .join('\n')));
                            _toastC(
                                'All ${list.length} links copied — paste them anywhere ✓');
                          }),
                    icon: const Icon(Icons.link_rounded, color: plum, size: 18),
                    label: const Text('Copy all links',
                        style: TextStyle(color: plum)),
                  ),
                  const Spacer(),
                  FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: gold, foregroundColor: plumDeep),
                    onPressed: _h(() => _openLink(
                        'https://meetlazo.com/w/$slug/?photos=1#photos')),
                    child: const Text('See the wall',
                        style: TextStyle(fontWeight: FontWeight.w700)),
                  ),
                ]),
              ],
            ),
          );
        },
      ),
    );
  }
''', "state + helpers")

# ---------------------------------------------------------------- 2. editor: load the slots
swap("""    _siteGal = List<String>.from(
        (w['siteGallery'] as List?)?.map((dynamic e) => e.toString()) ??
            const <String>[]);
    // ---- SMART PREFILL: never ask what Lazo already knows ----
""", """    _siteGal = List<String>.from(
        (w['siteGallery'] as List?)?.map((dynamic e) => e.toString()) ??
            const <String>[]);
    // v136: where the couple put their photos, and the guests' wall
    _siteHero = _slotFrom(w['heroPhoto']);
    _siteStory = _slotFrom(w['storyPhoto']);
    _siteGalFocus = <Map<String, dynamic>>[
      for (final dynamic f in (w['siteGalleryFocus'] as List?) ?? const <dynamic>[])
        _slotFrom(f) ?? <String, dynamic>{'x': .5, 'y': .5, 'zoom': 1.0}
    ];
    bool guestOn = w['guestPhotosOn'] != false;
    final TextEditingController guestNoteC =
        TextEditingController(text: (w['guestPhotosNote'] ?? '').toString());
    // ---- SMART PREFILL: never ask what Lazo already knows ----
""", "editor: load slots")

# ---------------------------------------------------------------- 3. editor: the placed-photos section
swap("""                          _wbSection('PHOTOS \\u00b7 ${_siteGal.length} OF 6'),
                          const Padding(
                            padding: EdgeInsets.only(bottom: 10),
                            child: Text(
                                'These fill your website\\u2019s photo section \\u2014 the first one leads.',
                                style: TextStyle(fontSize: 11.5, color: muted)),
                          ),
""", """                          _wbSection('PHOTOS, PLACED'),
                          const Padding(
                            padding: EdgeInsets.only(bottom: 10),
                            child: Text(
                                'Tap a photo, drag it into place and zoom \\u2014 your site shows exactly this.',
                                style: TextStyle(fontSize: 11.5, color: muted)),
                          ),
                          Builder(builder: (BuildContext pc) {
                            final Map<String, dynamic>? homeFocus =
                                _slotFrom(couple['photoFocus']);
                            final String homeUrl =
                                (couple['photoUrl'] ?? '').toString();
                            final Map<String, dynamic>? heroFallback =
                                homeUrl.isEmpty
                                    ? null
                                    : <String, dynamic>{
                                        'url': homeUrl,
                                        'x': homeFocus?['x'] ?? .5,
                                        'y': homeFocus?['y'] ?? .5,
                                        'zoom': 1.0,
                                      };
                            return Wrap(
                              spacing: 12,
                              runSpacing: 12,
                              children: <Widget>[
                                _slotTile(
                                  label: 'Header',
                                  current: _siteHero,
                                  fallback: heroFallback,
                                  onTap: () => _slotFlow(
                                    setD: setD,
                                    slot: 'hero',
                                    current: _siteHero,
                                    fallback: heroFallback,
                                    title: 'Your header photo',
                                    hint:
                                        'The big picture at the top of your site. Drag until the two of you are where you want them; check the phone frame too \\u2014 most guests open it there.',
                                    frames: _heroFrames,
                                    apply: (Map<String, dynamic>? v) =>
                                        _siteHero = v,
                                  ),
                                ),
                                _slotTile(
                                  label: 'Our story',
                                  current: _siteStory,
                                  onTap: () => _slotFlow(
                                    setD: setD,
                                    slot: 'story',
                                    current: _siteStory,
                                    title: 'Your story photo',
                                    hint:
                                        'Sits beside your story as a portrait \\u2014 a favorite of the two of you.',
                                    frames: const <List<dynamic>>[
                                      <dynamic>['Portrait', .8]
                                    ],
                                    apply: (Map<String, dynamic>? v) =>
                                        _siteStory = v,
                                  ),
                                ),
                              ],
                            );
                          }),
                          _wbSection('GALLERY \\u00b7 ${_siteGal.length} OF 6'),
                          const Padding(
                            padding: EdgeInsets.only(bottom: 10),
                            child: Text(
                                'These fill your website\\u2019s photo section \\u2014 the first one leads. Tap one to position it.',
                                style: TextStyle(fontSize: 11.5, color: muted)),
                          ),
""", "editor: placed photos section")

# gallery tile: tap to position + focus kept in step on remove
swap("""                                        ClipRRect(
                                          borderRadius:
                                              BorderRadius.circular(14),
                                          child: Image.network(
                                            e.value,
                                            fit: BoxFit.cover,
""", """                                        _Press(
                                          tick: _Tick.select,
                                          onTap: () =>
                                              _galPosition(setD, e.key),
                                          child: ClipRRect(
                                          borderRadius:
                                              BorderRadius.circular(14),
                                          child: e.key < _siteGalFocus.length &&
                                                  ((_siteGalFocus[e.key]['zoom']
                                                                  as num?)
                                                              ?.toDouble() ??
                                                          1) >
                                                      1
                                              ? _placed(<String, dynamic>{
                                                  'url': e.value,
                                                  ..._siteGalFocus[e.key]
                                                }, resize: 400)
                                              : Image.network(
                                            e.value,
                                            fit: BoxFit.cover,
""", "gallery tile: open the sheet")
# close the extra _Press( ... child: ClipRRect( wrapper: the ClipRRect closes right before the COVER badge
swap("""                                          ),
                                        ),
                                        if (e.key == 0)
                                          Positioned(
                                            left: 5,
                                            bottom: 5,
""", """                                          ),
                                        ),
                                        ),
                                        if (e.key == 0)
                                          Positioned(
                                            left: 5,
                                            bottom: 5,
""", "gallery tile: close wrapper")
swap("""                                            onTap: () => setD(
                                                () => _siteGal.removeAt(e.key)),
""", """                                            onTap: () => setD(() {
                                              _siteGal.removeAt(e.key);
                                              if (e.key < _siteGalFocus.length) {
                                                _siteGalFocus.removeAt(e.key);
                                              }
                                            }),
""", "gallery tile: remove keeps focus in step")

# ---------------------------------------------------------------- 4. editor: guest photos controls
swap("""                            title: const Text('Accept RSVPs on the site',
                                style: TextStyle(fontSize: 13.5)),
                            value: rsvpOpen,
                            onChanged:
                                _hb((bool v) => setD(() => rsvpOpen = v)),
                          ),
                        ];
""", """                            title: const Text('Accept RSVPs on the site',
                                style: TextStyle(fontSize: 13.5)),
                            value: rsvpOpen,
                            onChanged:
                                _hb((bool v) => setD(() => rsvpOpen = v)),
                          ),
                          _wbSection('PHOTOS FROM YOUR GUESTS'),
                          const Padding(
                            padding: EdgeInsets.only(bottom: 4),
                            child: Text(
                                'From the wedding day on, your site gets a \\u201cShare the day as you saw it\\u201d section: guests add photos straight from their phones and everyone sees them. Preview it any time from the Website screen.',
                                style: TextStyle(fontSize: 11.5, color: muted)),
                          ),
                          SwitchListTile(
                            dense: true,
                            contentPadding: EdgeInsets.zero,
                            activeColor: Colors.white,
                            activeTrackColor: vGreen,
                            inactiveThumbColor: Colors.white,
                            inactiveTrackColor: muted.withOpacity(.4),
                            title: const Text('Let guests add photos',
                                style: TextStyle(fontSize: 13.5)),
                            value: guestOn,
                            onChanged:
                                _hb((bool v) => setD(() => guestOn = v)),
                          ),
                          if (guestOn)
                            TextField(
                                controller: guestNoteC,
                                maxLength: 140,
                                style:
                                    const TextStyle(color: ink, fontSize: 14),
                                decoration: _lightDeco(
                                    'A line for your guests (optional)',
                                    hint:
                                        'Took a photo we\\u2019d love to see? Add it here.')),
                        ];
""", "editor: guest photos controls")

# ---------------------------------------------------------------- 5. save
swap("""        'coverUrl': (couple['photoUrl'] ?? '') as String,
        'dateIso': wd == null
""", """        'coverUrl': (couple['photoUrl'] ?? '') as String,
        // v136: where the photos sit, and the guests' wall
        'coverFocus': _slotFrom(couple['photoFocus']) ?? FieldValue.delete(),
        'heroPhoto': _siteHero ?? FieldValue.delete(),
        'storyPhoto': _siteStory ?? FieldValue.delete(),
        'siteGalleryFocus': <Map<String, dynamic>>[
          for (int i = 0; i < _siteGal.length; i++)
            i < _siteGalFocus.length
                ? _siteGalFocus[i]
                : <String, dynamic>{'x': .5, 'y': .5, 'zoom': 1.0}
        ],
        'guestPhotosOn': guestOn,
        'guestPhotosNote': guestNoteC.text.trim(),
        'dateIso': wd == null
""", "save")

# ---------------------------------------------------------------- 6. website screen card
swap("""              const SizedBox(height: 14),
              const Padding(
                padding: EdgeInsets.only(left: 6, bottom: 8),
                child: Text('RSVPs waiting to import',
""", """              const SizedBox(height: 14),
              _guestPhotosCard(slug, w),
              const SizedBox(height: 14),
              const Padding(
                padding: EdgeInsets.only(left: 6, bottom: 8),
                child: Text('RSVPs waiting to import',
""", "website screen: guest photos card")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT.name} ({len(s):,} chars)")
