"""Regenerate the full favicon set from ANY square source image
(e.g. Batul's exact mark). Usage: python favicon_make.py path\\to\\mark.png
Outputs into the current folder; drop results into generate/static root."""
import sys
from PIL import Image
src = Image.open(sys.argv[1]).convert("RGBA")
for s, name in [(16,"favicon-16.png"),(32,"favicon-32.png"),(48,"favicon-48.png"),
                (180,"apple-touch-icon.png"),(192,"icon-192.png"),(512,"icon-512.png")]:
    src.resize((s,s), Image.LANCZOS).save(name)
Image.open("favicon-48.png").save("favicon.ico", sizes=[(16,16),(32,32),(48,48)])
print("favicon set regenerated")
