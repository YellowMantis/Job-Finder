"""Tests for remembering the jobs you applied to (applied.py). conftest.py
points applied.json to each test's own folder."""

import threading
from datetime import date

import applied
import pipeline
import preferences

DAY = date(2026, 10, 28)


def test_ticking_saves_the_job_and_unticking_removes_it():
    assert applied.mark("https://jobs/1", "QA Engineer", "Acme", "https://acme/apply", DAY) == "2026-10-28"
    assert applied.count() == 1
    applied.unmark("https://jobs/1")
    assert applied.count() == 0


def test_ticking_again_keeps_the_first_date():
    applied.mark("https://jobs/1", "QA Engineer", "Acme", "", DAY)
    assert applied.mark("https://jobs/1", "QA Engineer", "Acme", "", date(2026, 11, 5)) == "2026-10-28"


def test_without_an_apply_link_the_job_link_is_kept():
    applied.mark("https://jobs/1", "QA Engineer", "Acme", "", DAY)
    [entry] = applied.everything(set())
    assert entry["apply_url"] == "https://jobs/1"


def test_everything_is_newest_first_and_says_what_is_still_listed():
    applied.mark("https://jobs/old", "Old", "A", "", date(2026, 9, 1))
    applied.mark("https://jobs/new", "New", "B", "", DAY)
    entries = applied.everything({"https://jobs/new"})
    assert [(e["title"], e["listed"]) for e in entries] == [("New", True), ("Old", False)]


def test_many_ticks_at_once_are_all_kept():
    # Many requests at the same moment: without the lock, some writes would
    # replace others and lose their job.
    threads = [threading.Thread(target=applied.mark, args=(f"https://jobs/{n}", "T", "C", "", DAY))
               for n in range(30)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert applied.count() == 30


def test_a_job_you_applied_to_is_never_hidden(tmp_path, monkeypatch):
    for name in ["POSTINGS_PATH", "FITS_PATH"]:
        monkeypatch.setattr(pipeline, name, tmp_path / f"{name}.json")
    # The default preferences: postings up to 60 days old.
    monkeypatch.setattr(preferences, "PREFERENCES_PATH", tmp_path / "preferences.json")
    old = {"url": "https://jobs/old", "title": "QA Engineer", "company": "Acme", "level": "junior",
           "level_reason": "", "field": "QA", "updated": "2025-01-01", "industries": {},
           "distance_km": 5}
    pipeline.write_json(tmp_path / "jobs.json", [old, {**old, "url": "https://jobs/other"}])
    monkeypatch.setattr(pipeline, "JOBS_PATH", tmp_path / "jobs.json")
    applied.mark("https://jobs/old", "QA Engineer", "Acme", "", DAY)

    rows = {row["url"]: row for row in pipeline.jobs_for_display()}
    assert rows["https://jobs/old"]["hidden"] is None
    assert rows["https://jobs/old"]["applied"] == "2026-10-28"
    assert rows["https://jobs/other"]["hidden"].startswith("Older than")
