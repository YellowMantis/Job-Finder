"""Tests for marking jobs new since your last visit (src/new_jobs.py). The
files go to each test's own folder (see conftest.py)."""

from datetime import datetime, timedelta

import new_jobs

START = datetime(2026, 10, 25, 9, 0)


def at(minutes):
    return START + timedelta(minutes=minutes)


def jobs(*urls):
    return [{"url": url} for url in urls]


def test_the_first_list_counts_as_already_seen():
    new_jobs.record_first_seen(jobs("a", "b"), at(0))
    assert new_jobs.first_seen() == {"a": "", "b": ""}


def test_later_jobs_keep_the_time_they_first_appeared():
    new_jobs.record_first_seen(jobs("a"), at(0))
    new_jobs.record_first_seen(jobs("a", "b"), at(60))
    new_jobs.record_first_seen(jobs("a", "b", "c"), at(120))
    assert new_jobs.first_seen() == {"a": "", "b": "2026-10-25T10:00:00", "c": "2026-10-25T11:00:00"}


def test_jobs_no_longer_listed_are_forgotten():
    new_jobs.record_first_seen(jobs("a", "b"), at(0))
    new_jobs.record_first_seen(jobs("b"), at(60))
    assert new_jobs.first_seen() == {"b": ""}


def test_the_first_visit_has_nothing_to_compare_with():
    assert new_jobs.visit(at(0)) is None


def test_a_visit_lasts_while_the_app_is_in_use():
    new_jobs.visit(at(0))
    # Asked again 20 and 40 minutes later: still the same visit.
    assert new_jobs.visit(at(20)) is None
    assert new_jobs.visit(at(40)) is None


def test_after_a_break_jobs_since_the_previous_visit_are_new():
    new_jobs.visit(at(0))
    new_jobs.visit(at(25))        # last seen in use at 9:25
    # Back the next day: what appeared after 9:25 is new...
    assert new_jobs.visit(at(24 * 60)) == "2026-10-25T09:25:00"
    # ...for the whole of this visit, not only its first request.
    assert new_jobs.visit(at(24 * 60 + 10)) == "2026-10-25T09:25:00"
