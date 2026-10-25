# Job Finder

[![Tests](https://github.com/YellowMantis/Job-Finder/actions/workflows/tests.yml/badge.svg)](https://github.com/YellowMantis/Job-Finder/actions/workflows/tests.yml)

**One clear place to find the tech jobs in Israel that actually fit you.**

<img width="1424" height="753" alt="A job's fit review, quoting the CV for each requirement, next to the table of positions" src="https://github.com/user-attachments/assets/4e0504d5-5881-4446-bf80-8b684faeec1c" />


<img width="1434" height="937" alt="The table of positions with fit, distance, work mode and posting date" src="https://github.com/user-attachments/assets/06d23916-8783-48c7-ad77-7bb0e61f8f0f" />


Today it brings together thousands of open positions from hundreds of companies, shows how far
each one is from your home and how well it fits your CV, and links straight to the application.

## Why I built it

During my own job search, my experience with the well-known job sites kept repeating itself:
endless scrolling, postings that turned out to be irrelevant or months old, filters that didn't
really help, company names hidden unless you paid for premium, and CV-match scores behind yet
another subscription, even though I was already paying for an AI.

So I built the tool I wanted: one table with only what matters (the field, the distance from
home, when it was posted, how well it fits my CV), a direct link to apply, and a tick for the
positions I've applied to.

It's free and runs on your own computer. It's also an ongoing project: I keep adding features
and refining it to make it as useful as possible.

## What it does

- **One table of open positions.** Listings from the open [techmap](https://github.com/mluggy/techmap)
  data, plus complete job lists from companies' own hiring systems (Greenhouse, Lever, Ashby,
  SmartRecruiters, Comeet, Workday), without duplicates. Filter by company, field, level, posting age, years of experience asked and distance from your home.
- **A fit score you can check.** An AI reads each posting and lists its requirements, quoting the
  words in your CV that show each one. Code then checks every quote is really in your CV and
  calculates the 0–100% score, so the AI can't invent a match. Open a job to see why it scored
  what it did, line by line.
- **The AI you already have.** Claude Code (with your Claude plan), the Claude API, any service
  with your own key (OpenAI, Groq, OpenRouter…), or a model on your own PC (Ollama, LM Studio).
  Score a batch or a single job, see what each run used, and stop at any time.
- **Your preferences.** Choose the levels and fields you want, how recent a posting must be, and
  any industries to hide. Hidden jobs aren't deleted: each one says why it's hidden.
- **Track applications** with one tick per job.

## Install

From the latest [Release](https://github.com/YellowMantis/Job-Finder/releases):

- **Windows:** download `Job-Finder-Setup.exe` and run it. It installs for you only (no
  administrator rights), adds Job Finder to the Start menu, and can be removed like any app.
  Windows may warn about an unknown publisher, since the app isn't code-signed yet: choose
  "More info" and "Run anyway".
- **macOS (beta):** open `Job-Finder-mac.dmg` and drag Job Finder into Applications. The first
  time, right-click it and choose Open (the app isn't notarised by Apple).
- **Linux (beta):** unpack `Job-Finder-linux.tar.gz` and run `Job Finder` inside.

Nothing else is needed: no Python, Node or Git. The first time, a short setup asks which AI
should score the fit, takes your CV, suggests what to look for, asks where you live, and
downloads the jobs. Change anything later in **Settings**.

When a new version comes out, the app tells you. On Windows one click installs it; on macOS
and Linux it opens the download page. Your data stays either way.

## Privacy and security

- **Everything stays on your computer.** There is no server of ours: your CV, preferences,
  scores and applications are files on your own PC, in `%LOCALAPPDATA%\Job Finder` (macOS:
  `~/Library/Application Support/Job Finder`, Linux: `~/.local/share/job-finder`). Installing a
  new version or uninstalling never touches them.
- **The AI never learns who you are.** Your name, email, phone number, address and links are
  removed from your CV before it's sent to any AI. The CV box shows exactly what the AI receives.
  With a model on your own PC, your CV doesn't leave the computer at all.
- **Keys stay in your system's password safe** (Windows Credential Manager, macOS Keychain),
  never in a file, and are only ever sent to their own service.
- **Only the app can use the app.** It listens on your own computer only, and refuses any
  request that doesn't come from its own window, so other websites open in your browser can't
  reach it.
- **Updates come only from this project's Releases.** The app never installs anything without
  you choosing to.

## Status

Job Finder is in early development (version 0.x).

- **Windows** is the main platform, built and tested.
- **macOS and Linux** builds are made automatically but haven't been tried by many people yet.
- The installer isn't code-signed yet, which is why Windows shows a warning.
- Listings cover the companies that techmap tracks and that have public job boards, so some
  jobs are still missing.

## For developers

### Run from the source code

Requirements: Python 3.12 and Node.js 22.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

cd job_finder/frontend
npm install
npm run build        # builds the page into job_finder/frontend/dist
cd ../..

python job_finder/desktop.py    # in its own window, like the desktop app
python job_finder/app.py        # or in your browser, at http://127.0.0.1:5000
```

Data is then kept in `job_finder/data/`, which Git never uploads.

Working on the page: run `npm run dev` in `job_finder/frontend` alongside `app.py`, and open
http://localhost:5173, which redraws the moment a file is saved.

### Tests and releases

```powershell
python -m pytest                       # the Python side
cd job_finder/frontend; npm test       # the page's logic
```

GitHub Actions runs both, plus a type-check and build of the page, on every push.

To publish a new version: raise `VERSION` in `job_finder/version.py`, commit, and push a tag
with the same number (`git tag v1.2.3`, `git push origin v1.2.3`). GitHub then builds the app
on Windows, macOS and Linux after the tests pass, and publishes them as one Release
(`.github/workflows/release.yml`). To build it yourself: `python job_finder/tools/build_desktop.py`
(on Windows this needs [Inno Setup 6](https://jrsoftware.org/isinfo.php) for the installer).

### How it works

[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) explains everything from start to finish: the
pipeline stage by stage, how the fit score is calculated, the AI providers and connections,
the web app and the desktop app, where data is stored, security, strengths and weaknesses,
and the job of every file.

## Data and credit

Job listings come from [techmap](https://github.com/mluggy/techmap) by Michael Lugassy,
licensed under the Open Database License (ODbL). Posting texts are read from the employers'
own career sites and the public job feeds of their hiring systems. The list of Israeli towns
and villages used to choose your home (`job_finder/src/places_il.json`) comes from
[GeoNames](https://www.geonames.org), licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Licence

[MIT](LICENSE): free to use, copy and change, with no warranty.
