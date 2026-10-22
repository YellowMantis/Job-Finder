"""Tests for finding your home town by name (places.py), with the spellings
people really type. The list is the real one built from GeoNames."""

import pytest

from places import search, skeleton


@pytest.mark.parametrize("typed, found", [
    ("Kfar Kana", "Kafr Kanna"),      # GeoNames spells it "Kafr Kanna"
    ("kfar kan", "Kafr Kanna"),       # unfinished typing
    ("כפר כנא", "Kafr Kanna"),         # Hebrew
    ("Hayfa", "Haifa"),
    ("Petach Tikva", "Petah Tiqva"),
    ("Yokneam", "Yoqne'am 'Illit"),
    ("Nof Hagalil", "Nazerat 'Illit"), # the city's new name finds its old entry
    ("Afula", "Afula"),
])
def test_spellings_people_type_are_found(typed, found):
    assert found in [place["name"] for place in search(typed)]


def test_the_bigger_place_comes_first():
    assert search("tel aviv")[0]["name"] == "Tel Aviv"


def test_each_result_has_its_hebrew_name_and_position():
    place = search("Kfar Kana")[0]
    assert place["he"] == "כפר כנא"
    assert place["lat"] == pytest.approx(32.75, abs=0.01)
    assert place["lon"] == pytest.approx(35.34, abs=0.01)


def test_too_little_typed_finds_nothing():
    assert search("k") == [] and search("  ") == [] and search("!!") == []


def test_skeletons():
    assert skeleton("Kfar Kana") == skeleton("Kafr Kanna") == "kfrkn"
    assert skeleton("כפר כנא") == "כפרכנא"
