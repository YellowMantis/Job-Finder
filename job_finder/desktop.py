"""The job finder as a desktop app: its own window, no browser tab, no terminal.

    python job_finder/desktop.py        (from the source code)
    Job Finder.exe                      (the packaged app; see tools/build_desktop.py)

It starts the same back end as app.py, on a free port of this computer only,
and shows the same page in a window of its own (pywebview, which uses the
Edge WebView2 component built into Windows). Closing the window ends the app.
"""

import socket
import threading
import time

import webview

from app import app, start_up


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
    port = free_port()
    # 127.0.0.1: only this computer can reach it. A daemon thread ends with the window.
    threading.Thread(target=app.run, kwargs={"host": "127.0.0.1", "port": port},
                     daemon=True).start()
    wait_until_answering(port)
    start_up()  # bring the data up to date with this version; refresh old listings
    webview.create_window("Job Finder", f"http://127.0.0.1:{port}",
                          width=1440, height=900, min_size=(960, 640))
    webview.start()  # returns when the window is closed


if __name__ == "__main__":
    main()
