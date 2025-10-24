import csv
import re
from pathlib import Path
from rapidfuzz import process, fuzz
from typing import Dict, List, Optional

DATADIR = (Path(__file__).parent / "data").resolve()
_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]")

def _normalize_phrase(s: str) -> str:
    t = (s or "").lower()
    t = _PUNCT.sub(" ", t)
    t = _WS.sub(" ", t).strip()
    parts = t.split()
    if parts and len(parts[-1]) > 3 and parts[-1].endswith("s"):
        parts[-1] = parts[-1][:-1]
    return " ".join(parts)

def _read_csv_clean(path: Path) -> List[Dict]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames:
            reader.fieldnames = [h.strip() for h in reader.fieldnames]
        rows: List[Dict] = []
        for row in reader:
            rows.append({(k.strip() if isinstance(k, str) else k): (v.strip() if isinstance(v, str) else v)
                        for k, v in row.items()})
        return rows

def _load_csv(name: str) -> List[Dict]:
    path = (DATADIR / name).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Missing data file: {path}")
    return _read_csv_clean(path)

def load_all() -> Dict:
    departments = _load_csv("departments.csv")
    programs = _load_csv("programs.csv")
    courses = _load_csv("courses.csv")
    plan = _load_csv("curriculum_plan.csv")
    prereqs = _load_csv("prerequisites.csv")
    synonyms = _load_csv("synonyms.csv")
    return {
        "departments": departments,
        "programs": programs,
        "courses": courses,
        "plan": plan,
        "prereqs": prereqs,
        "synonyms": synonyms,
    }

def find_course_by_code(courses: List[Dict], code: str) -> Optional[Dict]:
    if not code:
        return None
    norm = code.strip().upper().replace(" ", "").replace("-", "")
    for c in courses:
        ccode = (c.get("course_code") or "").strip().upper().replace(" ", "").replace("-", "")
        if ccode == norm:
            return c
    return None

def courses_for_plan(plan: List[Dict], courses: List[Dict], program_id: str, year: int, semester: int) -> List[Dict]:
    rows = []
    for entry in plan:
        if (entry.get("program_id") == program_id
            and str(entry.get("year_level")) == str(year)
            and str(entry.get("semester")) == str(semester)):
            cid = entry.get("course_id")
            course = next((c for c in courses if c["course_id"] == cid), None)
            if course:
                rows.append(course)
    return rows

def fuzzy_best_program(programs: List[Dict], query: str, score_cutoff=70):
    if not query:
        return None
    choices = {p["program_name"]: p for p in programs}
    result = process.extractOne(
        query,
        choices.keys(),
        scorer=fuzz.WRatio,
        score_cutoff=score_cutoff
    )
    if not result:
        return None
    match, score, _ = result
    return match, score, choices[match]

def fuzzy_top_programs(programs: List[Dict], query: str, limit=3, score_cutoff=60):
    if not query:
        return []
    choices = {p["program_name"]: p for p in programs}
    results = process.extract(
        query,
        choices.keys(),
        scorer=fuzz.WRatio,
        limit=limit,
        score_cutoff=score_cutoff
    )
    return [(match, score, choices[match]) for match, score, _ in results]

def fuzzy_best_course_title(courses: List[Dict], query: str, score_cutoff=80):
    if not query:
        return None
    choices = {c["course_title"]: c for c in courses if c.get("course_title")}
    result = process.extractOne(
        query,
        choices.keys(),
        scorer=fuzz.WRatio,
        score_cutoff=score_cutoff
    )
    if not result:
        return None
    match, score, _ = result
    return match, score, choices[match]

def fuzzy_top_course_titles(courses: List[Dict], query: str, limit=3, score_cutoff=60):
    if not query:
        return []
    choices = {c["course_title"]: c for c in courses if c.get("course_title")}
    results = process.extract(
        query,
        choices.keys(),
        scorer=fuzz.WRatio,
        limit=limit,
        score_cutoff=score_cutoff
    )
    return [(match, score, choices[match]) for match, score, _ in results]

def get_prerequisites(prereqs: List[Dict], courses: List[Dict], course_id: str) -> List[Dict]:
    needed = []
    for p in prereqs:
        if p.get("course_id") == course_id:
            prereq_id = p.get("prerequisite_course_id")
            prereq_course = next((c for c in courses if c["course_id"] == prereq_id), None)
            if prereq_course:
                needed.append(prereq_course)
    return needed

def course_by_alias(data: Dict, alias: str) -> Optional[Dict]:
    """Match course by alias with enhanced normalization"""
    if not alias:
        return None
    
    synonyms = data.get("synonyms", [])
    courses = data.get("courses", [])
    
    alias_norm = _normalize_phrase(alias)
    
    # Direct alias match
    for row in synonyms:
        if _normalize_phrase(row.get("alias", "")) == alias_norm:
            cid = row.get("courseid") or row.get("course_id")
            if cid:
                return next((c for c in courses if c.get("course_id") == cid), None)
    
    for row in synonyms:
        row_alias = _normalize_phrase(row.get("alias", ""))
        if alias_norm in row_alias or row_alias in alias_norm:
            cid = row.get("courseid") or row.get("course_id")
            if cid:
                return next((c for c in courses if c.get("course_id") == cid), None)
    
    return None

