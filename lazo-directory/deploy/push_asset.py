r"""push_asset.py - JC-LAZO-LOCAL-1017-002: ship one static asset without a full sync.

    python deploy\push_asset.py lazo.vendor.css

Copies generate/static/<name> into dist/assets/, uploads that one key to R2 with deploy_site's own
rclone settings, and purges its URLs (bare, and with the ?v= the live pages carry) from Cloudflare's cache.
For stylesheet/script fixes only: pages keep their ?v=, so the purge is what makes browsers see the new file.
"""
import json, re, shutil, sys, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy_site as ds  # noqa: E402  (loads .env at import)

name = sys.argv[1]
src = ds.ROOT / "generate" / "static" / name
assert src.is_file(), src
dst = ds.DIST / "assets" / name
shutil.copy2(src, dst)
ds.RCLONE = ds.find_rclone()
r = ds.rclone(["copyto", str(dst), f"r2:{ds.BUCKET}/assets/{name}", "--checksum"], ds.rclone_env())
print("upload:", "ok" if r.returncode == 0 else f"FAILED {r.stderr[-400:]}")
if r.returncode:
    sys.exit(1)
# the ?v= the live pages reference
vs = set()
for page in sys.argv[2:] or ["https://meetlazo.com/dallas-fort-worth/wedding-photographers/olivia-layne-studios/"]:
    html = urllib.request.urlopen(urllib.request.Request(page, headers={"User-Agent": "Lazo/1.0"}), timeout=30).read().decode("utf-8", "replace")
    vs |= set(re.findall(rf"/assets/{re.escape(name)}\?v=([a-z0-9]+)", html))
urls = [f"https://meetlazo.com/assets/{name}"] + [f"https://meetlazo.com/assets/{name}?v={v}" for v in sorted(vs)]
import os
zone, token = os.environ.get("CF_ZONE_ID"), os.environ.get("CF_API_TOKEN")
req = urllib.request.Request(f"https://api.cloudflare.com/client/v4/zones/{zone}/purge_cache", data=json.dumps({"files": urls}).encode(),
                             headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="POST")
ok = json.loads(urllib.request.urlopen(req, timeout=30).read()).get("success")
print("purge:", "ok" if ok else "FAILED", urls)
