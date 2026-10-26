"""Is there a newer version of the app?

GitHub knows: the latest Release of the project, with its version tag, its
notes and its files. The app asks once when it starts (the same public
information as the Releases page), and the page offers the update; it is
never installed without you choosing to.

While the project's repository is private, GitHub answers "not found", which
simply means "no update information": nothing is shown and nothing breaks.
"""

import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path

import httpx

from settings import NO_WINDOW, UPDATES_REPOSITORY

LATEST_RELEASE_URL = f"https://api.github.com/repos/{UPDATES_REPOSITORY}/releases/latest"
INSTALLER_NAME = "Job-Finder-Setup.exe"


def version_tuple(version):
    """"v1.10.2" -> (1, 10, 2), so versions compare as numbers, not as text
    (as text, "1.10" would come before "1.9")."""
    return tuple(int(part) for part in version.lstrip("v").split(".") if part.isdigit())


def check(current):
    """The newer release, or None: {"version", "notes", "page", "installer"}.
    None also when GitHub can't be reached or doesn't answer."""
    try:
        response = httpx.get(LATEST_RELEASE_URL, timeout=10,
                             headers={"Accept": "application/vnd.github+json"})
        if response.status_code != 200:
            return None
        release = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    latest = release.get("tag_name", "")
    if not latest or version_tuple(latest) <= version_tuple(current):
        return None
    installer = next((asset["browser_download_url"] for asset in release.get("assets", [])
                      if asset.get("name") == INSTALLER_NAME), "")
    return {"version": latest.lstrip("v"), "notes": (release.get("body") or "")[:4000],
            "page": release.get("html_url", ""), "installer": installer}


def install(update):
    """Start updating. On Windows: download the new installer and open it (the
    app then closes, so the installer can replace it). Elsewhere: open the
    Release page to download it. Returns whether the app should close now."""
    if sys.platform != "win32" or not update.get("installer"):
        webbrowser.open(update["page"])
        return False
    # Only GitHub's own download address is accepted for something we run.
    if not update["installer"].startswith(f"https://github.com/{UPDATES_REPOSITORY}/releases/"):
        raise ValueError("The installer's address isn't this project's GitHub Releases.")
    response = httpx.get(update["installer"], follow_redirects=True, timeout=300)
    response.raise_for_status()
    installer = Path(tempfile.mkdtemp()) / INSTALLER_NAME
    installer.write_bytes(response.content)
    # A quiet update: only a progress bar, no questions (it's an update you
    # already chose), and Job Finder opens again by itself when it's done
    # (tools/installer.iss). /CLOSEAPPLICATIONS closes anything still using the
    # app's files.
    subprocess.Popen([str(installer), "/SILENT", "/SUPPRESSMSGBOXES", "/CLOSEAPPLICATIONS"],
                     creationflags=NO_WINDOW)
    return True
