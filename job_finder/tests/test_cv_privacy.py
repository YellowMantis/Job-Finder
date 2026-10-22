"""Tests for what an AI is sent of a CV (cv_privacy.py): no name, contact
details or links, but everything scoring needs. The CVs here are made up."""

import pytest

import cv_privacy

CV = """Dana Levi
dana.levi@example.com | 052-123-4567 | Afula, 1830000 | Dana Levi | LinkedIn
PROFESSIONAL EXPERIENCE
Acme - Backend Developer 2021 - 2024
Technologies: Python, Node.js, Socket.io, GitHub Actions, AWS
Worked with Dana Levi's team lead on REST APIs. Portfolio: https://dana.dev/work
EDUCATION
Technion - B.Sc. Computer Science 2017-2021"""


def test_the_name_contact_details_and_links_are_not_sent():
    sent = cv_privacy.for_ai(CV)
    for private in ["Dana", "Levi", "dana.levi@example.com", "052-123-4567", "1830000",
                    "LinkedIn", "https://dana.dev"]:
        assert private not in sent


def test_everything_scoring_needs_is_kept():
    sent = cv_privacy.for_ai(CV)
    for needed in ["Acme - Backend Developer 2021 - 2024", "2017-2021", "Node.js", "Socket.io",
                   "GitHub Actions", "Technion - B.Sc. Computer Science", "REST APIs"]:
        assert needed in sent


@pytest.mark.parametrize("phone", ["+972 52 123 4567", "(04) 123-4567", "0521234567"])
def test_phone_numbers_in_other_formats_are_removed(phone):
    assert phone not in cv_privacy.for_ai(f"Dana Levi\nPhone: {phone}\nEXPERIENCE\nAcme")


def test_a_job_title_on_the_first_line_is_not_taken_for_a_name():
    assert cv_privacy.for_ai("Software Engineer\nEXPERIENCE\nAcme").startswith("Software Engineer")
    # Nor two words that aren't in the email address.
    assert cv_privacy.for_ai("Backend Team\nx.y@example.com\nAcme").startswith("Backend Team")


def test_a_hebrew_name_is_removed():
    sent = cv_privacy.for_ai("דנה לוי\ndana@example.com | 052-123-4567\nניסיון\nAcme 2020-2022")
    assert "דנה" not in sent and "Acme 2020-2022" in sent

