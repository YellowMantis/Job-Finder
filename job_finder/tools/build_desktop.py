"""Package the job finder as a desktop app that runs without Python, Node or Git.

    python job_finder/tools/build_desktop.py

Steps: build the page (npm), draw the icon, run PyInstaller, then package the
result the usual way for the system it runs on (PyInstaller can only build for
the system it runs on, so the release job runs this on Windows, Mac and Linux):

  Windows  job_finder/build/Job-Finder-Setup.exe   an installer (Inno Setup, tools/installer.iss)
  macOS    job_finder/build/Job-Finder-mac.dmg     drag "Job Finder" into Applications
  Linux    job_finder/build/Job-Finder-linux.tar.gz  unpack, run "Job Finder"

PyInstaller copies Python itself, our code and every package it imports into
one folder. A folder ("onedir") rather than a single .exe: a single .exe must
unpack itself to a temporary folder on every start, which is slower and more
often mistaken for malware by antivirus programs.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

JOB_FINDER = Path(__file__).parent.parent
sys.path.insert(0, str(JOB_FINDER))
from version import VERSION  # noqa: E402

FRONTEND = JOB_FINDER / "frontend"
BUILD = JOB_FINDER / "build"
NAME = "Job Finder"
SEPARATOR = ";" if sys.platform == "win32" else ":"  # PyInstaller's "source;destination"


def build_page():
    npm = shutil.which("npm")
    subprocess.run([npm, "ci"], cwd=FRONTEND, check=True)
    subprocess.run([npm, "run", "build"], cwd=FRONTEND, check=True)


def draw_icon(path):
    """The briefcase from the page's tab icon, in the app's blue, at several sizes."""
    size = 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    blue, light = (31, 95, 168, 255), (232, 240, 250, 255)
    draw.rounded_rectangle((88, 40, 168, 96), radius=18, outline=blue, width=18)  # handle
    draw.rounded_rectangle((24, 72, 232, 216), radius=32, fill=blue)              # case
    draw.rectangle((24, 120, 232, 136), fill=light)                              # band
    image.save(path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


def package(icon):
    def data(source, destination):
        return ["--add-data", f"{source}{SEPARATOR}{destination}"]

    subprocess.run([
        sys.executable, "-m", "PyInstaller", str(JOB_FINDER / "desktop.py"),
        "--name", NAME, "--windowed", "--onedir", "--noconfirm", "--clean",
        "--icon", str(icon),
        "--distpath", str(BUILD), "--workpath", str(BUILD / "work"), "--specpath", str(BUILD),
        "--paths", str(JOB_FINDER), "--paths", str(JOB_FINDER / "src"),
        # Files the code reads next to itself (see WEB_DIR in app.py and places.py).
        *data(FRONTEND / "dist", "frontend/dist"),
        *data(JOB_FINDER / "src" / "places_il.json", "."),
        # The password safe backends are found at run time, so PyInstaller can't see them.
        "--collect-submodules", "keyring.backends",
        # A browser-automation tool used only for checking the page while developing.
        "--exclude-module", "playwright",
    ], check=True)


def inno_setup():
    """The Inno Setup compiler: on GitHub's Windows machines, or installed per user."""
    for candidate in [shutil.which("iscc"),
                      Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Inno Setup 6/ISCC.exe",
                      Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6/ISCC.exe"]:
        if candidate and Path(candidate).exists():
            return str(candidate)
    sys.exit("Inno Setup 6 is needed to build the Windows installer: https://jrsoftware.org")


def windows_installer():
    subprocess.run([inno_setup(), f"/DAppVersion={VERSION}", f"/DSourceDir={BUILD / NAME}",
                    f"/DOutputDir={BUILD}", str(Path(__file__).parent / "installer.iss")],
                   check=True)
    return BUILD / "Job-Finder-Setup.exe"


def mac_disk_image():
    image = BUILD / "Job-Finder-mac.dmg"
    image.unlink(missing_ok=True)
    subprocess.run(["hdiutil", "create", "-volname", NAME, "-srcfolder", str(BUILD / f"{NAME}.app"),
                    "-ov", "-format", "UDZO", str(image)], check=True)
    return image


def linux_archive():
    return Path(shutil.make_archive(str(BUILD / "Job-Finder-linux"), "gztar", BUILD, NAME))


def main():
    BUILD.mkdir(exist_ok=True)
    build_page()
    icon = BUILD / "icon.ico"
    draw_icon(icon)
    package(icon)
    if sys.platform == "win32":
        result = windows_installer()
    elif sys.platform == "darwin":
        result = mac_disk_image()
    else:
        result = linux_archive()
    print(f"\nJob Finder {VERSION}, ready to share: {result}")


if __name__ == "__main__":
    main()
