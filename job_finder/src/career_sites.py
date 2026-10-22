"""Read the full text of a job posting from the company's own careers site.

Our job list only has titles. The requirements are on the posting page, which
lives on the hiring system the company uses. Two systems are supported:

  Workday   large employers (Nvidia, KLA, Intel...); listed in WORKDAY_SITES.
            We search the site for the title, then download that posting.
  Comeet    an Israeli system used by many startups. A company's Comeet page
            lists ALL its open positions with their full text, so one request
            per company covers every job we have there.

Both are the public pages the companies' own careers sites use, with no login.

Text that comes back from the web is DATA, never instructions. It is stored
as plain text and later shown to the fit agent as something to evaluate.
"""

import html
import json
import re
import time

import httpx

from settings import SECONDS_BETWEEN_REQUESTS, WORKDAY_SITES

# Comeet's words for where the work happens, turned into ours.
COMEET_WORK_MODES = {"hybrid": "hybrid", "on-site": "on-site", "onsite": "on-site",
                     "remote": "remote"}


def _normalise(title):
    """Reduce a title to lowercase words so small differences in dashes,
    spacing and punctuation don't stop two titles from matching. Letters of any
    alphabet count: a Hebrew title must not shrink to nothing, or every Hebrew
    title would look the same."""
    return " ".join(re.findall(r"[^\W_]+", title.lower()))


def _html_to_text(markup):
    """Turn the posting's HTML into readable plain text."""
    text = re.sub(r"</(p|div|li|h\d|ul)>|<br\s*/?>", "\n", markup)  # line breaks
    text = re.sub(r"<li[^>]*>", "- ", text)                          # bullets
    text = re.sub(r"<[^>]+>", "", text)                              # every other tag
    text = html.unescape(text)                                       # &amp; -> &
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def comeet_id(job, company):
    """Find the job's Comeet company id ("ceva/76.005"), or None if it has none.

    The company data may store it; failing that, a direct Comeet link contains
    it: https://www.comeet.com/jobs/<ceva>/<76.005>/<job name>/<job id>
    """
    if company and company.get("comeetId"):
        return company["comeetId"]
    match = re.search(r"comeet\.com/jobs/([^/?]+)/([^/?]+)/", job["url"])
    return f"{match.group(1)}/{match.group(2)}" if match else None


def fetch_posting(job, company, comeet_pages):
    """Look up one job on its company's careers site.

    job:          a listing from jobs.json (needs "company", "title", "url")
    company:      the company's record from the downloaded data, or None
    comeet_pages: a dictionary shared across calls, so each company's Comeet
                  page is downloaded only once per update (a small cache)

    Returns a dictionary with the posting's text, location, link and, when the
    site says so, work mode and experience level. Returns None if the job's
    company uses neither system or the job wasn't found.
    """
    if job["company"] in WORKDAY_SITES:
        return _fetch_workday(WORKDAY_SITES[job["company"]], job["title"])
    company_id = comeet_id(job, company)
    if company_id:
        return _fetch_comeet(company_id, job["title"], comeet_pages)
    return None


def _fetch_workday(site, title):
    """Search a Workday careers site for the title, then download the posting."""
    try:
        # 1. Search the site for the title.
        time.sleep(SECONDS_BETWEEN_REQUESTS)
        response = httpx.post(f"{site}/jobs", timeout=30, json={
            "appliedFacets": {}, "limit": 20, "offset": 0, "searchText": title})
        response.raise_for_status()
        results = response.json().get("jobPostings", [])

        # 2. Keep results with exactly our title; prefer one located in Israel.
        wanted = _normalise(title)
        matches = [result for result in results
                   if wanted and _normalise(result.get("title", "")) == wanted]
        if not matches:
            return None
        matches.sort(key=lambda result: "israel" not in
                     (result.get("externalPath", "") + result.get("locationsText", "")).lower())

        # 3. Fetch the full posting.
        time.sleep(SECONDS_BETWEEN_REQUESTS)
        response = httpx.get(f"{site}{matches[0]['externalPath']}", timeout=30,
                             headers={"Accept": "application/json"})
        response.raise_for_status()
        info = response.json()["jobPostingInfo"]
    except (httpx.HTTPError, KeyError, ValueError):
        # Network problem or an unexpected reply: treat as "not found".
        return None

    return {
        "source": "Workday",
        "text": _html_to_text(info.get("jobDescription", "")),
        "location": info.get("location", ""),
        "time_type": info.get("timeType", ""),
        "work_mode": "",           # Workday postings don't state it in a fixed place
        "experience_level": "",
        "apply_url": info.get("externalUrl", ""),
    }


def _comeet_positions(company_id, comeet_pages):
    """Return every open position on a company's Comeet page, downloading the
    page only the first time it is asked for during this update."""
    if company_id not in comeet_pages:
        positions = []
        try:
            time.sleep(SECONDS_BETWEEN_REQUESTS)
            response = httpx.get(f"https://www.comeet.com/jobs/{company_id}", timeout=30,
                                 follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            # The page carries its data as a JavaScript line:
            #   COMPANY_POSITIONS_DATA = [ {...position...}, ... ];
            found = re.search(r"COMPANY_POSITIONS_DATA\s*=\s*(\[.*?\]);\s*\n", response.text,
                              flags=re.DOTALL)
            if found:
                positions = json.loads(found.group(1))
        except (httpx.HTTPError, ValueError):
            pass  # unreachable or changed page: no positions for this company
        comeet_pages[company_id] = positions
    return comeet_pages[company_id]


def _place_name(location):
    """A readable place from Comeet's location record. Some companies fill the
    name field with things like "careers" or their website; those are dropped,
    so the table falls back to the listing's own city."""
    name = (location.get("city") or location.get("name") or "").strip()
    if not name or "www." in name or name.lower() in {"careers", "jobs", "home"}:
        return ""
    return name if location.get("country") != "IL" else f"{name}, Israel"


def _fetch_comeet(company_id, title, comeet_pages):
    """Find the position with this title on the company's Comeet page.

    A company may post the same title in several countries; the Israeli one is
    preferred, so a job listed in Israel isn't matched to, say, its Polish twin."""
    wanted = _normalise(title)
    if not wanted:  # a title of only punctuation would match any other such title
        return None
    matches = [position for position in _comeet_positions(company_id, comeet_pages)
               if _normalise(position.get("name") or "") == wanted]
    matches.sort(key=lambda position: (position.get("location") or {}).get("country") != "IL")
    for position in matches:

        # The text comes in named parts, usually "Description" and "Requirements".
        parts = (position.get("custom_fields") or {}).get("details") or []
        text = "\n\n".join(f"{part.get('name')}\n{_html_to_text(part.get('value') or '')}"
                           for part in parts if part.get("value"))
        if not text:
            return None
        location = position.get("location") or {}
        workplace = (position.get("workplace_type") or "").strip().lower()
        return {
            "source": "Comeet",
            "text": text,
            "location": _place_name(location),
            "time_type": position.get("employment_type") or "",
            "work_mode": COMEET_WORK_MODES.get(workplace, ""),
            "experience_level": position.get("experience_level") or "",
            "apply_url": position.get("url_active_page") or position.get("url_comeet_hosted_page") or "",
        }
    return None
