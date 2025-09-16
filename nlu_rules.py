import re
from typing import Dict, List, Optional

import spacy
from spacy.matcher import Matcher, PhraseMatcher

nlp = spacy.blank("en")

WS_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[^\w\s\-]+")
TAGALOG_PARTICLES = {"po","na","pa","ba","nga","naman","daw","raw","rin","din","lang","nlang"}


def normalize_text(text: str) -> str:
    t = (text or "").lower().replace("\u00a0"," ")
    t = PUNCT_RE.sub(" ", t)
    t = WS_RE.sub(" ", t).strip()
    return t


def tokenize(text: str) -> List[str]:
    return [tok for tok in WS_RE.split(text) if tok]


def strip_particles(tokens: List[str]) -> List[str]:
    return [t for t in tokens if t not in TAGALOG_PARTICLES]


def tl_simplify_token(tok: str) -> str:
    base = tok
    if "um" in base[:4]:
        base = base.replace("um","",1)
    for pref in ("ipag","mag","nag","pag","ma","na","i"):
        if base.startswith(pref):
            base = base[len(pref):]
            break
    if len(base) >= 4 and base[:2] == base[2:4]:
        base = base[2:]
    for suf in ("hin","in","an","han","ng"):
        if base.endswith(suf) and len(base) > len(suf)+1:
            base = base[:-len(suf)]
            break
    return base


def tl_simplify(tokens: List[str]) -> List[str]:
    return [tl_simplify_token(t) for t in tokens]


matcher = Matcher(nlp.vocab)
phrase_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

matcher.add("INTENT_GREET", [[{"LOWER":{"IN":["hi","hello","hey","kumusta","kamusta"]}}]])
matcher.add("INTENT_GOODBYE", [[{"LOWER":{"IN":["bye","goodbye","salamat","thanks"]}}]])
matcher.add("INTENT_PREREQ", [[{"LOWER":{"IN":["prereq","prerequisite","requirement","requirements","kailangan","dapat"]}}]])
matcher.add("INTENT_PLAN", [[{"LOWER":{"IN":["first","second","third","fourth","1st","2nd","3rd","4th","year"]}},{"LOWER":{"IN":["semester","sem"]},"OP":"?"}]])
matcher.add("INTENT_FACULTY", [[{"LOWER":{"IN":["who","sino"]}},{"LOWER":{"IN":["teaches","is","ang"]},"OP":"?"},{"LOWER":{"IN":["teaching","instructor","teacher"]},"OP":"?"}]])

CODE_RE = re.compile(r"\b([A-Za-z]{2,}\s?-?\s?\d{2,3})\b")


def build_gazetteers(programs: List[Dict], courses: List[Dict]):
    if "PROG" in phrase_matcher:
        phrase_matcher.remove("PROG")
    if "COURSE_TITLE" in phrase_matcher:
        phrase_matcher.remove("COURSE_TITLE")
    prog_docs = [nlp(p["program_name"]) for p in programs]
    title_docs = [nlp(c["course_title"]) for c in courses]
    if prog_docs:
        phrase_matcher.add("PROG", prog_docs)
    if title_docs:
        phrase_matcher.add("COURSE_TITLE", title_docs)


def detect_intent(text: str) -> str:
    doc = nlp(text or "")
    matches = {nlp.vocab.strings[m_id] for m_id, _s, _e in matcher(doc)}
    if "INTENT_GREET" in matches: return "small_talk"
    if "INTENT_GOODBYE" in matches: return "goodbye"
    if "INTENT_PREREQ" in matches: return "prerequisites"
    if "INTENT_FACULTY" in matches: return "faculty_lookup"
    if "INTENT_PLAN" in matches: return "plan_lookup"
    toks = tokenize(normalize_text(text)); toks = strip_particles(toks); lemmas = tl_simplify(toks)
    if any(l.startswith("turo") for l in lemmas): return "faculty_lookup"
    return "course_info"


def extract_entities(text: str) -> Dict[str, Optional[str]]:
    doc = nlp(text or "")
    ents: Dict[str, Optional[str]] = {"program": None, "course_title": None, "course_code": None}
    for m_id, s, e in phrase_matcher(doc):
        label = nlp.vocab.strings[m_id]
        span = doc[s:e].text
        if label == "PROG" and not ents["program"]:
            ents["program"] = span
        elif label == "COURSE_TITLE" and not ents["course_title"]:
            ents["course_title"] = span
    m = CODE_RE.search(text or "")
    if m:
        ents["course_code"] = m.group(1).upper().replace(" ", "").replace("-", "")
    return ents

