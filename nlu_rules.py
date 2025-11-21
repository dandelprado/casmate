import re
from typing import Dict, List, Optional, Tuple

import spacy
from spacy.matcher import Matcher, PhraseMatcher

nlp = spacy.blank("en")

matcher = Matcher(nlp.vocab)
phrase_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

WS_RE = re.compile(r"\s+")
CODE_RE = re.compile(r"\b([A-Za-z]{2,4})-?(\d{2,3})\b")


PROGRAM_CANON = {
    "CS": "BS in Computer Science",
    "BSCS": "BS in Computer Science",

    "PSYCH": "BS in Psychology",
    "BS PSYCH": "BS in Psychology",

    "POLSAY": "BA in Political Science",
    "POLSCI": "BA in Political Science",
    "AB POLSCI": "BA in Political Science",
    "AB PS": "BA in Political Science",
    "ABPS": "BA in Political Science",
    "BAPS": "BA in Political Science",
    "BA PS": "BA in Political Science",

    "BAEL": "BA in English Language",
    "ABEL": "BA in English Language",

    "BACOMM": "BA in Communications",
    "COMM": "BA in Communications",

    "BIO": "BS in Biology",
    "BS BIO": "BS in Biology",
}



def norm_key(s: str) -> str:
    return "".join(s or "").strip().upper()


PROGRAM_ABBREVIATIONS: Dict[str, str] = {norm_key(k): v for k, v in PROGRAM_CANON.items()}

DEPT_ALIASES = [
    "CAS", "College of Arts and Sciences",
    "Computer Science", "Comp Sci", "CS", "CS Department", "CS Dept", "CS Dept.",
    "Social Sciences", "SocSci",
    "Language and Literature", "Lang & Lit", "Lang Lit",
    "Natural Sciences", "NatSci",
    "Mathematics", "Math", "Math Department", "Math Dept",
]

YEAR_WORDS = {
    "first": 1, "1st": 1, "year 1": 1, "yr 1": 1, "freshman": 1,
    "second": 2, "2nd": 2, "year 2": 2, "yr 2": 2, "sophomore": 2,
    "third": 3, "3rd": 3, "year 3": 3, "yr 3": 3, "junior": 3,
    "fourth": 4, "4th": 4, "year 4": 4, "yr 4": 4, "senior": 4,
}


def build_gazetteers(
    programs: List[Dict],
    courses: List[Dict],
    departments: Optional[List[Dict]] = None,
) -> None:
    """
    Build spaCy PhraseMatcher patterns for:
      - PROG: program names and abbreviations
      - COURSETITLE: full course titles (from JSON only)
      - DEPT: department names and aliases

    All hand-written course aliases like 'data struct', 'calc', 'psych',
    and 'bio' have been removed so this function only depends on your data.
    """

    # ----- Programs (PROG) -----
    if "PROG" in phrase_matcher:
        phrase_matcher.remove("PROG")

    prog_docs = [
        nlp(p["program_name"])
        for p in programs
        if p.get("program_name")
    ]
    base_docs: List = []

    for p in programs:
        name = p.get("program_name") or ""
        low = name.lower()
        # Also index program names without leading "BS " / "BA "
        if low.startswith("bs "):
            base_docs.append(nlp(name[3:]))
        elif low.startswith("ba "):
            base_docs.append(nlp(name[3:]))

    abbrev_docs = [nlp(k) for k in PROGRAM_ABBREVIATIONS.keys()]
    all_prog_docs = prog_docs + base_docs + abbrev_docs

    if all_prog_docs:
        phrase_matcher.add("PROG", all_prog_docs)

    # ----- Course titles (COURSETITLE) -----
    if "COURSETITLE" in phrase_matcher:
        phrase_matcher.remove("COURSETITLE")

    # Only index the actual course titles from courses.json
    title_docs = [
        nlp(c["course_title"])
        for c in courses
        if c.get("course_title")
    ]

    if title_docs:
        phrase_matcher.add("COURSETITLE", title_docs)

    # ----- Departments (DEPT) -----
    if "DEPT" in phrase_matcher:
        phrase_matcher.remove("DEPT")

    dept_docs = [nlp(x) for x in DEPT_ALIASES]

    if departments:
        dept_docs += [
            nlp(d.get("department_name") or "")
            for d in departments
            if d.get("department_name")
        ]

    if dept_docs:
        phrase_matcher.add("DEPT", dept_docs)

def add_lower_in(name: str, words: List[str]) -> None:
    matcher.add(name, [[{"LOWER": {"IN": words}}]])


add_lower_in("INTENT_GREET", ["hi", "hello", "hey"])
add_lower_in("INTENT_GOODBYE", ["bye", "goodbye", "thanks", "thank", "tnx"])

matcher.add(
    "INTENT_PREREQ",
    [
        [{"LOWER": {"IN": ["prereq", "prereqs", "prerequisite", "prerequisites", "requirement", "requirements"]}}],
        [
            {"LOWER": {"IN": ["what", "whats", "what's"]}},
            {"LOWER": {"IN": ["is", "are", "the"]}, "OP": "?"},
            {"LOWER": {"IN": ["prereq", "prereqs", "prerequisite", "prerequisites", "requirement"]}},
        ],
        [
            {"LOWER": {"IN": ["prereq", "prereqs", "prerequisite", "prerequisites"]}},
            {"LOWER": {"IN": ["of", "for"]}},
        ],
        [
            {"LOWER": {"IN": ["what"]}},
            {"LOWER": {"IN": ["do", "should"]}, "OP": "?"},
            {"LOWER": {"IN": ["i", "we"]}, "OP": "?"},
            {"LOWER": {"IN": ["need", "take"]}},
            {"LOWER": {"IN": ["before", "for", "prior"]}},
        ],
    ],
)

matcher.add(
    "INTENT_UNITS",
    [
        [{"LOWER": "how"}, {"LOWER": "many"}, {"LOWER": "units"}],
        [{"LOWER": "units"}, {"LOWER": {"IN": ["for", "of", "in"]}}],
        [{"LOWER": {"IN": ["total", "sum", "load"]}}, {"LOWER": "units"}],
    ],
)

matcher.add(
    "INTENT_DEPT_HEADS_LIST",
    [
        [
            {"LOWER": {"IN": ["list", "show", "different", "all"]}},
            {"LOWER": {"IN": ["department", "dept", "dept."]}},
            {"LOWER": {"IN": ["heads", "chairs", "leadership"]}},
        ],
        [
            {"LOWER": {"IN": ["who"]}},
            {"LOWER": {"IN": ["are"]}},
            {"LOWER": {"IN": ["the"]}, "OP": "?"},
            {"LOWER": {"IN": ["different", "department", "dept", "dept."]}, "OP": "*"},
            {"LOWER": {"IN": ["heads", "chairs", "leadership"]}},
        ],
        [
            {"LOWER": {"IN": ["department", "dept", "dept."]}},
            {"LOWER": {"IN": ["heads", "chairs", "leadership"]}},
        ],
    ],
)

matcher.add(
    "INTENT_DEPT_HEAD_ONE",
    [
        [
            {"LOWER": {"IN": ["who", "who's", "whos"]}},
            {"LOWER": {"IN": ["is"]}, "OP": "?"},
            {"LOWER": "the", "OP": "*"},
            {"IS_ALPHA": True, "OP": "+"},
            {"LOWER": {"IN": ["department", "dept", "dept.", "deprtment", "deprtmnt", "detp"]}, "OP": "?"},
            {"LOWER": {"IN": ["head", "haed", "hed", "chair", "dean"]}},
        ],
        [
            {"LOWER": {"IN": ["head", "haed", "hed", "chair", "dean"]}},
            {"LOWER": "of"},
            {"IS_ALPHA": True, "OP": "+"},
        ],
        [
            {"IS_ALPHA": True, "OP": "+"},
            {"LOWER": {"IN": ["dept", "department", "dept.", "deprtment", "deprtmnt", "detp"]}},
            {"LOWER": {"IN": ["head", "haed", "hed", "chair"]}},
        ],
    ],
)


def detect_intent(text: str) -> str:
    doc = nlp(text or "")
    labels = [nlp.vocab.strings[mid] for mid, _, _ in matcher(doc)]
    tlow = (text or "").lower().strip()

    # Department head / leadership questions
    if "dean" in tlow:
        return "dept_head_one"
    if "heads" in tlow or "leadership" in tlow:
        return "dept_heads_list"
    if "INTENT_DEPT_HEADS_LIST" in labels or tlow in {
        "department heads",
        "dept heads",
        "dept. heads",
        "different department heads",
    }:
        return "dept_heads_list"
    if "INTENT_DEPT_HEAD_ONE" in labels or (
        "dept head" in tlow or "department head" in tlow or "who's the" in tlow
    ):
        return "dept_head_one"

    if "INTENT_PREREQ" in labels or "prereq" in tlow or "prerequisite" in tlow:
        return "prerequisites"

    if "INTENT_UNITS" in labels or "units" in tlow:
        return "units"

    if any(w in tlow for w in ["subject", "subjects", "course", "courses", "curriculum"]):
        has_year_hint = (
            "year" in tlow
            or "yr " in tlow
            or any(x in tlow for x in ["1st", "2nd", "3rd", "4th", "first", "second", "third", "fourth"])
        )
        has_prog_hint = any(
            x in tlow
            for x in [
                # Computer Science
                "cs",
                "computer science",
                "bscs",
                "bs cs",
                # Psychology
                "psych",
                "psychology",
                "bs psych",
                # Biology
                "bio",
                "biology",
                "bsbio",
                "bs bio",
                # Political Science
                "political science",
                "polsci",
                "ab ps",
                "abps",
                "baps",
                "ba ps",
                # Communication
                "communication",
                "comm",
                # English Language
                "bael",
                "abel",
                "english language",
            ]
        )
        if has_year_hint or has_prog_hint:
            return "curriculum"

    has_year_only = (
        "year" in tlow
        or "yr " in tlow
        or any(x in tlow for x in ["1st", "2nd", "3rd", "4th", "first", "second", "third", "fourth"])
    )
    has_prog_only = any(
        x in tlow
        for x in [
            # Computer Science
            "cs",
            "computer science",
            "bscs",
            "bs cs",
            # Psychology
            "psych",
            "psychology",
            "bs psych",
            # Biology
            "bio",
            "biology",
            "bsbio",
            "bs bio",
            # Political Science
            "political science",
            "polsci",
            "ab ps",
            "abps",
            "baps",
            "ba ps",
            # Communication
            "communication",
            "comm",
            # English Language
            "bael",
            "abel",
            "english language",
        ]
    )
    if has_year_only and has_prog_only:
        return "curriculum"

    # Fallback: course info / single-course questions
    return "courseinfo"


def _extract_year(text: str) -> Optional[int]:
    tl = (text or "").lower()
    for k, v in YEAR_WORDS.items():
        if k in tl:
            return v

    m = re.search(r"\b(?:year|yr)\s*(\d)\b", tl)
    if m:
        return int(m.group(1))

    m2 = re.search(r"\b(1st|2nd|3rd|4th)\s+year\b", tl)
    if m2:
        return int(m2.group(1)[0])

    return None


def _extract_term(text: str) -> Optional[int]:
    """
    Extract a term/semester number (1–3) from text, based on phrases like
    '1st semester', 'first trimester', '2nd term', etc.
    """
    tl = (text or "").lower()

    # 1st / first
    if re.search(r"\b(1st|first)\s+(sem|sem\.|semester|trimester|term)\b", tl):
        return 1
    # 2nd / second
    if re.search(r"\b(2nd|second)\s+(sem|sem\.|semester|trimester|term)\b", tl):
        return 2
    # 3rd / third
    if re.search(r"\b(3rd|third)\s+(sem|sem\.|semester|trimester|term)\b", tl):
        return 3

    return None


def extract_entities(text: str) -> Dict[str, Optional[str]]:
    doc = nlp(text or "")

    ents: Dict[str, Optional[str]] = {
        "program": None,
        "course_title": None,
        "course_code": None,
        "department": None,
        "year_num": None,
        "term_num": None,
    }

    m = CODE_RE.search(text or "")
    if m:
        ents["course_code"] = f"{m.group(1)}{m.group(2)}"

    for mid, s, e in phrase_matcher(doc):
        label = nlp.vocab.strings[mid]
        span_text = doc[s:e].text
        if label == "PROG" and not ents["program"]:
            ents["program"] = span_text
        elif label == "COURSETITLE" and not ents["course_title"]:
            ents["course_title"] = span_text
        elif label == "DEPT" and not ents["department"]:
            ents["department"] = span_text

    ents["year_num"] = _extract_year(text)
    ents["term_num"] = _extract_term(text)

    return ents

