"""Keep your data working across app updates.

Every version of the app knows the shape of the data it writes. When that
shape changes (a new field, a renamed file), a new version number is added
here with a small migration: a function that upgrades data from the previous
version. When the app starts, run() brings your data folder up to date:

  data_version.json says which version the data is at (missing: 0, data
  written before versions were kept). Each migration after it runs in order,
  and the folder records the new version.

Before migrating, the data files are copied to data/backups/, so nothing is
ever lost to a faulty migration. If the data is newer than this app (an older
version was installed over a newer one), it is left untouched and the page
asks you to install the latest version.

To change the data's shape: write the migration, add it to MIGRATIONS with
the next number, and add a test with data in the old shape.
"""

import json
import re
import shutil
from datetime import datetime

from fit_rules import score_of
from settings import DATA_DIR

VERSION_PATH = DATA_DIR / "data_version.json"
BACKUPS_DIR = DATA_DIR / "backups"
# The files a migration may change. Downloaded job data (techmap/) isn't backed
# up: it can always be downloaded again.
DATA_FILES = ["jobs.json", "postings.json", "fits.json", "applied.json", "preferences.json",
              "connections.json", "cv_info.json", "scoring_log.json", "missing_postings.json",
              "company_boards.json", "hidden_by_you.json",
              "earlier_reviews.json"]


def _read(name, default):
    path = DATA_DIR / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _write(name, data):
    (DATA_DIR / name).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---- The migrations -----------------------------------------------------------------

def _to_version_1():
    """Data from before versions were kept (October 2026 and earlier):
    - excluded.json was replaced by labels on every job: remove it;
    - scoring log entries from before AI connections name no connection: they
      were all made by Claude Code, so give them the Claude Code connection,
      if there is exactly one."""
    (DATA_DIR / "excluded.json").unlink(missing_ok=True)

    claude = [c["id"] for c in _read("connections.json", {"connections": []})["connections"]
              if c["kind"] == "claude"]
    log = _read("scoring_log.json", None)
    if log is not None and len(claude) == 1:
        for record in log:
            record.setdefault("connection", claude[0])
        _write("scoring_log.json", log)


def _to_version_2():
    """applied.json kept only a date per job: {job link: "2026-10-20"}. It now
    keeps the title, company and apply link too, so a job you applied to is
    still known after its listing closes. They are filled in from the
    listings; a job no longer listed keeps just its link and date."""
    applied = _read("applied.json", None)
    if applied is None:
        return
    jobs = {job["url"]: job for job in _read("jobs.json", [])}
    postings = _read("postings.json", {})
    for url, entry in applied.items():
        if isinstance(entry, str):
            job = jobs.get(url, {})
            applied[url] = {"date": entry, "title": job.get("title", ""),
                            "company": job.get("company", ""),
                            "apply_url": postings.get(url, {}).get("apply_url") or url}
    _write("applied.json", applied)


YEARS_SHOWN = re.compile(r"CV shows about (\d+) year")


def _rescored(review):
    """A saved review worked out again under today's years rule. Reviews of
    postings that ask no years, or with no score, are left as they were."""
    if review.get("score") is None or not review.get("years_required"):
        return review
    # The years line the code added says how many years the CV showed.
    shown = next((YEARS_SHOWN.search(r["evidence"]) for r in review["requirements"]
                  if YEARS_SHOWN.search(r["evidence"])), None)
    if shown is None:
        return review
    score, note = score_of(review["requirements"], review["years_required"], int(shown[1]))
    notes = [n for n in review["notes"] if not n.startswith(("Halved:", "Lowered by"))]
    return {**review, "score": score, "notes": notes + ([note] if note else [])}


def _to_version_3():
    """A posting asking 2 more years than the CV shows used to halve the fit
    score; now that lowers it by a quarter, and halving starts at 3 more.
    Saved scores are worked out again from their saved requirements."""
    fits = _read("fits.json", None)
    if fits is not None:
        _write("fits.json", {url: _rescored(review) for url, review in fits.items()})
    earlier = _read("earlier_reviews.json", None)
    if earlier is not None:
        _write("earlier_reviews.json", {url: [_rescored(review) for review in reviews]
                                        for url, reviews in earlier.items()})


# Version number -> the migration that brings the data up to that version.
MIGRATIONS = {1: _to_version_1, 2: _to_version_2, 3: _to_version_3}
CURRENT_VERSION = max(MIGRATIONS)


def data_version():
    return _read("data_version.json", {"version": 0})["version"]


def run():
    """Bring the data folder up to CURRENT_VERSION. Returns None if all is well,
    or a message for the page if the data can't be used by this app."""
    if not any((DATA_DIR / name).exists() for name in DATA_FILES):
        mark_current()  # a first run: the data will be written in today's shape
        return None
    version = data_version()
    if version > CURRENT_VERSION:
        return ("Your data was saved by a newer version of Job Finder. Install the latest "
                "version to use it; nothing has been changed.")
    if version == CURRENT_VERSION:
        return None

    _back_up(version)
    for number in range(version + 1, CURRENT_VERSION + 1):
        MIGRATIONS[number]()
        _write("data_version.json", {"version": number})  # each step is recorded as it's done
    return None


def mark_current():
    """A brand-new data folder is written in today's shape: record that."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _write("data_version.json", {"version": CURRENT_VERSION})


def _back_up(version):
    folder = BACKUPS_DIR / f"before-version-{version + 1}-{datetime.now():%Y-%m-%d-%H%M%S}"
    folder.mkdir(parents=True, exist_ok=True)
    for name in DATA_FILES:
        if (DATA_DIR / name).exists():
            shutil.copy2(DATA_DIR / name, folder / name)
