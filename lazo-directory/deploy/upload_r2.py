"""Sync dist/ to the lazo-site R2 bucket via S3 API (parallel, content-typed).
Env (.env): R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY
Usage: python deploy\\upload_r2.py            # full sync
       python deploy\\upload_r2.py --prefix phoenix   # partial
"""
import argparse, mimetypes, os, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
try:
    from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError: pass
import boto3

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUCKET = "lazo-site"

def client():
    acct = os.environ["R2_ACCOUNT_ID"]
    return boto3.client("s3",
        endpoint_url=f"https://{acct}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--prefix", action="append", default=[])  # JC-LAZO-SEO-0921-003: repeatable, one walk of dist
    a = ap.parse_args()
    s3 = client()
    files = [p for p in DIST.rglob("*") if p.is_file()
             and any(str(p.relative_to(DIST)).replace("\\", "/").startswith(px) for px in (a.prefix or [""]))]
    print(f"Uploading {len(files)} files to r2://{BUCKET}/ prefixes={a.prefix or ['(all)']}")
    def put(p: Path):
        key = str(p.relative_to(DIST)).replace("\\", "/")
        ctype = mimetypes.guess_type(key)[0] or "application/octet-stream"
        s3.upload_file(str(p), BUCKET, key, ExtraArgs={"ContentType": ctype})
        return key
    with ThreadPoolExecutor(max_workers=16) as ex:
        for i, k in enumerate(ex.map(put, files), 1):
            if i % 200 == 0: print(f"  {i}/{len(files)}")
    print("Sync complete.")

if __name__ == "__main__":
    main()
