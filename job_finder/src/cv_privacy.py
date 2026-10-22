"""What an AI is sent of your CV: everything except who you are and how to reach you.

Scoring needs your skills, jobs, dates and studies. It doesn't need your name,
email, phone number, address or profile links, so those are removed here, on
this PC, before the CV goes to any AI, whichever one you use.

A CV starts with a header: your name, then lines of contact details, until the
first section heading ("EXPERIENCE"). So:

  the name line      the first line, when it is your name
  in the header      every line with contact details (an email address, phone
                     number, link, or the word LinkedIn or GitHub). The whole
                     line goes: what else is on it (an address, a postcode, a
                     link's label) is contact detail too.
  everywhere else    emails, phone numbers, links and your name are cut out, and
                     the rest of the line is kept.

The AI is told these were removed on purpose (fit_rules.SYSTEM_PROMPT), so their
absence never counts against you. (Your home town, for distances, is one you
type in the setup; nothing reads it from the CV.)

The page shows exactly what is sent ("See what the AI receives").
"""

import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Web links. Bare domains only for profile sites, so "Socket.io" or "Node.js"
# in a skills list are left alone.
LINK = re.compile(r"(?:https?://|www\.)\S+|\b(?:linkedin|github|gitlab|behance|dribbble)\.com/\S*",
                  re.IGNORECASE)
# A run of digits with spaces, dots, dashes or brackets: a phone number if it
# has 9 to 15 digits. Date ranges such as "2021 - 2026" are kept (see _is_phone).
NUMBER_RUN = re.compile(r"\+?\d[\d\s().-]{6,}\d")
PROFILE_WORDS = re.compile(r"\b(linkedin|github|portfolio)\b", re.IGNORECASE)
HEADER_LINES = 5  # a header is never longer than this
HEADINGS = {"experience", "work experience", "professional experience", "education", "skills",
            "summary", "profile", "about", "about me", "projects", "ניסיון", "ניסיון תעסוקתי",
            "השכלה", "כישורים", "פרופיל", "תקציר"}
# Words of a job title, never of a name: "Software Engineer" as a first line stays.
TITLE_WORDS = {"engineer", "developer", "programmer", "architect", "analyst", "designer",
               "manager", "scientist", "intern", "student", "graduate", "software", "data",
               "backend", "frontend", "full", "stack", "devops", "qa", "senior", "junior",
               "lead", "team", "resume", "curriculum", "vitae", "cv", "קורות"}


def _is_phone(text):
    digits = re.sub(r"\D", "", text)
    if all(re.fullmatch(r"(19|20)\d\d", group) for group in re.findall(r"\d+", text)):
        return False  # only years: a date range, which scoring needs
    return 9 <= len(digits) <= 15


def _has_contact(line):
    return bool(EMAIL.search(line) or LINK.search(line)
                or any(_is_phone(run) for run in NUMBER_RUN.findall(line)))


def _lines(cv_text):
    return [line.strip() for line in cv_text.splitlines() if line.strip()]


def _is_heading(line):
    letters = re.sub(r"[^\w ]", "", line).strip()
    return letters.lower() in HEADINGS or (len(letters) >= 4 and letters == letters.upper()
                                           and re.search("[A-Z]", letters) is not None)


def _header_size(lines):
    """How many lines the header has: up to the first section heading."""
    for number, line in enumerate(lines[:HEADER_LINES]):
        if number > 0 and _is_heading(line):
            return number
    return min(len(lines), HEADER_LINES)


def _name(lines):
    """The first line if it is the person's name, else None.

    A name is 2 to 4 words of letters only, with no job-title word. Then one of
    these must hold: a word of it is in the CV's email address (dana.cohen@...),
    the next line holds contact details, or the CV has no email at all."""
    if not lines:
        return None
    first = lines[0]
    words = first.split()
    if not 2 <= len(words) <= 4 or _has_contact(first):
        return None
    if not all(re.fullmatch(r"[^\W\d_][^\W\d_'.-]*", word) for word in words):
        return None
    if any(word.lower() in TITLE_WORDS for word in words):
        return None
    emails = [email.split("@")[0].lower() for email in EMAIL.findall("\n".join(lines))]
    in_email = any(word.lower() in email for word in words for email in emails)
    contact_follows = len(lines) > 1 and _has_contact(lines[1])
    return first if in_email or contact_follows or not emails else None


def _without_contacts(line):
    line = LINK.sub("", EMAIL.sub("", line))
    return NUMBER_RUN.sub(lambda run: "" if _is_phone(run.group()) else run.group(), line).strip()


def for_ai(cv_text):
    """The CV without the name, contact details and links."""
    lines = _lines(cv_text)
    name = _name(lines)
    header = _header_size(lines)
    kept = []
    for number, line in enumerate(lines):
        if number == 0 and name:
            continue
        if number < header and (_has_contact(line) or PROFILE_WORDS.search(line)):
            continue
        line = _without_contacts(line)
        if line:
            kept.append(line)
    text = "\n".join(kept)
    if name:  # the name elsewhere, in either order ("Dana Cohen", "Cohen Dana")
        words = name.split()
        for order in (words, words[::-1]):
            text = re.sub(r"\s+".join(map(re.escape, order)), "", text, flags=re.IGNORECASE)
    return text

