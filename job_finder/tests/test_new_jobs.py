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


def test_a_job_left_out_of_one_update_isnt_new_when_it_comes_back():
    new_jobs.record_first_seen(jobs("a"), at(0))
    new_jobs.record_first_seen(jobs("a", "b"), at(60))       # b appears
    new_jobs.record_first_seen(jobs("a"), at(120))           # a source leaves a and b out...
    new_jobs.record_first_seen(jobs(), at(150))
    new_jobs.record_first_seen(jobs("a", "b"), at(180))      # ...and brings them back
    assert new_jobs.first_seen() == {"a": "", "b": "2026-10-25T10:00:00"}


def test_jobs_gone_for_long_are_forgotten():
    days = 24 * 60
    new_jobs.record_first_seen(jobs("a"), at(0))
    new_jobs.record_first_seen(jobs("a", "b"), at(60))
    new_jobs.record_first_seen(jobs("a"), at(new_jobs.REMEMBER_GONE_DAYS * days + 61))
    assert new_jobs.first_seen() == {"a": ""}


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
