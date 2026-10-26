"""The job finder as a desktop app: its own window, no browser tab, no terminal.

    python job_finder/desktop.py        (from the source code)
    Job Finder.exe                      (the packaged app; see tools/build_desktop.py)

It starts the same back end as app.py, on a free port of this computer only,
and shows the same page in a window of its own (pywebview, which uses the
Edge WebView2 component built into Windows). Closing the window ends the app.

The installed app runs once at a time: opening it again while it's open only
says so. The installer looks for the same marker (MUTEX_NAME, see
tools/installer.iss) before replacing the app's files, which Windows keeps
locked while the app runs.
"""

import ctypes
import os
import socket
import sys
import threading
import time

import webview

from app import app, start_up


# A name Windows keeps while the installed app runs. It must match
# tools/installer.iss.
MUTEX_NAME = "JobFinderIsRunning"
ALREADY_EXISTS = 183  # Windows' ERROR_ALREADY_EXISTS


def already_running():
    """True if the installed app is already open. Only the packaged app on
    Windows checks: the source copy can run beside it for trying changes."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return False
    kernel32 = ctypes.windll.kernel32
    # Kept for as long as this app runs; Windows lets it go when the app ends.
    kernel32.CreateMutexW(None, False, MUTEX_NAME)
    return kernel32.GetLastError() == ALREADY_EXISTS


def free_port():
    """A port nothing else is using, so the app can't clash with other programs."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def wait_until_answering(port, seconds=15):
    """Wait for the back end to accept connections before the window opens."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
            return
        except OSError:
            time.sleep(0.1)


def main():
    if already_running():
        ctypes.windll.user32.MessageBoxW(
            None, "Job Finder is already open. Look for its window on the taskbar.",
            "Job Finder", 0x40)  # 0x40: an "information" box
        return
    port = free_port()
    # 127.0.0.1: only this computer can reach it. A daemon thread ends with the window.
    threading.Thread(target=app.run, kwargs={"host": "127.0.0.1", "port": port},
                     daemon=True).start()
    wait_until_answering(port)
    start_up()  # bring the data up to date with this version; refresh old listings
    webview.create_window("Job Finder", f"http://127.0.0.1:{port}",
                          width=1440, height=900, min_size=(960, 640))
    webview.start()  # returns when the window is closed
    # End now, even if an update or scoring run is still going in the
    # background: otherwise Python waits for it, and Job Finder keeps running
    # without a window (and keeps its files locked against an update). Data is
    # saved all or nothing (pipeline.write_json), so stopping here is safe.
    os._exit(0)


if __name__ == "__main__":
    main()
