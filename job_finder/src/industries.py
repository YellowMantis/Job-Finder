"""Which industries a company is in: gambling, crypto, defence, banking...

Nothing here hides a job. It only LABELS companies, with the reason for each
label; your preferences decide which labels to hide, and the page shows the
reason, so a wrong label is visible rather than silently hiding a job.

Each industry has a "rule card" with up to four kinds of evidence:

  techmap     techmap's own category for the company ("AdTech")
  companies   exact company names we know belong there ("Aitech")
  name_words  whole words in the company NAME ("bank")
  phrases     whole words or phrases in the name OR the one-line description

For banking and insurance only the name is used: the aim is companies that ARE
banks or insurers. Many descriptions say "software for banks", and those are
ordinary software jobs.

guard_before stops a phrase from counting when one of the two words just before
it shows a different meaning: "cyber defense" or "detection and defense" is
cybersecurity, not the military.

Tests: job_finder/tests/test_industries.py, with real company descriptions.
"""

import re

INDUSTRIES = {
    "defence": {
        "label": "Defence and military",
        "companies": ["aitech", "imi systems"],
        "name_words": ["elbit", "rafael", "elta", "israel aerospace industries",
                       "israel military industries", "israel shipyards"],
        "phrases": ["defense", "defence", "military", "army", "weapon", "weapons", "missile",
                    "missiles", "warfare", "homeland security", "armed forces", "battlefield",
                    "munitions", "ammunition"],
        "guard_before": ["cyber", "detection", "multilayered", "layered", "effective", "network",
                         "threat", "threats", "fraud", "email", "endpoint", "proactive",
                         "active", "ransomware", "bot", "malware", "phishing", "identity",
                         "data", "cloud"],
    },
    "banking": {
        "label": "Banks",
        "companies": ["citi", "jpmorgan", "jp morgan", "goldman sachs", "bank leumi",
                      "leumi", "hapoalim", "mizrahi tefahot", "israel discount bank"],
        "name_words": ["bank", "banks"],
    },
    "insurance": {
        "label": "Insurance companies",
        "companies": ["lemonade", "harel", "migdal", "clal", "menora mivtachim", "ayalon",
                      "aig", "the phoenix"],
        "name_words": ["insurance", "insurer"],
    },
    "gambling": {
        "label": "Gambling and casino games",
        "companies": ["888"],
        "phrases": ["gambling", "casino", "casinos", "betting", "igaming", "sportsbook",
                    "poker", "lottery", "lotteries", "wagering", "bingo", "slot machines"],
    },
    "crypto": {
        "label": "Crypto and blockchain",
        "phrases": ["crypto", "cryptocurrency", "cryptocurrencies", "blockchain", "web3",
                    "bitcoin", "ethereum", "defi", "nft", "nfts"],
    },
    "adtech": {
        "label": "Advertising technology",
        "techmap": ["AdTech"],
        "phrases": ["advertising", "adtech", "ad tech", "advertisers", "ad network",
                    "programmatic"],
    },
    "government": {
        "label": "Government and public sector",
        "name_words": ["ministry", "municipality", "government"],
        "phrases": ["government-owned", "government owned", "state-owned", "government company"],
    },
    "staffing": {
        "label": "Staffing and recruitment agencies",
        "companies": ["manpowergroup israel holdings", "adecco", "ethosia", "nisha"],
        "name_words": ["staffing", "recruitment", "manpower", "headhunting"],
        "phrases": ["staffing agency", "staffing company", "recruitment agency",
                    "placement agency", "headhunting"],
    },
    "consulting": {
        "label": "IT consulting and outsourcing",
        "companies": ["accenture", "tata consultancy services", "wipro givon", "tech mahindra",
                      "ness", "infosys", "capgemini", "deloitte", "kpmg", "pwc", "ey",
                      "mckinsey", "matrix", "malam team"],
        "phrases": ["outsourcing", "it services", "system integrator", "consulting firm",
                    "consulting company"],
    },
    "vice": {
        "label": "Tobacco, alcohol and cannabis",
        "phrases": ["tobacco", "cigarette", "cigarettes", "e-cigarette", "vape", "vaping",
                    "nicotine", "alcohol", "alcoholic", "brewery", "winery", "distillery",
                    "cannabis"],
    },
}


def _find(phrases, text, guard_before=()):
    """The first phrase found in the text as whole words, skipping matches whose
    two preceding words include a guard word. Returns the phrase, or None."""
    for phrase in phrases:
        for match in re.finditer(rf"\b{re.escape(phrase)}\b", text, flags=re.IGNORECASE):
            words_before = re.findall(r"[a-z]+", text[:match.start()].lower())[-2:]
            if not any(word in guard_before for word in words_before):
                return phrase
    return None


def company_industries(name, description="", techmap_category=""):
    """Label one company. Returns {industry id: reason}, empty if none apply.

    name:             the company's name
    description:      techmap's one-line description, or "" if we have none
    techmap_category: techmap's category for the company, e.g. "AdTech"
    """
    labels = {}
    for industry, card in INDUSTRIES.items():
        if techmap_category and techmap_category in card.get("techmap", []):
            labels[industry] = f'techmap lists the company under "{techmap_category}"'
        elif name.strip().lower() in card.get("companies", []):
            labels[industry] = "on the list of known companies"
        elif word := _find(card.get("name_words", []), name):
            labels[industry] = f'company name contains "{word}"'
        elif word := _find(card.get("phrases", []), f"{name}. {description}",
                           card.get("guard_before", [])):
            labels[industry] = f'company description mentions "{word}"'
    return labels
