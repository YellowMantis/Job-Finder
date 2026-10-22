"""Build the shared snapshot of every job listing (see src/snapshot.py).

    python job_finder/tools/build_snapshot.py [output file]

GitHub Actions runs this every few hours (.github/workflows/data.yml) and
publishes the file for every copy of the app to download. Output, by default:
job_finder/build/job-data.json.gz
"""

import sys
from pathlib import Path

JOB_FINDER = Path(__file__).parent.parent
sys.path.insert(0, str(JOB_FINDER / "src"))

import snapshot  # noqa: E402
from pipeline import collect_listings  # noqa: E402


class Progress(dict):
    """Prints each stage as it starts, instead of showing it on the page."""
    def __setitem__(self, key, value):
        if key == "stage":
            print(value, flush=True)
        super().__setitem__(key, value)

    def update(self, *args, **changes):
        for key, value in dict(*args, **changes).items():
            self[key] = value


def main():
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else JOB_FINDER / "build" / "job-data.json.gz"
    output.parent.mkdir(parents=True, exist_ok=True)
    jobs, _, companies = collect_listings(Progress(done=0, total=0))
    snapshot.write(snapshot.build(jobs, companies), output)
    print(f"{len(jobs)} jobs, {output.stat().st_size / 1e6:.1f} MB: {output}")


if __name__ == "__main__":
    main()
