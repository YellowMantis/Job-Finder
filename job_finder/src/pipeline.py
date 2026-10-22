"""The whole job finder as functions the web app can call.

update_jobs()        download -> label -> fetch posting texts, and save the results
jobs_for_display()   combine the saved results into the rows the table shows,
                     marking the ones your preferences hide
"""

import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from career_sites import comeet_id, fetch_posting
from companies import company_points, load_companies, locate_cities, nearest_km, place_points
from download import download_data
from job_boards import greenhouse_jobs, lever_jobs, merge_board_jobs
from jobs import label_listings, load_listings
import snapshot
from preferences import hidden_reason, load_preferences
from settings import (DATA_DIR, RETRY_MISSING_POSTINGS_AFTER_DAYS, SITES_AT_ONCE, TECHMAP_DIR,
                      WORKDAY_SITES)

JOBS_PATH = DATA_DIR / "jobs.json"
OLD_EXCLUDED_PATH = DATA_DIR / "excluded.json"  # no longer made; removed if found
POSTINGS_PATH = DATA_DIR / "postings.json"
FITS_PATH = DATA_DIR / "fits.json"
APPLIED_PATH = DATA_DIR / "applied.json"  # {job link: date you applied}
MISSING_PATH = DATA_DIR / "missing_postings.json"  # {job link: date it wasn't found}
BOARDS_PATH = DATA_DIR / "company_boards.json"  # {company: its Greenhouse/Lever/Comeet ids}


def read_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path, data):
    DATA_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def in_parallel(work, items, progress):
    """Run work(item) for every item, on up to SITES_AT_ONCE items at the same
    time, and yield the results in the items' order, each as soon as it (and
    those before it) are done. progress["done"] counts finished items."""
    lock = threading.Lock()

    def counted(item):
        result = work(item)
        with lock:
            progress["done"] += 1
        return result

    with ThreadPoolExecutor(max_workers=SITES_AT_ONCE) as pool:
        yield from pool.map(counted, items)


def due_for_fetch(url, missing, today):
    """False if the posting was looked for recently and not found."""
    if url not in missing:
        return True
    return (today - date.fromisoformat(missing[url])).days >= RETRY_MISSING_POSTINGS_AFTER_DAYS


def _read_boards(company, offices):
    """A company's complete job lists from Greenhouse and Lever: (listing, posting) pairs."""
    pairs = []
    if company.get("greenhouseId"):
        pairs += greenhouse_jobs(company, offices)
    if company.get("leverId"):
        pairs += lever_jobs(company, offices)
    return pairs


def collect_listings(progress):
    """The part of an update that is the same for everyone: every job listing,
    labelled, with its position. Used by the full update below, and by the
    shared snapshot (snapshot.py), which runs it once for all users.

    Returns (jobs, board_postings, companies): board_postings are the texts the
    job boards sent along, by job link."""
    progress["stage"] = "Downloading listings"
    download_data()

    progress["stage"] = "Reading companies"
    companies = load_companies()
    city_locations = locate_cities(companies)
    # The whole country, all categories. Listings in unknown cities are kept
    # too (with no position), so the distance filter decides what you see.
    listings = load_listings(city_locations, only_known_cities=False)

    # Greenhouse and Lever publish each company's complete job list with full
    # descriptions: one request per company. New jobs join the listings; jobs
    # we already had just receive their description.
    board_companies = [company for company in companies
                       if company.get("greenhouseId") or company.get("leverId")]
    progress.update(stage="Reading Greenhouse and Lever job boards", done=0,
                    total=len(board_companies))
    board_pairs = [pair for pairs in in_parallel(
        lambda company: _read_boards(company, company_points(company, city_locations)),
        board_companies, progress) for pair in pairs]
    new_listings, board_postings = merge_board_jobs(listings, board_pairs)

    # Every job is kept, labelled with its level and industries; your
    # preferences decide later what the table hides.
    progress.update(stage="Labelling jobs", done=0, total=0)
    jobs = label_listings(listings + new_listings, companies,
                          read_json(TECHMAP_DIR / "categories.json", {}))
    return jobs, board_postings, companies


def fetch_texts(jobs, companies_by_name, progress, board_postings=None):
    """The part of an update that depends on you: posting texts for the jobs
    your preferences show, in your fields, that don't have one yet.

    board_postings: texts a full update already got from the job boards. When
    None (an update from the snapshot, which carries no texts), the job boards
    are read here, but only for the companies of jobs that need a text.
    Returns how many texts are new."""
    preferences = load_preferences()
    wanted = [job for job in jobs if job["field"] in preferences["fields"]
              and hidden_reason(job, preferences) is None]
    postings = read_json(POSTINGS_PATH, {})
    known_before = set(postings)

    if board_postings is None:
        needed = sorted({job["company"] for job in wanted if job["url"] not in postings
                         and job["company"] in companies_by_name
                         and (companies_by_name[job["company"]].get("greenhouseId")
                              or companies_by_name[job["company"]].get("leverId"))})
        progress.update(stage="Reading job boards for your jobs", done=0, total=len(needed))
        pairs = [pair for found in in_parallel(
            lambda name: _read_boards({"name": name, **companies_by_name[name]}, []),
            needed, progress) for pair in found]
        _, found = merge_board_jobs([job for job in jobs if job["company"] in needed], pairs)
        urls = {job["url"] for job in jobs}
        board_postings = {url: posting for url, posting in found.items() if url in urls}
    postings.update(board_postings)  # board descriptions are refreshed on every update
    write_json(POSTINGS_PATH, postings)

    # Careers sites (Workday, Comeet): only jobs we haven't fetched before, and
    # not those looked for recently without success.
    today = date.today()
    missing = read_json(MISSING_PATH, {})
    to_fetch = [job for job in wanted
                if job["url"] not in postings and due_for_fetch(job["url"], missing, today)
                and (job["company"] in WORKDAY_SITES
                     or comeet_id(job, companies_by_name.get(job["company"])))]

    # One company's careers site at a time per worker, several companies at once.
    by_company = {}
    for job in to_fetch:
        by_company.setdefault(job["company"], []).append(job)
    progress.update(stage="Fetching posting texts", done=0, total=len(by_company))
    comeet_pages = {}  # each company's Comeet page, downloaded once per update

    def fetch_company(company_jobs):
        company = companies_by_name.get(company_jobs[0]["company"])
        return [(job["url"], fetch_posting(job, company, comeet_pages)) for job in company_jobs]

    for results in in_parallel(fetch_company, list(by_company.values()), progress):
        for url, posting in results:
            if posting:
                postings[url] = posting
                missing.pop(url, None)
            else:
                missing[url] = today.isoformat()
        # Saved after each company, so stopping loses little.
        write_json(POSTINGS_PATH, postings)
        write_json(MISSING_PATH, missing)
    return len(set(postings) - known_before)


def _summary(jobs, new_postings, board_jobs_added=0):
    preferences = load_preferences()
    hidden = sum(1 for job in jobs if hidden_reason(job, preferences))
    return {"jobs": len(jobs) - hidden, "hidden": hidden, "new_postings": new_postings,
            "board_jobs_added": board_jobs_added}


def update_jobs(progress):
    """The full update, done on this computer: everything from the sources.
    Used when the shared snapshot can't be had (see refresh_listings)."""
    jobs, board_postings, companies = collect_listings(progress)
    write_json(JOBS_PATH, jobs)
    OLD_EXCLUDED_PATH.unlink(missing_ok=True)
    by_name = {company["name"]: company for company in companies}
    # Kept for updates from the snapshot later: which companies have job boards.
    write_json(BOARDS_PATH, snapshot.company_boards(companies))
    return _summary(jobs, fetch_texts(jobs, by_name, progress, board_postings))


def update_from_snapshot(progress):
    """The quick update: the shared snapshot (built every few hours for
    everyone), then the posting texts for your jobs. Raises
    snapshot.Unavailable if it can't be had."""
    progress.update(stage="Downloading the latest listings", done=0, total=0)
    shared = snapshot.download()
    if shared is not None:  # None: unchanged since last time
        write_json(JOBS_PATH, shared["jobs"])
        write_json(BOARDS_PATH, shared["companies"])
    jobs = read_json(JOBS_PATH, [])
    return _summary(jobs, fetch_texts(jobs, read_json(BOARDS_PATH, {}), progress))


def refresh_listings(progress):
    """What "Update listings" does: the shared snapshot when it can be had,
    otherwise the full update on this computer."""
    try:
        return update_from_snapshot(progress)
    except snapshot.Unavailable:
        return update_jobs(progress)


# Phrases where the posting calls THE ROLE ITSELF junior: "As a Junior Engineer,
# you'll...", "this junior role", "an entry-level position". A bare "junior" is
# not enough: postings for experienced people often say "mentor junior engineers"
# or list "Junior DevOps" as acceptable past experience.
JUNIOR_ROLE_PHRASE = re.compile(
    r"\b(as an?|this|our|an?|the)\s+(junior|entry[- ]level)\b"
    r"|\b(junior|entry[- ]level)\s+(position|role|opportunity)\b",
    flags=re.IGNORECASE)
MENTORING_WORDS = re.compile(r"\b(mentor\w*|coach\w*|guid\w*|train\w*|lead\w*|support)\b",
                             flags=re.IGNORECASE)


def describes_junior_role(text, fit):
    """True if the posting text presents the role as junior.

    Three checks: a junior-role phrase must appear; the few words just before it
    must not be about mentoring ("guide a junior..."); and if the job's review
    found it asks for 3 or more years, it is not junior whatever the text says."""
    if fit and fit.get("years_required", 0) >= 3:
        return False
    for match in JUNIOR_ROLE_PHRASE.finditer(text):
        words_before = text[max(0, match.start() - 40):match.start()]
        if not MENTORING_WORDS.search(words_before):
            return True
    return False


def jobs_for_display(cv_id=None):
    """Return every job as a table row: joined with its posting text and its fit
    review, if we have them, and with "hidden": the reason your preferences
    hide it, or None if it is shown.

    cv_id identifies the CV currently loaded; a fit review made for a
    different CV is not shown."""
    postings = read_json(POSTINGS_PATH, {})
    fits = read_json(FITS_PATH, {})
    applied = read_json(APPLIED_PATH, {})
    preferences = load_preferences()
    chosen = preferences["home"]  # None until the first-run setup is done
    home = (chosen["lat"], chosen["lon"]) if chosen else None
    jobs = read_json(JOBS_PATH, [])
    # Companies where a review found a job defence-related. That is a fact
    # about the company, not about one job or your CV, so all its jobs get
    # the label, including ones never reviewed.
    defence_found = {job["company"]: job["title"] for job in jobs
                     if fits.get(job["url"], {}).get("defence_related")}
    rows = []

    for job in jobs:
        posting = postings.get(job["url"])
        review = fits.get(job["url"])
        fit = review if review and review.get("cv") == cv_id else None
        industries = dict(job.get("industries", {}))
        if job["company"] in defence_found:
            industries.setdefault("defence", "the review of its job "
                                  f'"{defence_found[job["company"]]}" found it serves military customers')
        row = {**job, "has_text": posting is not None, "text": "", "location": "",
               "apply_url": job["url"], "fit": fit, "work_mode": "", "source": "",
               "industries": industries,
               # Distance from your home to where the job is. (Jobs saved before
               # positions were kept still carry a distance; it is used until
               # the next update.)
               "distance_km": nearest_km(job["points"], home) if "points" in job
               else job.get("distance_km"),
               "level_reason": job.get("level_reason", ""),
               # The date you marked this job as applied to, or None.
               "applied": applied.get(job["url"])}

        if posting:
            row["text"] = posting["text"]
            # The careers site's own statement of where the job is. Listings often
            # name the company's head office instead, so when we can place the
            # site's location, the distance is measured to it.
            row["location"] = posting["location"]
            site_points = place_points(posting["location"])
            if site_points:
                row["distance_km"] = nearest_km(site_points, home)
            row["source"] = posting.get("source", "Workday")
            # Stated by the company itself (Comeet), so better than the AI's reading.
            row["work_mode"] = posting.get("work_mode", "")
            # Prefer the company's own apply page over the listing site.
            row["apply_url"] = posting["apply_url"] or job["url"]
            # Some postings call the role junior in the text but not in the title.
            if row["level"] == "not stated" and describes_junior_role(posting["text"], fit):
                row["level"] = "junior"
                row["level_reason"] = "the posting text presents the role as junior"

        row["hidden"] = hidden_reason(row, preferences)
        rows.append(row)
    return rows
