r"""Ship a lazo.css / lazo.js change without a full rebuild.  JC-LAZO-BUMP-0916-002

build.py stamps every page with /assets/lazo.css?v=<md5 of generate/static/lazo.*>
so Cloudflare and browsers fetch a fresh stylesheet when it changes.  When a
rebuild is not possible (Firestore blocked, no keys), this does the same thing
to the existing dist/: copies the two assets in and rewrites the ?v= stamp in
every built HTML page.  Then sync with:

    python deploy\deploy_site.py --skip-build

YOU DO NOT NEED THIS AFTER A FULL BUILD. build.py already copies generate/static
into dist/assets and stamps every page itself. Running it after a build is at best
a no-op and at worst what happened on 2026-09-16 - see below.

Two things learned the hard way on 2026-09-16:

  1. It used to read with universal newlines (CRLF -> LF) and write back with
     newline="", so every page it touched was silently converted to LF and shrank
     by one byte per line. A 44,735-byte page became 44,012. That made ALL 108,679
     files differ from the copy in R2, turning a stamp change into a full-site
     re-upload. It now edits bytes and never touches line endings.

  2. It ran while three rclone syncs were reading dist/, so rclone hashed a file,
     uploaded it, and found the bytes had changed underneath - fifteen
     "corrupted on transfer" errors and an aborted deploy. It now refuses to start
     while a sync is running.

Safe to re-run; it only writes pages whose stamp actually differs.
"""
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "generate" / "static"
DIST = ROOT / "dist"


def asset_version():
    h = hashlib.md5()
    for f in sorted(STATIC.glob("lazo.*")):   # same files build.py hashes
        h.update(f.read_bytes())
    return h.hexdigest()[:8]


def sync_running() -> bool:
    """True if an rclone is live. Rewriting dist/ under a sync corrupts the transfer."""
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq rclone.exe", "/NH"],
                             capture_output=True, text=True, timeout=20).stdout
        return "rclone.exe" in out
    except Exception:
        return False        # cannot tell - do not block the user


def main():
    if not DIST.is_dir():
        sys.exit("dist/ not found - nothing to bump")
    if sync_running() and "--force" not in sys.argv:
        sys.exit(
            "rclone is running - refusing to rewrite dist/ underneath it.\n"
            "  A sync hashes each file, uploads it, then verifies; changing the bytes\n"
            "  mid-flight gives 'corrupted on transfer' and aborts the deploy.\n"
            "  Wait for the sync to finish, then re-run. (--force overrides.)")

    ver = asset_version()
    for name in ("lazo.css", "lazo.js"):
        shutil.copy(STATIC / name, DIST / "assets" / name)
    print(f"assets copied; new stamp v={ver}")

    # bytes in, bytes out: the stamp is the only thing that may change, and line
    # endings are left exactly as build.py wrote them
    pat = re.compile(rb"(/assets/lazo\.(?:css|js)\?v=)[0-9A-Za-z]{1,12}")
    rep = lambda m: m.group(1) + ver.encode()      # noqa: E731
    scanned = changed = 0
    for p in DIST.rglob("*.html"):
        scanned += 1
        b = p.read_bytes()
        new, n = pat.subn(rep, b)
        if n and new != b:
            p.write_bytes(new)
            changed += 1
        if scanned % 5000 == 0:
            print(f"  {scanned:,} scanned, {changed:,} updated", flush=True)
    print(f"done: {scanned:,} pages scanned, {changed:,} updated to v={ver}")


if __name__ == "__main__":
    main()
