#!/usr/bin/env python3
"""JC-ATV-PAY-1001: balance due 14 CALENDAR days after signing (was 14 business days).

Run from ~/bs:  python3 patch_calendar_days.py
Anchor-and-assert: every edit must find its anchor exactly once or the script
stops without writing anything. Already-patched files are reported and skipped.

1. main.py                              — _compute_balance_due counts calendar days.
2. contract/atavia_contract_generator.py — three "business days" clauses -> "calendar days".

Then deploy book_submit (computes balance_due_at and renders the contract) and
admin_action (re-renders contracts), with the usual vintage diff first.
"""
import pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
edits = [
    ("main.py",
     '''    """Balance is due 14 business days (Mon-Fri) after booking/signing. If the
    Event is sooner than that, the balance falls due the day before the Event
    (never after it), and never earlier than now."""
    from datetime import timezone as _tz
    due = now
    added = 0
    while added < RULES["balance_due_days_from_booking"]:
        due = due + timedelta(days=1)
        if due.weekday() < 5:
            added += 1
''',
     '''    """Balance is due 14 calendar days after booking/signing (changed from
    business days 2026-10-01). If the Event is sooner than that, the balance
    falls due the day before the Event (never after it), and never earlier than now."""
    from datetime import timezone as _tz
    due = now + timedelta(days=RULES["balance_due_days_from_booking"])
'''),
    ("contract/atavia_contract_generator.py",
     "is due fourteen (14) business days ", "is due fourteen (14) calendar days "),
    ("contract/atavia_contract_generator.py",
     "method on file fourteen (14) business days after this Agreement is signed",
     "method on file fourteen (14) calendar days after this Agreement is signed"),
    ("contract/atavia_contract_generator.py",
     "to the payment method on file fourteen (14) business days after signing",
     "to the payment method on file fourteen (14) calendar days after signing"),
]

def read(p):
    with open(p, encoding="utf-8", newline="") as f: return f.read()
def write(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(s)

texts = {}
for path, anchor, new in edits:
    s = texts.get(path) or read(ROOT / path)
    if new in s and anchor not in s:
        print(f"already patched: {path}: {anchor[:50]!r}"); texts[path] = s; continue
    if s.count(anchor) != 1:
        sys.exit(f"ABORT: anchor found {s.count(anchor)}x in {path}: {anchor[:60]!r}")
    texts[path] = s.replace(anchor, new)
for path, s in texts.items():
    write(ROOT / path, s); print("patched", path)
print("done. Now: diff against each function's live vintage, then deploy book_submit and admin_action.")
