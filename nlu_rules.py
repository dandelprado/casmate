import re
from typing import Dict, List, Optional
import spacy
from spacy.matcher import Matcher, PhraseMatcher

nlp = spacy.blank("en")
matcher = Matcher(nlp.vocab)
phrase_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

WS_RE = re.compile(r'\s+')
PUNCT_RE = re.compile(r'[-/]')
CODE_RE = re.compile(r'([A-Za-z]{2,4})-?(\d{2,3})')

PROGRAM_CANON = {
    "CS": "BS in Computer Science",
    "BSCS": "BS in Computer Science",
    "PSYCH": "BS in Psychology",
    "BS PSYCH": "BS in Psychology",
    "POLSAY": "BA in Political Science",
    "POLSCI": "BA in Political Science",
    "AB POLSCI": "BA in Political Science",
    "BAEL": "BA in English Language",
    "ABEL": "BA in English Language",
    "BACOMM": "BA in Communications",
    "COMM": "BA in Communications",
    "BIO": "BS in Biology",
    "BS BIO": "BS in Biology",
}


def norm_key(s: str) -> str:
    return ''.join(s or '').strip().upper()


PROGRAM_ABBREVIATIONS: Dict[str, str] = {norm_key(k): v for k, v in PROGRAM_CANON.items()}


def build_gazetteers(programs: List[Dict], courses: List[Dict], synonyms: List[Dict]):
    """Build phrase matchers for programs and course titles"""
    if "PROG" in phrase_matcher:
        phrase_matcher.remove("PROG")
    if "COURSETITLE" in phrase_matcher:
        phrase_matcher.remove("COURSETITLE")

    prog_docs = [nlp(p["program_name"]) for p in programs if p.get("program_name")]
    base_docs = []
    for p in programs:
        name = p.get("program_name") or ''
        low = name.lower()
        if low.startswith("bs "):
            base_docs.append(nlp(name[3:]))
        elif low.startswith("ba "):
            base_docs.append(nlp(name[3:]))
    abbrev_docs = [nlp(k) for k in PROGRAM_ABBREVIATIONS.keys()]
    all_prog_docs = prog_docs + base_docs + abbrev_docs
    if all_prog_docs:
        phrase_matcher.add("PROG", all_prog_docs)

    title_docs = [nlp(c["course_title"]) for c in courses if c.get("course_title")]
    alias_docs = []
    if synonyms:
        for row in synonyms:
            alias = row.get("alias")
            if alias:
                alias_docs.append(nlp(alias))
                if alias.endswith('s'):
                    alias_docs.append(nlp(alias[:-1]))
                else:
                    alias_docs.append(nlp(alias + " s"))
    short_docs = []
    for c in courses:
        t = (c.get("course_title") or '').lower()
        if "data structure" in t or "data structures" in t:
            variations = ["data struct", "datastruct", "data structure", "data structures", 
                         "ds", "data algo", "data structures and algorithms", "dsa", "data struct algo"]
            for v in variations:
                short_docs.append(nlp(v))
        if "calculus" in t:
            calc_vars = ["calc 1", "cal 1", "calculus 1", "calc i", "calculus i", "calc"]
            for v in calc_vars:
                short_docs.append(nlp(v))
        if "psychology" in t:
            short_docs.extend([nlp("psych"), nlp("psychology"), nlp("intro psych")])
        if "biology" in t:
            short_docs.extend([nlp("bio"), nlp("biology"), nlp("general bio")])
    all_course_docs = title_docs + alias_docs + short_docs
    if all_course_docs:
        phrase_matcher.add("COURSETITLE", all_course_docs)


def add_lower_in(name: str, words: List[str]):
    """Helper to add lowercase word patterns"""
    matcher.add(name, [[{"LOWER": {"IN": words}}]])


add_lower_in("INTENT_GREET", ["hi", "hello", "hey"])
add_lower_in("INTENT_GOODBYE", ["bye", "goodbye", "thanks", "thank", "tnx"])

matcher.add("INTENT_CONFIRM", [
    [{"LOWER": {"IN": ["sure"]}}, {"LOWER": {"IN": ["are", "correct"]}}, {"LOWER": {"IN": ["you"]}}, {"OP": "?"}],
    [{"LOWER": {"IN": ["sure", "correct"]}}],
    [{"LOWER": {"IN": ["correct"]}}],
])

matcher.add("INTENT_CONFUSION", [
    [{"LOWER": {"IN": ["i"]}}, {"LOWER": {"IN": ["dont", "don't"]}}, {"LOWER": {"IN": ["get", "understand"]}}],
    [{"LOWER": {"IN": ["what", "huh"]}}, {"OP": "?"}],
    [{"LOWER": {"IN": ["what"]}}, {"LOWER": {"IN": ["are"]}}, {"OP": "?"}, {"LOWER": {"IN": ["talking", "saying"]}}, {"OP": "?"}],
    [{"LOWER": {"IN": ["huh", "again", "repeat"]}}],
])

matcher.add("INTENT_PREREQ", [
    [{"LOWER": {"IN": ["prereq", "prereqs", "prerequisite", "prerequisites", "requirement", "requirements"]}}],
    [{"LOWER": {"IN": ["what", "whats", "what's"]}}, {"LOWER": {"IN": ["is", "are", "the"]}}, {"OP": "?"}, 
     {"LOWER": {"IN": ["the"]}, "OP": "?"}, {"LOWER": {"IN": ["prereq", "prereqs", "prerequisite", "prerequisites", "requirement"]}}],
    [{"LOWER": {"IN": ["prereq", "prereqs", "prerequisite", "prerequisites"]}}, 
     {"LOWER": {"IN": ["of", "for"]}}],
    [{"LOWER": {"IN": ["what"]}}, {"LOWER": {"IN": ["do", "should"]}, "OP": "?"}, 
     {"LOWER": {"IN": ["i", "we"]}, "OP": "?"}, {"LOWER": {"IN": ["need", "take"]}}, 
     {"LOWER": {"IN": ["before", "for", "prior"]}}],
])

matcher.add("INTENT_PLAN", [
    [{"LOWER": {"IN": ["first", "second", "third", "fourth", "1st", "2nd", "3rd", "4th", "year", "yr"]}}, 
     {"LOWER": {"IN": ["semester", "sem", "trimester", "tri"]}, "OP": "?"}],
])

matcher.add("INTENT_FACULTY", [
    [{"LOWER": {"IN": ["who"]}}, {"LOWER": {"IN": ["is", "teaches", "teaching"]}}, {"OP": "*"}],
    
    [{"LOWER": {"IN": ["who"]}}, {"LOWER": {"IN": ["is"]}}, {"LOWER": {"IN": ["the"]}}, {"OP": "?"}, 
     {"LOWER": {"IN": ["dean", "head", "chair"]}}],
    [{"LOWER": {"IN": ["dean", "head", "chair"]}}, {"LOWER": {"IN": ["of"]}}],
    [{"LOWER": {"IN": ["cas", "college"]}}, {"LOWER": {"IN": ["dean"]}}],
    [{"LOWER": {"IN": ["current"]}}, {"LOWER": {"IN": ["dean", "head"]}}],
    
    [{"LOWER": {"IN": ["department"]}}, {"LOWER": {"IN": ["head", "chair"]}}],
    [{"LOWER": {"IN": ["head"]}}, {"LOWER": {"IN": ["of"]}}, {"OP": "*"}],
])


def detect_intent(text: str) -> str:
    """Detect user's intent from input text"""
    doc = nlp(text or '')
    matches = [nlp.vocab.strings[mid] for mid, _, _ in matcher(doc)]
    text_lower = (text or '').lower()
    prereq_keywords = ["prereq", "prerequisite", "requirement", "what's the prerequisite", "whats the prerequisite"]
    has_prereq_keyword = any(kw in text_lower for kw in prereq_keywords)
    if "INTENT_PREREQ" in matches or has_prereq_keyword:
        return "prerequisites"
    if "INTENT_GREET" in matches:
        return "smalltalk"
    if "INTENT_GOODBYE" in matches:
        return "goodbye"
    if "INTENT_CONFIRM" in matches:
        return "confirm"
    if "INTENT_CONFUSION" in matches:
        return "confusion"
    if "INTENT_FACULTY" in matches:
        return "facultylookup"
    if "INTENT_PLAN" in matches:
        return "planlookup"
    return "courseinfo"


def extract_entities(text: str) -> Dict[str, Optional[str]]:
    """Extract program names, course titles, and course codes"""
    doc = nlp(text or '')
    ents = {"program": None, "course_title": None, "course_code": None}
    for mid, s, e in phrase_matcher(doc):
        label = nlp.vocab.strings[mid]
        span_text = doc[s:e].text
        if label == "PROG" and not ents["program"]:
            key = norm_key(span_text)
            ents["program"] = PROGRAM_ABBREVIATIONS.get(key, span_text)
        elif label == "COURSETITLE" and not ents["course_title"]:
            ents["course_title"] = span_text
    m = CODE_RE.search(text or '')
    if m and not ents["course_code"]:
        ents["course_code"] = f"{m.group(1).upper()}-{m.group(2)}"
    return ents

