"""Lazo one-command site deploy - build, verify, sync to R2, purge cache.
Build ID: JC-LAZO-DEPLOY-0825-002

Usage:
  python deploy\\deploy_site.py                 # build + verify + incremental sync (no deletions)
  python deploy\\deploy_site.py --prune         # also delete bucket orphans (dry-run + confirm first)
  python deploy\\deploy_site.py --skip-build    # sync existing dist/ without rebuilding

Pipeline:
  1. Build full site (--tranche 4 = all metros, cumulative).
  2. Assert the "[build] skipped N delisted" receipt matches Firestore's count.
  3. Sanity-gate dist/ file count (floor + drop-vs-last-deploy) before anything destructive.
  4. rclone sync (incremental via --checksum --fast-list; only changed files upload).
     --prune adds --delete-after, ALWAYS preceded by a dry-run + typed confirmation,
     because sync-delete removes ANY bucket key not in dist/ (protects non-dist assets).
  5. Purge Cloudflare cache for sitemaps/homepage/robots if CF_ZONE_ID + CF_API_TOKEN
     are in .env (zone token needs Cache Purge permission); otherwise prints a reminder.

Requires: rclone on PATH (winget install Rclone.Rclone). Reuses the same .env keys
as upload_r2.py: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY.
"""
import argparse, glob, json, os, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUCKET = "lazo-site"
MANIFEST = Path(__file__).resolve().parent / ".last_deploy.json"
FILE_FLOOR = 50000          # abort below this - a broken build must never reach sync
MAX_DROP_PCT = 20           # abort if dist shrank more than this vs last deploy
TRANCHE = "7"               # cumulative: tranche 7 is the whole site - 108 metros.
                            # Was "4" (31 metros), which silently built two thirds of the
                            # site and left the delisted-vendor gate blind to the rest.
                            # Raised to 6 on 2026-09-16 with the gap-pass metros. This MUST
                            # match the --tranche in lazo-nightly.bat or the nightly and a
                            # manual deploy will build different subsets of the site.


def find_rclone():
    """Locate rclone.exe even when the shell's PATH is stale."""
    p = shutil.which("rclone")
    if p:
        return p
    home = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(home, "Microsoft", "WinGet", "Links", "rclone.exe"),
        *glob.glob(os.path.join(home, "Microsoft", "WinGet", "Packages",
                                "Rclone.Rclone*", "**", "rclone.exe"), recursive=True),
        r"C:\Program Files\rclone\rclone.exe",
        r"C:\rclone\rclone.exe",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    die("rclone.exe not found - install with: winget install Rclone.Rclone, then reopen PowerShell")


RCLONE = None  # resolved lazily in main()

sys.path.insert(0, str(ROOT))
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def die(msg):
    print(f"\nSTOP: {msg}")
    sys.exit(1)


def run_build():
    print(f"== 1/5 build (--tranche {TRANCHE}) ==")
    r = subprocess.run([sys.executable, str(ROOT / "generate" / "build.py"), "--tranche", TRANCHE],
                       capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    if r.returncode != 0:
        die("build failed")
    m = re.search(r"\[build\] skipped (\d+) delisted", r.stdout)
    return int(m.group(1)) if m else 0


def firestore_delisted_count():
    import firebase_admin
    from firebase_admin import credentials, firestore
    from config.metros import metros_for_tranche
    cred = credentials.Certificate(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    ids = {m["id"] for m in metros_for_tranche(int(TRANCHE))}
    docs = db.collection("vendors").where("delisted", "==", True).stream()
    return sum(1 for d in docs if d.to_dict().get("metroId") in ids)


def sanity_gate():
    print("== 3/5 sanity gate ==")
    count = sum(1 for p in DIST.rglob("*") if p.is_file())
    print(f"  dist/ holds {count:,} files")
    if count < FILE_FLOOR:
        die(f"dist has {count:,} files, below floor {FILE_FLOOR:,} - refusing to sync a broken build")
    if MANIFEST.exists():
        last = json.loads(MANIFEST.read_text()).get("files", 0)
        if last and count < last * (1 - MAX_DROP_PCT / 100):
            die(f"dist shrank {last:,} -> {count:,} (>{MAX_DROP_PCT}%) - investigate before deploying")
    return count


def rclone_env():
    env = os.environ.copy()
    acct = env.get("R2_ACCOUNT_ID") or die("R2_ACCOUNT_ID missing from .env")
    env.update({
        "RCLONE_CONFIG_R2_TYPE": "s3",
        "RCLONE_CONFIG_R2_PROVIDER": "Cloudflare",
        "RCLONE_CONFIG_R2_ACCESS_KEY_ID": env.get("R2_ACCESS_KEY_ID", ""),
        "RCLONE_CONFIG_R2_SECRET_ACCESS_KEY": env.get("R2_SECRET_ACCESS_KEY", ""),
        "RCLONE_CONFIG_R2_ENDPOINT": f"https://{acct}.r2.cloudflarestorage.com",
        "RCLONE_CONFIG_R2_NO_CHECK_BUCKET": "true",
    })
    return env


def rclone(args, env):
    cmd = [RCLONE] + args
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return r


def sync(prune: bool):
    env = rclone_env()
    base = ["sync", str(DIST), f"r2:{BUCKET}",
            "--checksum", "--fast-list", "--transfers", "16", "--checkers", "16",
            "--stats-one-line", "--stats", "30s"]
    # -v logged every one of 87,805 transfers and made the 2026-09-16 nightly log
    # 10 MB, burying the four lines that matter. Stats still report progress.
    if os.environ.get("LAZO_RCLONE_VERBOSE"):
        base.append("-v")
    # Non-build content living in the bucket: never delete, never touch.
    # pro/ = checkout, chimes = widget audio.
    # JC-LAZO-INBOX-0916-003: _inbox/ and signups/ are WRITTEN BY THE WORKER and so
    # are never in dist/. Without these two lines a --prune deletes every contact
    # message and every early-access signup the site has ever received, silently,
    # because that is exactly what "delete any bucket key not in dist/" means.
    # JC-LAZO-WWSEO-0920-001: wedding-websites/ is no longer excluded. build.py now copies
    # it into dist (source of truth: lazo-directory/wedding-websites/), and the old
    # unanchored "wedding-websites/**" also matched every {metro}/wedding-websites/
    # page, which is why the 2026-09-20 nightly built 83 metro pages and shipped none.
    for _pfx in ("pro/**", "assets/chime-*.mp3", "badges/**", ".well-known/**", "seating/**", "showcase/**", "nearby/**", "_inbox/**", "signups/**"):
        base += ["--exclude", _pfx]
    if prune:
        print("== 4/5 sync (PRUNE dry-run first) ==")
        dr = rclone(base + ["--delete-after", "--dry-run"], env)
        deletes = [ln for ln in (dr.stdout + dr.stderr).splitlines() if "Skipped delete" in ln or "delete" in ln.lower() and "NOTICE" in ln]
        print(f"  dry-run reports {len(deletes)} deletion(s)")
        for ln in deletes[:20]:
            print("   ", ln.strip())
        if len(deletes) > 20:
            print(f"    ... and {len(deletes) - 20} more")
        if deletes:
            print("\n  These bucket keys are NOT in dist/ and will be DELETED.")
            print("  If any are non-site assets (photos, worker-written files), answer no and")
            print("  we exclude their prefixes before ever pruning.")
            if input("  Type YES to delete them: ").strip() != "YES":
                die("prune declined - run again without --prune, or exclude prefixes first")
        r = subprocess.run([RCLONE] + base + ["--delete-after"], env=env)
    else:
        print("== 4/5 sync (incremental, no deletions) ==")
        r = subprocess.run([RCLONE] + base, env=env)
    if r.returncode != 0:
        die("rclone sync failed")


def indexnow():
    """JC-LAZO-SEO-0921-001: tell IndexNow (Bing, Yandex, DuckDuckGo, Naver) which
    URLs changed today, straight after the sync. Non-fatal; Google ignores it."""
    print("== 6/6 IndexNow ==")
    import datetime as _dt, subprocess as _sp
    try:
        r = _sp.run([sys.executable, str(ROOT / "deploy" / "indexnow.py"), "--since",
                     _dt.date.today().isoformat()], capture_output=True, text=True, timeout=600)
        print((r.stdout or "").strip()[-1500:])
        if r.returncode:
            print("  indexnow failed (non-fatal):", (r.stderr or "").strip()[-400:])
    except Exception as e:  # noqa: BLE001
        print("  indexnow skipped (non-fatal):", e)


def purge():
    print("== 5/6 cache purge ==")
    zone, token = os.environ.get("CF_ZONE_ID"), os.environ.get("CF_API_TOKEN")
    urls = ["https://meetlazo.com/", "https://meetlazo.com/robots.txt",
            "https://meetlazo.com/sitemap.xml", "https://meetlazo.com/llms.txt"]
    urls += [f"https://meetlazo.com/{p.name}" for p in DIST.glob("sitemap-*.xml")]
    if not (zone and token):
        print("  CF_ZONE_ID / CF_API_TOKEN not in .env - purge these by hand in the dash:")
        for u in urls:
            print("   ", u)
        return
    import urllib.request
    for i in range(0, len(urls), 30):  # 30 URLs per purge request
        body = json.dumps({"files": urls[i:i + 30]}).encode()
        req = urllib.request.Request(
            f"https://api.cloudflare.com/client/v4/zones/{zone}/purge_cache",
            data=body, method="POST",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        # JC-LAZO-PURGE-0916-001: a timeout, and a purge failure must never take the
        # deploy down with it. urlopen() with no timeout blocks forever, which in an
        # unattended nightly means hanging until the task's 6h limit - worse than
        # simply not purging. The files are already in R2 by this point; the edge
        # TTL (1h) will catch up on its own.
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                ok = json.loads(resp.read()).get("success")
                print(f"  purged {len(urls[i:i+30])} url(s): {'ok' if ok else 'FAILED'}")
        except Exception as e:
            print(f"  purge of {len(urls[i:i+30])} url(s) failed: {type(e).__name__}: {e}")
            print("  (deploy is complete; these will clear on the 1h edge TTL)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prune", action="store_true", help="delete bucket orphans (dry-run + confirm)")
    ap.add_argument("--skip-build", action="store_true")
    a = ap.parse_args()

    global RCLONE
    RCLONE = find_rclone()
    print(f"rclone: {RCLONE}")

    if a.skip_build:
        skipped = None
        print("== 1/5 build: skipped (--skip-build) ==")
    else:
        skipped = run_build()

    print("== 2/5 delist receipt ==")
    if skipped is None:
        print("  (no build this run - receipt not checked)")
    else:
        try:
            expected = firestore_delisted_count()
            print(f"  build skipped {skipped}, Firestore says {expected} delisted in scope")
            if skipped != expected:
                die("delist receipt mismatch - the build did not exclude what Firestore says is delisted")
        except Exception as e:
            print(f"  receipt check unavailable ({e}) - continuing on build output alone: skipped {skipped}")

    files = sanity_gate()
    sync(a.prune)
    purge()
    indexnow()
    MANIFEST.write_text(json.dumps({"files": files}))
    print(f"\nDeploy complete. {files:,} files - manifest updated.")


if __name__ == "__main__":
    main()
