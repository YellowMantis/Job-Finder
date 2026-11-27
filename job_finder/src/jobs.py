"""Read the raw job listings and label each one.

Nothing is dropped here. Every job gets its level (junior, senior or not
stated) and its company's industries (industries.py), each with the reason.
Your preferences (preferences.py) then decide what the table hides.
Every label comes from a plain rule, so you can always see why. No LLM.
"""

import csv
import re

from industries import company_industries
from settings import JUNIOR_WORDS, SENIOR_LEVELS, SENIOR_WORDS, TECHMAP_DIR


def _contains_word(text, words):
    """Return the first of the words found in the text as a whole word, or None.
    Whole word means "lead" matches "Team Lead" but not "Leading"."""
    for word in words:
        if re.search(rf"\b{re.escape(word)}\b", text, flags=re.IGNORECASE):
            return word
    return None


# Words in a title that place a job in a field, checked in this order. Jobs read
# from the job boards come without techmap's category, so we sort them here.
FIELD_WORDS = [
    # Site reliability is operations work, not quality: checked before "reliability".
    ("devops", ["site reliability", "sre"]),
    ("qa", ["qa", "test", "tester", "testing", "quality", "reliability", "verification",
            "validation"]),
    # Before the engineering fields, so "Data Product Manager" is product work.
    ("product", ["product manager", "product owner", "product analyst", "program manager",
                 "head of product", "vp product"]),
    ("project-management", ["project manager", "project management", "pmo"]),
    ("devops", ["devops", "sre", "site reliability", "infrastructure", "cloud", "platform",
                "it", "system administrator", "network engineer"]),
    ("data-science", ["data", "machine learning", "ml", "ai", "algorithm", "algorithms",
                      "scientist", "research", "researcher", "analyst"]),
    ("frontend", ["frontend", "front-end", "front end", "ui", "web developer"]),
    ("software", ["software", "developer", "engineer", "backend", "back-end", "back end",
                  "full stack", "fullstack", "full-stack", "programmer", "embedded", "mobile",
                  "android", "ios"]),
]


def web_link(url):
    """The link if it's a web address (http or https), otherwise "". Links come
    from outside data, and the desktop window hands a clicked link to Windows,
    which would also open other kinds ("file:", or an app's own scheme)."""
    return url if isinstance(url, str) and re.match(r"https?://", url, flags=re.IGNORECASE) else ""


def classify_title(title):
    """Guess a job's field from its title, or "other" if no field word appears."""
    for field, words in FIELD_WORDS:
        if _contains_word(title, words):
            return field
    return "other"


# The "qa" field holds two professions: testing software (often writing test
# code) and quality and reliability engineering (making sure physical products
# are built right and last: inspections, failure analysis, standards). The
# shared job list keeps them together as "qa", so older versions of the app
# read it unchanged; each app splits them here, by the title, then the company.
TESTING_WORDS = ["software", "automation", "sdet", "in test", "manual", "e2e", "end to end",
                 "performance", "firmware", "embedded", "framework", "frameworks", "selenium",
                 "playwright", "api", "web", "mobile", "data quality", "image quality", "תוכנה"]
QUALITY_WORDS = ["reliability", "qc", "quality control", "inspector", "supplier", "audit",
                 "audits", "manufacturing", "production", "shopfloor", "device", "mechanical",
                 "laboratory", "technician", "technologist", "regulatory", "iso", "rf",
                 "environmental",
                 # Hebrew: quality, reliability, non-destructive, lab, environmental
                 # tests, technician, mechanical
                 "איכות", "אמינות", "אל הרס", "מעבדת", "בדיקות סביבה", "טכנאי", "טכנאי/ת",
                 "מכאני", "מכונות"]
# Companies that make physical things, by techmap's category: there a title
# saying just "Quality" means quality engineering, elsewhere software quality.
MAKERS = {"Aerospace", "Health", "Semiconductors", "Robotics & Automation", "Automotive",
          "Sustainable Technology", "IoT"}


def testing_or_quality(job):
    """For a job in the "qa" field: ("qa", why) for software testing, or
    ("quality", why) for quality and reliability engineering."""
    title = job["title"]
    word = _contains_word(title, TESTING_WORDS)
    if word:
        return "qa", f'title contains "{word}"'
    word = _contains_word(title, QUALITY_WORDS)
    if word:
        return "quality", f'title contains "{word}"'
    if _contains_word(title, ["quality"]):
        industry = job.get("industry", "")
        if industry in MAKERS:
            return "quality", f'title says "quality" and techmap lists the company under "{industry}"'
        if "defence" in job.get("industries", {}):
            return "quality", 'title says "quality" at a defence company'
        return "qa", 'title says "quality" at a company that doesn\'t make physical products'
    return "qa", "title doesn't name quality or reliability work"


def with_own_field(job):
    """The job with the field this app shows: "qa" jobs split as above, with
    the reason in "field_reason"; any other job as it is."""
    if job.get("field") != "qa":
        return job
    field, reason = testing_or_quality(job)
    return {**job, "field": field, "field_reason": reason}


def load_listings(city_locations, categories=None, only_known_cities=True):
    """Read the job files and return their listings.

    city_locations: {city name: (lat, lon)}, to give each listing its position
    categories: which job files to read; None reads all of them
    only_known_cities: if True, skip listings whose city isn't in city_locations
                       (the step-by-step scripts pass only the cities in range)
    """
    if categories is None:
        categories = sorted(path.stem for path in (TECHMAP_DIR / "jobs").glob("*.csv"))
    listings = []
    for category in categories:
        path = TECHMAP_DIR / "jobs" / f"{category}.csv"
        # "utf-8-sig" skips the invisible marker at the start of these files.
        with open(path, encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                if row["city"] in city_locations or not only_known_cities:
                    listings.append({
                        "company": row["company"],
                        "title": row["title"],
                        "field": category,
                        "industry": row["category"],
                        "company_size": row["size"],
                        "city": row["city"],
                        # Where the job is: [] when the city has no position on
                        # the map. The distance is worked out from it when shown.
                        "points": ([list(city_locations[row["city"]])]
                                   if row["city"] in city_locations else []),
                        "url": row["url"],
                        "updated": row["updated"],
                        "data_level": row["level"],
                    })
    return listings


def job_level(listing):
    """Return the job's level and why: ("senior", 'title contains "lead"'),
    ("junior", ...), or ("not stated", "") when nothing says.

    Senior is checked first: a "Junior Team Lead" is still a lead."""
    word = _contains_word(listing["title"], SENIOR_WORDS)
    if word:
        return "senior", f'title contains "{word}"'
    if listing["data_level"] in SENIOR_LEVELS:
        return "senior", f'level in the data is "{listing["data_level"]}"'
    word = _contains_word(listing["title"], JUNIOR_WORDS)
    if word:
        return "junior", f'title contains "{word}"'
    return "not stated", ""


def label_listings(listings, companies, category_names):
    """Give every listing its level and its company's industries. None is dropped.

    companies:      the company records from the downloaded data
    category_names: techmap's {category id: name}, e.g. {"2": "AdTech"}

    Returns the labelled jobs, junior first.
    """
    by_name = {company["name"]: company for company in companies}
    industries_of = {}  # each company is labelled once, however many jobs it has
    jobs = []
    for listing in listings:
        name = listing["company"]
        if name not in industries_of:
            company = by_name.get(name, {})
            industries_of[name] = company_industries(
                name, company.get("description") or "",
                category_names.get(str(company.get("categoryId")), ""))
        level, level_reason = job_level(listing)
        jobs.append({**listing, "level": level, "level_reason": level_reason,
                     "industries": industries_of[name]})

    # Junior roles first. (The page sorts as you choose; distances depend on
    # your home, so they are worked out when the jobs are shown.)
    jobs.sort(key=lambda job: (job["level"] != "junior", job["company"]))
    return jobs
