"""Lazo metro census — prints unique vendor counts per metro from live Firestore.
Usage: python census.py"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
firebase_admin.initialize_app(cred)
db = firestore.client()

METROS = ["phoenix", "denver", "dallas-fort-worth", "houston", "austin",
          "san-antonio", "las-vegas", "atlanta", "nashville"]

total = 0
rows = []
for m in METROS:
    n = db.collection("vendors").where("metroId", "==", m).count().get()[0][0].value
    rows.append((m, n))
    total += n

rows.sort(key=lambda r: -r[1])
print(f"\n{'LAZO METRO CENSUS':^34}\n" + "-" * 34)
for i, (m, n) in enumerate(rows, 1):
    print(f"{i:>2}. {m:<20} {n:>7,}")
print("-" * 34)
print(f"{'TOTAL':<24} {total:>7,}\n")
