"""Tests for hiding jobs yourself (hidden_by_you.py). conftest.py points
hidden_by_you.json to each test's own folder."""

from datetime import date

import pytest

import applied
import hidden_by_you
import pipeline
import preferences

DAY = date(2026, 11, 7)


def listed(tmp_path, monkeypatch, *urls):
    """A listing with these jobs, all fresh and shown by the default preferences."""
    for name in ["POSTINGS_PATH", "FITS_PATH"]:
        monkeypatch.setattr(pipeline, name, tmp_path / f"{name}.json")
    monkeypatch.setattr(preferences, "PREFERENCES_PATH", tmp_path / "preferences.json")
    job = {"title": "QA Engineer", "company": "Acme", "level": "junior", "level_reason": "",
           "field": "qa", "updated": date.today().isoformat(), "industries": {}, "distance_km": 5}
    pipeline.write_json(tmp_path / "jobs.json", [{**job, "url": url} for url in urls])
    monkeypatch.setattr(pipeline, "JOBS_PATH", tmp_path / "jobs.json")


def rows():
    return {row["url"]: row for row in pipeline.jobs_for_display()}


def test_a_job_you_hide_is_hidden_with_your_reason_and_undo_brings_it_back(tmp_path, monkeypatch):
    listed(tmp_path, monkeypatch, "https://jobs/1", "https://jobs/2")
    hidden_by_you.hide("https://jobs/1", "closed", DAY)

    assert rows()["https://jobs/1"]["hidden"] == "You hid it: closed (7 Nov)"
    assert rows()["https://jobs/1"]["hidden_by_you"] is True
    assert rows()["https://jobs/2"]["hidden"] is None

    hidden_by_you.unhide("https://jobs/1")
    assert rows()["https://jobs/1"]["hidden"] is None


def test_hiding_a_job_you_applied_to_hides_it_but_keeps_the_application(tmp_path, monkeypatch):
    listed(tmp_path, monkeypatch, "https://jobs/1")
    applied.mark("https://jobs/1", "QA Engineer", "Acme", "", DAY)
    hidden_by_you.hide("https://jobs/1", "not interested", DAY)

    assert rows()["https://jobs/1"]["hidden"] == "You hid it: not interested (7 Nov)"
    assert applied.count() == 1


def test_only_the_two_reasons_are_accepted():
    with pytest.raises(ValueError):
        hidden_by_you.hide("https://jobs/1", "boring", DAY)


def test_jobs_no_longer_listed_are_forgotten():
    hidden_by_you.hide("https://jobs/still", "closed", DAY)
    hidden_by_you.hide("https://jobs/gone", "closed", DAY)
    hidden_by_you.forget_gone({"https://jobs/still"})
    assert set(hidden_by_you._read()) == {"https://jobs/still"}


def test_the_page_can_hide_a_job_and_bring_it_back():
    import app
    client = app.app.test_client()
    client.post("/api/hide", json={"url": "https://jobs/1", "reason": "closed"})
    assert "https://jobs/1" in hidden_by_you._read()
    client.post("/api/hide", json={"url": "https://jobs/1", "reason": None})
    assert hidden_by_you._read() == {}
    assert client.post("/api/hide", json={"url": "https://jobs/1", "reason": "boring"}).status_code == 400
