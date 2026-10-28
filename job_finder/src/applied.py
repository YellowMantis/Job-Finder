"""The jobs you applied to, kept in applied.json:

  {job link: {"date": "2026-10-28", "title": ..., "company": ..., "apply_url": ...}}

The title, company and apply link are saved when you tick Applied, so the
record stays whole after the listing closes and the job leaves jobs.json.
Unticking removes the entry (usually a tick by mistake).

Two ticks in quick succession arrive as two requests handled at the same
time. Each reads the file, adds its job and writes it back, so without a lock
the second write could replace the first and lose it (a "lost update").
"""

import json
import os
import threading
from datetime import date

from settings import DATA_DIR

APPLIED_PATH = DATA_DIR / "applied.json"
_lock = threading.Lock()  # one change to the file at a time


def _read():
    return json.loads(APPLIED_PATH.read_text(encoding="utf-8")) if APPLIED_PATH.exists() else {}


def _write(data):
    """All or nothing, like pipeline.write_json."""
    DATA_DIR.mkdir(exist_ok=True)
    temporary = APPLIED_PATH.with_name(APPLIED_PATH.name + ".saving")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, APPLIED_PATH)


def mark(url, title, company, apply_url, today=None):
    """Remember that you applied to this job. Returns the date saved: ticking a
    job that is already ticked keeps the date of the first tick."""
    with _lock:
        applied = _read()
        if url not in applied:
            applied[url] = {"date": (today or date.today()).isoformat(), "title": title,
                            "company": company, "apply_url": apply_url or url}
            _write(applied)
        return applied[url]["date"]


def unmark(url):
    with _lock:
        applied = _read()
        if applied.pop(url, None) is not None:
            _write(applied)


def count():
    return len(_read())


def everything(listed_urls):
    """Every job you applied to, newest first. "listed" says whether it is
    still in the listings (listed_urls); if not, it has probably closed."""
    entries = [{"url": url, **entry, "listed": url in listed_urls}
               for url, entry in _read().items()]
    return sorted(entries, key=lambda entry: entry["date"], reverse=True)
