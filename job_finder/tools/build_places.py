"""Build job_finder/src/places_il.json: Israel's towns and villages with English
and Hebrew names, other spellings, coordinates and population. The app uses it
to let you choose your home city by typing its name in either language.

The source is GeoNames (https://www.geonames.org), licensed CC BY 4.0, which
requires crediting it (see README.md). To rebuild the list, download and unzip
two files (both contain a file named IL.txt, so unzip them into separate folders):

    https://download.geonames.org/export/dump/IL.zip                 the places
    https://download.geonames.org/export/dump/alternatenames/IL.zip  their names by language

    python job_finder/tools/build_places.py places/IL.txt alternate/IL.txt
"""

import csv
import json
import re
import sys
from pathlib import Path

OUTPUT = Path(__file__).parent.parent / "src" / "places_il.json"

# GeoNames feature codes for places people live in: towns, cities, villages,
# settlements. Left out: abandoned places, sections of places and the like.
KEPT_CODES = {"PPL", "PPLA", "PPLA2", "PPLC", "STLMT"}

VOWEL_MARKS = re.compile("[֑-ׇ]")  # niqqud and cantillation


def hebrew_names(source):
    """{place id: [Hebrew names, the one to show first]} from the names file.

    The one shown is the name GeoNames marks as preferred in Hebrew (ירושלים,
    not the ancient שלם or "Aelia Capitolina"); without one, the first listed.
    Vowel marks are removed, and every spelling is kept for searching."""
    names = {}
    with open(source, encoding="utf-8") as file:
        for row in csv.reader(file, delimiter="\t", quoting=csv.QUOTE_NONE):
            if row[2] != "he" or row[7] == "1":  # Hebrew only, not historic names
                continue
            name = VOWEL_MARKS.sub("", row[3]).strip()
            if not re.fullmatch(r"[\u05d0-\u05ea\s'\"\-\u05be]+", name):
                continue
            found = names.setdefault(row[1], [])
            if name in found:
                found.remove(name)
            if row[4] == "1":  # preferred: shown first
                found.insert(0, name)
            elif name not in found:
                found.append(name)
    return names


def english_spellings(row):
    """Other English spellings people may type ("Kafr Kana", "Kfar Kana")."""
    alternates = row[3].split(",") if row[3] else []
    spellings = [name for name in alternates
                 if re.fullmatch(r"[A-Za-z][A-Za-z '`\-]{2,40}", name)
                 and not name.lower().startswith(("lungsod", "kibbutz", "moshav"))]
    return sorted(set(spellings) - {row[2]})[:10]


def tidy(name):
    """GeoNames writes some names squeezed together ("KfarAhim") or with a
    backtick for an apostrophe ("`Ein Gev"): "Kfar Ahim", "'Ein Gev"."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name.replace("`", "'"))


def main(source, names_source):
    hebrew_by_id = hebrew_names(names_source)
    places = []
    with open(source, encoding="utf-8") as file:
        for row in csv.reader(file, delimiter="\t", quoting=csv.QUOTE_NONE):
            if row[6] != "P" or row[7] not in KEPT_CODES:
                continue
            hebrew = hebrew_by_id.get(row[0], [])
            places.append({
                "name": tidy(row[2]),               # the plain English name, e.g. "Kafr Kanna"
                "he": hebrew[0] if hebrew else "",  # e.g. "כפר כנא"
                "aliases": english_spellings(row) + hebrew[1:],
                "lat": round(float(row[4]), 4),
                "lon": round(float(row[5]), 4),
                "population": int(row[14] or 0),
            })
    places.sort(key=lambda place: (-place["population"], place["name"]))
    OUTPUT.write_text(json.dumps(places, ensure_ascii=False, separators=(",", ":")),
                      encoding="utf-8")
    print(f"{len(places)} places written to {OUTPUT}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
