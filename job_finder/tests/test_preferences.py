"""Tests for job levels, labelling, and what your preferences hide.

Titles are real ones from the data. No downloaded data is needed: companies
here are small made-up records shaped like techmap's.
"""

import pytest

from jobs import job_level, label_listings
from preferences import DEFAULTS, check_preferences, hidden_reason


def listing(title, company="Some Company", data_level=""):
    return {"company": company, "title": title, "data_level": data_level}


# ---- Levels -------------------------------------------------------------------

@pytest.mark.parametrize("title, data_level, level", [
    ("Senior Software Engineer", "", "senior"),
    ("Data Engineering Team Lead", "", "senior"),
    ("Junior Team Lead", "", "senior"),             # a lead is a lead, whatever else it says
    ("Software Engineer", "Manager", "senior"),     # techmap's own level field
    ("Junior Automation Engineer", "", "junior"),
    ("R&D Geometry Creo Intern", "", "junior"),
    ("Software Engineer", "Engineer", "not stated"),
    ("Leading Edge Developer", "", "not stated"),   # "Leading" is not the word "lead"
])
def test_job_level(title, data_level, level):
    assert job_level(listing(title, data_level=data_level))[0] == level


def test_a_level_says_why():
    assert job_level(listing("Senior Software Engineer")) == \
        ("senior", 'title contains "senior"')


# ---- Labelling ----------------------------------------------------------------

def test_labelling_keeps_every_job_and_puts_juniors_first():
    companies = [{"name": "BIRD Aerosystems", "categoryId": 3,
                  "description": "A global innovative defense technology provider."},
                 {"name": "VAST Data", "categoryId": 6, "description": "AI infrastructure."}]
    jobs = label_listings([listing("Senior Engineer", "VAST Data"),
                           listing("Software Engineer", "BIRD Aerosystems"),
                           listing("Junior QA Engineer", "VAST Data")],
                          companies, {"3": "Aerospace", "6": "Cloud Computing"})

    assert [job["title"] for job in jobs] == \
        ["Junior QA Engineer", "Software Engineer", "Senior Engineer"]
    bird = jobs[1]
    assert bird["industries"] == {"defence": 'company description mentions "defense"'}
    assert jobs[0]["industries"] == {}


def test_a_company_missing_from_the_data_gets_no_industries():
    # Jobs from job boards can belong to companies techmap knows little about.
    jobs = label_listings([listing("Engineer", "Unknown Ltd")], [], {})
    assert jobs[0]["industries"] == {}


# ---- What is hidden -------------------------------------------------------------

def job(level="not stated", industries=None, level_reason=""):
    return {"level": level, "level_reason": level_reason, "industries": industries or {}}


def test_by_default_senior_jobs_are_hidden_with_their_reason():
    assert hidden_reason(job("senior", level_reason='title contains "lead"'), DEFAULTS) == \
        'Senior: title contains "lead"'
    assert hidden_reason(job("junior"), DEFAULTS) is None
    assert hidden_reason(job("not stated"), DEFAULTS) is None


def test_by_default_no_industry_is_hidden():
    # Nobody's personal choices are built in: a new user sees every industry.
    defence_job = job(industries={"defence": "on the list of known companies"})
    assert hidden_reason(defence_job, DEFAULTS) is None


def test_an_industry_you_hide_is_hidden_with_its_reason():
    preferences = {**DEFAULTS, "hide_industries": ["defence"]}
    defence_job = job(industries={"defence": "on the list of known companies"})
    assert hidden_reason(defence_job, preferences) == \
        "Defence and military: on the list of known companies"
    assert hidden_reason(job(industries={"adtech": "..."}), preferences) is None


def test_someone_looking_for_senior_roles_sees_them():
    preferences = {**DEFAULTS, "levels": ["senior", "not stated"]}
    assert hidden_reason(job("senior"), preferences) is None
    assert hidden_reason(job("junior", level_reason='title contains "junior"'), preferences) == \
        'Junior: title contains "junior"'


def test_postings_older_than_the_limit_are_hidden():
    from datetime import date
    today = date(2026, 10, 17)
    old = {**job(), "updated": "2025-01-27"}        # a real 628-day-old Comeet posting
    recent = {**job(), "updated": "2026-10-10"}
    edge = {**job(), "updated": "2026-09-17"}       # exactly 30 days: still shown
    assert hidden_reason(old, DEFAULTS, today) == "Older than 30 days: last updated 2025-01-27"
    assert hidden_reason(recent, DEFAULTS, today) is None
    assert hidden_reason(edge, DEFAULTS, today) is None


def test_postings_asking_for_too_many_years_are_hidden():
    limit = {**DEFAULTS, "max_years": 2}
    assert hidden_reason({**job(), "years": 5}, limit) == "Asks for 5+ years of experience"
    assert hidden_reason({**job(), "years": 2}, limit) is None
    assert hidden_reason({**job(), "years": 0}, limit) is None
    # No limit chosen: every number shows.
    assert hidden_reason({**job(), "years": 12}, DEFAULTS) is None


def test_postings_that_dont_say_are_kept_unless_you_choose_otherwise():
    unknown = {**job(), "years": None}
    assert hidden_reason(unknown, {**DEFAULTS, "max_years": 2}) is None
    assert hidden_reason(unknown, {**DEFAULTS, "max_years": 2, "keep_unknown_years": False}) ==         "Years of experience: the posting doesn't say"


def test_years_never_hide_a_job_whose_text_is_still_to_be_fetched():
    # Jobs being picked for fetching carry no "years" yet; hiding them would
    # mean their text, and so their years, would never be read.
    strict = {**DEFAULTS, "max_years": 2, "keep_unknown_years": False}
    assert hidden_reason(job(), strict) is None


def test_age_limit_zero_shows_every_age():
    from datetime import date
    old = {**job(), "updated": "2022-01-13"}
    assert hidden_reason(old, {**DEFAULTS, "max_age_days": 0}, date(2026, 10, 17)) is None


# ---- Checking preferences sent by the page ------------------------------------

HOME = {"name": "Kafr Kanna", "lat": 32.7466, "lon": 35.3424}


def test_good_preferences_pass():
    assert check_preferences({"levels": ["junior"], "fields": ["qa"],
                              "hide_industries": ["gambling", "crypto"],
                              "max_age_days": 30, "home": HOME}) is None
    assert check_preferences({"levels": ["junior"], "fields": ["qa"], "hide_industries": [],
                              "max_age_days": 30, "max_years": 3, "keep_unknown_years": False,
                              "home": HOME}) is None


@pytest.mark.parametrize("preferences", [
    {"levels": ["junior"], "fields": ["qa"], "hide_industries": ["no such industry"]},
    {"levels": ["boss"], "fields": ["qa"], "hide_industries": []},
    {"levels": [], "fields": ["qa"], "hide_industries": []},
    {"levels": "junior", "fields": ["qa"], "hide_industries": []},
    {"fields": ["qa"], "hide_industries": []},
    {"levels": ["junior"], "fields": [], "hide_industries": [], "max_age_days": -1},
    {"levels": ["junior"], "fields": [], "hide_industries": [], "max_age_days": "30"},
    {"levels": ["junior"], "fields": [], "hide_industries": [], "max_age_days": True},
    {"levels": ["junior"], "fields": [], "hide_industries": [], "max_age_days": 9999},
    {"levels": ["junior"], "fields": [], "hide_industries": [], "max_age_days": 30,
     "max_years": -1, "home": HOME},
    {"levels": ["junior"], "fields": [], "hide_industries": [], "max_age_days": 30,
     "max_years": "3", "home": HOME},
    {"levels": ["junior"], "fields": [], "hide_industries": [], "max_age_days": 30,
     "max_years": 3, "keep_unknown_years": "yes", "home": HOME},
    # A home must be a named place inside Israel's map area.
    {"levels": ["junior"], "fields": [], "hide_industries": [], "max_age_days": 30,
     "home": {"name": "London", "lat": 51.5, "lon": -0.1}},
    {"levels": ["junior"], "fields": [], "hide_industries": [], "max_age_days": 30,
     "home": {"name": "", "lat": 32.7, "lon": 35.4}},
    {"levels": ["junior"], "fields": [], "hide_industries": [], "max_age_days": 30,
     "home": {"name": "X", "lat": "32.7", "lon": 35.4}},
])
def test_bad_preferences_are_refused(preferences):
    assert check_preferences(preferences) is not None


# ---- The table rows, from saved files --------------------------------------------

def test_a_review_finding_defence_hides_every_job_at_that_company(tmp_path, monkeypatch):
    # tmp_path is an empty folder pytest makes for this test; the app's data
    # files are pointed there, so the test never touches your real data.
    import json

    import pipeline
    import preferences

    def save(name, data):
        (tmp_path / name).write_text(json.dumps(data), encoding="utf-8")
        return tmp_path / name

    jobs = [{"company": "XTEND", "title": "Engineering Pilot", "url": "a", "level": "not stated",
             "industries": {}},
            {"company": "XTEND", "title": "Software Engineer", "url": "b", "level": "not stated",
             "industries": {}},
            {"company": "VAST Data", "title": "Software Engineer", "url": "c",
             "level": "not stated", "industries": {}}]
    monkeypatch.setattr(pipeline, "JOBS_PATH", save("jobs.json", jobs))
    monkeypatch.setattr(pipeline, "FITS_PATH", save("fits.json", {
        # Reviewed for a different CV: the defence finding still counts.
        "a": {"defence_related": True, "cv": "another-cv"}}))
    monkeypatch.setattr(pipeline, "POSTINGS_PATH", tmp_path / "none.json")
    monkeypatch.setattr(pipeline, "APPLIED_PATH", tmp_path / "none.json")
    monkeypatch.setattr(preferences, "PREFERENCES_PATH", save("preferences.json", {
        "hide_industries": ["defence"]}))

    hidden = {row["url"]: row["hidden"] for row in pipeline.jobs_for_display()}

    assert hidden["a"] and hidden["b"]      # the reviewed job AND the one never reviewed
    assert hidden["c"] is None
    assert 'review of its job "Engineering Pilot"' in hidden["b"]


def test_a_rows_years_come_from_the_review_or_else_the_text(tmp_path, monkeypatch):
    import json

    import pipeline
    import preferences

    def save(name, data):
        (tmp_path / name).write_text(json.dumps(data), encoding="utf-8")
        return tmp_path / name

    jobs = [{"company": "Acme", "title": "QA Engineer", "url": url, "level": "not stated",
             "industries": {}} for url in ("reviewed", "text only", "says nothing", "no text")]
    posting = {"location": "", "apply_url": ""}
    monkeypatch.setattr(pipeline, "JOBS_PATH", save("jobs.json", jobs))
    monkeypatch.setattr(pipeline, "POSTINGS_PATH", save("postings.json", {
        "reviewed": {**posting, "text": "- 2.5-5 years of experience"},
        "text only": {**posting, "text": "- At least 4 years of experience in QA"},
        "says nothing": {**posting, "text": "- Strong experience with Python"}}))
    # The AI read 2.5-5 years as 3; its reading is used, whatever CV it was for.
    monkeypatch.setattr(pipeline, "FITS_PATH", save("fits.json", {
        "reviewed": {"years_required": 3, "cv": "another-cv"}}))
    monkeypatch.setattr(pipeline, "APPLIED_PATH", tmp_path / "none.json")
    monkeypatch.setattr(preferences, "PREFERENCES_PATH", save("preferences.json", {
        "max_years": 3, "keep_unknown_years": False}))

    rows = {row["url"]: row for row in pipeline.jobs_for_display()}

    assert {url: row["years"] for url, row in rows.items()} == {
        "reviewed": 3, "text only": 4, "says nothing": None, "no text": None}
    assert rows["reviewed"]["hidden"] is None
    assert rows["text only"]["hidden"] == "Asks for 4+ years of experience"
    assert rows["no text"]["hidden"] == "Years of experience: the posting doesn't say"



def test_changing_home_changes_every_distance(tmp_path, monkeypatch):
    # The distance is worked out from the job's position when it is shown, so
    # moving home needs no new download.
    import json

    import pipeline
    import preferences

    haifa_job = {"company": "Acme", "title": "Engineer", "url": "a", "level": "not stated",
                 "industries": {}, "points": [[32.813, 34.9993]]}            # Haifa
    (tmp_path / "jobs.json").write_text(json.dumps([haifa_job]), encoding="utf-8")
    monkeypatch.setattr(pipeline, "JOBS_PATH", tmp_path / "jobs.json")
    for name in ["POSTINGS_PATH", "FITS_PATH", "APPLIED_PATH"]:
        monkeypatch.setattr(pipeline, name, tmp_path / "none.json")
    monkeypatch.setattr(preferences, "PREFERENCES_PATH", tmp_path / "preferences.json")

    def distance_with_home(home):
        (tmp_path / "preferences.json").write_text(json.dumps({"home": home}), encoding="utf-8")
        return pipeline.jobs_for_display()[0]["distance_km"]

    from_kafr_kanna = distance_with_home(HOME)
    from_haifa = distance_with_home({"name": "Haifa", "lat": 32.813, "lon": 34.9993})
    assert 30 < from_kafr_kanna < 36
    assert from_haifa == 0


def test_a_job_with_several_offices_is_as_far_as_the_nearest():
    from companies import nearest_km
    tel_aviv, kinneret = (32.08, 34.78), (32.72, 35.56)
    assert nearest_km([tel_aviv, kinneret], (32.7219, 35.4404)) == \
        nearest_km([kinneret], (32.7219, 35.4404))
    assert nearest_km([], (32.7, 35.4)) is None
