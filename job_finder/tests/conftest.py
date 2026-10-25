"""pytest reads this file before running any test in this folder.

The job finder's code lives in job_finder/src and imports itself by plain
module names ("from settings import ..."), so that folder must be on Python's
search path, exactly as app.py arranges at its start. job_finder itself is
added too, so tests can import the web app (app.py).
"""

import sys
from pathlib import Path

JOB_FINDER = Path(__file__).parent.parent
sys.path.insert(0, str(JOB_FINDER / "src"))
sys.path.insert(0, str(JOB_FINDER))


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def new_jobs_files_in_a_test_folder(tmp_path, monkeypatch):
    """Asking for the app's status records a visit, and updates record when
    jobs first appeared (new_jobs.py). In every test those files go to the
    test's own empty folder, never to your real data."""
    import new_jobs
    monkeypatch.setattr(new_jobs, "FIRST_SEEN_PATH", tmp_path / "first_seen.json")
    monkeypatch.setattr(new_jobs, "VISITS_PATH", tmp_path / "visits.json")
