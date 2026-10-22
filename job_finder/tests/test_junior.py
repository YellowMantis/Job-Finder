"""Tests for spotting junior roles.

The sentences below are copied from real postings in our data. Most postings
that say "junior" are for experienced people who will mentor juniors; those
once got a wrong Junior badge, which these tests now guard against.
"""

import pytest

from jobs import JUNIOR_WORDS, _contains_word
from pipeline import describes_junior_role

# Sentences that present THIS role as junior: the badge is right.
JUNIOR_ROLE_TEXTS = [
    # Nvidia, Solution Validation Engineer (the title doesn't say junior)
    "Our platform powers the world's most demanding AI workloads. "
    "As a Junior Solution Validation Engineer, you'll drive validation of our systems.",
    "This is an entry-level position in our automation team.",
]

# Sentences that mention juniors but are about someone more senior.
NOT_JUNIOR_ROLE_TEXTS = [
    "- Mentor junior engineers and contribute to technical decisions.",
    "- Coach junior team members - Perform and Support Assembly tests.",
    "Provide technical guidance and mentorship to junior data engineers.",
    "Experience in a related role (e.g., Tier 3 Support, NOC, Production Engineer, "
    "or Junior DevOps/SRE) - Proven ability to manage incidents.",
    "You will guide the junior engineers in the team.",
]


@pytest.mark.parametrize("text", JUNIOR_ROLE_TEXTS)
def test_text_that_presents_the_role_as_junior(text):
    assert describes_junior_role(text, fit=None)


@pytest.mark.parametrize("text", NOT_JUNIOR_ROLE_TEXTS)
def test_text_about_mentoring_juniors_is_not_a_junior_role(text):
    assert not describes_junior_role(text, fit=None)


def test_a_review_finding_three_years_overrules_the_text():
    # The text says junior, but the review read "3+ years required" from it.
    assert not describes_junior_role(JUNIOR_ROLE_TEXTS[0], fit={"years_required": 3})


# Real titles. Whole words only: "Intern" is junior, "Internals" is not.
@pytest.mark.parametrize("title, is_junior", [
    ("Junior Automation Engineer", True),
    ("R&D Geometry Creo Intern", True),
    ("NOC - Student Position", True),
    # VAST Data's posting; it had no Junior badge until "grad" joined JUNIOR_WORDS.
    ("Software Engineer -New College Grad", True),
    ("Linux Internals Engineer", False),
    ("Software Engineer II, Mobile iOS", False),
])
def test_junior_words_in_titles(title, is_junior):
    assert bool(_contains_word(title, JUNIOR_WORDS)) == is_junior
