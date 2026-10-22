"""Your preferences: which jobs the table shows.

They are saved in job_finder/data/preferences.json, which stays on your own
computer (the data folder is never uploaded to GitHub), so your choices are
private. A missing file or setting falls back to DEFAULTS.

  levels           which levels to show: any of "junior", "not stated", "senior"
  fields           fields ticked in the Fields filter when the page opens;
                   posting texts are fetched only for these
  hide_industries  industries to hide: ids from industries.py, e.g. "defence"
  max_age_days     hide postings last updated longer ago than this; 0 shows all
  home             where distances are measured from: {"name", "he", "lat", "lon"}.
                   There is no default: you choose it in the first-run setup.

Hidden jobs are not deleted. The page can list them with the reason, and they
come back as soon as a preference changes. They are never fetched or scored.
"""

import json
from datetime import date

from industries import INDUSTRIES
from settings import DATA_DIR, JOB_CATEGORIES

PREFERENCES_PATH = DATA_DIR / "preferences.json"
LEVELS = ["junior", "not stated", "senior"]
FIELDS = ["software", "frontend", "qa", "devops", "data-science", "security", "hardware",
          "design", "support", "business", "finance", "sales", "marketing", "hr", "legal",
          "admin", "procurement-operations", "other"]

# Made for someone looking for their first job: junior roles and roles that
# don't state a level, posted in the last 30 days (older ones are usually
# filled or forgotten). Nothing is hidden by industry until you choose to.
DEFAULTS = {"levels": ["junior", "not stated"], "fields": JOB_CATEGORIES, "hide_industries": [],
            "max_age_days": 30, "home": None}
MAX_AGE_LIMIT = 365


def load_preferences():
    saved = {}
    if PREFERENCES_PATH.exists():
        saved = json.loads(PREFERENCES_PATH.read_text(encoding="utf-8"))
    return {**DEFAULTS, **saved}


def check_preferences(preferences):
    """Return what is wrong with preferences sent by the page, or None if all is well.
    Anything saved here is later used to filter jobs, so only known values pass."""
    allowed = {"levels": LEVELS, "fields": FIELDS, "hide_industries": list(INDUSTRIES)}
    for key, choices in allowed.items():
        values = preferences.get(key)
        if not isinstance(values, list) or not all(value in choices for value in values):
            return f'"{key}" must be a list of: {", ".join(choices)}'
    if not preferences["levels"]:
        return "Choose at least one level."
    age = preferences.get("max_age_days")
    # bool is a kind of int in Python, so True must be refused separately.
    if not isinstance(age, int) or isinstance(age, bool) or not 0 <= age <= MAX_AGE_LIMIT:
        return f'"max_age_days" must be a whole number from 0 (any age) to {MAX_AGE_LIMIT}'
    home = preferences.get("home")
    if home is None:
        return "Choose your home town: distances are measured from it."
    if not (isinstance(home, dict) and isinstance(home.get("name"), str)
            and 0 < len(home["name"]) <= 100
            and all(isinstance(home.get(axis), (int, float)) and not isinstance(home.get(axis), bool)
                    for axis in ("lat", "lon"))
            and 29 <= home["lat"] <= 34 and 34 <= home["lon"] <= 36):
        return '"home" must be a place in Israel: {"name", "lat", "lon"}'
    return None


def save_preferences(preferences):
    DATA_DIR.mkdir(exist_ok=True)
    chosen = {key: preferences[key] for key in DEFAULTS}  # nothing else is kept
    home = preferences["home"]
    chosen["home"] = {"name": home["name"], "he": str(home.get("he", ""))[:100],
                      "lat": home["lat"], "lon": home["lon"]}
    PREFERENCES_PATH.write_text(json.dumps(chosen, indent=2), encoding="utf-8")


def hidden_reason(job, preferences, today=None):
    """Why your preferences hide this job, e.g. 'Senior: title contains "lead"',
    or None if it is shown. today can be given, so tests don't depend on the date."""
    if job["level"] not in preferences["levels"]:
        return f'{job["level"].capitalize()}: {job["level_reason"]}'
    max_age = preferences["max_age_days"]
    if max_age and job.get("updated"):
        age = ((today or date.today()) - date.fromisoformat(job["updated"])).days
        if age > max_age:
            return f'Older than {max_age} days: last updated {job["updated"]}'
    for industry in preferences["hide_industries"]:
        if industry in job["industries"]:
            return f'{INDUSTRIES[industry]["label"]}: {job["industries"][industry]}'
    return None
