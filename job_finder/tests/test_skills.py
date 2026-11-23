"""Tests for reading skills from postings and CVs (skills.py).

The lines here are copied from real postings. When a skill is counted wrongly,
the line should be added here, so the spellings get better and never silently
get worse.
"""

import pytest

from skills import SKILLS, requirements_part, skills_in


def test_every_skill_has_a_unique_name():
    names = [name for name, _, _ in SKILLS]
    assert len(names) == len(set(names))


def test_each_skill_counts_once_however_often_it_appears():
    assert skills_in("Python, Python and more Python") == ["Python"]


def test_a_language_list():
    found = skills_in("Strong skills in at least one modern language (Go, Python or Rust).")
    assert {"Go", "Python", "Rust"} <= set(found)


# ---- One-letter and short names ----------------------------------------------

@pytest.mark.parametrize("line", [
    "Native code (C, C++), .NET (C# etc), Python, Node.JS",
    "Proficiency in C and Python",
    "Coding in C/C++",
])
def test_c_is_found(line):
    assert "C" in skills_in(line)


@pytest.mark.parametrize("line", [
    "NIST CSF, CIS Controls, and MITRE ATT&CK",
    "Kotlin, Swift, Objective C, Java",
    "Objective-C or Kotlin",
    "We raised our Series C last year",
    "Experience presenting to C-level executives",
    "Experience with C# and .NET",
    "Strong C++ skills",
])
def test_c_is_not_found(line):
    assert "C" not in skills_in(line)


def test_go_needs_to_sit_among_languages():
    assert "Go" in skills_in("Deep expertise in Java, Go, Python, Spring")
    assert "Go" in skills_in("Golang microservices")
    assert "Go" not in skills_in("Go beyond the obvious. You will go far here.")


def test_react_the_library_not_the_verb():
    assert "React" in skills_in("frontend (React, Next.js) and data pipelines")
    assert "React" not in skills_in("Able to react quickly to production incidents")


def test_excel_the_program_not_the_verb():
    assert "Excel" in skills_in("Proficiency in NetSuite and Microsoft Excel.")
    assert "Excel" not in skills_in("You will excel in this role if you enjoy working at scale")


def test_java_is_not_javascript():
    assert skills_in("Strong JavaScript skills") == ["JavaScript"]


# ---- Only the requirements count -----------------------------------------------

POSTING = """About the company
We are a leading cybersecurity company building agentic AI for the enterprise.

Requirements
- 2+ years of Python
- Experience with Docker
"""


def test_counting_starts_at_the_requirements_heading():
    found = skills_in(requirements_part(POSTING))
    assert found == ["Python", "Docker"]   # not the company's cybersecurity or agentic AI


def test_a_posting_without_a_heading_is_read_whole():
    text = "We need someone with Kubernetes and AWS."
    assert requirements_part(text) == text
    assert skills_in(requirements_part(text)) == ["Kubernetes", "AWS"]


@pytest.mark.parametrize("heading", ["Requirements", "Qualifications:", "What you'll bring",
                                     "What we’re looking for", "Who you are", "- Must have"])
def test_common_headings(heading):
    assert requirements_part(f"Intro about us.\n{heading}\nPython") .startswith(heading)
