"""Watches for a new Lazo release and publishes the notice by itself (JC-LAZO-RELEASE-1020).

Runs every hour from the "Lazo release watch" scheduled task (C:\\Users\\kurvh\\lazo-release-watch.bat).
No prompts, no Claude: plain Python against public endpoints and the admin SDK.

What it watches
  * The web app, https://app.meetlazo.com: version.json and the build markers the
    dashboards keep in main.dart.js (kBuildId: ...-C180 for Couple, ...-222 for
    Vendor). A higher build than last time = a new web release is live ->
    `release.py --upto couple=C vendor=V` publishes the notes for the masters up
    to the builds that are actually live.
  * The App Store (itunes lookup) and Google Play (store page): a changed version
    string = a new store release is live -> the store build for that platform is
    set to the web build live at that moment (FlutterFlow ships web and mobile
    from the same project state), so phones behind it get the Update popup.
    Override any time with `release.py --stores` or publish_release.py flags.

State lives in release_watch_state.json next to this file; output in release_watch.log.
    python release_watch.py            # one pass
    python release_watch.py --status   # print the state
    python release_watch.py --dry-run  # look, decide, publish nothing
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE = HERE / "release_watch_state.json"
WEB = "https://app.meetlazo.com"
ITUNES = "https://itunes.apple.com/lookup?id=6812863675"
PLAY = "https://play.google.com/store/apps/details?id=com.meetlazo.app&hl=en&gl=US"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LazoReleaseWatch/1.0"

COUPLE_MARK = re.compile(r"JC-LAZO-[A-Z0-9]+-\d{4}-C(\d+)\b")
VENDOR_MARK = re.compile(r"JC-LAZO-[A-Z0-9]+-\d{4}-(\d+)\b")


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {msg}", flush=True)


def get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_web() -> dict:
    bust = f"?lrw={int(time.time())}"
    out: dict = {"seen": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        vj = json.loads(get(f"{WEB}/version.json{bust}").decode("utf-8", "replace"))
        out["version"] = str(vj.get("version", ""))
        out["build_number"] = str(vj.get("build_number", ""))
    except Exception as e:  # noqa: BLE001
        log(f"web version.json: {e}")
    try:
        js = get(f"{WEB}/main.dart.js{bust}", timeout=180).decode("utf-8", "replace")
        couples = [int(m) for m in COUPLE_MARK.findall(js)]
        vendors = [int(m) for m in VENDOR_MARK.findall(js)]
        if couples:
            out["couple"] = max(couples)
        if vendors:
            out["vendor"] = max(vendors)
        out["js_bytes"] = len(js)
    except Exception as e:  # noqa: BLE001
        log(f"web main.dart.js: {e}")
    return out


def fetch_ios() -> dict:
    try:
        r = json.loads(get(ITUNES).decode("utf-8", "replace")).get("results") or []
        if r:
            return {"version": str(r[0].get("version", "")),
                    "released": str(r[0].get("currentVersionReleaseDate", ""))}
    except Exception as e:  # noqa: BLE001
        log(f"itunes: {e}")
    return {}


def fetch_android() -> dict:
    try:
        html = get(PLAY).decode("utf-8", "replace")
        m = re.search(r'\[\[\["(\d+(?:\.\d+)+)"\]\]', html)
        if m:
            return {"version": m.group(1)}
        log("play: version string not found on the page")
    except Exception as e:  # noqa: BLE001
        log(f"play: {e}")
    return {}


def run(cmd: list[str], dry: bool) -> bool:
    log(("would run: " if dry else "run: ") + " ".join(cmd[1:]))
    if dry:
        return True
    p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    for line in (p.stdout + p.stderr).strip().splitlines():
        log("  " + line)
    if p.returncode != 0:
        log(f"  exit {p.returncode}")
    return p.returncode == 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    py = sys.executable

    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    if args.status:
        print(json.dumps(state, indent=2))
        return

    web = fetch_web()
    ios = fetch_ios()
    android = fetch_android()
    prev_web = state.get("web", {})
    log(f"web couple={web.get('couple')} vendor={web.get('vendor')} v{web.get('version')} "
        f"| ios {ios.get('version')} | android {android.get('version')}")

    # 1. a newer web build is live -> notes for the masters up to it
    newer = {r: web[r] for r in ("couple", "vendor")
             if r in web and web[r] > int(prev_web.get(r) or 0)}
    if newer:
        log("new web build: " + ", ".join(f"{r} v{prev_web.get(r) or '?'} -> v{v}" for r, v in newer.items()))
        upto = [f"{r}={web[r]}" for r in ("couple", "vendor") if r in web]
        if run([py, str(HERE / "release.py"), "--upto", *upto], args.dry_run):
            for r in newer:
                prev_web[r] = web[r]
        # a failed run leaves the old build in state, so the next hour retries
    for k in ("version", "build_number", "seen", "js_bytes"):
        if k in web:
            prev_web[k] = web[k]
    state["web"] = prev_web

    # 2. a new store version is live -> that platform's store build = the live web build
    for plat, cur, key_c, key_v in (("ios", ios, "--couple-ios", "--vendor-ios"),
                                    ("android", android, "--couple-android", "--vendor-android")):
        if not cur.get("version"):
            continue
        old = state.get(plat, {})
        if not old.get("version"):
            log(f"{plat}: first sight of {cur['version']}, recorded")
            state[plat] = cur
            continue
        if cur["version"] == old["version"]:
            continue
        log(f"{plat}: {old['version']} -> {cur['version']} is live")
        flags: list[str] = []
        if "couple" in web:
            flags += [key_c, str(web["couple"])]
        if "vendor" in web:
            flags += [key_v, str(web["vendor"])]
        if not flags:
            log(f"{plat}: web builds unknown (no markers in main.dart.js), store builds left alone")
            state[plat] = cur
            continue
        if run([py, str(HERE / "publish_release.py"), "--notes-only", *flags], args.dry_run):
            cur["builds"] = {"couple": web.get("couple"), "vendor": web.get("vendor")}
            state[plat] = cur
        # failed -> state keeps the old version, retried next hour

    state["lastRun"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not args.dry_run:
        STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
