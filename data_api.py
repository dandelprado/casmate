import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

def _load_csv(name):
    path = DATA_DIR / name
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def load_all():
    return {
            "departments": _load_csv("departments.csv"),
            "programs": _load_csv("programs.csv"),
            "faculty": _load_csv("faculty.csv"),
            "courses": _load_csv("courses.csv"),
            "plan": _load_csv("curriculum_plan.csv"),
            }

def find_program(programs, text):
    t = text.strip().lower()
    for p in programs:
        if p["program_name"].strip().lower() == t:
            return p
    return None

def find_course_by_code(courses, code_text):
    if not code_text:
        return None
    norm = code_text.strip().upper().replace(" ", "")
    for c in courses:
        code = (c.get("course_code") or "").strip().upper().replace(" ", "")
        if code and code == norm:
            return c
    return None

def courses_for_plan(plan, courses, program_id, year_level, semester):
    rows = [
            r for r in plan
            if r["program_id"] == program_id
            and str(r["year_level"]) == str(year_level)
            and str(r["semester"]) == str(semester)
    ]
    ids = {r["course_id"] for r in rows}
    return [c for c in courses if c["course_id"] in ids]

def faculty_for_course(sections, faculty, course_id):


    return[]



