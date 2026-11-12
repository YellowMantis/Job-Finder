"""Tests for keeping data working across app updates (migrations.py). Each
test builds a data folder in the old shape in a throwaway folder."""

import json

import pytest

import migrations


@pytest.fixture
def folder(tmp_path, monkeypatch):
    monkeypatch.setattr(migrations, "DATA_DIR", tmp_path)
    monkeypatch.setattr(migrations, "BACKUPS_DIR", tmp_path / "backups")
    return tmp_path


def write(folder, name, data):
    (folder / name).write_text(json.dumps(data), encoding="utf-8")


def read(folder, name):
    return json.loads((folder / name).read_text(encoding="utf-8"))


def test_a_new_user_starts_at_the_current_version(folder):
    assert migrations.run() is None
    assert read(folder, "data_version.json")["version"] == migrations.CURRENT_VERSION
    assert not (folder / "backups").exists()


def test_data_from_before_versions_is_upgraded_and_backed_up_first(folder):
    # The shape of data written in October 2026, before versions were kept.
    write(folder, "excluded.json", [{"title": "old"}])
    write(folder, "connections.json", {"active": "c1", "connections": [
        {"id": "c1", "kind": "claude", "name": "Claude Code"}]})
    write(folder, "scoring_log.json", [{"time": "2026-10-17 03:21", "jobs": 4},
                                       {"time": "2026-10-18 12:00", "jobs": 1, "connection": "c2"}])

    assert migrations.run() is None

    assert not (folder / "excluded.json").exists()
    log = read(folder, "scoring_log.json")
    assert log[0]["connection"] == "c1"          # filled in
    assert log[1]["connection"] == "c2"          # left as it was
    assert read(folder, "data_version.json")["version"] == migrations.CURRENT_VERSION
    [backup] = (folder / "backups").iterdir()
    assert read(backup, "scoring_log.json")[0] == {"time": "2026-10-17 03:21", "jobs": 4}


def test_running_again_changes_nothing(folder):
    write(folder, "scoring_log.json", [{"time": "2026-10-17 03:21", "jobs": 4}])
    migrations.run()
    before = (folder / "scoring_log.json").read_text(encoding="utf-8")
    migrations.run()
    assert (folder / "scoring_log.json").read_text(encoding="utf-8") == before
    assert len(list((folder / "backups").iterdir())) == 1   # backed up only when migrating


def test_data_from_a_newer_app_is_left_untouched(folder):
    write(folder, "data_version.json", {"version": migrations.CURRENT_VERSION + 1})
    write(folder, "jobs.json", [{"title": "kept"}])
    problem = migrations.run()
    assert "newer version of Job Finder" in problem
    assert read(folder, "jobs.json") == [{"title": "kept"}]


def test_applied_dates_get_the_title_company_and_apply_link(folder):
    write(folder, "data_version.json", {"version": 1})
    write(folder, "applied.json", {"https://jobs/1": "2026-10-20", "https://jobs/gone": "2026-09-01"})
    write(folder, "jobs.json", [{"url": "https://jobs/1", "title": "QA Engineer", "company": "Acme"}])
    write(folder, "postings.json", {"https://jobs/1": {"apply_url": "https://acme/apply/1"}})

    assert migrations.run() is None

    assert read(folder, "applied.json") == {
        "https://jobs/1": {"date": "2026-10-20", "title": "QA Engineer", "company": "Acme",
                           "apply_url": "https://acme/apply/1"},
        # No longer listed: only what was saved, the link and the date.
        "https://jobs/gone": {"date": "2026-09-01", "title": "", "company": "",
                              "apply_url": "https://jobs/gone"}}
    [backup] = (folder / "backups").iterdir()
    assert read(backup, "applied.json")["https://jobs/1"] == "2026-10-20"


def saved_review(years_required, score, notes):
    """A review as fits.json keeps it: core and must met, the years line added by code."""
    return {"score": score, "years_required": years_required, "notes": notes, "requirements": [
        {"requirement": f"{years_required}+ years of experience", "importance": "must",
         "evidence": "CV shows about 1 year(s) of paid work", "match": "no"},
        {"requirement": "Python", "importance": "core", "evidence": "Python", "match": "yes"},
        {"requirement": "Linux", "importance": "must", "evidence": "Linux", "match": "yes"}]}


def test_scores_halved_for_3_years_asked_are_lowered_by_a_quarter_instead(folder):
    write(folder, "data_version.json", {"version": 2})
    halved = ["Halved: asks for 3+ years, CV shows about 1."]
    write(folder, "fits.json", {
        "three": saved_review(3, 38, halved),
        "five": saved_review(5, 38, ["Halved: asks for 5+ years, CV shows about 1."]),
        "none": {"score": 80, "years_required": 0, "notes": [], "requirements": []}})
    write(folder, "earlier_reviews.json", {"three": [saved_review(3, 38, halved)]})

    assert migrations.run() is None

    fits = read(folder, "fits.json")
    assert (fits["three"]["score"], fits["three"]["notes"]) == (
        56, ["Lowered by a quarter: asks for 3+ years, CV shows about 1."])   # 75% less a quarter
    assert fits["five"]["score"] == 38   # 3+ years short: still halved
    assert fits["none"]["score"] == 80
    assert read(folder, "earlier_reviews.json")["three"][0]["score"] == 56


def test_the_cv_loaded_before_becomes_the_first_in_your_list(folder):
    import cv_library
    write(folder, "data_version.json", {"version": 3})
    (folder / "cv.txt").write_text("Python developer", encoding="utf-8")
    (folder / "cv.pdf").write_bytes(b"%PDF-1.4 a CV")
    write(folder, "cv_info.json", {"name": "backend.pdf", "uploaded": "2026-10-14 01:17",
                                   "professional_years": 1})

    assert migrations.run() is None

    [saved] = cv_library.listing()
    assert saved["name"] == "backend.pdf"
    assert cv_library.info(saved["id"])["professional_years"] == 1
    pdf, text = cv_library.files(saved["id"])
    assert pdf.read_bytes() == b"%PDF-1.4 a CV"
