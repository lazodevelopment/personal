r"""patch_june_native_v11.py - JuneNative v10 -> v11 (JC-LAZO-JUNE-NATIVE-1016-011)

THE RADIO ON ANDROID. June's voice player and the radio player both asked Android for full audio focus
(audioplayers' default, AUDIOFOCUS_GAIN). Whenever June spoke - her line when the dashboard opens, or her
answer about the station - Android told the radio it had lost focus for good, and audioplayers answers a
permanent loss by pausing the player and never starting it again, so picking a station played nothing.
June's voice now asks for transient focus that may duck others (AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK): the
radio keeps playing, lowered while she talks (as on the web, where the radio already dips), and is back at
full volume when she stops. The radio keeps full focus, so other apps' music still pauses for it.

    python app-patches\patch_june_native_v11.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / "JuneNative_v10.txt").read_text(encoding="utf-8")
OUT = HERE / "JuneNative_v11.txt"


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"anchor found {n}x (want {count}): {old[:80]!r}")
    s = s.replace(old, new)


rep("// Build ID: JC-LAZO-JUNE-NATIVE-1016-010 (010:",
    "// Build ID: JC-LAZO-JUNE-NATIVE-1016-011 (011: on Android June's voice takes transient, duckable audio focus, so "
    "the radio keeps playing under her instead of being paused for good; base 010) (010:")
rep("// END OF FILE - JC-LAZO-JUNE-NATIVE-1016-010", "// END OF FILE - JC-LAZO-JUNE-NATIVE-1016-011")

rep("""    final AudioPlayer p = AudioPlayer();
    try {
      p.setAudioContext(AudioContext(
        iOS: AudioContextIOS(category: AVAudioSessionCategory.playback),
        android: AudioContextAndroid(),
      ));
    } catch (_) {}
    p.setReleaseMode(ReleaseMode.stop);""", """    final AudioPlayer p = AudioPlayer();
    try {
      p.setAudioContext(AudioContext(
        iOS: AudioContextIOS(category: AVAudioSessionCategory.playback),
        // v011: transient, duckable focus - a full-focus request made Android pause the radio for good
        android: const AudioContextAndroid(audioFocus: AndroidAudioFocus.gainTransientMayDuck),
      ));
    } catch (_) {}
    p.setReleaseMode(ReleaseMode.stop);""")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT.name} ({len(s):,} chars)")
