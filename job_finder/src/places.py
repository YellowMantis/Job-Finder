"""Finding a town or village by name, in English or Hebrew, to choose your home.

The list (places_il.json) comes from GeoNames; see tools/build_places.py.

Israeli place names are spelled many ways in English: "Kfar Kana", "Kafr Kana",
"Kafr Kanna". So names are compared by their skeleton: lowercase consonants
only, without doubled letters. "Kfar Kana" and "Kafr Kanna" both become
"kfrkn" and match. Hebrew names are compared without spaces and punctuation.
"""

import json
import re
from functools import cache
from pathlib import Path

PLACES_PATH = Path(__file__).parent / "places_il.json"


def skeleton(text):
    """"Kafr Kanna" -> "kfrkn"; "כפר כנא" -> "כפרכנא"."""
    text = text.lower()
    if re.search("[א-ת]", text):
        return re.sub("[^א-ת]", "", text)
    letters = re.sub("[^a-z]", "", text)
    consonants = letters[:1] + re.sub("[aeiouy]", "", letters[1:])  # keep a first vowel: "Afula"
    return re.sub(r"(.)\1+", r"\1", consonants)


@cache
def _places():
    """The list, each place with the skeletons of all its spellings (read once)."""
    places = json.loads(PLACES_PATH.read_text(encoding="utf-8"))
    for place in places:
        spellings = [place["name"], place["he"], *place["aliases"]]
        place["_keys"] = {skeleton(name) for name in spellings if name}
        place["_words"] = " ".join(name.lower() for name in spellings if name)
    return places


def search(query, limit=8):
    """Places matching what was typed, best first: [{name, he, lat, lon}].

    Best first means: a name starting with what was typed, then any spelling
    whose skeleton starts with it, then one containing it; within each, larger
    places first (the list is already sorted by population)."""
    typed = query.strip().lower()
    key = skeleton(typed)
    if len(typed) < 2 or not key:
        return []
    ranked = []
    for place in _places():
        if place["name"].lower().startswith(typed) or place["he"].startswith(typed):
            rank = 0
        elif any(k.startswith(key) for k in place["_keys"]):
            rank = 1
        elif typed in place["_words"] or any(key in k for k in place["_keys"]):
            rank = 2
        else:
            continue
        ranked.append((rank, place))
        if len(ranked) > 200:  # plenty to choose the best few from
            break
    ranked.sort(key=lambda item: item[0])  # stable: population order is kept within a rank
    return [{"name": place["name"], "he": place["he"], "lat": place["lat"], "lon": place["lon"]}
            for _, place in ranked[:limit]]
