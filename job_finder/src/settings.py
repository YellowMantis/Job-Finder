"""Settings for the job finder: where you live, how far to search, where files go.

Change the values here; the other files read them from this one place.
"""

import os
import subprocess
import sys
from pathlib import Path

# Jobs from the whole country are downloaded; distance is a filter in the page.
# This is where the distance filter starts (a 60 minute drive in the north is
# roughly 50 km in a straight line).
RADIUS_KM = 50

# All job categories are downloaded. These are the fields a new user starts
# with (preferences.py); posting texts are only fetched for the chosen fields.
JOB_CATEGORIES = ["software", "frontend", "qa", "devops", "data-science"]

# --- How a job's level is recognised -----------------------------------------
# These label jobs; your preferences (preferences.py) decide which levels show.
# Which industries a company is in is decided in industries.py.

# A job is labelled senior if its title contains one of these words...
SENIOR_WORDS = ["senior", "sr", "lead", "leader", "manager", "principal", "staff",
                "architect", "director", "head", "vp", "expert", "experienced"]
# ...or if the data labels its level as one of these.
SENIOR_LEVELS = ["Manager", "Executive", "Architect", "Tech Lead"]

# Words in a title that mark a job as aimed at beginners.
JUNIOR_WORDS = ["junior", "jr", "entry", "graduate", "graduates", "new grad", "grad", "intern",
                "internship", "student"]

# --- Company career sites ----------------------------------------------------

# Where companies' job boards and careers sites are, when techmap's data doesn't
# say (or is out of date), is in src/boards.json, found and checked by
# tools/find_boards.py.

# Pause between requests to a careers site, so we never load it heavily.
SECONDS_BETWEEN_REQUESTS = 1

# How many different sites are read at the same time during an update. Each
# site still gets one request at a time with the pause above, so no site sees
# more traffic; the update just doesn't wait for one site before the next.
SITES_AT_ONCE = 4

# A posting that wasn't found on its company's site (the listing is on techmap,
# but not on the careers page) isn't looked for again for this many days.
RETRY_MISSING_POSTINGS_AFTER_DAYS = 3

# When the app starts with listings older than this, they are refreshed in the
# background, so you rarely wait for "Update listings" yourself.
REFRESH_AFTER_HOURS = 12

# --- Updates ------------------------------------------------------------------

# The GitHub repository whose Releases hold new versions of the app (see
# updates.py). While it is private, GitHub doesn't answer, and no update is offered.
UPDATES_REPOSITORY = "YellowMantis/Job-Finder"

# The shared snapshot of all job listings (snapshot.py), published every few
# hours on the repository's "data" Release by .github/workflows/data.yml.
SNAPSHOT_URL = f"https://github.com/{UPDATES_REPOSITORY}/releases/download/data/job-data.json.gz"


# --- Fit scoring --------------------------------------------------------------

# Who reads the job postings for the fit score is chosen in the app (Settings,
# AI connections); see job_finder/src/connections.py. These are fixed details.

# How many jobs Claude scores in one session. Each session has a fixed start-up
# cost in tokens, so batches share it; very large batches risk sloppier reviews.
CLAUDE_BATCH_SIZE = 10

# Where Ollama answers on this PC, and jobs per request (small models lose
# track in long prompts, so one at a time).
OLLAMA_ADDRESS = "http://localhost:11434"
OLLAMA_BATCH_SIZE = 1

# Jobs per request for a service that speaks the OpenAI format.
API_BATCH_SIZE = 5

# --- Programs we start --------------------------------------------------------

# On Windows, a program started from the desktop app (which has no console of its
# own) would open a black console window. This flag starts it without one;
# everything it prints is still captured. Elsewhere it is 0: no effect.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# --- Where files go ----------------------------------------------------------

JOB_FINDER_DIR = Path(__file__).parent.parent


def _user_data_folder():
    """Where the packaged desktop app keeps your data: the system's usual place
    for one user's app data, which survives updating or moving the app."""
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Job Finder"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Job Finder"
    return Path.home() / ".local" / "share" / "job-finder"


# Running from the source code: job_finder/data. As the desktop app (PyInstaller
# sets sys.frozen): the user's app data folder.
DATA_DIR = _user_data_folder() if getattr(sys, "frozen", False) else JOB_FINDER_DIR / "data"

# The open data this project is built on: Israeli tech companies and their open
# positions, by Michael Lugassy (https://github.com/mluggy/techmap), licensed
# under the Open Database License. The licence requires this credit.
TECHMAP_URL = "https://github.com/mluggy/techmap.git"
TECHMAP_DIR = DATA_DIR / "techmap"
TECHMAP_CREDIT = "Data: techmap by Michael Lugassy, https://github.com/mluggy/techmap (ODbL)"
