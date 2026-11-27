"""Tests for reading posting texts from careers sites (career_sites.py) and how
an update treats a site that doesn't answer properly. Nothing is downloaded."""

import json

import httpx
import pytest

import career_sites
import pipeline


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(career_sites.time, "sleep", lambda seconds: None)


def answer(status, body=None):
    return lambda *args, **kwargs: httpx.Response(status, json=body or {}, request=httpx.Request("POST", "x"))


@pytest.mark.parametrize("status", [429, 503])
def test_a_workday_site_asking_to_slow_down_is_not_a_missing_job(monkeypatch, status):
    monkeypatch.setattr(career_sites.httpx, "post", answer(status))
    with pytest.raises(career_sites.Unreachable):
        career_sites._fetch_workday("https://acme.wd1.myworkdayjobs.com/wday/cxs/acme/Careers", "QA Engineer")


def test_a_workday_site_that_cant_be_reached_is_not_a_missing_job(monkeypatch):
    def offline(*args, **kwargs):
        raise httpx.ConnectError("no internet")
    monkeypatch.setattr(career_sites.httpx, "post", offline)
    with pytest.raises(career_sites.Unreachable):
        career_sites._fetch_workday("https://acme.wd1.myworkdayjobs.com/wday/cxs/acme/Careers", "QA Engineer")


def test_a_title_the_workday_site_doesnt_list_is_not_found(monkeypatch):
    monkeypatch.setattr(career_sites.httpx, "post", answer(200, {"jobPostings": [{"title": "Chef"}]}))
    assert career_sites._fetch_workday("https://acme.wd1.myworkdayjobs.com/wday/cxs/acme/Careers",
                                       "QA Engineer") is None


def test_a_comeet_page_asking_to_slow_down_is_not_a_company_without_jobs(monkeypatch):
    monkeypatch.setattr(career_sites.httpx, "get", answer(429))
    with pytest.raises(career_sites.Unreachable):
        career_sites._comeet_positions("acme/AB.001", {})


def test_an_update_waits_for_the_next_one_when_a_site_doesnt_answer(tmp_path, monkeypatch):
    # Big's site throttles us: its jobs are left for the next update, not marked
    # "not found" for days, and its site isn't asked again in this update.
    # Small's site answers that its job isn't there: that one is noted.
    monkeypatch.setattr(pipeline, "POSTINGS_PATH", tmp_path / "postings.json")
    monkeypatch.setattr(pipeline, "MISSING_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(pipeline, "load_preferences", lambda: {"fields": ["software"]})
    monkeypatch.setattr(pipeline, "hidden_reason", lambda job, preferences: None)
    jobs = [{"company": company, "title": title, "url": url, "field": "software"}
            for company, title, url in [("Big", "A", "big/1"), ("Big", "B", "big/2"), ("Small", "C", "small/1")]]
    companies = {"Big": {"workdaySite": "https://big"}, "Small": {"workdaySite": "https://small"}}
    asked = []

    def fetch(job, company, comeet_pages):
        asked.append(job["url"])
        if job["company"] == "Big":
            raise career_sites.Unreachable("429")
        return None
    monkeypatch.setattr(pipeline, "fetch_posting", fetch)

    pipeline.fetch_texts(jobs, companies, {"done": 0, "total": 0}, board_postings={})

    assert "big/2" not in asked                       # Big's site wasn't asked again
    missing = json.loads((tmp_path / "missing.json").read_text())
    assert set(missing) == {"small/1"}                # only the real "not there"
