"""Get (or refresh) the company and job data from the techmap project.

Two ways, depending on what this computer has:

  with Git   the data is a Git repository, so Git fetches it: only the two
             folders we need, and on later runs only what changed. Fast.
  without    GitHub's zip of the whole project (about 38 MB, mostly company
             logos we skip) is downloaded and only the data is unpacked.
             Most people don't have Git, so the desktop app relies on this.
"""

import io
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import httpx

from settings import NO_WINDOW, TECHMAP_DIR, TECHMAP_URL

TECHMAP_ZIP_URL = "https://codeload.github.com/mluggy/techmap/zip/refs/heads/main"
NEEDED_FOLDERS = ("companies", "jobs")  # plus the files at the top (categories.json...)


def download_data():
    """Download the data on the first run, update it on later runs."""
    if shutil.which("git"):
        _with_git()
    else:
        _with_zip()


def _git(*arguments):
    subprocess.run(["git", *arguments], check=True, creationflags=NO_WINDOW)


def _with_git():
    if (TECHMAP_DIR / ".git").exists():
        # Fetch only the newest snapshot, then switch the folder to it. (A plain
        # "git pull" fails here: with --depth 1 we never downloaded the history
        # that would connect the old snapshot to the new one.) The folder only
        # holds downloaded data, so replacing its contents loses nothing.
        _git("-C", str(TECHMAP_DIR), "fetch", "--quiet", "--depth", "1", "origin", "main")
        _git("-C", str(TECHMAP_DIR), "reset", "--quiet", "--hard", "FETCH_HEAD")
        return
    if TECHMAP_DIR.exists():
        shutil.rmtree(TECHMAP_DIR)  # an earlier zip download: Git takes over from here

    TECHMAP_DIR.parent.mkdir(parents=True, exist_ok=True)
    # --depth 1: only the latest version, not the whole history.
    # --sparse + sparse-checkout: only the two folders we need (skips the logos).
    _git("clone", "--quiet", "--depth", "1", "--filter=blob:none", "--sparse",
         TECHMAP_URL, str(TECHMAP_DIR))
    _git("-C", str(TECHMAP_DIR), "sparse-checkout", "set", *NEEDED_FOLDERS)


def _with_zip():
    response = httpx.get(TECHMAP_ZIP_URL, follow_redirects=True, timeout=300)
    response.raise_for_status()
    archive = zipfile.ZipFile(io.BytesIO(response.content))

    # Unpack into a new folder first, and swap it in only when complete, so a
    # failed download never leaves half the data behind.
    TECHMAP_DIR.parent.mkdir(parents=True, exist_ok=True)
    fresh = Path(tempfile.mkdtemp(dir=TECHMAP_DIR.parent, prefix="techmap-new-"))
    for entry in archive.infolist():
        # Entries look like "techmap-main/companies/510001886.json".
        parts = entry.filename.split("/", 1)
        if len(parts) < 2 or entry.is_dir() or not _wanted(parts[1]):
            continue
        target = (fresh / parts[1]).resolve()
        if not target.is_relative_to(fresh.resolve()):
            continue  # a path trying to escape the folder ("../..."): never written
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(entry))

    if TECHMAP_DIR.exists():
        shutil.rmtree(TECHMAP_DIR)
    fresh.rename(TECHMAP_DIR)


def _wanted(path):
    """The data we use: the two folders, and files at the top such as categories.json."""
    return path.split("/", 1)[0] in NEEDED_FOLDERS or "/" not in path
