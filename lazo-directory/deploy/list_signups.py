"""Print early-access signups from R2. Usage: python deploy\\list_signups.py"""
import json, os
from pathlib import Path
try:
    from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError: pass
import boto3

s3 = boto3.client("s3",
    endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
    aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")

rows = []
token = None
while True:
    kw = dict(Bucket="lazo-site", Prefix="signups/")
    if token: kw["ContinuationToken"] = token
    resp = s3.list_objects_v2(**kw)
    for o in resp.get("Contents", []):
        d = json.loads(s3.get_object(Bucket="lazo-site", Key=o["Key"])["Body"].read())
        rows.append(d)
    if not resp.get("IsTruncated"): break
    token = resp["NextContinuationToken"]

rows.sort(key=lambda r: r.get("ts", ""))
for r in rows:
    print(f"{r.get('ts','')[:16]:>17}  {r.get('email',''):<40} {r.get('metro','')}")
print(f"\n{len(rows)} signups")
