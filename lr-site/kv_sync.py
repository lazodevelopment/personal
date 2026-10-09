#!/usr/bin/env python3
"""kv_sync.py - push the LeaseReputation site into Cloudflare KV.

Replaces `wrangler pages deploy`, which is hard-capped at 20,000 files on the
direct-upload path regardless of plan (workers-sdk #12394). KV has no such
ceiling.

Incremental by content hash: a nightly run that changes 40 community pages
writes 40 keys, not 19,469. That matters because KV writes are metered and a
full rewrite every night would burn ~584K writes a month for no reason.

  python kv_sync.py --dry-run          # show what would change, touch nothing
  python kv_sync.py                    # sync
  python kv_sync.py --full             # ignore manifest, rewrite everything
"""
import os, sys, json, time, hashlib, base64, pathlib, argparse, subprocess, shutil

SITE = pathlib.Path(os.environ.get(
    "LR_SITE", r"C:\Users\kurvh\lr-site"))
MANIFEST = pathlib.Path(__file__).resolve().parent / "kv_manifest.json"
BINDING_NS = os.environ.get("LR_KV_NAMESPACE_ID", "")   # set in wrangler.toml too

# Never ship these. Generator sources, caches, backups, editor droppings.
SKIP_DIRS = {"__pycache__", ".git", ".wrangler", "_src", "node_modules", ".vscode"}
SKIP_EXT = {".py", ".pyc", ".pyo", ".bak", ".log", ".tmp", ".swp"}
SKIP_NAMES = {"kv_manifest.json", "wrangler.toml", "worker.js", "track.js", ".DS_Store",
              "kv_sync.py", ".gitignore"}
TEXT_EXT = {".html", ".htm", ".css", ".js", ".json", ".xml", ".txt", ".svg", ".webmanifest"}

# The KV bulk API caps a request at 10,000 pairs AND 100 MB of body. Pair count
# alone is not a safe bound: LeaseReputation pages average 22 KB, so 4,000 pairs
# is ~88 MB, and a batch of above-average pages would exceed the byte limit.
# Batch on both, whichever trips first. The byte cap is deliberately
# conservative - base64 inflates binaries ~33% and JSON escaping adds more.
BATCH = 2000                     # max key-value pairs per bulk call
BATCH_BYTES = 40 * 1024 * 1024   # max raw bytes per bulk call


def skip(p: pathlib.Path) -> bool:
    if any(part in SKIP_DIRS for part in p.parts):
        return True
    if p.name in SKIP_NAMES:
        return True
    if p.suffix.lower() in SKIP_EXT:
        return True
    if ".bak-" in p.name or p.name.endswith("~"):
        return True
    return False


def key_for(path: pathlib.Path, root: pathlib.Path) -> str:
    """KV key mirrors the on-disk relative path with forward slashes.

    Keeping the mapping this dumb is deliberate: the Worker can then reproduce
    it from a URL without consulting an index, and anyone debugging a missing
    page can find the key by looking at the file tree."""
    return path.relative_to(root).as_posix()


def scan(root: pathlib.Path):
    """-> {key: (sha256, size, is_binary, abspath)}"""
    out = {}
    for p in root.rglob("*"):
        if not p.is_file() or skip(p):
            continue
        data = p.read_bytes()
        out[key_for(p, root)] = (
            hashlib.sha256(data).hexdigest(),
            len(data),
            p.suffix.lower() not in TEXT_EXT,
            p)
    return out


def wrangler(args, check=True):
    exe = shutil.which("wrangler") or shutil.which("wrangler.cmd")
    if not exe:
        raise SystemExit("wrangler not found on PATH. npm i -g wrangler")
    r = subprocess.run([exe] + args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        sys.stderr.write((r.stdout or "") + "\n" + (r.stderr or "") + "\n")
        raise SystemExit("wrangler failed: " + " ".join(args[:4]))
    return r


def batches(pairs):
    """Split on pair count or accumulated bytes, whichever trips first."""
    cur, cur_bytes = [], 0
    for item in pairs:
        sz = item[1].stat().st_size
        if cur and (len(cur) >= BATCH or cur_bytes + sz > BATCH_BYTES):
            yield cur
            cur, cur_bytes = [], 0
        cur.append(item)
        cur_bytes += sz
    if cur:
        yield cur


def bulk_put(pairs, ns_id, tmpdir, label):
    """pairs -> [(key, abspath, is_binary)]"""
    chunks = list(batches(pairs))
    for n, chunk in enumerate(chunks, 1):
        payload = []
        for k, p, is_bin in chunk:
            raw = p.read_bytes()
            if is_bin:
                payload.append({"key": k,
                                "value": base64.b64encode(raw).decode("ascii"),
                                "base64": True})
            else:
                payload.append({"key": k, "value": raw.decode("utf-8", "replace")})
        f = tmpdir / ("bulk_%s_%d.json" % (label, n))
        f.write_text(json.dumps(payload), encoding="utf-8")
        mb = f.stat().st_size / 1e6
        print("  uploading %s batch %d/%d (%d keys, %.1f MB)"
              % (label, n, len(chunks), len(payload), mb), flush=True)
        if mb > 95:
            raise SystemExit("batch %d is %.1f MB, over the 100 MB API limit - "
                             "lower BATCH_BYTES in kv_sync.py" % (n, mb))
        wrangler(["kv", "bulk", "put", str(f), "--namespace-id", ns_id, "--remote"])
        f.unlink(missing_ok=True)


def bulk_delete(keys, ns_id, tmpdir):
    for i in range(0, len(keys), BATCH):
        chunk = keys[i:i + BATCH]
        f = tmpdir / ("del_%d.json" % (i // BATCH))
        f.write_text(json.dumps(chunk), encoding="utf-8")
        print("  deleting batch %d (%d keys)" % (i // BATCH + 1, len(chunk)), flush=True)
        wrangler(["kv", "bulk", "delete", str(f), "--namespace-id", ns_id,
                  "--remote", "--force"])
        f.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=str(SITE))
    ap.add_argument("--namespace-id", default=BINDING_NS)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--full", action="store_true", help="ignore manifest, rewrite all")
    a = ap.parse_args()

    root = pathlib.Path(a.site)
    if not root.is_dir():
        raise SystemExit("site folder not found: %s" % root)
    if not a.namespace_id and not a.dry_run:
        raise SystemExit("No KV namespace id. Pass --namespace-id or set LR_KV_NAMESPACE_ID.")

    t0 = time.time()
    print("scanning %s" % root, flush=True)
    now = scan(root)
    print("  %d files to serve (%.1f MB)"
          % (len(now), sum(v[1] for v in now.values()) / 1e6))

    old = {}
    if MANIFEST.exists() and not a.full:
        try:
            old = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except Exception:
            print("  ! manifest unreadable, treating as full sync")

    changed = [k for k, v in now.items() if old.get(k) != v[0]]
    removed = [k for k in old if k not in now]
    print("  %d new/changed, %d removed, %d unchanged"
          % (len(changed), len(removed), len(now) - len(changed)))

    if a.dry_run:
        for k in changed[:15]:
            print("    + %s" % k)
        if len(changed) > 15:
            print("    ... and %d more" % (len(changed) - 15))
        for k in removed[:10]:
            print("    - %s" % k)
        print("dry run, nothing written")
        return

    if not changed and not removed:
        print("nothing to do")
        return

    tmp = pathlib.Path(__file__).resolve().parent / "_kvtmp"
    tmp.mkdir(exist_ok=True)
    try:
        if changed:
            text = [(k, now[k][3], False) for k in changed if not now[k][2]]
            binary = [(k, now[k][3], True) for k in changed if now[k][2]]
            if text:
                bulk_put(text, a.namespace_id, tmp, "text")
            if binary:
                bulk_put(binary, a.namespace_id, tmp, "binary")
        if removed:
            bulk_delete(removed, a.namespace_id, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # Manifest is written only after every batch succeeded. A crash mid-run
    # leaves the old manifest, so the next run retries the same work rather
    # than assuming keys landed that never did.
    MANIFEST.write_text(json.dumps({k: v[0] for k, v in now.items()}, indent=0),
                        encoding="utf-8")
    print("synced %d keys in %.1fs" % (len(changed) + len(removed), time.time() - t0))


if __name__ == "__main__":
    main()
