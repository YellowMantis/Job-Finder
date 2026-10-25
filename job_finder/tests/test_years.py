"""Tests for reading the years of experience a posting asks for (src/years.py).
The sentences are taken from real postings."""

from years import years_asked


def test_the_usual_ways_of_asking():
    assert years_asked("- 4+ years of experience in production operations") == 4
    assert years_asked("- At least 7 years of experience as a backend engineer") == 7
    assert years_asked("- Minimum of 6 years of experience in program management") == 6
    assert years_asked("- 5 or more years of experience in RF system design") == 5
    assert years_asked("- 3+ overall years of experience in technical software development") == 3
    assert years_asked("- 5+\xa0years\xa0as\xa0a\xa0software\xa0engineer") == 5


def test_a_range_asks_for_its_lower_end():
    assert years_asked("✔️ 3-6 years of experience in finance or FP&A") == 3
    assert years_asked("- 0-2 years of industry experience (strong academic background)") == 0
    assert years_asked("- 2.5-5 years of proven experience in an IT Support role") == 2.5


def test_lines_without_a_list_marker_count_when_they_look_required():
    assert years_asked("3-5 years in software / hardware validation or verification.") == 3
    assert years_asked("Bachelor's Degree in engineering and 4 or more years of experience are required.") == 4


def test_hebrew():
    assert years_asked("• 3+ שנות ניסיון בבקרת איכות של כרטיסים אלקטרוניים") == 3
    assert years_asked("ניסיון כמהנדס/ת מכונות של 5 שנים בחברה יצרנית.") == 5


def test_the_largest_requirement_across_lines_wins():
    text = "- 6+ years of hands-on software engineering experience\n- 2+ years leading a team"
    assert years_asked(text) == 6


def test_a_line_counts_by_its_first_number():
    line = ("- You have 2+ years of manual software QA experience; or at least 4 years of "
            "relevant experience if you hold vocational education in IT.")
    assert years_asked(line) == 2


def test_company_history_and_studies_are_not_requirements():
    assert years_asked("In just 4 years, we've grown to 100+ people") is None
    assert years_asked("15+ years since starting the company, we continue to grow") is None
    assert years_asked("With over 40 years of semiconductor process control experience") is None
    assert years_asked("- At least 3 semesters (1.5 years) left until graduation") is None
    assert years_asked("QA Engineer – Backend Infrastructure (1-year fixed term contract)") is None


def test_a_bonus_is_not_a_requirement():
    assert years_asked("• 2+ שנות ניסיון בהלחמות מעגלים חשמליים – יתרון") is None
    assert years_asked("- Preferred: 2–3 years of experience in Quality Assurance") is None
    # The bonus is a different sentence: the requirement still counts.
    assert years_asked("At least 2 years' experience in testing tools. Python is a big advantage.") == 2


def test_no_years_stated():
    assert years_asked("- Strong experience with Python and SQL") is None
    assert years_asked("") is None
    assert years_asked(None) is None
