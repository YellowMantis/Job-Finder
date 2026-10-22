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
