import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rapidfuzz import process, fuzz, utils

DATADIR = (Path(__file__).parent / "data").resolve()

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]")
CODE_RE = re.compile(r"\b([A-Za-z]{2,4})[\s-]?(\d{2,})\b")

PROGRAM_ABBREV = {
    "CS": "Bachelor of Science in Computer Science",
    "BSCS": "Bachelor of Science in Computer Science",
    "COMPUTER SCIENCE": "Bachelor of Science in Computer Science",
    "COMP SCI": "Bachelor of Science in Computer Science",
    "COMSCI": "Bachelor of Science in Computer Science",
    "COM SCI": "Bachelor of Science in Computer Science",
    "BS COMP SCI": "Bachelor of Science in Computer Science",
    "BSCOMP SCI": "Bachelor of Science in Computer Science",
    "BS COM SCI": "Bachelor of Science in Computer Science",
    "BSCOMSCI": "Bachelor of Science in Computer Science",
    "PSYCH": "Bachelor of Science in Psychology",
    "BS PSYCH": "Bachelor of Science in Psychology",
    "BSPSYCH": "Bachelor of Science in Psychology",
    "PSYCHOLOGY": "Bachelor of Science in Psychology",
    "BS PSYCHOLOGY": "Bachelor of Science in Psychology",
    "POLSAY": "Bachelor of Arts in Political Science",
    "POLSCI": "Bachelor of Arts in Political Science",
    "AB POLSCI": "Bachelor of Arts in Political Science",
    "ABPOLSCI": "Bachelor of Arts in Political Science",
    "BAPOLSCI": "Bachelor of Arts in Political Science",
    "BA POLSCI": "Bachelor of Arts in Political Science",
    "POLITICAL SCIENCE": "Bachelor of Arts in Political Science",
    "POLS": "Bachelor of Arts in Political Science",
    "AB PS": "Bachelor of Arts in Political Science",
    "ABPS": "Bachelor of Arts in Political Science",
    "BAPS": "Bachelor of Arts in Political Science",
    "BA PS": "Bachelor of Arts in Political Science",
    "BAEL": "BA in English Language",
    "ABEL": "BA in English Language",
    "BACOMM": "Bachelor of Arts in Communication",
    "COMM": "Bachelor of Arts in Communication",
    "COMMUNICATION": "Bachelor of Arts in Communication",
    "ABCOMM": "Bachelor of Arts in Communication",
    "AB COMM": "Bachelor of Arts in Communication",
    "BA COMM": "Bachelor of Arts in Communication",
    "BIO": "Bachelor of Science in Biology",
    "BS BIO": "Bachelor of Science in Biology",
    "BSBIO": "Bachelor of Science in Biology",
    "BIOLOGY": "Bachelor of Science in Biology",
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

COURSE_TERM_SYNONYMS = {
    "stats": "statistics",
    "calc": "calculus",
    "info": "information",
    "intro": "introduction",
    "lab": "laboratory",
    "lec": "lecture"
}

COURSE_ALIASES = {
    "introduction programming": "Fundamentals of Programming",
    "fundamentals programming": "Fundamentals of Programming",
    "intermediate programming": "Intermediate Programming",
    "intro computing": "Introduction to Computing",
    "introduction computing": "Introduction to Computing",
    "automata": "Automata Theory and Formal Languages",
    "automata theory": "Automata Theory and Formal Languages",
    "data structures": "Data Structures and Algorithm",
    "data structure": "Data Structures and Algorithm",
    "math modern world": "Mathematics in the Modern World",
    "mathematics modern world": "Mathematics in the Modern World"
}


def _normalize_phrase(s: str) -> str:
    t = (s or "").lower()
    t = _PUNCT.sub(" ", t)
    t = _WS.sub(" ", t).strip()
    if not t:
        return ""
    parts = t.split()
    singular_parts = [p[:-1] if len(p) > 3 and p.endswith("s") else p for p in parts]
    return " ".join(singular_parts)


def _clean_course_query(text: str) -> str:
    base = _normalize_phrase(text)
    if not base:
        return base
    tokens = base.split()
    tokens = [COURSE_TERM_SYNONYMS.get(t, t) for t in tokens]
    remove = {
        "what", "whats", "what's", "is", "are", "the", "of", "for", "in", "on", "to", "and",
        "subject", "course", "subjects", "courses",
        "prereq", "prereqs", "prerequisite", "prerequisites",
        "requirement", "requirements",
        "about", "regarding", "do", "does", "should",
        "need", "take", "before", "prior",
        "how", "many", "unit", "units", "load", "total", "there"
    }
    kept = [t for t in tokens if t not in remove and not t.startswith("prereq") and not t.startswith("requirement")]
    return " ".join(kept) if kept else base


def _clean_program_query(text: str) -> str:
    base = _normalize_phrase(text)
    if not base:
        return base
    tokens = base.split()
    remove = {
        "what", "whats", "what's", "how", "many", "is", "are", "does", "do",
        "the", "a", "an", "of", "for", "in", "on", "about", "regarding",
        "take", "need", "unit", "units", "load", "total", "year", "yr",
        "freshman", "sophomore", "junior", "senior",
        "first", "1st", "second", "2nd", "third", "3rd", "fourth", "4th",
        "sem", "sem.", "semester", "trimester", "term",
    }
    kept = [t for t in tokens if t not in remove]
    return " ".join(kept) if kept else base


def _read_json_clean(path: Path) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"JSON file {path} must contain a list of objects")
    cleaned_data: List[Dict] = []
    for item in data:
        cleaned_item: Dict = {}
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


def _credit_units_to_int(val) -> int:
    if val is None:
        return 0
    s = str(val).strip()
    if not s:
        return 0
    try:
        if "/" in s:
            return sum(int(p) for p in s.split("/") if p.strip())
        return int(float(s))
    except:
        return 0


def _flatten_plan(plan_raw: List[Dict]) -> List[Dict]:
    if not plan_raw:
        return []
    if "terms" not in plan_raw[0]:
        return plan_raw
    flat: List[Dict] = []
    for prog in plan_raw:
        pid = prog.get("program_id")
        for term in prog.get("terms") or []:
            year, semester = term.get("year_level"), term.get("term")
            for code in term.get("courses") or []:
                flat.append({"program_id": pid, "year_level": year, "semester": semester, "course_id": code})
    return flat


def _normalize_prereqs(prereqs_raw: List[Dict]) -> List[Dict]:
    out: List[Dict] = []
    for row in prereqs_raw:
        r = dict(row)
        if "course_id" not in r and "course_code" in r:
            r["course_id"] = r.get("course_code")
        if "prerequisite_course_id" not in r and "prerequisite_course_code" in r:
            r["prerequisite_course_id"] = r.get("prerequisite_course_code")
        out.append(r)
    return out


def _postprocess_courses(courses: List[Dict]) -> List[Dict]:
    out: List[Dict] = []
    for c in courses:
        row = dict(c)
        code = row.get("course_code") or row.get("course_id")
        if code and not row.get("course_id"):
            row["course_id"] = code
        if not row.get("course_code") and row.get("course_id"):
            row["course_code"] = row.get("course_id")
        if "units" not in row:
            row["units"] = _credit_units_to_int(row.get("credit_units"))
        out.append(row)
    return out


def load_all() -> Dict:
    return {
        "departments": _load_json("departments.json"),
        "programs": _load_json("programs.json"),
        "courses": _postprocess_courses(_load_json("courses.json")),
        "plan": _flatten_plan(_load_json("curriculum_plan.json")),
        "prereqs": _normalize_prereqs(_load_json("prerequisites.json")),
        "faculty": _load_json("faculty.json"),
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


def fuzzy_best_course_title(
    courses: List[Dict], query: str, score_cutoff: int = 80
) -> Optional[Tuple[str, int, Dict]]:
    if not query:
        return None
    choices = {c["course_title"]: c for c in courses if c.get("course_title")}
    if not choices:
        return None
    result = process.extractOne(
        query, choices.keys(), scorer=fuzz.token_set_ratio, score_cutoff=score_cutoff, processor=utils.default_process
    )
    if not result:
        return None
    match, score, _ = result
    return match, score, choices[match]


def fuzzy_top_course_titles(
    courses: List[Dict], query: str, limit: int = 5, score_cutoff: int = 60
) -> List[Tuple[str, int, Dict]]:
    if not query:
        return []
    clean_q = _clean_course_query(query)
    if not clean_q:
        clean_q = query
    choices = {c["course_title"]: c for c in courses if c.get("course_title")}
    if not choices:
        return []
    results = process.extract(
        clean_q, choices.keys(), scorer=fuzz.token_set_ratio, limit=limit, score_cutoff=score_cutoff, processor=utils.default_process
    )
    return [(m, s, choices[m]) for m, s, _ in results]


def find_course_any(data: Dict, text: str) -> Tuple[Optional[Dict], str]:
    courses = data.get("courses", [])
    if not text or not courses:
        return None, "none"

    clean_for_alias = _clean_course_query(text)
    if clean_for_alias and clean_for_alias.lower() in COURSE_ALIASES:
        target = COURSE_ALIASES[clean_for_alias.lower()]
        for c in courses:
            if c.get("course_title", "").lower() == target.lower():
                return c, "alias"

    text_upper = (text or "").upper()
    m = CODE_RE.search(text_upper)
    if m:
        extracted = f"{m.group(1)}{m.group(2)}"
        for c in courses:
            ccode = (c.get("course_code") or "").strip().upper().replace(" ", "").replace("-", "")
            if ccode == extracted:
                return c, "code"
            if ccode.startswith(extracted):
                return c, "code"
        if extracted.startswith("CS"):
            alt_extracted = "CC" + extracted[2:]
            for c in courses:
                ccode = (c.get("course_code") or "").strip().upper().replace(" ", "").replace("-", "")
                if ccode.startswith(alt_extracted):
                    return c, "fuzzy_code"

    text_norm = _normalize_phrase(text)
    clean_text_norm = _normalize_phrase(clean_for_alias)
    
    exact_matches = []
    for c in courses:
        title = c.get("course_title", "")
        t_norm = _normalize_phrase(title)
        if t_norm == text_norm or t_norm == clean_text_norm:
            exact_matches.append(c)
    
    if exact_matches:
        return exact_matches[0], "exact_title"

    text_tokens = set(clean_text_norm.split())
    if len(text_tokens) >= 1:
        best_candidate = None
        best_overlap_ratio = 0.0
        
        for c in courses:
            title = c.get("course_title", "")
            title_norm = _normalize_phrase(title)
            title_tokens = set(title_norm.split())
            if not title_tokens: continue
            
            intersection = text_tokens.intersection(title_tokens)
            
            
            
            if len(intersection) == len(text_tokens):
                ratio = len(intersection) / len(title_tokens)
                if ratio > best_overlap_ratio:
                    best_overlap_ratio = ratio
                    best_candidate = c
        
        
        if best_candidate and best_overlap_ratio >= 0.8:
             return best_candidate, "exact_title_subset"

    for c in courses:
        code = (c.get("course_code") or c.get("course_id") or "").strip().upper()
        if not code:
            continue
        parts = [re.escape(p) for p in code.split()]
        pat = r"\b" + r"[\s-]*".join(parts) + r"\b"
        if re.search(pat, text_upper):
            return c, "code"

    text_nospace = text.replace(" ", "")
    code_choices = {c.get("course_code"): c for c in courses if c.get("course_code")}
    code_result = process.extractOne(text, code_choices.keys(), scorer=fuzz.ratio, score_cutoff=65, processor=utils.default_process)
    if not code_result:
        code_result = process.extractOne(text_nospace, code_choices.keys(), scorer=fuzz.ratio, score_cutoff=65, processor=utils.default_process)

    if code_result:
        match_code, score, _ = code_result
        if any(char.isdigit() for char in text):
            return code_choices[match_code], "fuzzy_code"

    fb = fuzzy_best_course_title(courses, text, score_cutoff=88)
    if fb:
        return fb[2], "fuzzy"
    if clean_for_alias and clean_for_alias != text:
        fb = fuzzy_best_course_title(courses, clean_for_alias, score_cutoff=88)
        if fb:
            return fb[2], "fuzzy"

    return None, "none"


def fuzzy_best_program(
    programs: List[Dict], query: str, score_cutoff: int = 70
) -> Optional[Tuple[str, int, Dict]]:
    if not query:
        return None
    raw = (query or "").strip()
    raw_upper = raw.upper()
    raw_tokens = [t for t in re.split(r"\s+", raw_upper) if t]
    abbrev_candidates = []
    for tok in raw_tokens:
        if tok in PROGRAM_ABBREV:
            abbrev_candidates.append(tok)
    if raw_upper in PROGRAM_ABBREV and raw_upper not in abbrev_candidates:
        abbrev_candidates.append(raw_upper)

    if abbrev_candidates:
        key = abbrev_candidates[0]
        target_full = PROGRAM_ABBREV[key].upper()
        for p in programs:
            pname = (p.get("program_name") or "").strip().upper()
            sname = (p.get("short_name") or "").strip().upper()
            if pname == target_full or sname == target_full or target_full in pname:
                return (raw, 100, p)

    cleaned = _clean_program_query(query)
    use_query = cleaned or query
    choices = {}
    for p in programs:
        name = p.get("program_name") or ""
        if name:
            choices[name] = p
        sname = p.get("short_name") or ""
        if sname:
            choices[sname] = p
    for abbrev, full_name in PROGRAM_ABBREV.items():
        full_up = full_name.upper()
        for p in programs:
            pname = (p.get("program_name") or "").strip().upper()
            sname = (p.get("short_name") or "").strip().upper()
            if pname == full_up or sname == full_up or full_up in pname:
                choices[abbrev] = p; break
    if not choices:
        return None
    result = process.extractOne(use_query, list(choices.keys()), scorer=fuzz.WRatio, score_cutoff=score_cutoff, processor=utils.default_process)
    if not result:
        return None
    match, score, _ = result
    return match, score, choices[match]


def get_prerequisites(prereqs: List[Dict], courses: List[Dict], course_id: str) -> List[Dict]:
    if not course_id: return []
    needed = []
    seen = set()
    by_id = {c.get("course_id"): c for c in courses if c.get("course_id")}
    for p in prereqs:
        if p.get("course_id") != course_id:
            continue
        ptype = (p.get("type") or "course").lower()
        pre_id = p.get("prerequisite_course_id")
        if not pre_id or pre_id in seen:
            continue
        if ptype != "course": continue
        prereq_course = by_id.get(pre_id)
        if prereq_course: seen.add(pre_id); needed.append(prereq_course)
    return needed

def get_program_head(programs: List[Dict], departments: List[Dict], query: str) -> Optional[Tuple[str, str]]:
    res = fuzzy_best_program(programs, query, score_cutoff=70)
    if not res:
        return None
    
    _, _, p_row = res
    pid = p_row.get("program_id")
    pname = p_row.get("program_name")
    dept_id = p_row.get("department_id")

    if not dept_id:
        return (pname, None)

    head_name = None
    for d in departments:
        if d.get("department_id") == dept_id:
            head_name = d.get("department_head")
            break
    return (pname, head_name)

def courses_for_plan(plan, courses, program_id, year, semester):
    rows = []
    by_id = {c.get("course_id"): c for c in courses if c.get("course_id")}
    for entry in plan:
        if (entry.get("program_id") == program_id and str(entry.get("year_level")) == str(year) and str(entry.get("semester")) == str(semester)):
            cid = entry.get("course_id")
            course = by_id.get(cid)
            if course: rows.append(course)
    return rows

def units_by_program_year(plan, courses, program_id, year):
    by_sem = {}
    total = 0
    for sem in ["1", "2", "3"]:
        sem_courses = []
        for entry in plan:
            if (entry.get("program_id") == program_id and str(entry.get("year_level")) == str(year) and str(entry.get("semester")) == str(sem)):
                cid = entry.get("course_id")
                c = next((x for x in courses if x.get("course_id") == cid), None)
                if c: sem_courses.append(c)
        sem_units = sum(_credit_units_to_int(c.get("units")) for c in sem_courses)
        if sem_units > 0: by_sem[sem] = sem_units; total += sem_units
    return total, by_sem

def units_by_program_year_with_exclusions(plan, courses, program_id, year):
    DIAGNOSTIC_COURSES = {"IMAT", "IENG"}
    by_sem = {}; diagnostic_by_sem = {}; total = 0
    for sem in ["1", "2", "3"]:
        sem_courses = []; had_diagnostic = False
        for entry in plan:
            if (entry.get("program_id") == program_id and str(entry.get("year_level")) == str(year) and str(entry.get("semester")) == str(sem)):
                cid = entry.get("course_id")
                c = next((x for x in courses if x.get("course_id") == cid), None)
                if c:
                    if (c.get("course_code") or "").strip().upper() in DIAGNOSTIC_COURSES:
                        had_diagnostic = True; continue
                    sem_courses.append(c)
        sem_units = sum(_credit_units_to_int(c.get("units")) for c in sem_courses)
        if sem_units > 0: by_sem[sem] = sem_units; total += sem_units
        diagnostic_by_sem[sem] = had_diagnostic
    return total, by_sem, diagnostic_by_sem

def list_department_heads(departments: List[Dict]) -> List[Dict]:
    rows = []
    for d in departments:
        head = d.get("department_head") or ""
        if head:
            rows.append({"department_id": d.get("department_id"), "department_name": d.get("department_name"), "department_head": head, "dean_flag": d.get("dean_flag") or "N"})
    rows.sort(key=lambda r: 0 if (r.get("dean_flag") or "N").upper() == "Y" else 1)
    return rows

def get_department_head_by_name(departments: List[Dict], dept_name: str) -> Optional[str]:
    d = department_lookup(departments, dept_name)
    return d.get("department_head") if d else None

def get_dept_role_label(dept_row: Dict, user_text: str) -> str:
    if not dept_row: return "Department head"
    if (dept_row.get("dean_flag") or "N").upper() == "Y": return "Dean"
    if "dean" in (user_text or "").lower(): return "Dean"
    return "Department head"

def get_cas_dean(departments: List[Dict]) -> Optional[Dict]:
    return next((d for d in departments if (d.get("dean_flag") or "N").upper() == "Y"), None)

def course_by_alias(data: Dict, alias: str) -> Optional[Dict]:
    return None 

def department_lookup(departments, name):
    if not name: return None
    key = _norm_upper(name)
    if key in DEPT_SYNONYMS: return get_department_by_id(departments, DEPT_SYNONYMS[key])
    for d in departments:
        if _norm_upper(d.get("department_name")) == key: return d
    for d in departments:
        if key in _norm_upper(d.get("department_name")): return d
    choices = {d.get("department_name") or "": d for d in departments}
    if not choices: return None
    result = process.extractOne(name, list(choices.keys()), scorer=fuzz.WRatio, score_cutoff=70, processor=utils.default_process)
    if result: return choices[result[0]]
    return None

def get_department_by_id(departments, dept_id):
    return next((d for d in departments if d.get("department_id") == dept_id), None)

def _norm_upper(s): return _PUNCT.sub(" ", (s or "")).upper().strip()
