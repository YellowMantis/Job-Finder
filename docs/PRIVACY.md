# Privacy policy: Veri – IL Tech Jobs

*Last updated: 20 November 2026*

Veri (formerly Job Finder) is a free, open-source desktop app that helps you find tech jobs in
Israel that fit your CV. This page explains what the app does with your information.

**In short:** everything stays on your computer. Veri has no server and no accounts, and it
doesn't track you. It only connects to job sites, to the AI you choose, and to GitHub.

## What stays on your computer

Everything you give the app, and everything it works out for you, is kept in files on your own
computer:

- your CVs, and the text read from them;
- your preferences: what you look for, your home town (which you type yourself), your filters;
- the jobs, their fit scores, the jobs you hid, and the applications you marked;
- the list of AI connections you added.

On Windows, with the installer from the website, they're in `%LOCALAPPDATA%\Job Finder`, the
folder name the app has always used. On macOS they're in `~/Library/Application Support/Job Finder`,
and on Linux in `~/.local/share/job-finder`. Updating or uninstalling the app doesn't delete them.
Delete the folder to remove them.

The copy from the **Microsoft Store** keeps what it creates in its own folder, which Windows sets
aside for it (under `%LOCALAPPDATA%\Packages`), and Windows deletes that folder when you uninstall
it. If Veri was installed before from GitHub, the Store copy finds the files already in
`%LOCALAPPDATA%\Job Finder` and uses them where they are; uninstalling it leaves those.

**AI keys** are kept in your system's password safe (Windows Credential Manager, macOS
Keychain), never in a file. A key is only ever sent to the service it belongs to.

The app doesn't look through your computer. It reads only the files you choose to give it.

## What leaves your computer, and where it goes

Veri connects to the internet for three things only.

### 1. Job listings

The app downloads public job listings:
- from this project's GitHub page, where a shared copy of the listings is updated every few
  hours;
- from the public careers pages and job boards of the companies themselves (such as Greenhouse,
  Lever, Ashby, SmartRecruiters, Comeet and Workday).

These requests contain nothing about you. As with visiting any website, those sites can see your
computer's internet address.

### 2. The AI that scores the fit

To score how well a job fits you, the app sends the AI you chose:
- **your CV without your name and contact details**: your name, email address, phone number,
  address and profile links are removed on your computer first;
- the text of the job postings being scored.

You can see exactly what the AI receives in the app ("See what the AI receives").

You choose the AI in Settings and can change it at any time:
- **Claude Code** runs through your own Claude account.
- **An AI service with your own key**: Anthropic, OpenAI, Google Gemini, Groq, OpenRouter,
  Mistral or DeepSeek.
- **A model on your own computer** (Ollama or LM Studio): nothing leaves your computer at all.

What the AI service then does with that text is governed by its own privacy policy and the terms
of your account with it. Some services' free plans may use what you send to improve their
models, so check that service's policy if this matters to you.

### 3. Updates

When it starts, the app asks GitHub whether a newer version exists, using the same public
information shown on the project's Releases page. Nothing about you is sent. Copies installed
from the Microsoft Store skip this, because the Store installs the updates.

## What Veri doesn't do

- No analytics, tracking or advertising.
- No accounts, and no server of ours that receives your data.
- Nothing is sold or shared with anyone.
- It doesn't apply to jobs for you or contact employers.
- It doesn't read LinkedIn or any site whose terms forbid it.

## Deleting your data

- To delete a CV and every score made for it: **Settings → Your CVs → Delete with its scores**.
  This also removes the backups the app keeps before upgrades.
- To remove an AI connection and its key: **Settings → AI connections → Remove**.
- To remove everything: remove your AI connections (their keys are in the password safe, which
  uninstalling doesn't clear), then uninstall the app. With the installer from the website, also
  delete the data folder listed above.

## Children

Veri is a job-search tool meant for adults and isn't directed at children.

## Changes to this policy

If the app starts handling information differently, this page will be updated first, and the
date at the top will change. The full history of this page is public in the project's
repository.

## Contact

Questions, or something that looks wrong: open an issue at
https://github.com/YellowMantis/Job-Finder/issues

The app's code is open source, so anyone can check that it does what this page says.
