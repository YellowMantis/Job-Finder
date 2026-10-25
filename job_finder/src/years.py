"""Read how many years of experience a posting asks for, with plain code (no AI).

Postings say it in a few set ways: "3+ years of experience", "2-4 years",
"at least 5 years", "5 or more years", "3+ שנות ניסיון". The traps are
sentences about the company ("In just 4 years, we've grown...", "15+ years
since starting the company"), so a number counts only when its line looks like
a requirement:

  - the line is a list item ("- 5+ years...", "• 3+ שנות...") or starts with
    the number ("3-5 years in software validation"), or
  - the number is written as a minimum ("3+", "at least 3", "minimum 3"), or
  - the line is about experience ("ניסיון ... של 5 שנים").

Words of company history next to the number ("over", "past", "since") rule it
out, as do studies ("1.5 years left until graduation"), and so does a sentence
marked as a bonus ("advantage", "nice to have", "יתרון"). A range counts as its
lower end: "2-4 years" asks for 2.

Each line counts once, by its first number: "2+ years of QA experience; or at
least 4 years if you hold..." asks for 2. Across lines the largest number is
what the posting asks for ("6+ years as an engineer" and "2+ years leading
teams" ask for 6).
"""

import re

NUMBER = r"(\d{1,2}(?:\.\d)?)"
# A number of years, alone or as a range: "3", "3+", "2-4", "2.5–5", "3 to 5",
# "3+ overall years", "5 or more years", "5 שנים", "3+ שנות".
YEARS = re.compile(
    rf"(?<![\d.,]){NUMBER}\s*\+?\s*(?:(?:-|–|—|to)\s*\d{{1,2}}(?:\.\d)?\s*\+?\s*)?"
    r"(?:(?:or more|or above|overall|full)\s+)?"
    r"(?:years?|yrs?\b|שנ(?:ות|ים|ה))",
    re.IGNORECASE)
LIST_ITEM = re.compile(r"^\W*(?:[-•*·▪●◦✔✓]|\d{1,2}[.)]\s)")
MINIMUM = re.compile(r"(?:at least|minimum(?: of)?|min\.?|לפחות|מינימום)\s*$", re.IGNORECASE)
EXPERIENCE = re.compile(r"experience|ניסיון|נסיון", re.IGNORECASE)
HISTORY_BEFORE = re.compile(r"(?:over|more than|past|just|nearly|almost|for)\s*$", re.IGNORECASE)
NOT_EXPERIENCE_AFTER = re.compile(
    r"^\W*(?:since|ago|of history|in business|in the market|left|till|until|to graduat)",
    re.IGNORECASE)
BONUS = re.compile(r"advantage|nice[ -]to[ -]have|\bbonus\b|\ba plus\b|^\W*preferred\b|יתרון",
                   re.IGNORECASE)
# Real requirements stop well below this; bigger numbers are company history.
MOST_YEARS = 20


def _sentence(line, start, end):
    """The sentence of the line that holds line[start:end]. A dot only ends a
    sentence before a space, so "1.5 years" stays whole."""
    begin = max(line.rfind(". ", 0, start), line.rfind(";", 0, start)) + 1
    stops = [i for i in (line.find(". ", end), line.find(";", end)) if i >= 0]
    return line[begin:min(stops) if stops else len(line)]


def _line_years(line):
    """The years a single line asks for, or None if it isn't a requirement."""
    for match in YEARS.finditer(line):
        before, after = line[:match.start()], line[match.end():]
        if (HISTORY_BEFORE.search(before) or NOT_EXPERIENCE_AFTER.search(after)
                or BONUS.search(_sentence(line, match.start(), match.end()))):
            continue
        number = float(match.group(1))
        looks_required = (LIST_ITEM.match(line) or not before.strip()
                          or "+" in match.group(0) or MINIMUM.search(before)
                          or EXPERIENCE.search(line))
        if looks_required and number <= MOST_YEARS:
            return int(number) if number.is_integer() else number
    return None


def years_asked(text):
    """The years of experience the posting asks for (a number, sometimes
    2.5), or None if it doesn't say."""
    found = [years for line in (text or "").splitlines()
             if (years := _line_years(line.replace("\xa0", " "))) is not None]
    return max(found) if found else None
