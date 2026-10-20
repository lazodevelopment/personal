"""One command per release: notes from the masters' headers, then publish.

    python release.py                 # new masters since the last run -> notes -> stats/appRelease
    python release.py --dry-run       # show the notes it would add, write nothing
    python release.py --stores        # ...and mark the newest masters as LIVE IN THE STORES
    python release.py --since couple=172 vendor=212   # redo from these builds (dry-run to preview)

How it works
  * Finds the newest Couple_master_vN.txt and Vendor_master_vN.txt here.
  * release_notes.json remembers the last build turned into notes ("covered").
    Every master newer than that gets one note from its Build ID line:
        // Build ID: JC-... (v179: TITLE IN CAPS - what it does; more; base v178)
    title -> sentence case, the description -> two plain lines with the
    developer tokens (field names, paths, worker/rules talk) stripped, and the
    screen it opens guessed from the words.
  * New notes go on top; hand-edited ones stay; each audience keeps its newest
    six. The release key becomes today's date, the title today's date in words.
  * Then it publishes exactly like publish_release.py. Store build numbers move
    only with --stores (after both stores approved that build), because a phone
    older than that number gets the Update popup pointing at the store.

Best: give every new master a line right under its Build ID, written for the
reader, and the script uses it as is:
    // What's new: Title | first line | second line | open
(open = a couple _View name, or a vendor mode: '' inbox, leads, profile, money,
studio, pipeline). Without it the Build ID line is parsed: title in caps before
" - ", clauses split by "; ", developer talk in parentheses.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTES = HERE / "release_notes.json"
KEEP_PER_ROLE = 6

ROLES = {
    "couple": ("Couple_master_v{}.txt", r"Couple_master_v(\d+)\.txt"),
    "vendor": ("Vendor_master_v{}.txt", r"Vendor_master_v(\d+)\.txt"),
}

# words kept as written when the caps title is turned into a sentence
PROPER = {"june": "June", "lazo": "Lazo", "whop": "Whop", "zola": "Zola", "knot": "Knot",
          "weddingwire": "WeddingWire", "instagram": "Instagram", "qr": "QR", "csv": "CSV",
          "rsvp": "RSVP", "rsvps": "RSVPs", "coi": "COI", "dj": "DJ", "pro": "Pro",
          "studio": "Studio", "google": "Google", "pdf": "PDF", "us": "US", "pearl": "Pearl",
          "joy": "Joy", "stripe": "Stripe", "square": "Square", "ai": "AI"}

# a clause that mentions any of these is for developers, not couples or vendors
DEV_WORDS = re.compile(
    r"\b(worker|rules?|functions?|firestore|arrayRemove|set\(merge\)|merge|endpoint|api|json|"
    r"cloudfunction|onCall|callable|base v\d+|kLz\w*|_\w+|schema|collection|doc|docs|"
    r"query|index|px|column|deploy|sitemap|canonical)\b", re.I)
CODE_TOKEN = re.compile(r"[A-Za-z]+\.[A-Za-z]\w*|/\S+|\{\w+\}|\b[a-z]+[A-Z]\w+\b|\b\w+_\w+\b")

OPEN_WORDS = {
    "couple": [
        ("website", ["website", "site", "search engine", "find a couple", "invitation", "collect address"]),
        ("guests", ["guest", "rsvp", "meal", "thank-you", "seating", "address"]),
        ("checklist", ["checklist", "task", "months out"]),
        ("messages", ["thread", "call", "message", "inbox", "vendor wrote", "questionnaire"]),
        ("vendors", ["booked", "contract", "invoice", "pay by card", "whop", "proposal"]),
        ("browse", ["browse", "three picks", "vendors from your city", "free on"]),
        ("dayof", ["day-of", "timeline", "license", "wedding day"]),
        ("registry", ["registry"]),
        ("shopping", ["shopping"]),
        ("board", ["dream board", "board", "inspiration"]),
        ("june", ["june"]),
        ("account", ["account", "export", "blocked", "theme"]),
    ],
    "vendor": [
        ("profile", ["listing", "bio", "profile", "photo", "market", "coi", "insurance", "services"]),
        ("money", ["get paid", "payment", "invoice", "payout", "whop", "money"]),
        ("studio", ["studio"]),
        ("pipeline", ["pipeline", "booked", "calendar"]),
        ("leads", ["automation", "lead form", "review", "export", "get booked", "today", "account"]),
        ("", ["inbox", "thread", "lead", "message", "call", "couple"]),
    ],
}


def newest(role: str) -> tuple[int, Path]:
    pat = re.compile(ROLES[role][1])
    best = (0, None)
    for p in HERE.iterdir():
        m = pat.fullmatch(p.name)
        if m and int(m.group(1)) > best[0]:
            best = (int(m.group(1)), p)
    if best[1] is None:
        raise SystemExit(f"no {role} master found in {HERE}")
    return best


def header(role: str, v: int) -> str | None:
    p = HERE / ROLES[role][0].format(v)
    if not p.exists():
        return None
    with p.open(encoding="utf-8") as f:
        for _ in range(80):
            line = f.readline()
            if not line:
                break
            if line.startswith("// Build ID:") and f"(v{v}:" in line:
                return line.strip()
    return None


def whats_new_line(role: str, v: int) -> dict | None:
    """A master may carry, near its Build ID, a line written for the reader:
        // What's new: Title | first line | second line | open
    That wins over the parsed header."""
    p = HERE / ROLES[role][0].format(v)
    if not p.exists():
        return None
    with p.open(encoding="utf-8") as f:
        for _ in range(80):
            line = f.readline()
            if not line:
                break
            if line.startswith("// What's new:") or line.startswith("// What’s new:"):
                parts = [x.strip() for x in line.split(":", 1)[1].split("|")]
                if len(parts) < 3 or not parts[0]:
                    return None
                while len(parts) < 4:
                    parts.append("")
                return {"for": role, "title": parts[0], "line1": parts[1], "line2": parts[2],
                        "open": parts[3], "build": v, "auto": True}
    return None


def sentence_case(caps: str) -> str:
    words = caps.strip().split()
    out = []
    for i, w in enumerate(words):
        core = re.sub(r"[^\w'-]", "", w).lower()
        if core in PROPER:
            out.append(w.replace(w.strip(",.'"), PROPER[core]) if w.strip(",.'") else PROPER[core])
        elif i == 0:
            out.append(w.capitalize())
        else:
            out.append(w.lower())
    return " ".join(out).replace("What'S", "What's").replace("what'S", "what's")


def clean_clause(c: str) -> str:
    c = re.sub(r"\([^()]*\)", "", c)          # parentheses hold the code talk
    c = re.sub(r"\s+", " ", c).replace(" ,", ",").replace(" .", ".").strip(" ,;:-")
    if not c or DEV_WORDS.search(c) or CODE_TOKEN.search(c):
        return ""
    c = c[0].upper() + c[1:]
    if c[-1] not in ".!?":
        c += "."
    return c


def parse(line: str) -> tuple[str, list[str]] | None:
    m = re.search(r"\(v\d+:\s*(.+?)\s+-\s+(.+?)(?:;\s*base v\d+)?\)\s*$", line)
    if not m:
        return None
    title = sentence_case(m.group(1))
    body = m.group(2)
    # clauses: split on "; " outside parentheses
    clauses, depth, cur = [], 0, []
    for ch in body:
        depth += ch == "("
        depth -= ch == ")"
        if ch == ";" and depth <= 0:
            clauses.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    clauses.append("".join(cur))
    lines = [x for x in (clean_clause(c) for c in clauses) if x]
    return title, lines


def guess_open(role: str, text: str) -> str:
    t = text.lower()
    for mode, words in OPEN_WORDS[role]:
        if any(w in t for w in words):
            return mode
    return "hub" if role == "couple" else ""


SCREEN = {"couple": {"hub": "Home", "website": "the Website screen", "guests": "Guests", "checklist": "the Checklist",
                     "messages": "Messages", "vendors": "Vendors", "browse": "Browse", "dayof": "Day-of",
                     "registry": "Registry", "shopping": "Shopping", "board": "the Dream board", "june": "June",
                     "account": "Account"},
          "vendor": {"": "the Inbox", "leads": "Today", "profile": "Profile", "money": "Get paid",
                     "studio": "Studio", "pipeline": "Pipeline"}}


def note_for(role: str, v: int) -> dict | None:
    ready = whats_new_line(role, v)
    if ready:
        return ready
    line = header(role, v)
    if not line:
        print(f"  v{v}: no Build ID line, skipped")
        return None
    parsed = parse(line)
    if not parsed:
        print(f"  v{v}: header not in the (vN: TITLE - text; base vM) shape, skipped")
        return None
    title, lines = parsed
    opn = guess_open(role, title + " " + " ".join(lines[:2]))
    where = SCREEN[role].get(opn, "Home")
    if not lines:
        lines = [f"Find it on {where}."]
    if len(lines) == 1:
        lines.append(f"Open {where} to try it.")
    return {
        "for": role,
        "title": title,
        "line1": lines[0],
        "line2": lines[1],
        "open": opn,
        "build": v,
        "auto": True,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stores", action="store_true", help="newest masters are now live in both stores")
    ap.add_argument("--since", nargs="*", default=[], metavar="role=build",
                    help="redo notes from this build on (couple=172 vendor=212)")
    ap.add_argument("--upto", nargs="*", default=[], metavar="role=build",
                    help="cover masters only up to this build (the watcher passes the builds live on the web)")
    args = ap.parse_args()
    upto: dict[str, int] = {}
    for s in args.upto:
        r, _, b = s.partition("=")
        upto[r] = int(b)

    data = json.loads(NOTES.read_text(encoding="utf-8")) if NOTES.exists() else {
        "key": "", "title": "", "ios": "", "android": "", "notes": []}
    covered = dict(data.get("covered", {}))
    for s in args.since:
        r, _, b = s.partition("=")
        covered[r] = int(b) - 1

    latest = {r: newest(r) for r in ROLES}
    for r, (v, p) in list(latest.items()):
        if r in upto and upto[r] < v:
            latest[r] = (upto[r], p)
    added: list[dict] = []
    for role, (v, _) in latest.items():
        start = int(covered.get(role, v))  # first run: nothing new, just the live builds
        fresh = list(range(v, start, -1))
        covered[role] = max(v, int(covered.get(role, 0)))  # --upto never moves it back
        if not fresh:
            print(f"{role}: v{v}, nothing new since v{start}")
            continue
        print(f"{role}: v{start + 1}..v{v} -> notes")
        for vv in fresh:
            n = note_for(role, vv)
            if n:
                added.append(n)
                print(f"  v{vv}: {n['title']!r} -> {n['open'] or 'inbox'!r}")
        covered[role] = v

    if added:
        kept = [n for n in data.get("notes", []) if n.get("build") not in {a["build"] for a in added if a["for"] == n.get("for")}]
        merged = added + kept
        out, count = [], {"couple": 0, "vendor": 0}
        for n in merged:
            who = n.get("for", "both")
            roles = ["couple", "vendor"] if who == "both" else [who]
            if all(count[r] >= KEEP_PER_ROLE for r in roles):
                continue
            for r in roles:
                count[r] += 1
            out.append(n)
        data["notes"] = out
        today = date.today()
        data["key"] = today.isoformat()
        data["title"] = today.strftime("%B %d, %Y").replace(" 0", " ")
    data["covered"] = covered
    data.setdefault("ios", "https://apps.apple.com/us/app/lazo-wedding-planner/id6812863675")
    data.setdefault("android", "https://play.google.com/store/apps/details?id=com.meetlazo.app")

    if args.dry_run:
        print(json.dumps({k: data[k] for k in ("key", "title", "covered")}, indent=2))
        for n in data["notes"]:
            print(f"- [{n['for']}] {n['title']}\n    {n['line1']}\n    {n['line2']}\n    open={n['open']!r}")
        if args.stores:
            print(f"stores -> couple={latest['couple'][0]} vendor={latest['vendor'][0]}")
        return

    NOTES.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    cmd = [sys.executable, str(HERE / "publish_release.py")]
    if args.stores:
        c, v = str(latest["couple"][0]), str(latest["vendor"][0])
        cmd += ["--couple", c, "--vendor", v, "--couple-ios", c, "--couple-android", c,
                "--vendor-ios", v, "--vendor-android", v]
    elif not added:
        print("no new notes and no --stores: nothing to publish")
        return
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
