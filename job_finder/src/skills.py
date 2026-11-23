"""Which skills a text names: a posting, or your CV. No AI: each skill is a name
plus the spellings that mean it, matched as whole words.

Postings are long and written in prose, so the spellings are strict: "Go" must
be capitalised and not start a sentence, "React" must look like the library,
and words that are ordinary English ("vision", "network", "agents") are left out.
Each skill counts once per text, however often it appears.

Tests: job_finder/tests/test_skills.py, with lines from real postings.
"""

import re

I = re.IGNORECASE

# (name, pattern, flags). Order is the order of the list on the page when counts tie.
SKILLS = [
    ("Python", r"\bpython\b", I),
    ("C++", r"\bc\+\+|\bcpp\b", I),
    # Capital C on its own: "C", "C/C++", "C and Python"; not "C#", "C-level",
    # "Series C", "C." as an initial, or "C/C" in a grade.
    ("C", r"(?<![\w#+.&-])C(?![\w#+.&-])(?! ?level)(?<!Series C)(?<!Objective C)", 0),
    ("C#", r"\bc#|\.net\b", I),
    ("Java", r"\bjava\b(?!script)", I),
    # "Go" only beside other languages or as "Golang": "Go, Python", "Python/Go".
    ("Go", r"\b(?i:golang)\b|(?<=[,/(] )Go\b|(?<=[,/(])Go\b|\bGo(?=\s*[,/)])", 0),
    ("Rust", r"\brust\b", I),
    ("JavaScript", r"\bjavascript\b|\bjs\b", I),
    ("TypeScript", r"\btypescript\b", I),
    ("React", r"\breact(?:\.js|js| native)?\b(?! (?:to|quickly|fast)\b)", I),
    ("Angular", r"\bangular(?:js)?\b", I),
    ("Node.js", r"\bnode\.?js\b", I),
    ("SQL", r"\bsql\b|\bpostgres(?:ql)?\b|\bmysql\b", I),
    ("NoSQL", r"\bnosql\b|\bmongo(?:db)?\b|\bredis\b|\bcassandra\b|\bdynamodb\b", I),
    ("Elasticsearch", r"\belastic ?search\b|\belk\b", I),
    ("Linux", r"\blinux\b|\bunix\b", I),
    ("Bash / shell", r"\bbash\b|\bshell script", I),
    ("Git", r"\bgit\b|\bgithub\b|\bgitlab\b", I),
    ("Docker", r"\bdocker\b|\bcontaineri[sz]", I),
    ("Kubernetes", r"\bkubernetes\b|\bk8s\b|\bhelm\b|\bopenshift\b", I),
    ("Terraform / IaC", r"\bterraform\b|\binfrastructure as code\b|\biac\b|\bpulumi\b|\bansible\b", I),
    ("CI/CD", r"\bci ?/ ?cd\b|\bjenkins\b|\bgithub actions\b|\bargo ?cd\b|\bcontinuous integration\b", I),
    ("AWS", r"\baws\b|\bamazon web services\b", I),
    ("Google Cloud", r"\bgcp\b|\bgoogle cloud\b", I),
    ("Azure", r"\bazure\b", I),
    ("Monitoring", r"\bgrafana\b|\bprometheus\b|\bdatadog\b|\bobservability\b|\bnew relic\b", I),
    ("Kafka", r"\bkafka\b|\brabbitmq\b", I),
    ("Spark / big data", r"\bspark\b|\bhadoop\b|\bairflow\b|\bdatabricks\b|\bsnowflake\b", I),
    ("Microservices", r"\bmicro-?services?\b", I),
    ("REST APIs", r"\brest(?:ful)?\b(?: ?apis?)?|\bgraphql\b", I),
    ("Networking", r"\btcp/ip\b|\bnetworking\b|\bdns\b|\bl2/l3\b|\bbgp\b|\bnetwork protocols?\b", I),
    ("Cybersecurity", r"\bcyber ?security\b|\bpenetration test|\bsiem\b|\bsoc\b|\bvulnerabilit", I),
    ("Machine learning", r"\bmachine learning\b|\bdeep learning\b|\bpytorch\b|\btensorflow\b|\bscikit|\bml\b", I),
    ("LLMs / generative AI", r"\bllms?\b|\bgenai\b|\bgenerative ai\b|\brag\b|\bprompt engineering\b|\bmcp\b|\bai agents?\b|\bagentic\b", I),
    ("Computer vision", r"\bcomputer vision\b|\bimage processing\b|\bopencv\b", I),
    ("Data analysis", r"\bpandas\b|\bnumpy\b|\bdata analy|\bpower ?bi\b|\btableau\b", I),
    ("MATLAB", r"\bmatlab\b|\bsimulink\b", I),
    ("Test automation", r"\btest automation\b|\bautomated tests?\b|\bautomation framework|\bplaywright\b|\bselenium\b|\bpytest\b|\bcypress\b", I),
    ("QA / testing", r"\bqa\b|\bquality assurance\b|\btest plans?\b|\bistqb\b|\bmanual testing\b", I),
    ("Embedded / firmware", r"\bembedded\b|\bfirmware\b|\brtos\b|\bmicrocontrollers?\b|\bmcus?\b", I),
    ("Hardware interfaces", r"\bspi\b|\bi2c\b|\buart\b|\bpcie\b|\bcan bus\b", I),
    ("Linux kernel / drivers", r"\bkernel\b|\bdevice drivers?\b", I),
    ("FPGA / chip design", r"\bfpga\b|\bverilog\b|\bvhdl\b|\basic\b|\brtl\b|\bsystemverilog\b", I),
    ("Electronics / lab", r"\boscilloscopes?\b|\blab equipment\b|\bschematics?\b|\bpcb\b|\blabview\b", I),
    ("RF / signal processing", r"\brf\b|\bdsp\b|\bsignal processing\b", I),
    ("Mechanical / CAD", r"\bsolidworks\b|\bcreo\b|\bcad\b|\bmechanical design\b", I),
    ("Mobile apps", r"\bandroid\b|\bios\b|\bswift\b|\bkotlin\b|\bflutter\b", I),
    ("Multithreading", r"\bmulti-?thread|\bconcurrency\b", I),
    ("Object-oriented design", r"\boop\b|\bobject[- ]oriented\b|\bdesign patterns\b", I),
    ("Algorithms / data structures", r"\balgorithms\b|\bdata structures\b", I),
    ("Excel", r"\bExcel\b(?! in\b)", 0),  # not "you will excel in"
    ("Agile / Jira", r"\bagile\b|\bscrum\b|\bjira\b", I),
    ("Salesforce / CRM", r"\bsalesforce\b|\bcrm\b|\bhubspot\b", I),
    ("Hebrew", r"\bhebrew\b", I),
]

_COMPILED = [(name, re.compile(pattern, flags)) for name, pattern, flags in SKILLS]

# Where a posting's requirements start. Most postings open with the company
# ("a leader in cybersecurity", "our agentic AI platform"); those words describe
# the company, not what the job asks for, so counting starts at this heading
# when the posting has one. About two thirds do.
REQUIREMENTS_HEADING = re.compile(
    r"^\W*(?:requirements|qualifications|required (?:skills|qualifications)|who you are|about you"
    r"|what you['’]ll (?:need|bring)|what we['’]re looking for|you(?:['’]ll)? have|must have)\b",
    re.IGNORECASE | re.MULTILINE)


def requirements_part(posting):
    """The posting from its requirements heading on, or all of it if it has none."""
    heading = REQUIREMENTS_HEADING.search(posting or "")
    return posting[heading.start():] if heading else (posting or "")


def skills_in(text):
    """The skills a text names, in list order, each once."""
    return [name for name, pattern in _COMPILED if pattern.search(text or "")]
