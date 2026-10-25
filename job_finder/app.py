"""The job finder's web app. It runs on your own PC only.

Start it from the project folder:
    python job_finder/app.py

Your browser opens http://127.0.0.1:5000. Press Ctrl+C in the terminal to stop.

How a web app is split:
  - this file is the "back end": it answers requests with data (as JSON)
  - job_finder/frontend/ is the "front end": the page, written in React and
    TypeScript. "npm run build" turns it into plain files in frontend/dist,
    which this file serves.
The page asks this file for data at addresses starting with /api/.
"""

import hashlib
import json
import os
import sys
import threading
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pdfplumber
from flask import Flask, jsonify, request, send_from_directory

# The pipeline code lives in job_finder/src; let Python find it.
sys.path.insert(0, str(Path(__file__).parent / "src"))

import migrations  # noqa: E402
import new_jobs  # noqa: E402
import updates  # noqa: E402
import scoring  # noqa: E402
import places  # noqa: E402
from industries import INDUSTRIES  # noqa: E402
from pipeline import (APPLIED_PATH, FITS_PATH, JOBS_PATH, POSTINGS_PATH,  # noqa: E402
                      jobs_for_display, read_json, refresh_listings, write_json)
from preferences import (FIELDS, LEVELS, PREFERENCES_PATH, check_preferences,  # noqa: E402
                         load_preferences, save_preferences)
import connections  # noqa: E402
import cv_privacy  # noqa: E402
from providers import ProviderError  # noqa: E402
from providers.claude_code import find_claude  # noqa: E402
from providers.ollama import installed_models  # noqa: E402
from settings import DATA_DIR, RADIUS_KM, REFRESH_AFTER_HOURS, TECHMAP_CREDIT  # noqa: E402
from version import VERSION  # noqa: E402

# The built page (job_finder/frontend, after "npm run build").
WEB_DIR = Path(__file__).parent / "frontend" / "dist"
CV_PDF_PATH = DATA_DIR / "cv.pdf"
CV_TEXT_PATH = DATA_DIR / "cv.txt"
CV_INFO_PATH = DATA_DIR / "cv_info.json"

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # refuse uploads over 10 MB

# Only this app's own page may use it. The server listens on 127.0.0.1, which
# other computers can't reach, but any website open in your browser can still
# send requests there. So every request is checked before it is answered:
#   Host            the name the request was sent to. A site that tricks the
#                   browser into treating 127.0.0.1 as its own name ("DNS
#                   rebinding", which would let it read the answers, your CV
#                   included) still sends its own name here.
#   Origin          the page that sent it, which browsers add to every POST and
#                   to requests from other sites: it must be this app's page.
#   Sec-Fetch-Site  browsers say "cross-site" when another site sent it.
LOCAL_NAMES = {"127.0.0.1", "localhost"}


def _is_local(address):
    """"127.0.0.1:5000" or "http://localhost:5173" -> True; "evil.example" -> False."""
    return urlsplit(address if "//" in address else f"//{address}").hostname in LOCAL_NAMES


@app.before_request
def only_this_apps_page():
    origin = request.headers.get("Origin")
    if (not _is_local(request.host)
            or (origin is not None and not _is_local(origin))
            or request.headers.get("Sec-Fetch-Site") == "cross-site"):
        return jsonify({"error": "Refused: this request didn't come from Job Finder's own page."}), 403
    return None

# Progress of the two long jobs, which run in the background. The page asks
# for these every couple of seconds while one is running.
# stop_requested: you asked to stop; scoring ends after the current batch.
# started: when scoring began (seconds since 1970). The page shows the time so far,
# since a batch's jobs only count as done once the whole batch is back.
fit_progress = {"running": False, "done": 0, "total": 0, "error": "", "stop_requested": False,
                "started": 0}
update_progress = {"running": False, "stage": "", "done": 0, "total": 0, "error": "",
                   "summary": None}


def cv_id():
    """A short fingerprint of the loaded CV's text, or None if no CV is loaded.
    Fit reviews are stored with it, so a review is never shown for a different CV."""
    if not CV_TEXT_PATH.exists():
        return None
    return hashlib.sha1(CV_TEXT_PATH.read_bytes()).hexdigest()[:12]


@app.get("/")
def home_page():
    if not (WEB_DIR / "index.html").exists():
        return ("<p>The page hasn't been built yet. In a terminal, run:</p>"
                "<pre>cd job_finder/frontend\nnpm install\nnpm run build</pre>"
                "<p>then reload this page.</p>"), 503
    return send_from_directory(WEB_DIR, "index.html")


@app.get("/api/status")
def status():
    """What the page needs to know when it loads."""
    updated = None
    if JOBS_PATH.exists():
        updated = datetime.fromtimestamp(JOBS_PATH.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    try:
        provider = connections.active_provider()
        scorer = {"id": provider.connection_id, "name": provider.label,
                  "kind": provider.id, "batch_size": provider.batch_size}
    except ProviderError:
        scorer = None  # no AI connection yet: jobs can be filtered and tracked, not scored
    preferences = load_preferences()
    return jsonify({"cv": read_json(CV_INFO_PATH, None), "jobs_updated": updated,
                    "home": (preferences["home"] or {}).get("name", ""), "default_max_km": RADIUS_KM,
                    "default_fields": preferences["fields"], "credit": TECHMAP_CREDIT,
                    "scorer": scorer,
                    # First run: no preferences saved yet, so the page shows the setup.
                    "setup_needed": not PREFERENCES_PATH.exists(),
                    "startup_problem": startup_problem,
                    "version": VERSION, "update": available_update,
                    # Jobs that first appeared after this are marked new. Asking
                    # for the status also counts as using the app (new_jobs.visit).
                    "new_since": new_jobs.visit()})


@app.get("/api/jobs")
def jobs():
    """The rows your preferences show, without their posting texts: the page
    asks for one text at a time (/api/posting) when you open a job, so the
    table stays small. Hidden jobs are only counted until you ask to see them
    (/api/hidden)."""
    rows = jobs_for_display(cv_id())
    shown = [{key: value for key, value in row.items() if key != "text"}
             for row in rows if not row["hidden"]]
    return jsonify({"jobs": shown, "hidden_count": len(rows) - len(shown)})


@app.get("/api/posting")
def posting_text():
    """The full posting text of one job, asked for by its link."""
    posting = read_json(POSTINGS_PATH, {}).get(request.args.get("url", ""))
    return jsonify({"text": posting["text"] if posting else ""})


@app.get("/api/hidden")
def hidden():
    """The jobs your preferences hide: just the three columns the Hidden tab shows."""
    return jsonify([{"title": row["title"], "company": row["company"], "reason": row["hidden"]}
                    for row in jobs_for_display(cv_id()) if row["hidden"]])


@app.get("/api/preferences")
def get_preferences():
    """Your preferences, and every choice the page can offer."""
    return jsonify({"preferences": load_preferences(), "levels": LEVELS, "fields": FIELDS,
                    "industries": {key: card["label"] for key, card in INDUSTRIES.items()}})


@app.post("/api/update-app")
def update_app():
    """Install the newer version you chose to install. On Windows the new
    installer opens and this app closes, so the installer can replace it."""
    if available_update is None:
        return jsonify({"error": "No newer version is known."}), 400
    try:
        closing = updates.install(available_update)
    except httpx.HTTPError as error:  # the kind of problem, not the raw details
        return jsonify({"error": "The update couldn't be downloaded "
                                 f"({type(error).__name__}). Try again later."}), 400
    except ValueError:  # an installer from anywhere but this project's Releases
        return jsonify({"error": "That update didn't come from this project's Releases, "
                                 "so it wasn't installed."}), 400
    if closing:
        threading.Timer(1.0, os._exit, args=[0]).start()  # after this answer reaches the page
    return jsonify({"closing": closing})


@app.get("/api/places")
def find_places():
    """Towns and villages matching what was typed (English or Hebrew), to
    choose your home. Data: GeoNames (CC BY 4.0)."""
    return jsonify(places.search(request.args.get("q", "")))


@app.post("/api/preferences")
def set_preferences():
    preferences = request.get_json()
    problem = check_preferences(preferences)
    if problem:
        return jsonify({"error": problem}), 400
    save_preferences(preferences)
    return jsonify(load_preferences())


def run_update():
    """Download fresh listings and fetch new posting texts, in the background."""
    try:
        update_progress["summary"] = refresh_listings(update_progress)
    except Exception as error:  # shown on the page instead of crashing the thread silently
        update_progress["error"] = f"Updating stopped: {error}"
    finally:
        update_progress["running"] = False


# A problem found when the app started that the page must show (for example,
# data saved by a newer version of the app). None when all is well.
startup_problem = None
# A newer version of the app, if GitHub has one (updates.check), else None.
available_update = None


def start_up():
    """What the app does before showing anything: bring the data up to date
    with this version of the app, then refresh listings if they're old."""
    global startup_problem
    startup_problem = migrations.run()
    if startup_problem is None:
        refresh_if_stale()
    # Asking GitHub can take a moment: in the background, so the app opens at once.
    threading.Thread(target=_check_for_update, daemon=True).start()


def _check_for_update():
    global available_update
    available_update = updates.check(VERSION)


def refresh_if_stale(now=None):
    """Called when the app starts: if the listings are older than
    REFRESH_AFTER_HOURS, refresh them in the background. The page shows the
    update's progress as usual. Not during the first-run setup, which starts
    its own download when it finishes. Returns whether it started one."""
    if update_progress["running"] or not PREFERENCES_PATH.exists() or not JOBS_PATH.exists():
        return False
    age_hours = ((now or datetime.now().timestamp()) - JOBS_PATH.stat().st_mtime) / 3600
    if age_hours < REFRESH_AFTER_HOURS:
        return False
    update_progress.update(running=True, stage="Starting", done=0, total=0, error="", summary=None)
    threading.Thread(target=run_update, daemon=True).start()
    return True


@app.post("/api/update")
def start_update():
    if not update_progress["running"]:
        update_progress.update(running=True, stage="Starting", done=0, total=0, error="",
                               summary=None)
        threading.Thread(target=run_update, daemon=True).start()
    return jsonify(update_progress)


@app.get("/api/update/status")
def update_status():
    return jsonify(update_progress)


@app.post("/api/cv")
def upload_cv():
    """Receive a CV PDF, keep it, and extract its text for the fit agent."""
    file = request.files.get("cv")
    if file is None:
        return jsonify({"error": "No file received."}), 400

    data = file.read()
    # Real PDF files start with these four characters, whatever they are named.
    if not data.startswith(b"%PDF"):
        return jsonify({"error": "That file is not a PDF."}), 400

    DATA_DIR.mkdir(exist_ok=True)
    # Always saved under our own fixed name, never the name the browser sent.
    CV_PDF_PATH.write_bytes(data)

    with pdfplumber.open(CV_PDF_PATH) as pdf:
        text = "\n\n".join(page.extract_text() or "" for page in pdf.pages).strip()
    if not text:
        return jsonify({"error": "No text found in that PDF. Is it a scanned image?"}), 400

    # The same CV again (identical text) keeps the years you corrected; a
    # different CV has its years read afresh when it is first scored.
    same_cv = CV_TEXT_PATH.exists() and CV_TEXT_PATH.read_text(encoding="utf-8") == text
    previous = read_json(CV_INFO_PATH, {}) if same_cv else {}

    CV_TEXT_PATH.write_text(text, encoding="utf-8")
    info = {"name": file.filename, "characters": len(text),
            "uploaded": datetime.now().strftime("%Y-%m-%d %H:%M")}
    if "professional_years" in previous:
        info["professional_years"] = previous["professional_years"]
    write_json(CV_INFO_PATH, info)
    return jsonify(info)


def cv_for_ai():
    """The CV as an AI receives it: without your name, contact details and links."""
    return cv_privacy.for_ai(CV_TEXT_PATH.read_text(encoding="utf-8"))


@app.get("/api/cv/sent")
def cv_sent():
    """Exactly what an AI is sent of your CV, so you can check it."""
    if not CV_TEXT_PATH.exists():
        return jsonify({"error": "Drop your CV first."}), 400
    return jsonify({"text": cv_for_ai()})


@app.post("/api/cv/suggest")
def suggest_preferences():
    """Suggest preferences for the loaded CV, using the AI connection in use:
    levels (from the years of paid work), fields and job titles. Your
    current preferences are the starting point; nothing is saved here except the
    years, so a later scoring run doesn't need to read them again."""
    if not CV_TEXT_PATH.exists():
        return jsonify({"error": "Drop your CV first."}), 400
    try:
        suggestions = scoring.suggest_from_cv(connections.active_provider(), cv_for_ai())
    except ProviderError as error:
        return jsonify({"error": str(error)}), 400

    info = read_json(CV_INFO_PATH, {})
    info["professional_years"] = suggestions.professional_years
    write_json(CV_INFO_PATH, info)

    suggested = {**load_preferences(), "levels": scoring.level_for(suggestions.professional_years)}
    if suggestions.fields:
        suggested["fields"] = suggestions.fields
    return jsonify({"preferences": suggested, "roles": suggestions.roles,
                    "professional_years": suggestions.professional_years})


@app.post("/api/cv/years")
def set_years():
    """Correct the years of paid work read from the CV. Used for new scores."""
    years = request.get_json().get("years")
    if not isinstance(years, int) or not 0 <= years <= 50:
        return jsonify({"error": "Years must be a whole number from 0 to 50."}), 400
    info = read_json(CV_INFO_PATH, None)
    if info is None:
        return jsonify({"error": "Drop your CV first."}), 400
    info["professional_years"] = years
    write_json(CV_INFO_PATH, info)
    return jsonify(info)


def score_jobs(wanted_urls, again=False):
    """Score the given jobs that have posting text and no review yet for this CV;
    with again=True, also the ones already scored (to score them anew, for
    example with another AI). Runs in a background thread, updating
    fit_progress as it goes."""
    try:
        cv_text = cv_for_ai()  # without your name and contact details
        current_cv = cv_id()

        provider = connections.active_provider()  # the AI connection in use

        # Work out the CV's years of experience once per CV, and remember it.
        info = read_json(CV_INFO_PATH, {})
        if "professional_years" not in info:
            info.update(scoring.read_cv_facts(provider, cv_text))
            write_json(CV_INFO_PATH, info)
        years = info["professional_years"]

        fits = read_json(FITS_PATH, {})
        # Jobs with no score for this CV yet. A score stays valid whichever AI
        # connection made it; scoring again is your choice (again=True), never automatic.
        todo = [job for job in jobs_for_display(current_cv)
                if job["url"] in wanted_urls and job["has_text"] and not job["hidden"]
                and (again or job["fit"] is None)]
        fit_progress.update(done=0, total=len(todo))

        # Each provider reviews a few jobs per request (Claude Code 10, a local
        # model 1), and an API may run several requests at the same time.
        size = provider.batch_size
        batches = [todo[start:start + size] for start in range(0, len(todo), size)]
        lock = threading.Lock()

        def score_batch(batch):
            if fit_progress["stop_requested"]:
                return  # a batch already started is never cut off: its work is kept
            reviews = scoring.review_batch(provider, cv_text, years, batch)
            with lock:
                for url, fit in reviews.items():
                    fit["cv"] = current_cv
                    fit["scored"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    fits[url] = fit
                write_json(FITS_PATH, fits)  # saved after every batch, so stopping loses little
                fit_progress["done"] += len(batch)

        with ThreadPoolExecutor(max_workers=provider.requests_at_once) as pool:
            for _ in pool.map(score_batch, batches):
                pass  # waiting for each in turn; a failed batch raises here
    except ProviderError as error:  # the AI can't be used: say why, plainly
        fit_progress["error"] = str(error)
    except Exception as error:  # shown on the page instead of crashing the thread silently
        fit_progress["error"] = f"Scoring stopped: {error}"
    finally:
        fit_progress["running"] = False


@app.post("/api/fit/start")
def start_fit():
    """Score the jobs the page sends: the ones currently shown in the table."""
    if cv_id() is None:
        return jsonify({"error": "Drop your CV first."}), 400
    body = request.get_json()
    urls = set(body.get("urls", []))
    if not fit_progress["running"]:
        fit_progress.update(running=True, done=0, total=0, error="", stop_requested=False,
                            started=datetime.now().timestamp())
        threading.Thread(target=score_jobs, args=(urls, bool(body.get("again"))),
                         daemon=True).start()
    return jsonify(fit_progress)


@app.post("/api/applied")
def set_applied():
    """Remember (or forget) that you applied to a job. The page sends the
    job's link and whether its box is now ticked."""
    body = request.get_json()
    applied = read_json(APPLIED_PATH, {})
    if body["applied"]:
        applied[body["url"]] = datetime.now().strftime("%Y-%m-%d")
    else:
        applied.pop(body["url"], None)
    write_json(APPLIED_PATH, applied)
    return jsonify({"applied": applied.get(body["url"])})


@app.get("/api/fit/status")
def fit_status():
    return jsonify(fit_progress)


@app.post("/api/fit/stop")
def stop_fit():
    """Finish the batch being scored, then stop."""
    if fit_progress["running"]:
        fit_progress["stop_requested"] = True
    return jsonify(fit_progress)


@app.get("/api/fit/log")
def fit_log():
    """The most recent scoring batches: when, how many jobs, tokens, time and
    the pay-per-use price equivalent (0 for a local model)."""
    batches = [record for record in read_json(scoring.SCORING_LOG_PATH, [])
               if record.get("task") == "score jobs"]
    return jsonify(batches[-20:])


# ---- AI connections ------------------------------------------------------------
# Keys come in with a request and go straight to the password safe; they are
# never sent back to the page, only a masked hint ("gsk_…3f9a").

def _connections_answer():
    return jsonify({**connections.for_page(), "kinds": connections.KINDS,
                    "services": connections.PAGE_SERVICES})


@app.get("/api/connections")
def list_connections():
    return _connections_answer()


@app.post("/api/connections")
def add_connection():
    body = request.get_json()
    fields = body.get("fields", {})
    problem = connections.check(fields)
    if problem:
        return jsonify({"error": problem}), 400
    try:
        connections.add(fields, body.get("key", ""))
    except ProviderError as error:
        return jsonify({"error": str(error)}), 400
    return _connections_answer()


@app.post("/api/connections/<connection_id>")
def update_connection(connection_id):
    """Change a connection. "key" left out keeps the stored key."""
    body = request.get_json()
    fields = body.get("fields", {})
    problem = connections.check(fields)
    if problem:
        return jsonify({"error": problem}), 400
    try:
        connections.update(connection_id, fields, body.get("key"))
    except ProviderError as error:
        return jsonify({"error": str(error)}), 400
    return _connections_answer()


@app.delete("/api/connections/<connection_id>")
def delete_connection(connection_id):
    try:
        connections.remove(connection_id)
    except ProviderError as error:
        return jsonify({"error": str(error)}), 404
    return _connections_answer()


@app.post("/api/connections/<connection_id>/activate")
def activate_connection(connection_id):
    """Score with this connection from now on."""
    if fit_progress["running"]:
        return jsonify({"error": "Wait for the scoring under way to finish first."}), 409
    try:
        connections.activate(connection_id)
    except ProviderError as error:
        return jsonify({"error": str(error)}), 404
    return _connections_answer()


@app.post("/api/connections/<connection_id>/calibrate")
def calibrate_connection(connection_id):
    """You type the "current session" % that Claude Code's /usage shows; the app
    divides it by the tokens it used in the same 5 hours, to estimate later
    batches as a % of your session."""
    percent = (request.get_json() or {}).get("percent")
    if not isinstance(percent, (int, float)) or isinstance(percent, bool) or not 0 < percent <= 100:
        return jsonify({"error": "Type the % that /usage shows, a number from 1 to 100."}), 400
    tokens = scoring.tokens_used_recently(connection_id)
    if not tokens:
        return jsonify({"error": "Score a batch first: there's nothing from the last 5 hours "
                                 "to compare the % with."}), 400
    try:
        connections.calibrate(connection_id, percent, tokens)
    except ProviderError as error:
        return jsonify({"error": str(error)}), 404
    return _connections_answer()


def _provider_from_request(body):
    """A provider for a connection being set up or edited, from the fields sent.
    The key sent is used; if none is sent for a saved connection (body "id"),
    its saved key is, so editing doesn't mean pasting the key again."""
    saved = None
    if body.get("id"):
        saved = next((c for c in connections.load()["connections"] if c["id"] == body["id"]), None)
        if saved is None:
            raise ProviderError("That AI connection doesn't exist any more.")
    fields = connections._clean({"name": "This service", **(body.get("fields") or saved or {})})
    key = body.get("key") or (connections.get_key(saved["id"]) if saved else "")
    return connections.provider_for(fields, key)


@app.post("/api/connections/models")
def connection_models():
    """The models a service offers, to choose from a list instead of typing."""
    try:
        return jsonify({"models": _provider_from_request(request.get_json()).list_models()})
    except ProviderError as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/connections/test")
def test_connection():
    """Send one tiny request, so you know a connection works before scoring.
    It uses a few tokens (for Claude Code about 5,000, its fixed start-up cost)."""
    body = request.get_json()
    try:
        provider = _provider_from_request(body)
        if not body.get("id"):
            provider.connection_id = "test"
        answer = scoring.check_connection(provider)
    except ProviderError as error:
        return jsonify({"ok": False, "error": str(error)})
    return jsonify({"ok": True, **answer})


@app.post("/api/connections/detect")
def detect_local_ai():
    """Look on this computer, only when you ask, and only for what you asked:
    "claude" (is the Claude Code program installed?) or "local" (are Ollama or
    LM Studio running, and with which models?). Nothing is sent anywhere."""
    what = (request.get_json() or {}).get("what")
    found = {"claude": None, "ollama": None, "lmstudio": None}
    if what == "claude":
        found["claude"] = find_claude() is not None
    if what == "local":
        try:
            found["ollama"] = installed_models()
        except ProviderError:
            pass  # not running
        try:
            lmstudio = connections.provider_for({"kind": "api", "name": "LM Studio", "model": "",
                                                 "base_url": connections.SERVICES["lmstudio"][1]}, "")
            found["lmstudio"] = lmstudio.list_models()
        except ProviderError:
            pass
    return jsonify(found)


if __name__ == "__main__":
    address = "http://127.0.0.1:5000"
    # Open the browser a moment after the server starts.
    threading.Timer(1.0, webbrowser.open, args=[address]).start()
    print(f"Job finder running at {address}  (Ctrl+C to stop)")
    start_up()
    # 127.0.0.1 means only this computer can reach the app.
    app.run(host="127.0.0.1", port=5000)
