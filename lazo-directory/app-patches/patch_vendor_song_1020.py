r"""patch_vendor_song_1020.py - JC-LAZO-VSONG-1020-VENDOR: Vendor v223, the storefront song.

Builds Vendor_master_v223.txt from v222: a 'Your song' card in the profile editor
(under Video). The vendor searches a title or artist (meetlazo.com/music/search,
the same Deezer/iTunes search the couples' Music page uses), hears a 30-second
clip (web: an audio element; phones: the clip opens outside the app), picks
one, and chooses whether it starts when a couple arrives. Save writes
vendors.song {title, artist, art, trackId, preview, autoplay, loop} - the map
the couple sites keep in weddingSites.song - and the storefront's lazo.js
mounts the record pill from meetlazo.com/music/song?v=<id>. Remove deletes the
field. No new dependencies (http, universal_html, url_launcher are already in).

    python app-patches\patch_vendor_song_1020.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = HERE / "Vendor_master_v222.txt"
dst = HERE / "Vendor_master_v223.txt"
s = src.read_text(encoding="utf-8")


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:80])
    s = s.replace(old, new)


# ---- header ----
rep("// lazo_vendor_dashboard.dart\n",
    "// lazo_vendor_dashboard.dart\n"
    "// Build ID: JC-LAZO-VSONG-1020-VENDOR (v223: YOUR SONG - a song that plays when a couple opens the storefront. "
    "A 'Your song' card in the profile editor under Video: search a title or artist (meetlazo.com/music/search, the couples' "
    "Music page search), hear the 30-second clip (web: an audio element read through dynamic; phones: the clip opens outside "
    "the app), pick one, choose whether it starts on arrival; Save writes vendors.song {title, artist, art, trackId, preview, "
    "autoplay, loop} - the same map the couples' wedding sites keep - and the storefront mounts the record pill from "
    "meetlazo.com/music/song?v=<id> (lazo.js, JC-LAZO-VSONG-1020-002). Remove deletes the field. No new dependencies. base v222)\n"
    "// What's new: Your storefront can play a song | Pick a track in Profile under Your song and it plays softly when a couple "
    "opens your page, with a record turning in the corner. | One tap pauses it; you choose whether it starts on arrival. | profile\n")

# ---- build ids ----
rep("  static const String kBuildId = 'JC-LAZO-RELEASE-1020-222';",
    "  static const String kBuildId = 'JC-LAZO-VSONG-1020-223';")
rep("  static const int kLzWidgetVersion = 222;",
    "  static const int kLzWidgetVersion = 223;")

# ---- state ----
rep("  final TextEditingController _epVideoC = TextEditingController();\n",
    "  final TextEditingController _epVideoC = TextEditingController();\n"
    "  // v223: the storefront song - what the vendor picked, the search, the preview\n"
    "  Map<String, dynamic>? _epSong;\n"
    "  bool _epSongAuto = true;\n"
    "  final TextEditingController _epSongQC = TextEditingController();\n"
    "  List<Map<String, dynamic>> _epSongHits = <Map<String, dynamic>>[];\n"
    "  bool _epSongBusy = false;\n"
    "  String _epSongErr = '';\n"
    "  Timer? _epSongT;\n"
    "  int _epSongTok = 0;\n"
    "  dynamic _epSongEl; // web only: the preview's audio element, read through dynamic\n"
    "  String _epSongPlaying = '';\n")

# ---- load ----
rep("    _epVideoC.text = v['videoUrl'] == null ? '' : v['videoUrl'].toString();\n",
    "    _epVideoC.text = v['videoUrl'] == null ? '' : v['videoUrl'].toString();\n"
    "    // v223: the storefront song\n"
    "    _epSong = v['song'] is Map ? Map<String, dynamic>.from(v['song'] as Map) : null;\n"
    "    if (_epSong != null && (_epSong!['title'] ?? '').toString().trim().isEmpty) {\n"
    "      _epSong = null;\n"
    "    }\n"
    "    _epSongAuto = _epSong == null ? true : _epSong!['autoplay'] != false;\n"
    "    _epSongQC.clear();\n"
    "    _epSongHits = <Map<String, dynamic>>[];\n"
    "    _epSongErr = '';\n"
    "    _epSongStop();\n")

# ---- fingerprint (unsaved-changes guard) ----
rep("      _epStartPriceC.text,\n      _epVideoC.text,\n      _epServicesC.text,\n",
    "      _epStartPriceC.text,\n      _epVideoC.text,\n"
    "      json.encode(_epSong ?? ''), // v223\n      _epSongAuto.toString(),\n"
    "      _epServicesC.text,\n")

# ---- save ----
rep("        'videoUrl': _epVideoC.text.trim(),\n        'servicesNote': _epServicesC.text.trim(),\n",
    "        'videoUrl': _epVideoC.text.trim(),\n"
    "        // v223: the storefront song - the map the couples' sites keep in weddingSites.song\n"
    "        'song': _epSong == null\n"
    "            ? FieldValue.delete()\n"
    "            : <String, dynamic>{\n"
    "                'title': (_epSong!['title'] ?? '').toString(),\n"
    "                'artist': (_epSong!['artist'] ?? '').toString(),\n"
    "                'art': (_epSong!['art'] ?? '').toString(),\n"
    "                'trackId': (_epSong!['trackId'] ?? '').toString(),\n"
    "                'preview': (_epSong!['preview'] ?? '').toString(),\n"
    "                'autoplay': _epSongAuto,\n"
    "                'loop': false,\n"
    "              },\n"
    "        'servicesNote': _epServicesC.text.trim(),\n")

# ---- the card, under Video ----
rep("        _epCard(\n            'Photo gallery',\n",
    "        _epSongCard(), // v223\n        _epCard(\n            'Photo gallery',\n")

# ---- methods ----
METHODS = r'''
  // ---- v223: the storefront song ----------------------------------------
  // Search goes through meetlazo.com/music/search (Deezer first, iTunes second,
  // reshaped to iTunes field names). A pick keeps title, artist, art, trackId
  // and preview; the worker refreshes Deezer clips at play time, so an old
  // preview link never matters. The clip plays here on the web through an
  // audio element read as dynamic (the phone stub of universal_html lacks the
  // members); on phones it opens outside the app.
  static const String _kSongSearch = 'https://meetlazo.com/music/search';

  void _epSongChanged(String q) {
    _epSongT?.cancel();
    final String t = q.trim();
    if (t.length < 2) {
      setState(() {
        _epSongHits = <Map<String, dynamic>>[];
        _epSongBusy = false;
        _epSongErr = '';
      });
      return;
    }
    _epSongT = Timer(const Duration(milliseconds: 350), () => _epSongSearch(t));
  }

  Future<void> _epSongSearch(String q) async {
    final int tok = ++_epSongTok;
    setState(() {
      _epSongBusy = true;
      _epSongErr = '';
    });
    List<Map<String, dynamic>> hits = <Map<String, dynamic>>[];
    String err = '';
    try {
      final httpc.Response r = await httpc
          .get(Uri.parse('$_kSongSearch?q=${Uri.encodeComponent(q)}'))
          .timeout(const Duration(seconds: 10));
      if (r.statusCode != 200) throw Exception('http ${r.statusCode}');
      final Map<String, dynamic> j = json.decode(r.body) as Map<String, dynamic>;
      final List<dynamic> rs = j['results'] is List ? j['results'] as List : <dynamic>[];
      for (final dynamic x in rs) {
        if (x is! Map) continue;
        final String title = (x['trackName'] ?? '').toString().trim();
        final String preview = (x['previewUrl'] ?? '').toString().trim();
        if (title.isEmpty || preview.isEmpty) continue;
        hits.add(<String, dynamic>{
          'title': title,
          'artist': (x['artistName'] ?? '').toString().trim(),
          'art': (x['artworkUrl100'] ?? '').toString().replaceAll('100x100bb', '200x200bb'),
          'trackId': (x['trackId'] ?? '').toString(),
          'preview': preview,
          'explicit': x['explicit'] == true,
        });
        if (hits.length >= 12) break;
      }
      if (hits.isEmpty) err = 'Nothing with a preview for that. Try the artist, or another title.';
    } catch (e) {
      debugPrint('LAZO song search: ' + e.toString());
      err = 'Search is unavailable right now. Try again in a moment.';
      hits = <Map<String, dynamic>>[];
    }
    if (!mounted || tok != _epSongTok) return;
    setState(() {
      _epSongHits = hits;
      _epSongBusy = false;
      _epSongErr = err;
    });
  }

  void _epSongStop() {
    if (_epSongEl != null) {
      try {
        _epSongEl.pause();
      } catch (_) {}
      _epSongEl = null;
    }
    if (_epSongPlaying.isNotEmpty && mounted) {
      setState(() => _epSongPlaying = '');
    } else {
      _epSongPlaying = '';
    }
  }

  void _epSongPreview(String url) {
    if (url.isEmpty) return;
    if (_epSongPlaying == url) {
      _epSongStop();
      return;
    }
    _epSongStop();
    if (!kIsWeb) {
      launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
      return;
    }
    try {
      final dynamic el = html.document.createElement('audio');
      el.src = url;
      el.volume = 0.9;
      el.play();
      _epSongEl = el;
      el.onEnded.listen((dynamic _) {
        if (mounted && _epSongEl == el) {
          setState(() => _epSongPlaying = '');
          _epSongEl = null;
        }
      });
      setState(() => _epSongPlaying = url);
    } catch (e) {
      debugPrint('LAZO song preview: ' + e.toString());
    }
  }

  void _epSongPick(Map<String, dynamic> hit) {
    _epSongStop();
    _epSongT?.cancel();
    setState(() {
      _epSong = <String, dynamic>{
        'title': hit['title'],
        'artist': hit['artist'],
        'art': hit['art'],
        'trackId': hit['trackId'],
        'preview': hit['preview'],
      };
      _epSongAuto = true;
      _epSongHits = <Map<String, dynamic>>[];
      _epSongQC.clear();
      _epSongErr = '';
    });
  }

  Widget _epSongArt(String art, double size) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(size / 2),
      child: Container(
        width: size,
        height: size,
        color: const Color(0xFF1A1A1A),
        child: art.isEmpty
            ? Icon(Icons.music_note_rounded, color: gold, size: size * .5)
            : Image.network(art, width: size, height: size, fit: BoxFit.cover,
                errorBuilder: (BuildContext c, Object e, StackTrace? st) =>
                    Icon(Icons.music_note_rounded, color: gold, size: size * .5)),
      ),
    );
  }

  Widget _epSongCard() {
    final Map<String, dynamic>? sg = _epSong;
    final List<Widget> kids = <Widget>[];
    if (sg != null) {
      final String pv = (sg['preview'] ?? '').toString();
      final bool on = _epSongPlaying.isNotEmpty && _epSongPlaying == pv;
      kids.add(Row(children: <Widget>[
        _epSongArt((sg['art'] ?? '').toString(), 52),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Text((sg['title'] ?? '').toString(),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: _lzFg(ink), fontSize: 15, fontWeight: FontWeight.w700)),
            Text((sg['artist'] ?? '').toString(),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: _lzFg(muted), fontSize: 13)),
          ]),
        ),
        IconButton(
          tooltip: on ? 'Stop' : (kIsWeb ? 'Hear the clip' : 'Open the clip'),
          onPressed: pv.isEmpty ? null : _h(() => _epSongPreview(pv)),
          icon: Icon(on ? Icons.stop_circle_rounded : Icons.play_circle_fill_rounded,
              color: _lzFg(plum), size: 30),
        ),
      ]));
      kids.add(const SizedBox(height: 6));
      kids.add(SwitchListTile(
        contentPadding: EdgeInsets.zero,
        value: _epSongAuto,
        activeColor: Colors.white,
        activeTrackColor: vGreen,
        title: Text('Start playing when a couple arrives',
            style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w700, fontSize: 14)),
        subtitle: Text(
            _epSongAuto
                ? 'It fades in softly. Browsers that wait for a tap play on the first one.'
                : 'The record waits in the corner until they tap it.',
            style: TextStyle(color: _lzFg(muted), fontSize: 12)),
        onChanged: (bool v) => setState(() => _epSongAuto = v),
      ));
      kids.add(Row(children: <Widget>[
        TextButton.icon(
          onPressed: _h(() {
            _epSongStop();
            setState(() {
              _epSong = null;
              _epSongAuto = true;
            });
          }),
          icon: Icon(Icons.close_rounded, size: 18, color: _lzFg(muted)),
          label: Text('Remove the song', style: TextStyle(color: _lzFg(muted), fontSize: 13)),
        ),
        const Spacer(),
        Text('Changes save with the profile.', style: TextStyle(color: _lzFg(muted), fontSize: 12)),
      ]));
    } else {
      kids.add(TextField(
        controller: _epSongQC,
        onChanged: _epSongChanged,
        textInputAction: TextInputAction.search,
        cursorColor: _lzFg(plum),
        style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
        decoration: _epDeco('Find a song', 'A title or an artist'),
      ));
      if (_epSongBusy) {
        kids.add(const Padding(
          padding: EdgeInsets.symmetric(vertical: 12),
          child: Center(child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))),
        ));
      } else if (_epSongErr.isNotEmpty) {
        kids.add(Padding(
          padding: const EdgeInsets.only(top: 10),
          child: Text(_epSongErr, style: TextStyle(color: _lzFg(muted), fontSize: 13)),
        ));
      } else if (_epSongHits.isNotEmpty) {
        kids.add(const SizedBox(height: 6));
        for (final Map<String, dynamic> h in _epSongHits) {
          final String pv = (h['preview'] ?? '').toString();
          final bool on = _epSongPlaying.isNotEmpty && _epSongPlaying == pv;
          kids.add(ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: 4),
            dense: true,
            leading: _epSongArt((h['art'] ?? '').toString(), 40),
            title: Text(
                (h['title'] ?? '').toString() + (h['explicit'] == true ? '  · E' : ''),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: _lzFg(ink), fontSize: 14, fontWeight: FontWeight.w600)),
            subtitle: Text((h['artist'] ?? '').toString(),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: _lzFg(muted), fontSize: 12)),
            trailing: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
              IconButton(
                tooltip: on ? 'Stop' : (kIsWeb ? 'Hear the clip' : 'Open the clip'),
                onPressed: _h(() => _epSongPreview(pv)),
                icon: Icon(on ? Icons.stop_circle_rounded : Icons.play_circle_outline_rounded,
                    color: _lzFg(plum), size: 26),
              ),
              TextButton(
                onPressed: _h(() => _epSongPick(h)),
                child: Text('Use it', style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w700)),
              ),
            ]),
            onTap: _h(() => _epSongPick(h)),
          ));
        }
      }
    }
    return _epCard(
        'Your song',
        sg == null
            ? 'A track that plays softly when a couple opens your page - a record turning in the corner, one tap to pause. 30-second clips.'
            : 'Plays softly on your storefront. A record turns in the corner; one tap pauses it.',
        kids);
  }

'''
rep("  Widget _epCard(String title, String subtitle, List<Widget> children) {\n",
    METHODS.lstrip("\n") + "  Widget _epCard(String title, String subtitle, List<Widget> children) {\n")

dst.write_text(s, encoding="utf-8")
print("wrote", dst, len(s.splitlines()), "lines")
