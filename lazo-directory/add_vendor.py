"""Manually add a vendor to Lazo (service-area businesses the seeder missed).
Usage example:
  python add_vendor.py --name "Atavia Weddings" --metro phoenix ^
    --categories wedding-videographers wedding-photographers ^
    --phone "(602) 555-0100" --website "https://ataviaweddings.com" ^
    --area "Serving Phoenix, Arizona"
"""
import argparse, os, re, sys
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
firebase_admin.initialize_app(cred)
db = firestore.client()

VALID_METROS = ["phoenix","denver","dallas-fort-worth","houston","austin",
                "san-antonio","las-vegas","atlanta","nashville"]
VALID_CATS = ["wedding-photographers","wedding-videographers","wedding-venues",
              "wedding-planners","wedding-djs","wedding-florists","wedding-caterers",
              "wedding-cakes","hair-and-makeup","wedding-officiants",
              "wedding-transportation","wedding-rentals","wedding-bands",
              "wedding-invitations","day-of-coordination"]

def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)

p = argparse.ArgumentParser()
p.add_argument("--name", required=True)
p.add_argument("--metro", required=True, choices=VALID_METROS)
p.add_argument("--categories", nargs="+", required=True, choices=VALID_CATS)
p.add_argument("--phone", default="")
p.add_argument("--website", default="")
p.add_argument("--area", default="", help='e.g. "Serving Phoenix, Arizona"')
p.add_argument("--place-id", default="", help="Real Google place_id if known")
args = p.parse_args()

slug = slugify(args.name)
doc_id = args.place_id if args.place_id else f"manual-{args.metro}-{slug}"

existing = db.collection("vendors").document(doc_id).get()
if existing.exists:
    print(f"ABORT: vendor doc '{doc_id}' already exists.")
    sys.exit(1)
dupe = db.collection("vendors").where("metroId", "==", args.metro)\
         .where("slug", "==", slug).limit(1).get()
if dupe:
    print(f"ABORT: a vendor with slug '{slug}' already exists in {args.metro}.")
    sys.exit(1)

db.collection("vendors").document(doc_id).set({
    "placeId": doc_id,
    "name": args.name,
    "slug": slug,
    "address": args.area or f"Serving {args.metro.replace('-', ' ').title()}",
    "phone": args.phone,
    "website": args.website,
    "metroId": args.metro,
    "categories": args.categories,
    "score": 65,
    "reviewCount": 0,
    "verified": False,
    "claimStatus": "unclaimed",
    "claimedBy": None,
    "source": "manual",
    "serviceArea": True,
    "seededAt": datetime.now(timezone.utc),
})
print(f"Added: {args.name}  ({doc_id})  metro={args.metro}  cats={args.categories}")
print("Next: python generate\\build.py --tranche 2  &&  python deploy\\upload_r2.py")
