"""Refuse to rewrite dist/ while a sync is reading it.  JC-LAZO-DISTLOCK-0917-001

bump_assets.py has carried this check since it was written. render_pages.py and
swap_footer.py did not, which is how, on 2026-09-17, a footer swap rewrote 108,614
files underneath a deploy that was already twenty minutes into uploading them.
rclone hashes a file, uploads it, then verifies; bytes that change mid-flight give
"corrupted on transfer", and the site ends up carrying a mix of the old and new
render until someone syncs again.

Nothing is lost when this happens - the sync does not delete, and a clean re-sync
corrects it - but the window where the site is internally inconsistent is real, and
it is entirely avoidable. Every script that writes into dist/ should call guard()
first.

    from distlock import guard
    guard()                    # exits with an explanation if rclone is live
    guard(force="--force" in sys.argv)
"""
import subprocess
import sys

MESSAGE = (
    "rclone is running - refusing to rewrite dist/ underneath it.\n"
    "  A sync hashes each file, uploads it, then verifies; changing the bytes\n"
    "  mid-flight gives 'corrupted on transfer' and leaves the site carrying a\n"
    "  mix of the old and new render.\n"
    "  Wait for the sync to finish, then re-run. (--force overrides.)"
)


def sync_running() -> bool:
    """True if an rclone process is live."""
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq rclone.exe", "/NH"],
                             capture_output=True, text=True, timeout=20).stdout
        return "rclone.exe" in out
    except Exception:
        return False        # cannot tell - do not block the user


def guard(force: bool = False) -> None:
    """Exit unless it is safe to write into dist/."""
    if force:
        return
    if sync_running():
        sys.exit(MESSAGE)
