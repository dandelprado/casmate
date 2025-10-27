import json
import re
from pathlib import Path
from rapidfuzz import process, fuzz
from typing import Dict, List, Optional, Tuple

DATADIR = (Path(__file__).parent / "data").resolve()

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]")
CODE_RE = re.compile(r"\b([A-Za-z]{2,4})-?(\d{2,3})\b")

PROGRAM_ABBREV = {
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

DEPT_SYNONYMS = {
    "CAS": "D-CAS",
    "COLLEGE OF ARTS AND SCIENCES": "D-CAS",
    "COMPUTER SCIENCE": "D-CS",
    "COMP SCI": "D-CS",
    "CS": "D-CS",
    "SOCIAL SCIENCES": "D-SS",
    "SOCSCI": "D-SS",
    "LANGUAGE AND LITERATURE": "D-LL",
    "LANG & LIT": "D-LL",
    "LANG LIT": "D-LL",
    "NATURAL SCIENCES": "D-NS",
    "NATSCI": "D-NS",
    "MATHEMATICS": "D-MATH",
    "MATH": "D-MATH",
}

def _normalize_phrase(s: str) -> str:
    t = (s or "").lower()
    t = _PUNCT.sub(" ", t)
    t = _WS.sub(" ", t).strip()
    parts = t.split()
    if parts and len(parts[-1]) > 3 and parts[-1].endswith("s"):
        parts[-1] = parts[-1][:-1]
    return " ".join(parts)

def _read_json_clean(path: Path) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"JSON file {path} must contain a list of objects")
    cleaned_data = []
    for item in data:
        cleaned_item = {}
        for key, value in item.items():
            clean_key = key.strip() if isinstance(key, str) else key
            clean_value = value.strip() if isinstance(value, str) else value
            cleaned_item[clean_key] = clean_value
        cleaned_data.append(cleaned_item)
    return cleaned_data

def _load_json(name: str) -> List[Dict]:
    path = (DATADIR / name).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Missing data file: {path}")
    return _read_json_clean(path)

def load_all() -> Dict:
    departments = _load_json("departments.json")
    programs = _load_json("programs.json")
    courses = _load_json("courses.json")
    plan = _load_json("curriculum_plan.json")
    prereqs = _load_json("prerequisites.json")
    synonyms = _load_json("synonyms.json")
    faculty = _load_json("faculty.json")
    return {
        "departments": departments,
        "programs": programs,
        "courses": courses,
        "plan": plan,
        "prereqs": prereqs,
        "synonyms": synonyms,
        "faculty": faculty,
    }


def find_course_by_code(courses: List[Dict], code: str) -> Optional[Dict]:
    if not code:
        return None
    norm = (code or "").strip().upper().replace(" ", "").replace("-", "")
    for c in courses:
        ccode = (c.get("course_code") or "").strip().upper().replace(" ", "").replace("-", "")
        if ccode == norm:
            return c
    return None

def fuzzy_best_course_title(courses: List[Dict], query: str, score_cutoff=80):
    if not query:
        return None
    choices = {c["course_title"]: c for c in courses if c.get("course_title")}
    result = process.extractOne(query, choices.keys(), scorer=fuzz.WRatio, score_cutoff=score_cutoff)
    if not result:
        return None
    match, score, _ = result
    return match, score, choices[match]

def fuzzy_top_course_titles(courses: List[Dict], query: str, limit=3, score_cutoff=60):
    if not query:
        return []
    choices = {c["course_title"]: c for c in courses if c.get("course_title")}
    results = process.extract(query, choices.keys(), scorer=fuzz.WRatio, limit=limit, score_cutoff=score_cutoff)
    return [(m, s, choices[m]) for m, s, _ in results]

def course_by_alias(data: Dict, alias: str) -> Optional[Dict]:
    if not alias:
        return None
    synonyms = data.get("synonyms", [])
    courses = data.get("courses", [])
    alias_norm = _normalize_phrase(alias)
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

def find_course_any(data: Dict, text: str) -> Optional[Dict]:
    courses = data.get("courses", [])
    m = CODE_RE.search(text or "")
    if m:
        code = f"{m.group(1)}{m.group(2)}"
        found = find_course_by_code(courses, code)
        if found:
            return found
    alias_hit = course_by_alias(data, text)
    if alias_hit:
        return alias_hit
    fb = fuzzy_best_course_title(courses, text, score_cutoff=70)
    if fb:
        return fb[2]
    return None


def fuzzy_best_program(programs: List[Dict], query: str, score_cutoff=70):
    if not query:
        return None
    choices = {p["program_name"]: p for p in programs if p.get("program_name")}
    for p in programs:
        name = p.get("program_name") or ""
        low = name.lower()
        if low.startswith("bs "):
            choices[name[3:]] = p
        elif low.startswith("ba "):
            choices[name[3:]] = p
    for k, v in PROGRAM_ABBREV.items():
        row = next((p for p in programs if (p.get("program_name") or "").lower() == v.lower()), None)
        if row:
            choices[k] = row
    result = process.extractOne(query, list(choices.keys()), scorer=fuzz.WRatio, score_cutoff=score_cutoff)
    if not result:
        return None
    match, score, _ = result
    return match, score, choices[match]


def get_prerequisites(prereqs: List[Dict], courses: List[Dict], course_id: str) -> List[Dict]:
    needed: List[Dict] = []
    seen = set()
    for p in prereqs:
        if p.get("course_id") == course_id:
            prereq_id = p.get("prerequisite_course_id")
            if prereq_id and prereq_id not in seen:
                seen.add(prereq_id)
                prereq_course = next((c for c in courses if c.get("course_id") == prereq_id), None)
                if prereq_course:
                    needed.append(prereq_course)
    return needed


def _to_units(val) -> int:
    try:
        return int(str(val).strip())
    except Exception:
        try:
            return int(float(str(val).strip()))
        except Exception:
            return 0

def courses_for_plan(plan: List[Dict], courses: List[Dict], program_id: str, year: int, semester: int) -> List[Dict]:
    rows = []
    for entry in plan:
        if (entry.get("program_id") == program_id
            and str(entry.get("year_level")) == str(year)
            and str(entry.get("semester")) == str(semester)):
            cid = entry.get("course_id")
            course = next((c for c in courses if c.get("course_id") == cid), None)
            if course:
                rows.append(course)
    return rows

def units_by_program_year(plan: List[Dict], courses: List[Dict], program_id: str, year: int) -> Tuple[int, Dict[str, int]]:
    by_sem: Dict[str, int] = {}
    total = 0
    for sem in ["1", "2", "3"]:
        sem_courses = []
        for entry in plan:
            if (entry.get("program_id") == program_id
                and str(entry.get("year_level")) == str(year)
                and str(entry.get("semester")) == str(sem)):
                cid = entry.get("course_id")
                c = next((x for x in courses if x.get("course_id") == cid), None)
                if c:
                    sem_courses.append(c)
        sem_units = sum(_to_units(c.get("units")) for c in sem_courses)
        if sem_units > 0:
            by_sem[sem] = sem_units
            total += sem_units
    return total, by_sem


def get_department_by_id(departments: List[Dict], dept_id: str) -> Optional[Dict]:
    return next((d for d in departments if d.get("department_id") == dept_id), None)

def _norm_upper(s: str) -> str:
    return _PUNCT.sub(" ", (s or "")).upper().strip()

def department_lookup(departments: List[Dict], name: str) -> Optional[Dict]:
    if not name:
        return None
    key = _norm_upper(name)
    if key in DEPT_SYNONYMS:
        return get_department_by_id(departments, DEPT_SYNONYMS[key])
    for d in departments:
        if _norm_upper(d.get("department_name")) == key:
            return d
    for d in departments:
        if key in _norm_upper(d.get("department_name")):
            return d
    choices = {d.get("department_name") or "": d for d in departments}
    result = process.extractOne(name, list(choices.keys()), scorer=fuzz.WRatio, score_cutoff=70)
    if result:
        return choices[result[0]]
    return None

def list_department_heads(departments: List[Dict]) -> List[Dict]:
    rows = []
    for d in departments:
        head = d.get("department_head") or ""
        if head:
            rows.append({
                "department_id": d.get("department_id"),
                "department_name": d.get("department_name"),
                "department_head": head,
                "dean_flag": d.get("dean_flag") or "N",
            })
    rows.sort(key=lambda r: 0 if (r.get("dean_flag") or "N").upper() == "Y" else 1)
    return rows

def get_department_head_by_name(departments: List[Dict], dept_name: str) -> Optional[str]:
    d = department_lookup(departments, dept_name)
    if not d:
        return None
    return d.get("department_head")

def get_dept_role_label(dept_row: Dict, user_text: str) -> str:
    if not dept_row:
        return "Department head"
    if (dept_row.get("dean_flag") or "N").upper() == "Y":
        return "Dean"
    if "dean" in (user_text or "").lower():
        return "Dean"
    return "Department head"

def get_cas_dean(departments: List[Dict]) -> Optional[Dict]:
    return next((d for d in departments if (d.get("dean_flag") or "N").upper() == "Y"), None)

