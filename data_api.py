import csv
from pathlib import Path
from rapidfuzz import process, fuzz

DATA_DIR = (Path(__file__).parent / "data").resolve()


def _load_csv(name: str):
    path = (DATA_DIR / name).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_all():
    return {
        "departments": _load_csv("departments.csv"),
        "programs": _load_csv("programs.csv"),
        "faculty": _load_csv("faculty.csv"),
        "courses": _load_csv("courses.csv"),
        "plan": _load_csv("curriculum_plan.csv"),
        "prereqs": _load_csv("prerequisites.csv") if (DATA_DIR / "prerequisites.csv").exists() else [],
        "synonyms": _load_csv("synonyms.csv") if (DATA_DIR / "synonyms.csv").exists() else [],
    }

def find_course_by_code(courses, code_text: str):
    if not code_text:
        return None
    norm = code_text.strip().upper().replace(" ", "").replace("-", "")
    for c in courses:
        code = (c.get("course_code") or "").strip().upper().replace(" ", "").replace("-", "")
        if code and code == norm:
            return c
    return None

def courses_for_plan(plan, courses, program_id: str, year_level: int, semester: int):
    rows = [r for r in plan if r["program_id"] == program_id and str(r["year_level"]) == str(year_level) and str(r["semester"]) == str(semester)]
    ids = {r["course_id"] for r in rows}
    return [c for c in courses if c["course_id"] in ids]

def fuzzy_best_program(programs, query: str, score_cutoff: int = 0):
    choice_map = {p["program_name"]: p for p in programs}
    if not choice_map:
        return None
    res = process.extractOne(query or "", choice_map.keys(), scorer=fuzz.WRatio)
    if not res:
        return None
    name, score, _ = res
    if int(score) < int(score_cutoff):
        return None
    return name, int(score), choice_map[name]

def fuzzy_top_programs(programs, query: str, limit: int = 3, score_cutoff: int = 0):
    choice_map = {p["program_name"]: p for p in programs}
    results = process.extract(query or "", choice_map.keys(), scorer=fuzz.WRatio, limit=limit)
    return [name for (name, score, _k) in results if int(score) >= int(score_cutoff)]

def fuzzy_best_course_title(courses, query: str, score_cutoff: int = 0):
    title_map = {c["course_title"]: c for c in courses}
    if not title_map:
        return None
    res = process.extractOne(query or "", title_map.keys(), scorer=fuzz.WRatio)
    if not res:
        return None
    title, score, _ = res
    if int(score) < int(score_cutoff):
        return None
    return title, int(score), title_map[title]

def fuzzy_top_course_titles(courses, query: str, limit: int = 3, score_cutoff: int = 0):
    title_map = {c["course_title"]: c for c in courses}
    results = process.extract(query or "", title_map.keys(), scorer=fuzz.WRatio, limit=limit)
    filtered = [(t, int(s), title_map[t]) for (t, s, _k) in results if int(s) >= int(score_cutoff)]
    return filtered

def get_prerequisites(prereqs, courses, course_id: str):
    reqs = [r for r in prereqs if r["course_id"] == course_id]
    id2course = {c["course_id"]: c for c in courses}
    resolved = []
    for r in reqs:
        pc = id2course.get(r["prerequisite_course_id"])
        if pc:
            resolved.append({
                "course_id": pc["course_id"],
                "course_code": pc.get("course_code") or pc["course_id"],
                "course_title": pc["course_title"],
            })
    return resolved

