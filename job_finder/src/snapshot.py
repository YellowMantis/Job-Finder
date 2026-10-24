"""The shared snapshot: every job listing, built once for everyone.

Every user would otherwise download the same 38 MB from techmap and ask the
same job boards the same questions. Instead, GitHub Actions runs the part of an
update that is the same for everyone (pipeline.collect_listings) every few
hours and publishes the result as one compressed file (tools/build_snapshot.py,
.github/workflows/data.yml). The app downloads that file, a few hundred KB, and
then fetches only the posting texts for its own user's jobs.

What it holds: the labelled jobs with their positions, and which companies have
job boards. Nothing personal (no CV, preferences or scores), and no posting
texts: those are the employers' own words, so each app reads them itself.

FORMAT is raised whenever the file's shape changes. An app that finds a newer
format than it knows doesn't use it (it falls back to the full update) until
the app itself is updated.
"""

import gzip
import json
from datetime import datetime, timezone

import httpx

from settings import DATA_DIR, SNAPSHOT_URL

FORMAT = 1
ETAG_PATH = DATA_DIR / "snapshot_etag.json"
BOARD_KEYS = ("greenhouseId", "leverId", "comeetId", "workdaySite")


class Unavailable(Exception):
    """The snapshot can't be used now (offline, not published, newer format)."""


def company_boards(companies):
    """{company name: its job board and careers system ids}, for companies that have any."""
    return {company["name"]: {key: company[key] for key in BOARD_KEYS if company.get(key)}
            for company in companies if any(company.get(key) for key in BOARD_KEYS)}


def build(jobs, companies):
    """The snapshot's contents, ready to write as compressed JSON."""
    return {"format": FORMAT, "built": datetime.now(timezone.utc).isoformat(timespec="minutes"),
            "jobs": jobs, "companies": company_boards(companies)}


def write(contents, path):
    path.write_bytes(gzip.compress(json.dumps(contents, ensure_ascii=False).encode("utf-8")))


def download():
    """The latest snapshot, or None if it hasn't changed since the last download.
    Raises Unavailable when it can't be used."""
    # The tag of the last download: if the file is unchanged, the server says
    # "not modified" instead of sending it again.
    saved = json.loads(ETAG_PATH.read_text(encoding="utf-8")) if ETAG_PATH.exists() else {}
    headers = {"If-None-Match": saved["etag"]} if saved.get("etag") else {}
    try:
        response = httpx.get(SNAPSHOT_URL, headers=headers, follow_redirects=True, timeout=60)
    except httpx.HTTPError as error:
        raise Unavailable(f"can't reach the snapshot: {type(error).__name__}") from error
    if response.status_code == 304:
        return None
    if response.status_code != 200:
        raise Unavailable(f"the snapshot answered {response.status_code}")
    try:
        contents = json.loads(gzip.decompress(response.content))
    except (OSError, ValueError) as error:
        raise Unavailable("the snapshot file is damaged") from error
    if contents.get("format") != FORMAT:
        raise Unavailable(f"the snapshot's format {contents.get('format')} is newer than this app")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ETAG_PATH.write_text(json.dumps({"etag": response.headers.get("etag", ""),
                                     "built": contents.get("built")}), encoding="utf-8")
    return contents
