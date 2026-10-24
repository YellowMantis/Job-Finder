"""Find job boards that techmap's data doesn't know about, and add the verified
ones to src/boards.json.

    python job_finder/tools/find_boards.py              # quick: plain page reads
    python job_finder/tools/find_boards.py --browser    # also opens pages in a browser

Many companies' listings come with only a LinkedIn link, so the app can't read
their postings. Most of those companies hire through a system the app can read
(Greenhouse, Lever, Ashby, SmartRecruiters, Comeet, Workday); techmap just
doesn't say which. For each such company this looks:

  1. at its careers page and home page, for the address of a hiring system
     ("job-boards.greenhouse.io/<id>", "<id>.wd5.myworkdayjobs.com/<site>"...).
     With --browser, the pages are also opened in a real browser (Edge, through
     Playwright), which sees the addresses that pages built with JavaScript
     load their jobs from.
  2. at the public job feeds under the company's likely names

and keeps a board only when it lists a job with the same title as one of the
company's listings, so a different company with a similar name can't slip in.

It reads public pages and feeds only, one request a second per site at most.
Needs the data of a full update (job_finder/data). Takes a few minutes; with
--browser, about 15 seconds more per company.
"""

import argparse
import asyncio
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
from job_boards import FEED_KEYS  # noqa: E402
from pipeline import JOBS_PATH, POSTINGS_PATH, read_json  # noqa: E402

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
# Where each system shows up in a page or an address, and how to read its id.
SIGNATURES = {
    "greenhouse": r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([\w-]+)"
                  r"|boards-api\.greenhouse\.io/v1/boards/([\w-]+)",
    "lever": r"jobs\.(?:eu\.)?lever\.co/([\w-]+)",
    "comeet": r"comeet\.(?:com|co)/jobs/([\w-]+/[\w.]+)",
    "workday": r"([\w-]+\.wd\d+\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?[\w-]+)",
    "ashby": r"jobs\.ashbyhq\.com/([\w.%-]+)|api\.ashbyhq\.com/posting-api/job-board/([\w.%-]+)",
    "smartrecruiters": r"(?:jobs|careers)\.smartrecruiters\.com/([\w-]+)"
                       r"|api\.smartrecruiters\.com/v1/companies/([\w-]+)",
    # Comeet's careers API, which pages embed with a public token: "<uid>:<token>".
    "comeet_api": r"careers-api/2\.0/company/([\w.]+)/positions\?token=(\w+)",
}
NOT_IDS = {"embed", "jobs", "api", "v1", "www", "careers", "job_board", "job-board"}
CAREER_WORDS = re.compile(r"career|jobs|join|positions|hiring|work-with-us|open-roles", re.I)
FEEDS = ("greenhouse", "lever", "ashby", "smartrecruiters")  # systems with a full job feed

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


def _json(url):
    response = _get(url)
    if response is None or response.status_code != 200:
        return None
    try:
        return response.json()
    except ValueError:
        return None


def _feed_titles(system, board_id):
    """The titles on a job feed, or None if there's no such board."""
    try:
        if system == "greenhouse":
            return [job["title"] for job in _json(f"https://boards-api.greenhouse.io/v1/boards/{board_id}/jobs")["jobs"]]
        if system == "lever":
            data = _json(f"https://api.lever.co/v0/postings/{board_id}?mode=json")
            return [job["text"] for job in data] if isinstance(data, list) else None
        if system == "ashby":
            return [job["title"] for job in _json(f"https://api.ashbyhq.com/posting-api/job-board/{board_id}")["jobs"]]
        if system == "smartrecruiters":
            data = _json(f"https://api.smartrecruiters.com/v1/companies/{board_id}/postings?limit=100")
            return [job["name"] for job in data["content"]] or None
    except (TypeError, KeyError):
        return None
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


def _comeet_from_api(board_id):
    """"<uid>:<token>" -> (the company's usual Comeet id "name/uid", its job titles).
    The API's replies carry each job's ordinary Comeet address, which names it."""
    uid, token = board_id.split(":")
    data = _json(f"https://www.comeet.co/careers-api/2.0/company/{uid}/positions?token={token}&details=false")
    if not isinstance(data, list) or not data:
        return None, []
    address = next((job.get("url_comeet_hosted_page") or "" for job in data), "")
    match = re.search(r"comeet\.com/jobs/([\w-]+)/([\w.]+)", address)
    return (f"{match.group(1)}/{match.group(2)}" if match else None), [job.get("name") or "" for job in data]


def _verified(system, board_id, titles):
    """The boards.json entry for this board if it lists one of the titles, else None."""
    if system in FEEDS:
        listed = _feed_titles(system, board_id)
        if listed and titles & {_normalise(title) for title in listed}:
            return {f"{system}Id": board_id}
    elif system == "comeet":
        listed = {_normalise(position.get("name") or "") for position in _comeet_positions(board_id, {})}
        if titles & listed:
            return {"comeetId": board_id}
    elif system == "comeet_api":
        comeet_id, listed = _comeet_from_api(board_id)
        if comeet_id and titles & {_normalise(title) for title in listed}:
            return {"comeetId": comeet_id}
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
            groups = groups if isinstance(groups, tuple) else (groups,)
            if system == "comeet_api":
                board_id = ":".join(groups)
            else:
                board_id = next((group for group in groups if group), "")
            if board_id and board_id.lower() not in NOT_IDS:
                found.append((system, board_id))
    return list(dict.fromkeys(found))


def _likely_ids(company):
    """Names a company's board is likely filed under: its web address, its name."""
    domain = (urlsplit(company.get("websiteUrl") or "").hostname or "").removeprefix("www.")
    words = re.findall(r"[a-z0-9]+", company["name"].lower())
    options = [domain.split(".")[0] if domain else "", "".join(words), "-".join(words)]
    return [option for option in dict.fromkeys(options) if len(option) >= 3]


def _page_text(company):
    """The careers page and home page as plain reads, with a careers link followed."""
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
    return text


async def _browser_texts(companies):
    """{company name: every address its careers page loaded, plus the page itself},
    from a real browser, four pages at a time."""
    from playwright.async_api import async_playwright  # only needed with --browser

    texts = {}
    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch(channel="msedge")
        except Exception:  # noqa: BLE001 - no Edge: Playwright's own Chromium
            browser = await playwright.chromium.launch()
        limit = asyncio.Semaphore(4)

        async def one(company):
            async with limit:
                page = await browser.new_page()
                seen = []
                page.on("request", lambda request: seen.append(request.url))
                try:
                    await page.goto(company.get("careersUrl") or company["websiteUrl"],
                                    wait_until="domcontentloaded", timeout=25000)
                    await page.wait_for_timeout(4000)
                    if not company.get("careersUrl"):
                        links = await page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
                        careers = [link for link in links if CAREER_WORDS.search(link)]
                        if careers:
                            await page.goto(careers[0], wait_until="domcontentloaded", timeout=25000)
                            await page.wait_for_timeout(4000)
                    for _ in range(3):  # pages that load jobs as you scroll
                        await page.mouse.wheel(0, 3000)
                        await page.wait_for_timeout(1000)
                    texts[company["name"]] = " ".join(seen + [frame.url for frame in page.frames]) \
                        + " " + await page.content()
                except Exception:  # noqa: BLE001 - a page that won't load is just skipped
                    texts[company["name"]] = " ".join(seen)
                finally:
                    await page.close()

        await asyncio.gather(*(one(company) for company in companies
                               if company.get("careersUrl") or company.get("websiteUrl")))
        await browser.close()
    return texts


def find_board(company, titles, browser_text=""):
    """The verified boards.json entry for one company, or None."""
    text = _page_text(company) + " " + browser_text
    # What the pages name first; then the feeds under the company's likely names,
    # for pages that give nothing away (or name a board that doesn't check out).
    candidates = _found_in(text) + [(system, board_id) for system in ("greenhouse", "lever", "ashby")
                                    for board_id in _likely_ids(company)]
    for system, board_id in dict.fromkeys(candidates):
        entry = _verified(system, board_id, titles)
        if entry:
            return entry
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--browser", action="store_true",
                        help="also open the pages in a browser (needs: pip install playwright)")
    options = parser.parse_args()

    jobs = read_json(JOBS_PATH, [])
    postings = read_json(POSTINGS_PATH, {})
    if not jobs:
        sys.exit("No job data yet: run a full update first (python job_finder/app.py, Update listings).")
    boards = json.loads(BOARDS_PATH.read_text(encoding="utf-8"))
    companies = {company["name"]: company for company in load_companies()}

    # Companies with listings the app can't read: no posting, and no feed or Workday site known.
    titles = defaultdict(set)
    for job in jobs:
        company = companies.get(job["company"])
        if (company and job["url"] not in postings and not company.get("workdaySite")
                and not any(company.get(key) for key in FEED_KEYS)):
            titles[job["company"]].add(_normalise(job["title"]))
    print(f"Looking for the job boards of {len(titles)} companies...", flush=True)

    browser_texts = {}
    if options.browser:
        print("Opening their careers pages in a browser...", flush=True)
        browser_texts = asyncio.run(_browser_texts([companies[name] for name in sorted(titles)]))

    def look(name):
        return name, find_board(companies[name], titles[name], browser_texts.get(name, ""))

    added = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for number, (name, entry) in enumerate(pool.map(look, sorted(titles)), start=1):
            if entry and entry != boards["companies"].get(name):
                added[name] = entry
                print(f"  {name}: {entry}", flush=True)
            if number % 50 == 0:
                print(f"  ...{number}/{len(titles)}", flush=True)

    boards["companies"] = dict(sorted({**boards["companies"], **added}.items()))
    BOARDS_PATH.write_text(json.dumps(boards, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(added)} new boards found and verified; {BOARDS_PATH.name} now lists "
          f"{len(boards['companies'])}.")


if __name__ == "__main__":
    main()
