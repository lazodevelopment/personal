"""patch_music_v26.py - Music widget v2.6 (phones: previews that actually play)
Music_master_v25.txt -> Music_master_v26.txt. Anchor-asserted, idempotent.
  1. The native player gets an explicit audio session: iOS category "playback"
     (plays with the ringer switch on silent, which the default ambient
     category does not) and Android media usage.
  2. When the direct preview URL fails on a phone, the same clip is retried
     through meetlazo.com/music/preview (the relay the web player already
     uses). Only if both fail does the toast appear, and it now says why.
  python app-patches\\patch_music_v26.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "Music_master_v25.txt"
DST = HERE / "Music_master_v26.txt"
s = SRC.read_text(encoding="utf-8")


def rep(old, new):
    global s
    assert s.count(old) == 1, f"anchor x{s.count(old)}: {old[:60]!r}"
    s = s.replace(old, new)


rep("""// (v2.5: COMPILE FIX""",
    """// (v2.6: PHONES - the native player sets an iOS "playback" audio session
// (ambient, the default, is silenced by the ringer switch) and, when the
// direct Deezer/Apple URL fails, retries the clip through the meetlazo.com
// relay before giving up; the toast then says why.)
// (v2.5: COMPILE FIX""")

rep("""    final AudioPlayer p = AudioPlayer();
    p.setReleaseMode(ReleaseMode.stop);
    p.setVolume(0.9);""",
    """    final AudioPlayer p = AudioPlayer();
    // v2.6: an explicit session so iOS treats this as media, not a UI sound
    try {
      // defaults everywhere else: the constructors differ between
      // audioplayers 5 and 6 and the category is the only thing that matters
      p.setAudioContext(AudioContext(
        iOS: AudioContextIOS(category: AVAudioSessionCategory.playback),
        android: AudioContextAndroid(),
      ));
    } catch (e) {
      debugPrint('LAZO music ctx: ' + e.toString());
    }
    p.setReleaseMode(ReleaseMode.stop);
    p.setVolume(0.9);""")

rep("""    try {
      final AudioPlayer p = _ensurePlayer();
      await p.stop();
      await p.play(UrlSource(s.preview));
    } catch (e) {
      debugPrint('LAZO music play: ' + e.toString());
      _toast('That preview would not play.');
      _stop();
      if (mounted) setState(() => _playingId = '');
    }""",
    """    // v2.6: direct first, then the relay; say why when both fail
    final AudioPlayer p = _ensurePlayer();
    String why = '';
    for (final String src in <String>[
      s.preview,
      '$kPreviewProxy?u=${Uri.encodeComponent(s.preview)}',
    ]) {
      try {
        await p.stop();
        await p.play(UrlSource(src));
        why = '';
        break;
      } catch (e) {
        why = e.toString();
        debugPrint('LAZO music play (' + src + '): ' + why);
      }
    }
    if (why.isNotEmpty) {
      final String short =
          why.replaceAll(RegExp(r'\\s+'), ' ').trim();
      _toast('That preview would not play. ' +
          (short.length > 90 ? short.substring(0, 90) + '\\u2026' : short));
      _stop();
      if (mounted) setState(() => _playingId = '');
    }""")

DST.write_text(s, encoding="utf-8", newline="\n")
b = s.count("{") - s.count("}")
p = s.count("(") - s.count(")")
print(f"wrote {DST.name}: {len(s):,} chars; brace balance {b}, paren balance {p}")
