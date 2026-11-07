"""The jobs you hid yourself, kept in hidden_by_you.json:

  {job link: {"reason": "closed" or "not interested", "date": "2026-11-07"}}

A job you hide leaves the table and is listed in the Hidden tab, where Undo
brings it back. Once a job is no longer in the listings its entry isn't
needed, so it is forgotten at the next update (forget_gone).

Saved one change at a time, for the reason given in applied.py.
"""

import json
import os
import threading
from datetime import date

from settings import DATA_DIR

HIDDEN_BY_YOU_PATH = DATA_DIR / "hidden_by_you.json"
REASONS = ("closed", "not interested")
_lock = threading.Lock()


def _read():
    path = HIDDEN_BY_YOU_PATH
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _write(data):
    """All or nothing, like pipeline.write_json."""
    DATA_DIR.mkdir(exist_ok=True)
    temporary = HIDDEN_BY_YOU_PATH.with_name(HIDDEN_BY_YOU_PATH.name + ".saving")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, HIDDEN_BY_YOU_PATH)


def hide(url, reason, today=None):
    if reason not in REASONS:
        raise ValueError(f"Unknown reason: {reason}")
    with _lock:
        hidden = _read()
        hidden[url] = {"reason": reason, "date": (today or date.today()).isoformat()}
        _write(hidden)


def unhide(url):
    with _lock:
        hidden = _read()
        if hidden.pop(url, None) is not None:
            _write(hidden)


def forget_gone(listed_urls):
    """Forget the jobs that are no longer in the listings."""
    with _lock:
        hidden = _read()
        kept = {url: entry for url, entry in hidden.items() if url in listed_urls}
        if len(kept) != len(hidden):
            _write(kept)


def reason_text(entry):
    """How the Hidden tab explains it, e.g. 'You hid it: closed (7 Nov)'."""
    day = date.fromisoformat(entry["date"])
    return f'You hid it: {entry["reason"]} ({day.day} {day:%b})'
