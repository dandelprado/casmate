import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rapidfuzz import process, fuzz

DATADIR = (Path(__file__).parent / "data").resolve()

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]")

CODE_RE = re.compile(r"\b([A-Za-z]{2,4})-?(\d{2,3})\b")


PROGRAM_ABBREV = {
    # BS Computer Science
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

    # BS Psychology
    "PSYCH": "Bachelor of Science in Psychology",
    "BS PSYCH": "Bachelor of Science in Psychology",
    "BSPSYCH": "Bachelor of Science in Psychology",
    "PSYCHOLOGY": "Bachelor of Science in Psychology",

    # BA Political Science
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

    # BA English Language
    "BAEL": "BA in English Language",
    "ABEL": "BA in English Language",

    # BA Communication
    "BACOMM": "Bachelor of Arts in Communication",
    "COMM": "Bachelor of Arts in Communication",
    "COMMUNICATION": "Bachelor of Arts in Communication",
    "ABCOMM": "Bachelor of Arts in Communication",
    "AB COMM": "Bachelor of Arts in Communication",
    "BA COMM": "Bachelor of Arts in Communication",

    # BS Biology
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


def _normalize_phrase(s: str) -> str:
    t = (s or "").lower()
    t = _PUNCT.sub(" ", t)
    t = _WS.sub(" ", t).strip()
    parts = t.split()
    if parts and len(parts[-1]) > 3 and parts[-1].endswith("s"):
        parts[-1] = parts[-1][:-1]
    return " ".join(parts)


def _clean_course_query(text: str) -> str:
    base = _normalize_phrase(text)
    if not base:
        return ""

    tokens = base.split()

    remove = {
        "what", "whats", "what's",
        "is", "are", "the",
        "of", "for",
        "subject", "course", "subjects", "courses",
        "prereq", "prereqs", "prerequisite", "prerequisites",
        "requirement", "requirements",
        "in", "about", "regarding",
        "do", "does", "should", "need", "take",
        "before", "prior",
    }

    kept = [t for t in tokens if t not in remove]

    # If everything was stripped, fall back to the normalized base.
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
            parts = s.split("/")
            total = 0
            for p in parts:
                p = p.strip()
                if not p:
                    continue
                total += int(p)
            return total
        return int(float(s))
    except Exception:
        return 0


def _flatten_plan(plan_raw: List[Dict]) -> List[Dict]:
    if not plan_raw:
        return []

    if "terms" not in plan_raw[0]:
        return plan_raw

    flat: List[Dict] = []
    for prog in plan_raw:
        pid = prog.get("program_id")
        terms = prog.get("terms") or []
        for term in terms:
            year_level = term.get("year_level")
            semester = term.get("term")
            courses = term.get("courses") or []
            for code in courses:
                flat.append(
                    {
                        "program_id": pid,
                        "year_level": year_level,
                        "semester": semester,
                        "course_id": code,
                    }
                )
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
        if "units" not in row:
            cu = row.get("credit_units")
            row["units"] = _credit_units_to_int(cu)
        out.append(row)
    return out


def load_all() -> Dict:
    departments = _load_json("departments.json")
    programs = _load_json("programs.json")
    courses_raw = _load_json("courses.json")
    plan_raw = _load_json("curriculum_plan.json")
    prereqs_raw = _load_json("prerequisites.json")
    faculty = _load_json("faculty.json")

    courses = _postprocess_courses(courses_raw)
    plan = _flatten_plan(plan_raw)
    prereqs = _normalize_prereqs(prereqs_raw)

    return {
        "departments": departments,
        "programs": programs,
        "courses": courses,
        "plan": plan,
        "prereqs": prereqs,
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


def fuzzy_best_course_title(
    courses: List[Dict], query: str, score_cutoff: int = 80
) -> Optional[Tuple[str, int, Dict]]:
    if not query:
        return None
    choices = {c["course_title"]: c for c in courses if c.get("course_title")}
    if not choices:
        return None
    result = process.extractOne(query, choices.keys(), scorer=fuzz.WRatio, score_cutoff=score_cutoff)
    if not result:
        return None
    match, score, _ = result
    return match, score, choices[match]


def fuzzy_top_course_titles(
    courses: List[Dict], query: str, limit: int = 3, score_cutoff: int = 60
) -> List[Tuple[str, int, Dict]]:
    if not query:
        return []
    choices = {c["course_title"]: c for c in courses if c.get("course_title")}
    if not choices:
        return []
    results = process.extract(
        query, choices.keys(), scorer=fuzz.WRatio, limit=limit, score_cutoff=score_cutoff
    )
    return [(m, s, choices[m]) for m, s, _ in results]


def _keyword_match_course(courses: List[Dict], text: str) -> Optional[Dict]:
    clean = _clean_course_query(text)
    if not clean:
        return None

    q_tokens = set(clean.split())
    if not q_tokens:
        return None

    best_course: Optional[Dict] = None
    best_overlap = 0

    for c in courses:
        title = c.get("course_title") or ""
        norm_title = _normalize_phrase(title)
        title_tokens = set(norm_title.split())
        overlap = len(q_tokens & title_tokens)
        if overlap > best_overlap:
            best_overlap = overlap
            best_course = c

    # Require at least one overlapping token to avoid nonsense matches.
    if best_overlap > 0:
        return best_course

    return None


def course_by_alias(data: Dict, alias: str) -> Optional[Dict]:
    if not alias:
        return None

    courses = data.get("courses", [])
    if not courses:
        return None

    # 1) Try keyword/token overlap on the cleaned query.
    kw_hit = _keyword_match_course(courses, alias)
    if kw_hit:
        return kw_hit

    # 2) Try fuzzy match on the raw text.
    fb = fuzzy_best_course_title(courses, alias, score_cutoff=70)
    if fb:
        return fb[2]

    # 3) Try fuzzy match again on the cleaned text.
    clean = _clean_course_query(alias)
    if clean and clean != alias:
        fb = fuzzy_best_course_title(courses, clean, score_cutoff=70)
        if fb:
            return fb[2]

    return None


def find_course_any(data: Dict, text: str) -> Optional[Dict]:
    courses = data.get("courses", [])
    if not text or not courses:
        return None

    text_upper = (text or "").upper()
    no_space = text_upper.replace(" ", "")

    for c in courses:
        code = (c.get("course_code") or c.get("course_id") or "").upper()
        if not code:
            continue
        code_no_space = code.replace(" ", "")
        if code in text_upper or code_no_space in no_space:
            return c

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
    if not fb:
        clean = _clean_course_query(text)
        if clean and clean != text:
            fb = fuzzy_best_course_title(courses, clean, score_cutoff=70)

    if fb:
        return fb[2]

    return None


def fuzzy_best_program(
    programs: List[Dict], query: str, score_cutoff: int = 70
) -> Optional[Tuple[str, int, Dict]]:
    if not query:
        return None

    query_upper = query.strip().upper()
    if query_upper in PROGRAM_ABBREV:
        target_name = PROGRAM_ABBREV[query_upper]
        for p in programs:
            if (p.get("program_name") or "").strip().upper() == target_name.upper():
                return (query, 100, p)
    for p in programs:
        pname = (p.get("program_name") or "").strip()
        if pname.upper() == query_upper:
            return (pname, 100, p)
    for p in programs:
        pname = (p.get("program_name") or "").strip()
        if query_upper in pname.upper():
            return (pname, 95, p)
    for p in programs:
        sname = (p.get("short_name") or "").strip()
        if sname.upper() == query_upper:
            return (p.get("program_name"), 100, p)
        if query_upper in sname.upper():
            return (p.get("program_name"), 95, p)
    choices: Dict[str, Dict] = {}
    for p in programs:
        name = p.get("program_name") or ""
        if name:
            choices[name] = p
    for p in programs:
        sname = p.get("short_name") or ""
        if sname:
            choices[sname] = p
    for p in programs:
        name = p.get("program_name") or ""
        low = name.lower()
        if low.startswith("bachelor of science in "):
            short = name[23:]
            choices[short] = p
        elif low.startswith("bachelor of arts in "):
            short = name[20:]
            choices[short] = p
    for abbrev, full_name in PROGRAM_ABBREV.items():
        row = next(
            (p for p in programs if (p.get("program_name") or "").upper() == full_name.upper()),
            None,
        )
        if row:
            choices[abbrev] = row

    if not choices:
        return None

    result = process.extractOne(query, list(choices.keys()), scorer=fuzz.WRatio, score_cutoff=score_cutoff)
    if not result:
        return None
    match, score, _ = result
    return match, score, choices[match]


def get_prerequisites(
    prereqs: List[Dict],
    courses: List[Dict],
    course_id: str,
) -> List[Dict]:
    if not course_id:
        return []

    needed: List[Dict] = []
    seen = set()

    by_id: Dict[str, Dict] = {}
    for c in courses:
        cid = c.get("course_id")
        if cid:
            by_id[cid] = c

    for p in prereqs:
        if p.get("course_id") != course_id:
            continue

        ptype = (p.get("type") or "course").lower()
        pre_id = p.get("prerequisite_course_id")

        if not pre_id or pre_id in seen:
            continue

        if ptype != "course":
            continue

        prereq_course = by_id.get(pre_id)
        if prereq_course:
            seen.add(pre_id)
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


def courses_for_plan(
    plan: List[Dict],
    courses: List[Dict],
    program_id: str,
    year: int,
    semester: int,
) -> List[Dict]:
    rows: List[Dict] = []

    by_id: Dict[str, Dict] = {}
    for c in courses:
        cid = c.get("course_id")
        if cid:
            by_id[cid] = c

    for entry in plan:
        if (
            entry.get("program_id") == program_id
            and str(entry.get("year_level")) == str(year)
            and str(entry.get("semester")) == str(semester)
        ):
            cid = entry.get("course_id")
            course = by_id.get(cid)
            if course:
                rows.append(course)

    return rows


def units_by_program_year(
    plan: List[Dict],
    courses: List[Dict],
    program_id: str,
    year: int,
) -> Tuple[int, Dict[str, int]]:
    by_sem: Dict[str, int] = {}
    total = 0

    for sem in ["1", "2", "3"]:
        sem_courses: List[Dict] = []

        for entry in plan:
            if (
                entry.get("program_id") == program_id
                and str(entry.get("year_level")) == str(year)
                and str(entry.get("semester")) == str(sem)
            ):
                cid = entry.get("course_id")
                c = next((x for x in courses if x.get("course_id") == cid), None)
                if c:
                    sem_courses.append(c)

        sem_units = sum(_to_units(c.get("units")) for c in sem_courses)
        if sem_units > 0:
            by_sem[sem] = sem_units
            total += sem_units

    return total, by_sem


def units_by_program_year_with_exclusions(
    plan: List[Dict],
    courses: List[Dict],
    program_id: str,
    year: int,
) -> Tuple[int, Dict[str, int], bool]:
    DIAGNOSTIC_COURSES = {"IMAT", "IENG"}
    
    by_sem: Dict[str, int] = {}
    total = 0
    diagnostic_excluded = False

    for sem in ["1", "2", "3"]:
        sem_courses: List[Dict] = []

        for entry in plan:
            if (
                entry.get("program_id") == program_id
                and str(entry.get("year_level")) == str(year)
                and str(entry.get("semester")) == str(sem)
            ):
                cid = entry.get("course_id")
                c = next((x for x in courses if x.get("course_id") == cid), None)
                if c:
                    course_code = (c.get("course_code") or "").strip().upper()
                    if course_code in DIAGNOSTIC_COURSES:
                        diagnostic_excluded = True
                        continue
                    sem_courses.append(c)

        sem_units = sum(_to_units(c.get("units")) for c in sem_courses)
        if sem_units > 0:
            by_sem[sem] = sem_units
            total += sem_units

    return total, by_sem, diagnostic_excluded


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
    if not choices:
        return None

    result = process.extractOne(name, list(choices.keys()), scorer=fuzz.WRatio, score_cutoff=70)
    if result:
        return choices[result[0]]

    return None


def list_department_heads(departments: List[Dict]) -> List[Dict]:
    rows: List[Dict] = []
    for d in departments:
        head = d.get("department_head") or ""
        if head:
            rows.append(
                {
                    "department_id": d.get("department_id"),
                    "department_name": d.get("department_name"),
                    "department_head": head,
                    "dean_flag": d.get("dean_flag") or "N",
                }
            )

    rows.sort(
        key=lambda r: 0 if (r.get("dean_flag") or "N").upper() == "Y" else 1
    )
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
    return next(
        (d for d in departments if (d.get("dean_flag") or "N").upper() == "Y"),
        None,
    )

