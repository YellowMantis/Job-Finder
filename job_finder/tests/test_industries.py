"""Tests for the industry labels (industries.py).

Every description here is copied from the real company data. When a company
is labelled wrongly, its description should be added here, so the rules can
get better and never silently get worse.
"""

import pytest

from industries import company_industries


def labels(name, description="", techmap_category=""):
    return set(company_industries(name, description, techmap_category))


# ---- Defence ------------------------------------------------------------------

@pytest.mark.parametrize("name, description", [
    ("BIRD Aerosystems", "A global innovative defense technology provider, securing air, sea, "
     "and land fleets for governments with advanced missile protection and border task force "
     "solutions."),
    ("IMCO Industries", "IMCO Industries is a leading Israeli defense company that specializes "
     "in the development, design and production of mechanical, electro-mechanical, electrical "
     "and electronic products, assemblies and sub-assemblies for airborne, land and naval "
     "applications."),
    ("Smart Shooter", "A modular, lightweight remote-controlled weapon station designed for safe "
     "and rapid elimination of both ground and aerial targets."),
    ("KELA", "Kela is developing an innovative operating system for military systems."),
    # Cybersecurity, but sold to the defence sector: that still counts.
    ("KayHut", "KayHut is a leading provider of cyber security solutions for the defense and "
     "private sectors."),
    # Its description never mentions defence: only the known-companies list catches it.
    ("Aitech", "Providing customized, rugged embedded computer systems for extreme environments."),
    ("Elbit Systems BMD and Land EW", ""),
])
def test_defence_companies(name, description):
    assert "defence" in labels(name, description)


@pytest.mark.parametrize("name, description", [
    # "defense" here is cybersecurity language, not the military.
    ("Onyxia Cyber", "Our platform empowers CISOs with comprehensive cybersecurity insights to "
     "develop effective defense strategies aligned with business goals."),
    ("CHEQ", "Providing precise detection and defense solutions tailored for your go-to-market "
     "strategy."),
    ("CRITIFENCE Technologies", "A cutting-edge cybersecurity platform offering passive "
     "monitoring, control of OT and IT networks, and remote site connectivity through a "
     "server/agent architecture for enhanced multilayered defense."),
])
def test_cyber_defense_is_not_military(name, description):
    assert "defence" not in labels(name, description)


# ---- Banks and insurers: only companies that ARE one --------------------------

def test_a_bank_is_a_bank():
    assert "banking" in labels("ONE ZERO Digital Bank")
    assert "banking" in labels("Citi")


def test_software_for_banks_is_not_a_bank():
    assert "banking" not in labels("Surecomp", "A world leader in trade finance software and "
                                   "solutions, offering SWIFT certified options both on the "
                                   "cloud and on-premise for banks and corporations.")


def test_an_insurer_is_an_insurer():
    assert "insurance" in labels("Lemonade")
    assert "insurance" in labels("Libra Insurance")


def test_software_for_insurers_is_not_an_insurer():
    assert "insurance" not in labels("Sapiens International Corporation", "Enabling insurance "
                                     "companies to adapt and thrive in a transforming industry.")


# ---- Other industries -----------------------------------------------------------

@pytest.mark.parametrize("name, description, industry", [
    # Social casino games count as gambling (decided together).
    ("SciPlay", "We ignite daily enthusiasm for gaming through innovative social casino and "
     "casual games.", "gambling"),
    ("Spinomenal", "Spinomenal is one of the fastest-growing iGaming suppliers with more than "
     "300 game releases so far.", "gambling"),
    ("Coinbase Israel", "A secure online platform for cryptocurrency transactions and storage.",
     "crypto"),
    ("Kendago", "Kendago is a premium digital advertising agency that partners with direct "
     "response brands.", "adtech"),
    ("Manpowergroup Israel Holdings", "", "staffing"),
    ("Tata Consultancy Services", "", "consulting"),
])
def test_other_industries(name, description, industry):
    assert industry in labels(name, description)


def test_techmap_category_is_used():
    assert "adtech" in labels("Taboola", "", techmap_category="AdTech")


def test_video_games_are_not_gambling():
    # techmap's "Gaming" category means video games.
    assert "gambling" not in labels("Some Studio", "We make mobile puzzle games.", "Gaming")


def test_an_ordinary_software_company_gets_no_label():
    assert labels("VAST Data", "The AI operating system for data-intensive workloads.",
                  "Cloud Computing") == set()


def test_every_label_says_why():
    reasons = company_industries("Kendago", "a digital advertising agency")
    assert reasons["adtech"] == 'company description mentions "advertising"'
