"""Tests for what makes updates faster: reading several sites at once, and not
looking again too soon for postings that weren't found."""

import threading
import time
from datetime import date

import pipeline


def test_results_come_back_in_order_and_progress_is_counted():
    progress = {"done": 0}

    def slow_first(n):
        time.sleep(0.05 if n == 0 else 0)
        return n * 10

    assert list(pipeline.in_parallel(slow_first, [0, 1, 2, 3, 4], progress)) == [0, 10, 20, 30, 40]
    assert progress["done"] == 5


def test_several_sites_are_read_at_the_same_time_but_never_more_than_allowed():
    running, most = [0], [0]
    lock = threading.Lock()

    def visit(site):
        with lock:
            running[0] += 1
            most[0] = max(most[0], running[0])
        time.sleep(0.05)
        with lock:
            running[0] -= 1

    list(pipeline.in_parallel(visit, range(12), {"done": 0}))
    assert 1 < most[0] <= pipeline.SITES_AT_ONCE


def test_a_posting_not_found_is_not_looked_for_again_for_a_few_days():
    missing = {"a": "2026-10-16"}
    assert not pipeline.due_for_fetch("a", missing, date(2026, 10, 18))   # 2 days ago
    assert pipeline.due_for_fetch("a", missing, date(2026, 10, 19))       # 3 days: try again
    assert pipeline.due_for_fetch("b", missing, date(2026, 10, 18))       # never missed


# ---- Refreshing old listings when the app starts -----------------------------------

import os  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture
def app_files(tmp_path, monkeypatch):
    import app
    jobs, preferences = tmp_path / "jobs.json", tmp_path / "preferences.json"
    jobs.write_text("[]")
    preferences.write_text("{}")
    monkeypatch.setattr(app, "JOBS_PATH", jobs)
    monkeypatch.setattr(app, "PREFERENCES_PATH", preferences)
    started = []
    monkeypatch.setattr(app, "run_update", lambda: started.append(True))
    app.update_progress["running"] = False
    yield app, jobs, preferences, started
    app.update_progress["running"] = False


def hours_old(path, hours):
    old = path.stat().st_mtime - hours * 3600
    os.utime(path, (old, old))


def test_listings_older_than_12_hours_refresh_when_the_app_starts(app_files):
    app, jobs, _, started = app_files
    hours_old(jobs, 13)
    assert app.refresh_if_stale() is True
    import time
    time.sleep(0.1)  # the update runs in a background thread
    assert started == [True]


def test_recent_listings_are_left_alone(app_files):
    app, jobs, _, started = app_files
    hours_old(jobs, 2)
    assert app.refresh_if_stale() is False and started == []


def test_no_refresh_during_the_first_run_setup(app_files):
    app, jobs, preferences, started = app_files
    hours_old(jobs, 48)
    preferences.unlink()   # no preferences yet: the setup will download the jobs itself
    assert app.refresh_if_stale() is False
