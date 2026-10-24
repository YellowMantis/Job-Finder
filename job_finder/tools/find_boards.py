"""Find job boards that techmap's data doesn't know about, and add the verified
ones to src/boards.json.

    python job_finder/tools/find_boards.py

Many companies' listings come with only a LinkedIn link, so the app can't read
their postings. Most of those companies hire through a system the app can read
(Greenhouse, Lever, Comeet, Workday); techmap just doesn't say which. For each
such company this looks:

  1. at its careers page and home page, for the address of a hiring system
     ("job-boards.greenhouse.io/<id>", "<id>.wd5.myworkdayjobs.com/<site>"...)
  2. failing that, at the public job feeds under the company's likely names

and keeps a board only when it lists a job with the same title as one of the
company's listings, so a different company with a similar name can't slip in.

It reads public pages and feeds only, one request a second per site at most.
Needs the data of a full update (job_finder/data). Takes a few minutes.
"""

import json
import re
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

JOB_FINDER = Path(__file__).parent.parent
sys.path.insert(0, str(JOB_FINDER / "src"))

from career_sites import _comeet_positions, _normalise  # noqa: E402
from companies import BOARDS_PATH, load_companies  # noqa: E402
from pipeline import JOBS_PATH, POSTINGS_PATH, read_json  # noqa: E402

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
# Where each system shows up in a page or an address.
SIGNATURES = {
    "greenhouse": r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([\w-]+)"
                  r"|boards-api\.greenhouse\.io/v1/boards/([\w-]+)",
    "lever": r"jobs\.(?:eu\.)?lever\.co/([\w-]+)",
    "comeet": r"comeet\.(?:com|co)/jobs/([\w-]+/[\w.]+)",
    "workday": r"([\w-]+\.wd\d+\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?[\w-]+)",
}
NOT_IDS = {"embed", "jobs", "api", "v1", "www", "careers", "job_board"}
CAREER_WORDS = re.compile(r"career|jobs|join|positions|hiring|work-with-us|open-roles", re.I)

_lock = threading.Lock()
_last_request = defaultdict(float)


def _polite(url):
    """Wait so that no site gets more than one request a second from us."""
    host = urlsplit(url).hostname or ""
    with _lock:
        wait = _last_request[host] + 1.0 - time.time()
        _last_request[host] = max(time.time(), _last_request[host] + 1.0)
    if wait > 0:
        time.sleep(wait)


def _get(url, **options):
    _polite(url)
    try:
        return httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=15, **options)
    except (httpx.HTTPError, ValueError):
        return None


def _feed_titles(system, board_id):
    """The titles on a Greenhouse or Lever board, or None if there's no such board."""
    url = (f"https://boards-api.greenhouse.io/v1/boards/{board_id}/jobs" if system == "greenhouse"
           else f"https://api.lever.co/v0/postings/{board_id}?mode=json")
    response = _get(url)
    if response is None or response.status_code != 200:
        return None
    try:
        data = response.json()
        return [job["title"] for job in data["jobs"]] if system == "greenhouse" else [job["text"] for job in data]
    except (ValueError, KeyError, TypeError):
        return None


def _workday_site(address):
    """"tenant.wd5.myworkdayjobs.com/en-US/Careers" -> the site's search address."""
    match = re.match(r"([\w-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([\w-]+)$", address)
    if not match or re.fullmatch(r"[a-z]{2}-[A-Z]{2}", match.group(3)):
        return None
    tenant, server, site = match.groups()
    return f"https://{tenant}.{server}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"


def _workday_has(site, titles):
    """Does this Workday site list one of these titles?"""
    for title in list(titles)[:3]:
        _polite(site)
        try:
            response = httpx.post(f"{site}/jobs", timeout=15, json={
                "appliedFacets": {}, "limit": 20, "offset": 0, "searchText": title})
            found = {_normalise(job.get("title", "")) for job in response.json().get("jobPostings", [])}
        except (httpx.HTTPError, ValueError, AttributeError):
            return False
        if found & titles:
            return True
    return False


def _verified(system, board_id, titles):
    """The boards.json entry for this board if it lists one of the titles, else None."""
    if system in ("greenhouse", "lever"):
        listed = _feed_titles(system, board_id)
        if listed and titles & {_normalise(title) for title in listed}:
            return {f"{system}Id": board_id}
    elif system == "comeet":
        listed = {_normalise(position.get("name") or "") for position in _comeet_positions(board_id, {})}
        if titles & listed:
            return {"comeetId": board_id}
    elif system == "workday":
        site = _workday_site(board_id)
        if site and _workday_has(site, titles):
            return {"workdaySite": site}
    return None


def _found_in(text):
    """(system, id) pairs named in a page, in the order of SIGNATURES."""
    found = []
    for system, pattern in SIGNATURES.items():
        for groups in re.findall(pattern, text, flags=re.I):
            board_id = next((group for group in (groups if isinstance(groups, tuple) else [groups]) if group), "")
            if board_id and board_id.lower() not in NOT_IDS:
                found.append((system, board_id))
    return list(dict.fromkeys(found))


def _likely_ids(company):
    """Names a company's board is likely filed under: its web address, its name."""
    domain = (urlsplit(company.get("websiteUrl") or "").hostname or "").removeprefix("www.")
    words = re.findall(r"[a-z0-9]+", company["name"].lower())
    options = [domain.split(".")[0] if domain else "", "".join(words), "-".join(words)]
    return [option for option in dict.fromkeys(options) if len(option) >= 3]


def find_board(company, titles):
    """The verified boards.json entry for one company, or None."""
    text = ""
    for page in [company.get("careersUrl"), company.get("websiteUrl")]:
        response = _get(page) if page else None
        if response is None:
            continue
        text += f" {response.url} {response.text[:2_000_000]}"
        if page == company.get("websiteUrl") and not company.get("careersUrl"):
            links = re.findall(r'href=["\']([^"\'#]+)["\']', response.text)
            careers = [urljoin(str(response.url), link) for link in links if CAREER_WORDS.search(link)]
            for link in list(dict.fromkeys(careers))[:2]:
                follow = _get(link)
                if follow is not None:
                    text += f" {follow.url} {follow.text[:2_000_000]}"
    # What the pages name first; then the feeds under the company's likely names,
    # for pages that give nothing away (or name a board that doesn't check out).
    candidates = _found_in(text) + [(system, board_id) for system in ("greenhouse", "lever")
                                    for board_id in _likely_ids(company)]
    for system, board_id in dict.fromkeys(candidates):
        entry = _verified(system, board_id, titles)
        if entry:
            return entry
    return None


def main():
    jobs = read_json(JOBS_PATH, [])
    postings = read_json(POSTINGS_PATH, {})
    if not jobs:
        sys.exit("No job data yet: run a full update first (python job_finder/app.py, Update listings).")
    boards = json.loads(BOARDS_PATH.read_text(encoding="utf-8"))
    companies = {company["name"]: company for company in load_companies()}

    # Companies with listings the app can't read: no posting, and no board known.
    titles = defaultdict(set)
    for job in jobs:
        company = companies.get(job["company"])
        if (company and job["url"] not in postings and not company.get("workdaySite")
                and not company.get("greenhouseId") and not company.get("leverId")):
            titles[job["company"]].add(_normalise(job["title"]))
    print(f"Looking for the job boards of {len(titles)} companies...", flush=True)

    def look(name):
        return name, find_board(companies[name], titles[name])

    added = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for number, (name, entry) in enumerate(pool.map(look, sorted(titles)), start=1):
            if entry:
                added[name] = entry
                print(f"  {name}: {entry}", flush=True)
            if number % 50 == 0:
                print(f"  ...{number}/{len(titles)}", flush=True)

    boards["companies"] = dict(sorted({**boards["companies"], **added}.items()))
    BOARDS_PATH.write_text(json.dumps(boards, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(added)} boards found and verified; {BOARDS_PATH} now lists {len(boards['companies'])}.")


if __name__ == "__main__":
    main()
