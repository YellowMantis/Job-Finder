"""Tests for where a job is, and for not showing the same job twice.

The cases come from real problems we hit: Comeet locations filled with
"careers" or a web address, Parallel Wireless's Kinneret office shown at the
company's 70 km, and jobs arriving from both techmap and a job board.
"""

import pytest

from career_sites import _fetch_comeet, _html_to_text, _place_name
from companies import nearest_km, place_points
from job_boards import job_key, merge_board_jobs

# The home these tests measure from: Kafr Kanna, near Nazareth.
HOME = {"name": "Kafr Kanna", "he": "כפר כנא", "lat": 32.7466, "lon": 35.3424}


def place_distance(place):
    """Distance from HOME to the nearest place named in a location, or None."""
    return nearest_km(place_points(place), (HOME["lat"], HOME["lon"]))

# ---- Place names and distances ------------------------------------------------


@pytest.mark.parametrize("location, expected", [
    ({"name": "careers", "country": "IL"}, ""),          # junk: fall back to the listing's city
    ({"name": "www.final.co.il", "country": "IL"}, ""),
    ({"city": "Kinneret", "country": "IL"}, "Kinneret, Israel"),
    ({"city": "Krakow", "country": "PL"}, "Krakow"),
])
def test_comeet_place_names(location, expected):
    assert _place_name(location) == expected


def test_kinneret_is_near_home():
    # Parallel Wireless's Kinneret site is about 21 km from Kafr Kanna.
    assert place_distance("Kinneret, Israel") == pytest.approx(21, abs=2)


def test_tel_aviv_is_far():
    assert 80 < place_distance("Tel Aviv, Israel") < 110


@pytest.mark.parametrize("variant, usual", [
    # Real spellings from careers sites, and the spelling in our table.
    ("Giv'atayim, Israel", "Givatayim, Israel"),
    ("Petah-Tikva, Israel", "Petah Tikva, Israel"),
    ("Tel-Aviv, Israel", "Tel Aviv, Israel"),
    ("Israel, Migdal Ha-Emek", "Migdal HaEmek, Israel"),
    ("Israel, Kiryat-Gat", "Kiryat Gat, Israel"),
])
def test_spelling_variants_are_placed(variant, usual):
    assert place_distance(variant) == place_distance(usual) is not None


def test_a_job_in_several_places_counts_the_nearest():
    # JFrog: "Tel Aviv/ Netanya". Netanya is the nearer of the two.
    assert place_distance("Tel Aviv/ Netanya, Israel") == place_distance("Netanya, Israel")


def test_no_distances_before_a_home_is_chosen():
    assert nearest_km(place_points("Haifa, Israel"), None) is None


@pytest.mark.parametrize("place", ["Poland", "Remote", "", "Lodz, Poland", "Israel",
                                   "Israel, Remote"])
def test_unknown_places_have_no_distance(place):
    # "Lodz" contains "lod" (an Israeli city): only whole words may match.
    assert place_distance(place) is None


# ---- The same job from two sources --------------------------------------------


def listing(company, title, url):
    return {"company": company, "title": title, "url": url}


def test_job_key_ignores_punctuation_and_case():
    assert job_key("VAST Data", "Software Engineer -New College Grad") == \
           job_key("Vast Data", "Software Engineer - New College Grad")


def test_hebrew_titles_keep_their_words():
    # Two different jobs at one company: they used to shrink to the same empty key.
    assert job_key("SodaStream", "מבקר/ת איכות") != job_key("SodaStream", "ראש צוות למחסן")
    assert job_key("Elbit", "בוחנ.ת איכות") == job_key("Elbit", "בוחנ/ת  איכות")


def test_a_hebrew_title_gets_its_own_posting_not_another_jobs():
    page = [{"name": name, "location": {"country": "IL"},
             "custom_fields": {"details": [{"name": "Description", "value": f"<p>{text}</p>"}]}}
            for name, text in [("מבקר/ת איכות", "Quality"), ("ראש צוות למחסן", "Warehouse")]]
    posting = _fetch_comeet("soda/1", "ראש צוות למחסן", {"soda/1": page})
    assert "Warehouse" in posting["text"]
    assert _fetch_comeet("soda/1", "--", {"soda/1": page}) is None


def test_a_board_job_we_already_have_is_not_added_twice():
    techmap = [listing("Wix", "Backend Developer", "https://techmap/wix-1")]
    board = [(listing("Wix", "Backend  Developer", "https://greenhouse/wix-1"),
              {"text": "Full description"})]

    new_rows, postings = merge_board_jobs(techmap, board)

    assert new_rows == []
    # Its description is attached to the row we already had.
    assert postings == {"https://techmap/wix-1": {"text": "Full description"}}


def test_a_board_job_we_dont_have_becomes_a_new_row():
    techmap = [listing("Wix", "Backend Developer", "https://techmap/wix-1")]
    board = [(listing("Wix", "QA Engineer", "https://greenhouse/wix-2"), {"text": "QA"})]

    new_rows, postings = merge_board_jobs(techmap, board)

    assert [row["title"] for row in new_rows] == ["QA Engineer"]
    assert "https://greenhouse/wix-2" in postings


def test_the_same_job_twice_on_one_board_becomes_one_row():
    board = [(listing("Wix", "QA Engineer", "https://greenhouse/a"), {"text": "QA"}),
             (listing("Wix", "QA Engineer", "https://greenhouse/b"), {"text": "QA"})]

    new_rows, _ = merge_board_jobs([], board)

    assert len(new_rows) == 1


# ---- Posting text --------------------------------------------------------------


def test_posting_html_becomes_plain_text():
    markup = "<p>Hello &amp; welcome</p><ul><li>Python</li><li>Linux</li></ul>"
    assert _html_to_text(markup) == "Hello & welcome\n- Python\n- Linux"


def test_posting_html_cannot_smuggle_in_tags():
    # Text from the web is shown as plain text; no tag may survive.
    assert "<" not in _html_to_text('<script>alert("x")</script><p>Job</p>')


# ---- The table's distance follows the company's own site --------------------------

def test_distance_follows_the_careers_site_location(tmp_path, monkeypatch):
    # SolarEdge: techmap lists the job at the Herzliya head office (86 km), but
    # the company's own site says Nazareth Illit, a few km from home.
    import json

    import pipeline
    import preferences

    def save(name, data):
        (tmp_path / name).write_text(json.dumps(data), encoding="utf-8")
        return tmp_path / name

    monkeypatch.setattr(preferences, "PREFERENCES_PATH", save("preferences.json", {"home": HOME}))

    job = {"company": "SolarEdge Technologies", "title": "Software Engineer", "url": "a",
           "city": "Herzliya", "distance_km": 85.7, "level": "not stated", "industries": {}}
    posting = {"text": "...", "location": "Nazareth Iliit, Israel", "apply_url": ""}
    monkeypatch.setattr(pipeline, "JOBS_PATH", save("jobs.json", [job]))
    monkeypatch.setattr(pipeline, "POSTINGS_PATH", save("postings.json", {"a": posting}))
    monkeypatch.setattr(pipeline, "FITS_PATH", tmp_path / "none.json")
    monkeypatch.setattr(pipeline, "APPLIED_PATH", tmp_path / "none.json")

    row = pipeline.jobs_for_display()[0]

    assert row["distance_km"] == place_distance("Nazareth, Israel")
    assert row["distance_km"] < 20


def test_a_board_job_that_only_says_israel_gets_the_company_offices(monkeypatch):
    # Real case: Aiven's Greenhouse job located just "Israel". A name clash once
    # turned the word "Israel" into positions, one per letter.
    import job_boards
    monkeypatch.setattr(job_boards, "_get_json", lambda url, params=None: {"jobs": [{
        "title": "Engineer", "absolute_url": "https://example.com/1", "updated_at": "2026-10-12",
        "location": {"name": "Israel"}, "offices": [{"name": "Tel Aviv"}], "content": ""}]})
    offices = [(32.08, 34.78)]

    [(listing, _)] = job_boards.greenhouse_jobs({"name": "Aiven", "greenhouseId": "aiven"}, offices)

    assert listing["points"] == [[32.08, 34.78]]


def test_a_board_job_with_a_known_place_gets_that_place(monkeypatch):
    import job_boards
    monkeypatch.setattr(job_boards, "_get_json", lambda url, params=None: {"jobs": [{
        "title": "Engineer", "absolute_url": "https://example.com/2", "updated_at": "2026-10-12",
        "location": {"name": "Haifa, Israel"}, "offices": [], "content": ""}]})

    [(listing, _)] = job_boards.greenhouse_jobs({"name": "Acme", "greenhouseId": "acme"},
                                                [(32.08, 34.78)])

    assert listing["points"] == [list(job_boards.place_points("Haifa")[0])]
