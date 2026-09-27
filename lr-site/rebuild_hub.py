# rebuild_hub.py — rebuilds community/index.html (the Browse Communities
# hub) from algolia_communities_backup.json, with every link verified
# against the page files actually on disk. Needs NO Google access.
#
# Run from the marketing site folder:
#   python rebuild_hub.py
# then: python repair_sitemap.py && wrangler deploy as usual.

import importlib.util
import json
import os
import sys

base = os.path.dirname(os.path.abspath(__file__))

# Reuse the generator's own hub renderer so styling stays identical.
spec = importlib.util.spec_from_file_location(
    "gen", os.path.join(base, "generate_community_pages.py"))
gen = importlib.util.module_from_spec(spec)
sys.modules["gen"] = gen
spec.loader.exec_module(gen)  # safe: generation only runs under __main__

# Find the Algolia backup (site folder or the lease-reputation folder)
CANDIDATES = [
    os.path.join(base, "algolia_communities_backup.json"),
    r"C:\Users\kurvh\lease-reputation\algolia_communities_backup.json",
]
backup_path = next((p for p in CANDIDATES if os.path.exists(p)), None)
if backup_path is None:
    print("! algolia_communities_backup.json not found — put it in this")
    print("  folder or C:\\Users\\kurvh\\lease-reputation and rerun.")
    sys.exit(1)

records = json.load(open(backup_path, encoding="utf-8"))
print(f"backup loaded: {len(records)} communities ({backup_path})")

comm_dir = os.path.join(base, "community")
entries, skipped_parse, skipped_nopage = [], 0, 0
for r in records:
    e = gen.synthesize_entry(r.get("objectID", ""), {
        "name": r.get("name", ""), "address": r.get("address", "")})
    if e is None:
        skipped_parse += 1
        continue
    # Link only to pages that actually exist on disk (collision suffixes
    # from the original generation are probed in order).
    found = None
    stem = gen.slugify(e["name"], e["city"])
    for cand in [stem] + [f"{stem}-{i}" for i in range(2, 5)]:
        if os.path.exists(os.path.join(comm_dir, cand + ".html")):
            found = cand
            break
    if found is None:
        skipped_nopage += 1
        continue
    e["_slug"] = found
    entries.append(e)

# De-dupe entries that resolved to the same page file (collision pairs both
# probing to the same base slug would double-list it).
seen, unique = set(), []
for e in entries:
    if e["_slug"] in seen:
        continue
    seen.add(e["_slug"])
    unique.append(e)

print(f"hub entries: {len(unique)} "
      f"(skipped {skipped_parse} unparseable, {skipped_nopage} without pages "
      f"— those get pages at the next full generation)")

with open(os.path.join(comm_dir, "index.html"), "w", encoding="utf-8") as f:
    f.write(gen.hub_page(unique))
print("community/index.html rebuilt.")
print("\nNext: python repair_sitemap.py")
print("Then: wrangler pages deploy . --project-name=leasereputation")
