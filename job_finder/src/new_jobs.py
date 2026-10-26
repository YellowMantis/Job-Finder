"""Which jobs are new since you last used the app.

Two small files in the data folder:

  first_seen.json  {job link: when it first appeared in your list}, kept up to
                   date by every listings update
  visits.json      {"active": when the app was last in use,
                    "new_since": the end of your previous visit}

A visit is a stretch of use with no gap of VISIT_GAP_MINUTES or more. The page
asks for the app's status when it opens and after every update, so the visit
is kept up to date from there (see visit()). A job is new if it first appeared
after your previous visit ended.

Times are "2026-10-25T15:24:07" strings, which sort in time order.
"""

import json
import os
from datetime import datetime, timedelta

from settings import DATA_DIR

FIRST_SEEN_PATH = DATA_DIR / "first_seen.json"
VISITS_PATH = DATA_DIR / "visits.json"
VISIT_GAP_MINUTES = 30


def _read(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _write(path, data):
    """All or nothing, like pipeline.write_json."""
    DATA_DIR.mkdir(exist_ok=True)
    temporary = path.with_name(path.name + ".saving")
    temporary.write_text(json.dumps(data, indent=1), encoding="utf-8")
    os.replace(temporary, path)


def _now(now):
    return (now or datetime.now()).isoformat(timespec="seconds")


def record_first_seen(jobs, now=None):
    """Note when each job first appeared. The very first list counts as
    already seen (""): on a fresh install every job would otherwise be new.
    Jobs no longer listed are forgotten, so the file stays the size of the list."""
    seen = _read(FIRST_SEEN_PATH, None)
    stamp = "" if seen is None else _now(now)
    seen = seen or {}
    _write(FIRST_SEEN_PATH, {job["url"]: seen.get(job["url"], stamp) for job in jobs})


def first_seen():
    """{job link: when it first appeared}; "" for jobs from the very first list."""
    return _read(FIRST_SEEN_PATH, {})


def visit(now=None):
    """Record that the app is in use, and return the end of your previous visit
    (or None on the first one): jobs that appeared after it are new."""
    visits = _read(VISITS_PATH, {})
    stamp = _now(now)
    active = visits.get("active")
    gap = timedelta(minutes=VISIT_GAP_MINUTES)
    if active and datetime.fromisoformat(stamp) - datetime.fromisoformat(active) >= gap:
        visits["new_since"] = active  # a new visit begins
    visits["active"] = stamp
    _write(VISITS_PATH, visits)
    return visits.get("new_since")
