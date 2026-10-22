"""Where companies and cities are, and how far they are from home.

Each company in the data is one JSON file with a list of office addresses,
and each address has a city name and map coordinates (lat, lon).
No LLM is involved.
"""

import json
import re
from math import asin, cos, radians, sin, sqrt
from statistics import median

from settings import TECHMAP_DIR

def distance_km(lat1, lon1, lat2, lon2):
    """Straight-line distance between two points on Earth (the haversine formula)."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))  # 6371 km is the Earth's radius


def load_companies():
    """Read every active company file."""
    companies = []
    for path in (TECHMAP_DIR / "companies").glob("*.json"):
        company = json.loads(path.read_text(encoding="utf-8"))
        if company.get("isActive"):
            companies.append(company)
    return companies


def _addresses(company):
    """The company's addresses that have a position on the map."""
    return [address for address in company.get("addresses") or []
            if address.get("lat") is not None and address.get("lon") is not None]


def locate_cities(companies):
    """Return {city name: (lat, lon)}, placing each city at the middle of all
    the company addresses that name it. Using the middle (the median) means one
    misplaced address cannot move a whole city."""
    points = {}
    for company in companies:
        for address in _addresses(company):
            if address.get("city"):
                points.setdefault(address["city"], []).append((address["lat"], address["lon"]))
    return {city: (median(lat for lat, _ in found), median(lon for _, lon in found))
            for city, found in points.items()}


def nearest_km(points, home):
    """Distance in km from home (lat, lon) to the nearest of the points, or None
    if there are none or no home is chosen yet. A job keeps its points; the distance is worked out when
    it is shown, so changing your home changes every distance at once."""
    if not points or home is None:
        return None
    return min(round(distance_km(home[0], home[1], lat, lon), 1) for lat, lon in points)


# Approximate positions (latitude, longitude) of places that job feeds name in
# English ("Tel Aviv, Israel"). Our city list only has Hebrew names, so English
# place names are matched here. Longer names come first so that, for example,
# "ramat hasharon" is tried before "ramat gan" could match a shorter piece.
ENGLISH_PLACES = {
    "ramat hasharon": (32.145, 34.84), "hod hasharon": (32.15, 34.89),
    "petah tikva": (32.09, 34.88), "petach tikva": (32.09, 34.88),
    "rishon lezion": (31.97, 34.80), "rishon le zion": (31.97, 34.80),
    "rosh haayin": (32.095, 34.96), "rosh ha'ayin": (32.095, 34.96),
    "tirat carmel": (32.76, 34.97), "migdal haemek": (32.67, 35.24),
    "migdal ha'emek": (32.67, 35.24), "airport city": (32.00, 34.88),
    "ness ziona": (31.93, 34.80), "nes ziona": (31.93, 34.80),
    "beer sheva": (31.25, 34.79), "be'er sheva": (31.25, 34.79),
    "kiryat gat": (31.61, 34.76), "or yehuda": (32.03, 34.86),
    "kfar saba": (32.175, 34.91), "ramat gan": (32.08, 34.82),
    "bnei brak": (32.08, 34.83), "givatayim": (32.07, 34.81),
    "tel aviv": (32.08, 34.78), "herzliya": (32.165, 34.84), "herzliyya": (32.165, 34.84),
    "ra'anana": (32.18, 34.87), "raanana": (32.18, 34.87), "jerusalem": (31.77, 35.21),
    "haifa": (32.79, 34.99), "yokneam": (32.66, 35.11), "yoqneam": (32.66, 35.11),
    "rehovot": (31.89, 34.81), "netanya": (32.32, 34.86), "caesarea": (32.50, 34.90),
    "holon": (32.01, 34.78), "modiin": (31.90, 35.01), "modi'in": (31.90, 35.01),
    "yavne": (31.88, 34.74), "ashdod": (31.80, 34.65), "ashkelon": (31.67, 34.57),
    "nazareth": (32.70, 35.30), "kinneret": (32.72, 35.56), "karmiel": (32.92, 35.30),
    "carmiel": (32.92, 35.30), "hadera": (32.43, 34.92), "lod": (31.95, 34.89),
    "shoham": (31.99, 34.95), "yehud": (32.03, 34.89), "afula": (32.61, 35.29),
    "tiberias": (32.79, 35.53), "migdal ha emek": (32.67, 35.24), "rahat": (31.39, 34.75),
    "magal": (32.39, 35.03), "yiftah": (33.13, 35.55),
}


def _simplify(text):
    """Lowercase, apostrophes dropped, hyphens as spaces, so that spelling
    variants match: "Giv'atayim" -> "givatayim", "Petah-Tikva" -> "petah tikva"."""
    return re.sub(r"\s+", " ", text.lower().replace("'", "").replace("-", " "))


def place_points(place):
    """The positions [(lat, lon), ...] of every known place named in an English
    location ("Kfar Saba, Israel", "Tel Aviv/ Netanya"); [] if it names none
    ("Israel", "Remote")."""
    text = _simplify(place)
    found = []
    for name in sorted(ENGLISH_PLACES, key=len, reverse=True):
        pattern = rf"\b{re.escape(_simplify(name))}\b"
        if re.search(pattern, text):
            found.append(ENGLISH_PLACES[name])
            text = re.sub(pattern, " ", text)  # so a shorter name can't match inside it
    return found


def company_points(company, city_locations):
    """The positions of the company's offices whose city we know. Used for jobs
    that name only an English place our Hebrew city list can't place; most
    Israeli companies have a single office in Israel, so this is usually right."""
    points = {city_locations[address["city"]] for address in _addresses(company)
              if address.get("city") in city_locations}
    return sorted(points)
