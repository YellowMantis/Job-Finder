"""Fit reviews replaced by a newer one, kept in earlier_reviews.json:

  {job link: [review, review, ...]}   oldest first, each as fits.json keeps it

fits.json holds each job's current review, the one the table shows: the latest.
When a job is scored again (for example with another model), the review it
replaces moves here instead of being lost, so the job's panel can show what
each model scored, and one of them can be made the current review again.

Saved one change at a time, for the reason given in applied.py.
"""

import json
import os
import threading

from settings import DATA_DIR

EARLIER_REVIEWS_PATH = DATA_DIR / "earlier_reviews.json"
MOST_PER_JOB = 10  # older ones are dropped; enough to compare several models
_lock = threading.Lock()


def _read():
    path = EARLIER_REVIEWS_PATH
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _write(data):
    """All or nothing, like pipeline.write_json."""
    DATA_DIR.mkdir(exist_ok=True)
    temporary = EARLIER_REVIEWS_PATH.with_name(EARLIER_REVIEWS_PATH.name + ".saving")
    temporary.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, EARLIER_REVIEWS_PATH)


def keep(url, review):
    """Keep a review that is being replaced."""
    with _lock:
        earlier = _read()
        earlier[url] = (earlier.get(url, []) + [review])[-MOST_PER_JOB:]
        _write(earlier)


def for_job(url, cv):
    """The job's earlier reviews made for this CV, newest first. A review made
    for another CV doesn't apply to this one, so it isn't shown."""
    return [review for review in reversed(_read().get(url, [])) if review.get("cv") == cv]


def swap(url, scored, current):
    """Take out the earlier review made at `scored` and keep `current` (the
    review it replaces) in its place. Returns the review taken out, or None
    if there is no such review."""
    with _lock:
        earlier = _read()
        reviews = earlier.get(url, [])
        chosen = next((review for review in reviews if review.get("scored") == scored), None)
        if chosen is None:
            return None
        earlier[url] = [review for review in reviews if review is not chosen]
        if current:
            earlier[url].append(current)
        _write(earlier)
        return chosen
