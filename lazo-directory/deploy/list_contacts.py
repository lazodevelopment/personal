r"""Print contact-form submissions from R2.  JC-LAZO-CFORM-0916-001

The site no longer publishes hello@ / vendors@ / press@ / trust@ / privacy@.
/contact/, /delete-account/, /privacy/ and /terms/ all post one form to the
worker's /api/contact, which writes a JSON object per message under contact/.
This is how you read the inbox until RESEND_API_KEY + CONTACT_TO are set as
worker secrets and the worker starts forwarding to a real mailbox as well.

    python deploy\list_contacts.py                 # newest last, one line each
    python deploy\list_contacts.py --full          # with the message body
    python deploy\list_contacts.py --topic privacy # one topic only
    python deploy\list_contacts.py --since 2026-09-01

Same .env keys and the same bucket as deploy\list_signups.py.
"""
import argparse, json, os
from pathlib import Path

try:
    from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass
import boto3

# JC-LAZO-INBOX-0916-003: NOT "contact/". The bucket serves the site, so a key
# under contact/ was reachable at https://meetlazo.com/contact/<id>.json - the
# submission, with the sender's name and email, as a public file. The "_" prefix
# is this codebase's mark for a key the worker refuses to serve.
PREFIX = "_inbox/contact/"

TOPIC_LABEL = {
    "general": "couple/general", "vendor": "vendor", "trust": "review/trust",
    "privacy": "privacy/data", "press": "press", "delete": "delete account",
    "legal": "legal", "other": "other",
}

ap = argparse.ArgumentParser()
ap.add_argument("--full", action="store_true", help="print the message body too")
ap.add_argument("--topic", help="filter to one topic (%s)" % ", ".join(TOPIC_LABEL))
ap.add_argument("--since", help="ISO date, e.g. 2026-09-01")
args = ap.parse_args()

s3 = boto3.client("s3",
    endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
    aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")

rows, token = [], None
while True:
    kw = dict(Bucket="lazo-site", Prefix=PREFIX)
    if token:
        kw["ContinuationToken"] = token
    resp = s3.list_objects_v2(**kw)
    for o in resp.get("Contents", []):
        rows.append(json.loads(s3.get_object(Bucket="lazo-site", Key=o["Key"])["Body"].read()))
    if not resp.get("IsTruncated"):
        break
    token = resp["NextContinuationToken"]

if args.topic:
    rows = [r for r in rows if r.get("topic") == args.topic]
if args.since:
    rows = [r for r in rows if r.get("ts", "") >= args.since]
rows.sort(key=lambda r: r.get("ts", ""))

for r in rows:
    topic = TOPIC_LABEL.get(r.get("topic", ""), r.get("topic", ""))
    who = f"{r.get('name','')} <{r.get('email','')}>".strip()
    print(f"{r.get('ts','')[:16]:>17}  {topic:<15} {who}")
    if args.full:
        if r.get("accountEmail"):
            print(f"{'':19}account: {r['accountEmail']}")
        if r.get("page"):
            print(f"{'':19}from:    {r['page']}")
        for line in (r.get("message") or "").splitlines():
            print(f"{'':19}| {line}")
        print()

print(f"\n{len(rows)} message{'' if len(rows) == 1 else 's'}")
