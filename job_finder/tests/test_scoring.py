"""Tests for the fit score maths (check_and_score in fit_rules.py).

No AI is called here. The AI's part of a review is a list of requirements; we
write that list by hand, so each test knows exactly what score must come out.

Run all tests from the project folder with:
    python -m pytest
"""

from fit_rules import check_and_score

# A tiny made-up CV. Evidence quotes in the tests are copied from it, unless a
# test is checking what happens to a quote that ISN'T in it.
CV = """B.Sc. in Computer Science.
Wrote Python and Bash automation on Linux.
System validation and debugging of embedded boards.
Built telemetry dashboards."""


def req(requirement, importance, match, evidence="not in CV"):
    """One requirement, shaped the way the AI returns it."""
    return {"requirement": requirement, "importance": importance,
            "evidence": evidence, "match": match}


def score(requirements, years_required=0, professional_years=1):
    """Run the code checks and return the whole result."""
    return check_and_score(CV, professional_years, years_required, requirements,
                           work_mode="hybrid", summary="", reviewer="test")


def test_worked_example_from_the_guide_scores_59():
    # The Nvidia example in docs/ARCHITECTURE.md: 10 points out of 17 -> 59%.
    # The "2+ years" line isn't listed here: the code adds it itself (see below).
    result = score([
        req("System validation and debugging", "core", "partial",
            "System validation and debugging of embedded boards"),
        req("Bachelor's in a related field", "must", "yes", "B.Sc. in Computer Science"),
        req("Linux and debugging tools", "must", "yes", "automation on Linux"),
        req("Python or Bash automation", "must", "yes", "Python and Bash automation"),
        req("Telemetry data analysis", "must", "partial", "telemetry dashboards"),
        req("Networking protocols", "nice", "no"),
        req("AI-driven monitoring", "nice", "no"),
        req("InfiniBand / NVLink", "nice", "no"),
    ], years_required=2, professional_years=1)

    assert result["score"] == 59
    # The years line was added first, as a must-have, half met (one year short).
    assert result["requirements"][0]["requirement"] == "2+ years of experience"
    assert result["requirements"][0]["match"] == "partial"


def test_two_or_more_years_short_halves_the_score():
    # Everything met, but the posting asks for 4 years and the CV shows 1.
    result = score([
        req("Python", "core", "yes", "Python and Bash automation"),
        req("Linux", "must", "yes", "automation on Linux"),
    ], years_required=4, professional_years=1)

    # Before halving: core 4 + must 2 met, years (must 2) not met -> 6/8 = 75%.
    assert result["score"] == 38   # 75% halved, rounded
    assert any("Halved" in note for note in result["notes"])


def test_enough_years_is_not_penalised():
    result = score([
        req("Python", "core", "yes", "Python and Bash automation"),
        req("Linux", "must", "yes", "automation on Linux"),
    ], years_required=1, professional_years=1)

    assert result["score"] == 100
    assert result["notes"] == []


def test_a_quote_that_is_not_in_the_cv_counts_as_not_met():
    # The AI claims Kubernetes with a "quote" the CV doesn't contain.
    result = score([
        req("Kubernetes", "core", "yes", "Deployed services on Kubernetes clusters"),
        req("Python", "must", "yes", "Python and Bash automation"),
    ])

    kubernetes = result["requirements"][0]
    assert kubernetes["match"] == "no"
    assert kubernetes["evidence"] == "not in CV"
    assert result["score"] == 33   # only the must-have (2 of 6) is met


def test_soft_skills_are_left_out_of_the_score():
    result = score([
        req("Python", "core", "yes", "Python and Bash automation"),
        req("Linux", "must", "yes", "automation on Linux"),
        req("Excellent communication skills", "must", "no"),
    ])

    names = [item["requirement"] for item in result["requirements"]]
    assert "Excellent communication skills" not in names
    assert result["score"] == 100


def test_fewer_than_two_requirements_gives_no_score():
    # One requirement is too little to judge a fit: show "?" rather than 100%.
    result = score([req("Python", "core", "yes", "Python and Bash automation")])

    assert result["score"] is None
    assert result["notes"]
