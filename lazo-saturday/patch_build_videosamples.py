"""Adds videoSamples -> videoEmbeds to saturday_enrich. Run once from lazo-directory root."""
from pathlib import Path
bp = Path("generate/build.py")
src = bp.read_text(encoding="utf-8")
if "videoEmbeds" in src:
    print("Already patched.")
    raise SystemExit
anchor = '''        if emb:
            v["videoEmbed"] = emb'''
assert anchor in src, "enrich anchor missing — run patch_build_saturday.py first"
inject = '''        if emb:
            v["videoEmbed"] = emb

        embeds = []
        for s in (v.get("videoSamples") or []):
            s = str(s).strip()
            e2 = None
            if "youtu.be/" in s:
                e2 = "https://www.youtube.com/embed/" + s.split("youtu.be/")[1].split("?")[0].split("&")[0]
            elif "youtube.com/watch" in s and "v=" in s:
                e2 = "https://www.youtube.com/embed/" + s.split("v=")[1].split("&")[0]
            elif "youtube.com/shorts/" in s:
                e2 = "https://www.youtube.com/embed/" + s.split("shorts/")[1].split("?")[0]
            elif "vimeo.com/" in s:
                vid = s.split("vimeo.com/")[1].split("?")[0].split("/")[0]
                if vid.isdigit():
                    e2 = "https://player.vimeo.com/video/" + vid
            if e2:
                embeds.append(e2)
        if embeds:
            v["videoEmbeds"] = embeds[:4]'''
src = src.replace(anchor, inject)
bp.write_text(src, encoding="utf-8")
print("PATCHED: videoSamples render as film gallery.")
