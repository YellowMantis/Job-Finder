"""Tests for the job boards techmap doesn't know about: src/boards.json, read
by companies.load_companies(), and the finder that fills it
(tools/find_boards.py). No page is fetched here."""

import json
import sys
from pathlib import Path

import companies

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
import find_boards  # noqa: E402


def techmap_with(tmp_path, monkeypatch, records, boards):
    (tmp_path / "companies").mkdir()
    for number, record in enumerate(records):
        (tmp_path / "companies" / f"{number}.json").write_text(json.dumps(record), encoding="utf-8")
    (tmp_path / "boards.json").write_text(json.dumps({"companies": boards}), encoding="utf-8")
    monkeypatch.setattr(companies, "TECHMAP_DIR", tmp_path)
    monkeypatch.setattr(companies, "BOARDS_PATH", tmp_path / "boards.json")


def test_a_known_board_fills_in_what_techmap_lacks(tmp_path, monkeypatch):
    techmap_with(tmp_path, monkeypatch, [{"name": "Acme", "isActive": True},
                                         {"name": "Other", "isActive": True, "leverId": "other"}],
                 {"Acme": {"greenhouseId": "acme"}})
    loaded = {company["name"]: company for company in companies.load_companies()}
    assert loaded["Acme"]["greenhouseId"] == "acme"
    assert loaded["Other"]["leverId"] == "other" and "greenhouseId" not in loaded["Other"]


def test_a_known_board_replaces_an_out_of_date_one(tmp_path, monkeypatch):
    # techmap still names a Comeet page the company no longer uses.
    techmap_with(tmp_path, monkeypatch, [{"name": "Acme", "isActive": True, "comeetId": "acme/OLD"}],
                 {"Acme": {"comeetId": "acme/NEW"}})
    assert companies.load_companies()[0]["comeetId"] == "acme/NEW"


def test_the_shipped_boards_file_is_well_formed():
    boards = json.loads(companies.BOARDS_PATH.read_text(encoding="utf-8"))["companies"]
    allowed = {"greenhouseId", "leverId", "ashbyId", "smartrecruitersId", "comeetId", "workdaySite"}
    assert boards and all(entry and set(entry) <= allowed for entry in boards.values())
    assert all(site.startswith("https://") and ".myworkdayjobs.com/wday/cxs/" in site
               for entry in boards.values() for key, site in entry.items() if key == "workdaySite")


def test_hiring_systems_are_recognised_in_a_page():
    page = """<a href="https://job-boards.greenhouse.io/catonetworks/jobs/123">Apply</a>
              <iframe src="https://boards.greenhouse.io/embed/job_board?for=acme"></iframe>
              <a href="https://jobs.lever.co/walkme">Jobs</a>
              <a href="https://www.comeet.com/jobs/infinidat/D6.003">Careers</a>
              <a href="https://ffive.wd5.myworkdayjobs.com/en-US/f5jobs">Open roles</a>"""
    assert find_boards._found_in(page) == [
        ("greenhouse", "catonetworks"), ("greenhouse", "acme"), ("lever", "walkme"),
        ("comeet", "infinidat/D6.003"), ("workday", "ffive.wd5.myworkdayjobs.com/en-US/f5jobs")]


def test_a_lever_account_on_the_eu_servers_is_told_apart():
    page = '<a href="https://jobs.eu.lever.co/mobileye/7aa00e13/apply">Apply now</a>'
    assert find_boards._found_in(page) == [("lever", "eu/mobileye")]


def test_each_lever_id_is_read_from_its_own_servers():
    from job_boards import lever_feed
    assert lever_feed("walkme") == "https://api.lever.co/v0/postings/walkme"
    assert lever_feed("eu/mobileye") == "https://api.eu.lever.co/v0/postings/mobileye"


def test_a_workday_address_becomes_its_search_address():
    assert find_boards._workday_site("ffive.wd5.myworkdayjobs.com/en-US/f5jobs") == \
        "https://ffive.wd5.myworkdayjobs.com/wday/cxs/ffive/f5jobs"
    # Only a language, no site name: nothing to search.
    assert find_boards._workday_site("acme.wd1.myworkdayjobs.com/en-US") is None


def test_a_board_counts_only_if_it_lists_one_of_the_companys_titles(monkeypatch):
    monkeypatch.setattr(find_boards, "_feed_titles", lambda system, board_id: ["QA Engineer"])
    assert find_boards._verified("greenhouse", "acme", {"qa engineer"}) == {"greenhouseId": "acme"}
    # A board under the same name, but another company's jobs: not taken.
    assert find_boards._verified("greenhouse", "acme", {"backend developer"}) is None


def test_newer_systems_are_recognised_in_a_page():
    page = """<iframe src="https://jobs.ashbyhq.com/moonactive/embed?version=2"></iframe>
              <a href="https://jobs.smartrecruiters.com/Wix2/123-engineer">Apply</a>
              <script src="https://www.comeet.co/careers-api/2.0/company/87.00B/positions?token=ABC123&details=true"></script>"""
    assert find_boards._found_in(page) == [
        ("ashby", "moonactive"), ("smartrecruiters", "Wix2"), ("comeet_api", "87.00B:ABC123")]


def test_comeets_api_gives_the_companys_usual_comeet_id(monkeypatch):
    monkeypatch.setattr(find_boards, "_json", lambda url: [
        {"name": "Data Scientist", "url_comeet_hosted_page":
            "https://www.comeet.com/jobs/sentra/87.00B/data-scientist/F6.078"}])
    entry = find_boards._verified("comeet_api", "87.00B:ABC123", {"data scientist"})
    assert entry == {"comeetId": "sentra/87.00B"}
    assert find_boards._verified("comeet_api", "87.00B:ABC123", {"qa engineer"}) is None


# The feeds' own places. Many Israeli companies write only the city ("Tel Aviv",
# "Ramat Gan (Hybrid)") or a street address, without the word "Israel": those
# jobs must count as Israeli, and get their posting text. Jobs abroad must not.
PLACES = ["Tel Aviv", "Ramat Gan (Hybrid)", "21 Ha'Arba'a St., 20th floor, Tel Aviv",
          "Haifa, Israel", "London", "United States - Remote"]
ISRAELI = ["Tel Aviv", "Ramat Gan (Hybrid)", "21 Ha'Arba'a St., 20th floor, Tel Aviv", "Haifa, Israel"]


def test_greenhouse_counts_a_job_in_an_israeli_city_without_the_word_israel(monkeypatch):
    import job_boards
    monkeypatch.setattr(job_boards, "_get_json", lambda url, params=None: {"jobs": [
        {"title": place, "location": {"name": place}, "offices": [], "content": "", "absolute_url": place}
        for place in PLACES]})
    kept = [listing["title"] for listing, _ in job_boards.greenhouse_jobs({"name": "Acme", "greenhouseId": "acme"}, [])]
    assert kept == ISRAELI


def test_lever_and_ashby_count_israeli_cities_too(monkeypatch):
    import job_boards
    monkeypatch.setattr(job_boards, "_get_json", lambda url, params=None: [
        {"text": place, "categories": {"location": place}, "hostedUrl": place} for place in PLACES])
    kept = [listing["title"] for listing, _ in job_boards.lever_jobs({"name": "Acme", "leverId": "acme"}, [])]
    assert kept == ISRAELI
    monkeypatch.setattr(job_boards, "_get_json", lambda url, params=None: {"jobs": [
        {"title": place, "location": place, "jobUrl": place} for place in PLACES]})
    kept = [listing["title"] for listing, _ in job_boards.ashby_jobs({"name": "Acme", "ashbyId": "acme"}, [])]
    assert kept == ISRAELI
