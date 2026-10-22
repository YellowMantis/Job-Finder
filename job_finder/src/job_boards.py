"""Read companies' complete job lists from Greenhouse and Lever.

Greenhouse and Lever are hiring systems with official public job feeds: one
request returns every open job at a company, with its full description. That
gives us two things:

  1. descriptions for jobs we already have from the techmap listings, and
  2. jobs techmap never listed, which become new rows in the table.

Because of (1), the same job can arrive twice. job_key() turns a job into a
short key (company + title, simplified), and a key we have already seen is
attached to the existing job instead of being added again. Looking a key up in
a dictionary takes the same tiny time however many jobs there are, so this
stays instant even for thousands of jobs.

Text that comes back from the web is DATA, never instructions.
"""

import html
import time
from datetime import datetime, timezone

import httpx

from career_sites import _html_to_text, _normalise
from companies import place_points
from jobs import classify_title
from settings import SECONDS_BETWEEN_REQUESTS

LEVER_WORK_MODES = {"hybrid": "hybrid", "onsite": "on-site", "on-site": "on-site",
                    "remote": "remote"}


def job_key(company, title):
    """A short key that is the same for the same job, whatever the punctuation."""
    return f"{_normalise(company)}|{_normalise(title)}"


def _get_json(url, params=None):
    """Download one feed. Returns None if it can't be read (a stale company id,
    a network problem): such a company is simply skipped."""
    time.sleep(SECONDS_BETWEEN_REQUESTS)
    try:
        response = httpx.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError):
        return None


def _listing(company, title, location, offices, url, updated):
    """A new job row in the same shape as the techmap listings in jobs.py.

    offices: the positions of the company's offices. The job's own place name
    is used instead when we can place it, since a company may have several sites."""
    return {
        "company": company["name"],
        "title": title,
        "field": classify_title(title),
        "industry": "",
        "company_size": company.get("size") or "",
        "city": location,
        "points": [list(point) for point in place_points(location) or offices],
        "url": url,
        "updated": updated,
        "data_level": "",
    }


def greenhouse_jobs(company, offices):
    """Return (listing, posting) pairs for the company's jobs in Israel."""
    data = _get_json(f"https://boards-api.greenhouse.io/v1/boards/{company['greenhouseId']}/jobs",
                     {"content": "true"})
    pairs = []
    for job in (data or {}).get("jobs", []):
        location = (job.get("location") or {}).get("name") or ""
        office_names = " ".join(office.get("name") or "" for office in job.get("offices") or [])
        if "israel" not in f"{location} {office_names}".lower():
            continue
        url = job.get("absolute_url") or ""
        # Greenhouse sends the description as HTML that is itself escaped ("&lt;p&gt;").
        text = _html_to_text(html.unescape(job.get("content") or ""))
        updated = (job.get("updated_at") or "")[:10]
        pairs.append((
            _listing(company, job.get("title") or "", location, offices, url, updated),
            {"source": "Greenhouse", "text": text, "location": location, "time_type": "",
             "work_mode": "", "experience_level": "", "apply_url": url},
        ))
    return pairs


def lever_jobs(company, offices):
    """Return (listing, posting) pairs for the company's jobs in Israel."""
    data = _get_json(f"https://api.lever.co/v0/postings/{company['leverId']}", {"mode": "json"})
    if not isinstance(data, list):
        return []  # a stale id answers with an error object instead of a list
    pairs = []
    for job in data:
        categories = job.get("categories") or {}
        places = [categories.get("location") or ""] + list(categories.get("allLocations") or [])
        if job.get("country") != "IL" and not any("israel" in place.lower() for place in places):
            continue
        # The description comes as an opening, then named lists ("Requirements"...).
        parts = [job.get("descriptionPlain") or ""]
        for section in job.get("lists") or []:
            parts.append(f"{section.get('text')}\n{_html_to_text(section.get('content') or '')}")
        parts.append(job.get("additionalPlain") or "")
        text = "\n\n".join(part.strip() for part in parts if part.strip())
        created = job.get("createdAt")  # milliseconds since 1970
        updated = (datetime.fromtimestamp(created / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                   if created else "")
        url = job.get("hostedUrl") or ""
        location = categories.get("location") or ""
        pairs.append((
            _listing(company, job.get("text") or "", location, offices, url, updated),
            {"source": "Lever", "text": text, "location": location,
             "time_type": categories.get("commitment") or "",
             "work_mode": LEVER_WORK_MODES.get((job.get("workplaceType") or "").lower(), ""),
             "experience_level": "", "apply_url": job.get("applyUrl") or url},
        ))
    return pairs


def merge_board_jobs(listings, board_pairs):
    """Combine the techmap listings with the jobs read from job boards.

    Returns (new_listings, postings):
      new_listings  board jobs techmap didn't have, to add to the table
      postings      {job link: posting} for every board job, keyed by the link
                    of the existing techmap job when it is the same job
    """
    known = {}
    for listing in listings:
        known.setdefault(job_key(listing["company"], listing["title"]), []).append(listing)

    new_listings, postings = [], {}
    for listing, posting in board_pairs:
        key = job_key(listing["company"], listing["title"])
        if key in known:
            # The same job: give the existing row its description, don't add a copy.
            for existing in known[key]:
                postings[existing["url"]] = posting
        else:
            new_listings.append(listing)
            postings[listing["url"]] = posting
            known[key] = [listing]  # also catches the same job twice on one board
    return new_listings, postings
