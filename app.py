import re
from pathlib import Path
from typing import Optional

import streamlit as st
from rapidfuzz import fuzz

from chat_ui import getchatbubblehtml, getfooterhtml

from data_api import (
    load_all,
    find_course_by_code,
    fuzzy_best_program,
    fuzzy_best_course_title,
    fuzzy_top_course_titles,
    get_prerequisites,
    course_by_alias,
    find_course_any,
    courses_for_plan,
    units_by_program_year,
    units_by_program_year_with_exclusions,
    list_department_heads,
    get_department_head_by_name,
    department_lookup,
    get_dept_role_label,
    get_cas_dean,
    _clean_course_query
)
from nlu_rules import (
    build_gazetteers,
    detect_intent,
    extract_entities,
)


def load_css_rel_path(css_path: Path):
    relpath = (Path(__file__).parent / css_path).resolve()
    if relpath.exists():
        css = relpath.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


st.set_page_config(page_title="CASmate Chat", layout="centered")
load_css_rel_path(Path("styles.css"))


@st.cache_data(show_spinner=False)
def bootstrap_data():
    data = load_all()
    build_gazetteers(data["programs"], data["courses"], data["departments"])
    return data


data = bootstrap_data()

if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "did_intro_prompt" not in st.session_state:
    st.session_state.did_intro_prompt = False
if "chat" not in st.session_state:
    st.session_state.chat = []
if "awaiting_dept_scope" not in st.session_state:
    st.session_state.awaiting_dept_scope = False
if "pending_intent" not in st.session_state:
    st.session_state.pending_intent = None
if "awaiting_college_scope" not in st.session_state:
    st.session_state.awaiting_college_scope = False


def render_header():
    st.markdown(
        """
        <div class="hero">
          <h1 class="hero-title gradient-text">CASmate — College of Arts & Sciences Assistant</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )


render_header()


def render_message(sender, message):
    st.markdown(
        getchatbubblehtml(sender, message, user_name=st.session_state.user_name),
        unsafe_allow_html=True
    )


if not st.session_state.did_intro_prompt:
    st.session_state.chat.append({"sender": "CASmate", "message": "Hello! I'm CASmate. What's your name?"})
    st.session_state.did_intro_prompt = True

for msg in st.session_state.chat:
    render_message(msg["sender"], msg["message"])

CODE_RE = re.compile(r"\b([A-Za-z]{2,4})[\s-]?(\d{2,})\b")
GREETINGS = {
    "hi", "hello", "hey", "hiya", "yo", "howdy", "good morning", "good afternoon", "good evening",
    "greetings", "sup", "morning", "afternoon", "evening"
}
NON_NAMES = {"thanks", "thank you", "ok", "okay", "pls", "please", "yes", "no"}

COLLEGE_ALIASES = {
    "CAS": ["CAS", "COLLEGE OF ARTS AND SCIENCES", "COLLEGE OF ARTS & SCIENCES"],
    "CCJE": ["CCJE", "COLLEGE OF CRIMINAL JUSTICE EDUCATION"],
    "COL": ["COL", "COLLEGE OF LAW"],
    "COBE": ["COBE", "COLLEGE OF BUSINESS EDUCATION"],
    "COME": ["COME", "COLLEGE OF MARITIME EDUCATION"],
    "CTE": ["CTE", "COLLEGE OF TEACHER EDUCATION"],
    "CAHS": ["CAHS", "COLLEGE OF ALLIED HEALTH SCIENCES"],
    "CIHTM": ["CIHTM", "COLLEGE OF INTERNATIONAL HOSPITALITY AND TOURISM MANAGEMENT"],
    "CEAT": ["CEAT", "COLLEGE OF ENGINEERING", "COLLEGE OF ENGINEERING, ARCHITECTURE, AND TECHNOLOGY", "COLLEGE OF ENGINEERING ARCHITECTURE AND TECHNOLOGY"],
}

NWU_OFFICIAL_URL = "https://www.facebook.com/NWUofficial"
NWU_FINANCE_URL = "https://www.facebook.com/NWUFinance"


def format_course(c: dict) -> str:
    return f"{c.get('course_code', '').strip()} — {c.get('course_title', '').strip()}"


def _is_diagnostic_review_course(course: dict) -> bool:
    code = (course.get("course_code") or course.get("course_id") or "").strip().upper()
    return code in {"IENG", "IMAT"}


def _format_head_row(r: dict) -> str:
    name = r.get("department_name", "")
    head = r.get("department_head", "")
    flag = (r.get("dean_flag") or "N").upper()
    if flag == "Y":
        return f"Dean (CAS): {head}"
    return f"{name}: {head}"


def _is_dept_headish(text: str) -> bool:
    t = (text or "").lower()
    dept_like = any(x in t for x in ["department", "dept", "dept.", "deprt", "deprtm", "detp"])
    head_like = any(x in t for x in ["head", "haed", "hed", "chair", "dean"])
    fuzzy_dept = fuzz.partial_ratio(t, "department") >= 80 or fuzz.partial_ratio(t, "dept") >= 80
    fuzzy_head = fuzz.partial_ratio(t, "head") >= 80
    return (dept_like or fuzzy_dept) and (head_like or fuzzy_head)


def _looks_like_greeting(text: str) -> bool:
    t = (text or "").strip().lower()
    t = re.sub(r"[!.\s]+$", "", t)
    return t in GREETINGS


def _clean_as_name(s: str) -> str:
    t = re.sub(r"[^A-Za-z\-\s']", " ", s or "").strip()
    t = re.sub(r"\s+", " ", t)
    return t.title()


def _extract_name(text: str) -> Optional[str]:
    t = (text or "").strip()
    if _looks_like_greeting(t) or t.lower() in NON_NAMES:
        return None
    p = re.compile(r"^(?:my\s+name\s+is|i\s*am|i'm|im|call\s+me|this\s+is)\s+([A-Za-z][A-Za-z'\-\s]{0,40})[.!?]*$", re.IGNORECASE)
    m = p.match(t)
    if m:
        return _clean_as_name(m.group(1))
    blacklist = {"units", "prereq", "prerequisite", "department", "dept", "head", "program", "year", "semester", "course", "dean"}
    if "?" not in t and CODE_RE.search(t) is None:
        tokens = re.findall(r"[A-Za-z][A-Za-z'\-]*", t)
        if 1 <= len(tokens) <= 3:
            cand = " ".join(tokens)
            low = cand.lower()
            if low not in GREETINGS and all(w not in blacklist for w in low.split()):
                return _clean_as_name(cand)
    return None


def _looks_like_question(text: str) -> bool:
    t = (text or "").strip().lower()
    if "?" in t: return True
    if any(t.startswith(w) for w in ["who", "what", "how", "where", "when"]): return True
    if any(k in t for k in ["units", "prereq", "prerequisite", "department", "dept", "head", "program", "year", "semester", "course", "dean"]): return True
    if CODE_RE.search(t): return True
    return False


def _looks_like_payment(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in ["tuition", "payment", "pay", "downpayment", "down payment", "cashier", "finance", "fees", "balance"])


def _detect_college(text: str) -> Optional[str]:
    t = (text or "").upper()
    for code, aliases in COLLEGE_ALIASES.items():
        for a in aliases:
            if a and a.upper() in t:
                return code
    return None


def _refer_university(channel_hint: Optional[str] = None) -> str:
    if channel_hint == "finance":
        return "For payment-related inquiries, please contact the University Finance office through its official channel."
    return "For colleges outside CAS, please reach out through the University's official channel."


def format_course_name_then_code(c: dict) -> str:
    title = (c.get("course_title") or "").strip()
    code = (c.get("course_code") or c.get("course_id") or "").strip()
    upper_code = code.upper()

    if upper_code == "NSTP 2":
        clean_title = "Civic Welfare Training 2"
        if code:
            return f"{clean_title} ({code})"
        return clean_title

    if title and code:
        return f"{title} ({code})"
    if title:
        return title
    if code:
        return code
    return "this course"


def _term_label(term: int) -> str:
    labels = {
        1: "First Trimester",
        2: "Second Trimester",
        3: "Third Trimester",
    }
    return labels.get(term, f"Term {term}")


def _is_generic_pathfit_query(user_text: str) -> bool:
    if not user_text:
        return False
    t = re.sub(r"[^a-z0-9\s]", " ", user_text.lower())
    tokens = [tok for tok in t.split() if tok]
    if "pathfit" not in tokens:
        return False
    if any(tok in {"1", "2", "3", "4", "1st", "2nd", "3rd", "4th"} for tok in tokens):
        return False
    allowed = {
        "what", "whats", "what's", "is", "are", "the", "a", "an", "of", "for",
        "subject", "course", "subject?", "course?", "prereq", "prereqs",
        "prerequisite", "prerequisites", "requirement", "requirements",
        "in", "about", "this", "that", "does", "require"
    }
    others = [tok for tok in tokens if tok not in allowed and tok != "pathfit"]
    return len(others) == 0


def _is_generic_nstp_query(user_text: str) -> bool:
    if not user_text:
        return False
    t = re.sub(r"[^a-z0-9\s]", " ", user_text.lower())
    tokens = [tok for tok in t.split() if tok]
    if "nstp" not in tokens:
        return False
    if any(tok in {"1", "2", "1st", "2nd"} for tok in tokens):
        return False
    allowed = {
        "what", "whats", "what's", "is", "are", "the", "a", "an", "of", "for",
        "subject", "course", "subject?", "course?", "prereq", "prereqs",
        "prerequisite", "prerequisites", "requirement", "requirements",
        "in", "about", "this", "that", "does", "require"
    }
    others = [tok for tok in tokens if tok not in allowed and tok != "nstp"]
    return len(others) == 0


def _build_nstp_overview() -> str:
    courses = data["courses"]
    prereqs = data["prereqs"]
    nstp1 = find_course_by_code(courses, "NSTP 1")
    nstp2 = find_course_by_code(courses, "NSTP 2")

    lines: list[str] = [
        "The National Service Training Program (NSTP) has two parts:"
    ]

    if nstp1:
        lines.append(f"• {format_course_name_then_code(nstp1)} – no listed prerequisites.")
    else:
        lines.append("• NSTP 1 – no listed prerequisites.")

    if nstp2:
        needed2 = get_prerequisites(prereqs, courses, nstp2.get("course_id"))
        if needed2:
            prereq_list = ", ".join(
                format_course_name_then_code(p) for p in needed2
            )
            lines.append(
                f"• {format_course_name_then_code(nstp2)} – prerequisite: {prereq_list}."
            )
        else:
            lines.append(
                f"• {format_course_name_then_code(nstp2)} – no listed prerequisites."
            )
    else:
        lines.append("• NSTP 2 – prerequisite: NSTP 1.")
    
    lines.append("")
    return "\n".join(lines)


def _is_generic_thesis_query(user_text: str) -> bool:
    if not user_text:
        return False
    t = re.sub(r"[^a-z\s]", " ", user_text.lower())
    tokens = [tok for tok in t.split() if tok]
    if "thesis" not in tokens:
        return False
    allowed = {
        "what", "whats", "what's", "is", "are", "the", "a", "an", "of", "for",
        "subject", "course", "subject?", "course?", "prereq", "prereqs",
        "prerequisite", "prerequisites", "requirement", "requirements",
        "in", "about", "this", "that", "does", "require"
    }
    others = [tok for tok in tokens if tok not in allowed and tok != "thesis"]
    return len(others) == 0


def _build_pathfit_overview() -> str:
    courses = data["courses"]
    prereqs = data["prereqs"]
    pathfit_courses = []
    for c in courses:
        code = (c.get("course_code") or c.get("course_id") or "").strip().upper()
        if code.startswith("PATHFIT"):
            pathfit_courses.append(c)

    if not pathfit_courses:
        return "I couldn't find any PATHFIT courses listed right now."

    def _pathfit_key(c: dict) -> int:
        code = (c.get("course_code") or c.get("course_id") or "").strip().upper()
        parts = code.split()
        for p in parts:
            if p.isdigit():
                return int(p)
        return 0

    pathfit_courses = sorted(pathfit_courses, key=_pathfit_key)
    lines: list[str] = ["The PATHFIT (Physical Fitness) subjects are taken in sequence:"]

    for c in pathfit_courses:
        name_code = format_course_name_then_code(c)
        needed = get_prerequisites(prereqs, courses, c.get("course_id"))
        if not needed:
            lines.append(f"• {name_code} – no listed prerequisites.")
        elif len(needed) == 1:
            lines.append(f"• {name_code} – prerequisite: {format_course_name_then_code(needed[0])}.")
        else:
            prereq_list = ", ".join(format_course_name_then_code(p) for p in needed)
            lines.append(f"• {name_code} – prerequisites: {prereq_list}.")
    

    return "\n".join(lines)


def _build_thesis_overview() -> str:
    courses = data["courses"]
    prereqs = data["prereqs"]
    programs = data["programs"]
    plan = data["plan"]

    thesis_courses_by_code: dict[str, dict] = {}
    for c in courses:
        title = (c.get("course_title") or "").strip().lower()
        code = (c.get("course_code") or c.get("course_id") or "").strip().upper()
        if not code:
            continue
        if "thesis" in title or "thesis/special project" in title or "research in psychology" in title:
            thesis_courses_by_code[code] = c

    if not thesis_courses_by_code:
        return "I couldn't find any thesis or research courses listed in the data right now."

    thesis_codes = set(thesis_courses_by_code.keys())
    course_programs: dict[str, set[str]] = {}
    for entry in plan:
        cid = (entry.get("course_id") or "").strip().upper()
        if cid in thesis_codes:
            pid = entry.get("program_id")
            if not pid: continue
            course_programs.setdefault(cid, set()).add(pid)

    lines: list[str] = [
        "Here are the thesis and research courses across CAS, "
        "grouped by program, with their prerequisites:"
    ]

    def _sorted_thesis_for_program(pid: str) -> list[dict]:
        rows = []
        for entry in plan:
            if entry.get("program_id") != pid: continue
            cid = (entry.get("course_id") or "").strip().upper()
            if cid not in thesis_codes: continue
            rows.append((int(entry.get("year_level") or 0), int(entry.get("term") or 0), cid))
        seen = set()
        ordered: list[dict] = []
        for year, term, cid in sorted(rows):
            if cid in seen: continue
            seen.add(cid)
            course = thesis_courses_by_code.get(cid)
            if course: ordered.append(course)
        return ordered

    any_output = False
    for prog in programs:
        pid = prog.get("program_id")
        pname = prog.get("program_name") or ""
        thesis_for_prog = _sorted_thesis_for_program(pid)
        if not thesis_for_prog: continue
        any_output = True
        lines.append("")
        lines.append(f"For {pname}, the thesis courses are:")
        for c in thesis_for_prog:
            name_code = format_course_name_then_code(c)
            needed = get_prerequisites(prereqs, courses, c.get("course_id"))
            if not needed:
                lines.append(f"• {name_code} – no listed prerequisites.")
            elif len(needed) == 1:
                lines.append(f"• {name_code} – prerequisite: {format_course_name_then_code(needed[0])}.")
            else:
                prereq_list = ", ".join(format_course_name_then_code(p) for p in needed)
                lines.append(f"• {name_code} – prerequisites: {prereq_list}.")

    leftover = [c for code, c in thesis_courses_by_code.items() if code not in course_programs]
    if leftover:
        lines.append("")
        lines.append("These thesis courses are listed but not mapped to a specific CAS program in the current plan:")
        for c in leftover:
            name_code = format_course_name_then_code(c)
            needed = get_prerequisites(prereqs, courses, c.get("course_id"))
            if not needed:
                lines.append(f"• {name_code} – no listed prerequisites.")
            elif len(needed) == 1:
                lines.append(f"• {name_code} – prerequisite: {format_course_name_then_code(needed[0])}.")
            else:
                prereq_list = ", ".join(format_course_name_then_code(p) for p in needed)
                lines.append(f"• {name_code} – prerequisites: {prereq_list}.")

    if not any_output:
        return "I see thesis courses in the data, but they aren't currently mapped to any CAS program in my records."
    
    lines.append("")
    return "\n".join(lines)


def handle_prereq(user_text: str, ents: dict, course_obj: Optional[dict] = None) -> str:
    courses = data["courses"]
    prereqs = data["prereqs"]

    if _is_generic_thesis_query(user_text): return _build_thesis_overview()
    if _is_generic_nstp_query(user_text): return _build_nstp_overview()
    if _is_generic_pathfit_query(user_text): return _build_pathfit_overview()

    course = course_obj
    
    if not course:
        if ents.get("course_code"):
            course, _ = find_course_any(data, ents["course_code"])
            if not course:
                 return f"I see you mentioned '{ents['course_code']}', but I can't find a course with that code. Could you check the spelling?"

        if not course and ents.get("course_title"):
            fb = fuzzy_best_course_title(courses, ents["course_title"], score_cutoff=70)
            if fb: course = fb[2]

        if not course and not ents.get("course_code"):
            course, _ = find_course_any(data, user_text)

    if not course:
        return (
            "I'm not totally sure which course you mean yet. "
            "Could you give me the full course title or code? For example:\n"
            "• Prerequisite of Microbiology (BIO 103 L/L)\n"
            "• What are the prereqs for Purposive Communication (PCOM)?"
        )

    course_code = (course.get("course_code") or course.get("course_id") or "").strip().upper()

    if course_code == "IENG":
        return (
            "English Review (IENG) is a diagnostic-placement subject based on your "
            "English diagnostic test results. Please check with the Guidance Office "
            "via their Facebook page https://www.facebook.com/NWUGuidance to confirm if you need it."
        )

    if course_code == "IMAT":
        return (
            "Math Review (IMAT) is a diagnostic-placement subject based on your "
            "Math diagnostic test results. Please check with the Guidance Office "
            "via their Facebook page https://www.facebook.com/NWUGuidance to confirm if you need it."
        )

    needed = get_prerequisites(prereqs, courses, course.get("course_id"))
    heading = format_course_name_then_code(course)
    
    is_yes_no = any(user_text.lower().strip().startswith(x) for x in ["does", "do", "is", "are", "can", "could"])

    lines = []
    if not needed:
        prefix = "No, " if is_yes_no else ""
        lines.append(f"{prefix}{heading} has no listed prerequisites.")
    else:
        if is_yes_no:
            lines.append(f"Yes, the prerequisite for {heading} is:" if len(needed) == 1 else f"Yes, the prerequisites for {heading} are:")
        else:
            lines.append(f"Prerequisite of {heading}:" if len(needed) == 1 else f"Prerequisites of {heading}:")

    has_diagnostic = False
    diag_codes = set()

    for c in needed:
        c_code = (c.get("course_code") or c.get("course_id") or "").strip().upper()
        if c_code == "IENG":
            has_diagnostic = True
            diag_codes.add("IENG")
            lines.append("• English Review (IENG)")
        elif c_code == "IMAT":
            has_diagnostic = True
            diag_codes.add("IMAT")
            lines.append("• Math Review (IMAT)")
        else:
            lines.append(f"• {format_course_name_then_code(c)}")

    if has_diagnostic:
        lines.append("")
        if diag_codes == {"IENG"}:
            lines.append("Note: English Review (IENG) depends on your English diagnostic test results.")
        elif diag_codes == {"IMAT"}:
            lines.append("Note: Math Review (IMAT) depends on your Math diagnostic test results.")
        else:
            lines.append("Note: English Review (IENG) and Math Review (IMAT) depend on your diagnostic test results.")
        lines.append("You can check with the Guidance Office via their Facebook page https://www.facebook.com/NWUGuidance.")
    
    lines.append(f"")
    return "\n".join(lines)


def _format_units(u_val) -> str:
    try:
        val = int(u_val)
        return f"{val} unit" if val == 1 else f"{val} units"
    except Exception:
        return f"{u_val} units"


def handle_units(user_text: str, ents: dict, course_obj: Optional[dict] = None) -> str:
    programs = data["programs"]
    plan = data["plan"]
    courses = data["courses"]

    tlow = (user_text or "").lower()
    t_clean = re.sub(r"[^\w\s]", "", tlow)
    tokens = t_clean.split()
    
    stops = {
        "units", "unit", "credit", "load", "what", "is", "are", "the", 
        "how", "many", "of", "for", "in", "does", "do", "a", "an", 
        "subject", "course", "about"
    }
    
    meaningful = [t for t in tokens if t not in stops]
    course_candidate = course_obj
    
    if not course_candidate and meaningful:
        course_candidate, _ = find_course_any(data, user_text)

    if course_candidate:
        has_number = bool(re.search(r"\d", user_text))
        if has_number or not ents.get("program"):
             u_str = _format_units(course_candidate.get('units', 'NA'))
             return f"{format_course(course_candidate)} — {u_str}. "

    prog_row = None
    if ents.get("program"):
        res = fuzzy_best_program(programs, ents["program"], score_cutoff=60)
        if res: _, _, prog_row = res
    
    if not prog_row:
        res = fuzzy_best_program(programs, user_text, score_cutoff=80)
        if res: _, _, prog_row = res

    if prog_row:
        pid = prog_row["program_id"]
        pname = prog_row["program_name"]
        pname_lower = (pname or "").lower()

        year_labels = {1: "First year", 2: "Second year", 3: "Third year", 4: "Fourth year"}
        term_labels = {1: "First trimester", 2: "Second trimester", 3: "Third trimester"}

        year = ents.get("year_num")
        if not year:
            has_entries = any((entry.get("program_id") == pid) for entry in plan)
            if not has_entries and "english language" in pname_lower:
                return (
                    "The detailed unit loading for BA in English Language isn’t loaded in my system yet.\n\n"
                    "For accurate info, please check directly with the Department of Language and Literature. "
                    "You can start with the department head, DR. JV."
                )

            year_values: list[int] = []
            for entry in plan:
                if entry.get("program_id") != pid: continue
                yl = entry.get("year_level")
                try:
                    y_int = int(str(yl))
                except Exception: continue
                if y_int not in year_values: year_values.append(y_int)
            
            year_values = sorted(year_values)
            if not year_values:
                return f"I couldn't find unit data for {pname} in the curriculum plan."

            lines: list[str] = [f"Total units for {pname} by year (excluding diagnostic review subjects):"]
            overall_total = 0
            any_diag_across = False

            for y in year_values:
                total_y, by_sem_y, diag_by_sem_y = units_by_program_year_with_exclusions(plan, courses, pid, y)
                if not by_sem_y: continue
                any_diag_across = any_diag_across or any(diag_by_sem_y.values())
                y_label = year_labels.get(y, f"Year {y}")
                lines.append("")
                lines.append(f"{y_label}:")
                for sem_key, units in sorted(by_sem_y.items(), key=lambda kv: int(kv[0])):
                    sem = int(sem_key)
                    sem_label = term_labels.get(sem, f"Trimester {sem}")
                    lines.append(f"• {sem_label}: {units} units")
                lines.append(f"Overall for {y_label}: {total_y} units")
                overall_total += total_y

            if overall_total == 0:
                return f"I couldn't find unit data for {pname} in the curriculum plan."

            lines.append("")
            overall_line = "Overall total for the full program"
            if any_diag_across: overall_line += " (excluding IMAT/IENG)"
            overall_line += f": {overall_total} units"
            lines.append(overall_line)

            if any_diag_across:
                lines.append("Note: Diagnostic review subjects like IMAT (Math Review) and IENG (English Review) are not included here.")
            
            lines.append(f"")
            return "\n".join(lines)

        total_units, by_sem, diagnostic_by_sem = units_by_program_year_with_exclusions(plan, courses, pid, year)
        year_label = year_labels.get(year, f"Year {year}")

        if not by_sem and "english language" in pname_lower:
            return (
                "The detailed unit loading for BA in English Language isn’t loaded yet.\n\n"
                "Please check directly with the Department of Language and Literature."
            )

        if not by_sem:
            return f"I couldn't find unit data for {year_label} {pname} in the curriculum plan."

        term = ents.get("term_num")
        lines: list[str] = []

        if term:
            term_key = str(term)
            units_for_term = by_sem.get(term_key)
            sem_label = term_labels.get(term, f"Trimester {term}")
            if not units_for_term:
                return f"I couldn't find unit data for {year_label} {pname}, {sem_label}."
            has_diag = bool(diagnostic_by_sem.get(term_key))
            header = f"Units for {year_label} {pname}, {sem_label}" + (" (excluding diagnostic review subjects):" if has_diag else ":")
            lines.append(header)
            lines.append(f"• {sem_label}: {units_for_term} units")
            if has_diag:
                lines.append("Note: Diagnostic review subjects like IMAT (Math Review) and IENG (English Review) are not included.")
            
            lines.append(f"")
            return "\n".join(lines)

        any_diag = any(diagnostic_by_sem.values())
        header = f"Total units for {year_label} {pname}" + (" (excluding diagnostic review subjects):" if any_diag else ":")
        lines.append(header)
        for sem_key, units in sorted(by_sem.items(), key=lambda kv: int(kv[0])):
            sem = int(sem_key)
            sem_label = term_labels.get(sem, f"Trimester {sem}")
            lines.append(f"• {sem_label}: {units} units")
        overall_line = "Overall total" + (" (excluding IMAT/IENG)" if any_diag else "") + f": {total_units} units"
        lines.append(f"\n{overall_line}")
        if any_diag:
            lines.append("Note: Diagnostic review subjects are not included.")
        
        lines.append(f"")
        return "\n".join(lines)

    if not course_candidate and meaningful:
        course_candidate, _ = find_course_any(data, user_text)
        if course_candidate:
            u_str = _format_units(course_candidate.get('units', 'NA'))
            return f"{format_course(course_candidate)} — {u_str}. "

    return (
        "I'd be happy to check the units for you! To give you the right number, "
        "could you mention the specific program or course?"
    )


def handle_curriculum(user_text: str, ents: dict) -> str:
    programs = data["programs"]
    plan = data["plan"]
    courses = data["courses"]

    if ents.get("program") and not bool(CODE_RE.search(user_text)):
         pass
    else:
        tlow = (user_text or "").lower()
        check_text = tlow.replace("curriculum", "").replace(" in ", " ").strip()
        potential_course, _ = find_course_any(data, check_text)
        
        if potential_course and not any(x in tlow for x in ["list", "all", "show me", "what are"]):
            c_title = potential_course.get("course_title")
            c_code = potential_course.get("course_code") or potential_course.get("course_id")
            
            found_programs = set()
            for entry in plan:
                if entry.get("course_id") == potential_course.get("course_id"):
                    pid = entry.get("program_id")
                    p_obj = next((p for p in programs if p["program_id"] == pid), None)
                    if p_obj:
                        found_programs.add(p_obj.get("program_name"))
            
            if found_programs:
                prog_list = "\n".join([f"• {p}" for p in sorted(found_programs)])
                return (
                    f"Yes, **{c_title} ({c_code})** is in the curriculum.\n\n"
                    f"It is part of the following programs:\n{prog_list}"
                )
            else:
                return (
                    f"I found the course **{c_title} ({c_code})**, but it doesn't appear "
                    "to be mapped to any specific program in the current curriculum plan."
                )

    if any(x in (user_text or "").lower() for x in ["bael", "abel", "ab english language", "ba english language", "ab english", "ba english", "english language"]):
        return (
            "The detailed curriculum plan for BA in English Language isn’t loaded in my system yet.\n\n"
            "For now, it’s best to check directly with the Department of Language and Literature."
        )

    prog_row = None
    if ents.get("program"):
        res = fuzzy_best_program(programs, ents["program"], score_cutoff=60)
        if res: _, _, prog_row = res
    if not prog_row:
        res = fuzzy_best_program(programs, user_text, score_cutoff=60)
        if res: _, _, prog_row = res

    if not prog_row:
        return (
            "I’m not sure which program you’re asking about yet.\n\n"
            "Some examples I can help with are:\n"
            "• BS Computer Science\n"
            "• BS Biology\n"
            "• BS Psychology\n"
            "• BA Communication\n"
            "• BA Political Science\n\n"
            "Which program are you interested in?"
        )

    pid = prog_row["program_id"]
    pname = prog_row["program_name"]
    has_entries = any((entry.get("program_id") == pid) for entry in plan)
    if not has_entries:
        return f"The detailed curriculum plan for {pname} isn’t available in my system yet."

    year = ents.get("year_num")
    term = ents.get("term_num")

    if not year:
        return (
            f"I can list all the subjects for {pname}, but that would be a very long answer.\n\n"
            f"To keep it readable, could you tell me which year level you’re looking at? For example:\n"
            f"• 1st year {pname} subjects?\n"
            f"• 2nd year {pname} courses?"
        )

    year_labels = {1: "First year", 2: "Second year", 3: "Third year", 4: "Fourth year"}
    year_label = year_labels.get(year, f"Year {year}")
    
    year_exists = any((entry.get("program_id") == pid and int(entry.get("year_level", 0)) == year) for entry in plan)
    if not year_exists:
         return f"I couldn’t find any curriculum entries for {year_label} (Year {year}) in {pname}. The current data might only cover up to Year 3."

    if term:
        term_courses = courses_for_plan(plan, courses, pid, year, term)
        if not term_courses:
            return f"I couldn’t find any curriculum entries for {year_label} {pname}, {_term_label(term)}."
        
        lines: list[str] = [f"Courses for {year_label} {pname}, {_term_label(term)}:"]
        diag_codes: set[str] = set()
        for c in term_courses:
            code = (c.get("course_code") or c.get("course_id") or "").strip().upper()
            if code in {"IMAT", "IENG"}: diag_codes.add(code)
            lines.append(f"• {format_course_name_then_code(c)}")
        if diag_codes:
            lines.append("\nNote: English Review (IENG) and Math Review (IMAT) depend on your diagnostic test results.")
        
        lines.append(f"")
        return "\n".join(lines)

    lines = [f"Courses for {year_label} {pname}:"]
    any_term = False
    diag_codes: set[str] = set()
    for t in [1, 2, 3]:
        term_courses = courses_for_plan(plan, courses, pid, year, t)
        if not term_courses: continue
        any_term = True
        lines.append("")
        lines.append(_term_label(t) + ":")
        for c in term_courses:
            code = (c.get("course_code") or c.get("course_id") or "").strip().upper()
            if code in {"IMAT", "IENG"}: diag_codes.add(code)
            lines.append(f"• {format_course_name_then_code(c)}")
    if not any_term:
        return f"I couldn’t find any curriculum entries for {year_label} {pname} in the current data. It might not be loaded yet."
    if diag_codes:
        lines.append("\nNote: English Review (IENG) and Math Review (IMAT) depend on your diagnostic test results.")
    
    lines.append(f"")
    return "\n".join(lines)


def handle_dept_heads_list_or_clarify(user_text: str, ents: dict) -> str:
    tlow = (user_text or "").lower().strip()
    college = _detect_college(user_text)
    if college and college != "CAS":
        return _refer_university()
    if "all" in tlow or "cas" in tlow or "entire" in tlow or "everyone" in tlow or college == "CAS":
        rows = list_department_heads(data["departments"])
        if not rows: return "No department heads found."
        lines = ["Department heads (including Dean):"]
        for r in rows:
            lines.append(f"- {_format_head_row(r)}")
        lines.append("")
        return "\n".join(lines)
    st.session_state.awaiting_college_scope = True
    st.session_state.pending_intent = "dept_heads_college"
    return "Do you mean CAS department heads, or heads from another college?"


def handle_dept_head_one(user_text: str, ents: dict) -> str:
    tlow = (user_text or "").lower()
    college = _detect_college(user_text)
    if "dean" in tlow:
        if college == "CAS" or (college is None):
            dean_row = get_cas_dean(data["departments"])
            if dean_row and dean_row.get("department_head"):
                return (
                    f"The current CAS Dean is {dean_row.get('department_head')}.\n\n"
                    "For information about other colleges, please check with their respective offices. "
                )
            return "No dean is recorded."
        if college and college != "CAS":
            return _refer_university()
        
        st.session_state.awaiting_college_scope = True
        st.session_state.pending_intent = "ask_dean_college"
        return "Which college dean are you referring to? CAS, or another college?"

    dep_name = ents.get("department") or user_text
    drow = department_lookup(data["departments"], dep_name)
    if not drow:
        if _is_dept_headish(user_text):
            st.session_state.awaiting_dept_scope = True
            st.session_state.pending_intent = "dept_heads_list"
            return "Which department do you mean (e.g., 'Computer Science')? Or say 'all' for the full CAS list."
        return "Sorry, that department wasn't recognized. Try the full name (e.g., Computer Science)."
    head = drow.get("department_head")
    role = get_dept_role_label(drow, user_text)
    if not head:
        return f"No {role.lower()} is recorded for {drow.get('department_name')}."
    return f"The {role.lower()} is {head}. "


def resolve_pending(user_text: str) -> Optional[str]:
    tlow = (user_text or "").lower().strip()
    if st.session_state.pending_intent == "dept_heads_list":
        st.session_state.awaiting_dept_scope = False
        st.session_state.pending_intent = None
        if "all" in tlow or "cas" in tlow or "everything" in tlow or "everyone" in tlow:
            rows = list_department_heads(data["departments"])
            if not rows: return "No department heads found."
            lines = ["Department heads (including Dean):"]
            for r in rows:
                lines.append(f"- {_format_head_row(r)}")
            lines.append("")
            return "\n".join(lines)
        head = get_department_head_by_name(data["departments"], user_text)
        if head:
            drow = department_lookup(data["departments"], user_text)
            role = get_dept_role_label(drow, user_text)
            return f"The {role.lower()} is {head}."
        return "Got it—please name the department (e.g., 'Computer Science') or say 'all'."
    if st.session_state.pending_intent in {"ask_dean_college","dept_heads_college"}:
        st.session_state.awaiting_college_scope = False
        intent = st.session_state.pending_intent
        st.session_state.pending_intent = None
        college = _detect_college(user_text)
        if college == "CAS":
            if intent == "ask_dean_college":
                dean_row = get_cas_dean(data["departments"])
                if dean_row and dean_row.get("department_head"):
                    return f"The dean is {dean_row.get('department_head')}."
                return "No dean is recorded."
            if intent == "dept_heads_college":
                rows = list_department_heads(data["departments"])
                if not rows: return "No department heads found."
                lines = ["Department heads (including Dean):"]
                for r in rows:
                    lines.append(f"- {_format_head_row(r)}")
                lines.append("")
                return "\n".join(lines)
        if college and college != "CAS":
            return _refer_university()
        return "Thanks. Please specify a college."
    return None


def route(user_text: str) -> str:
    if st.session_state.awaiting_dept_scope or st.session_state.awaiting_college_scope:
        resolved = resolve_pending(user_text)
        if resolved: return resolved

    if _looks_like_payment(user_text):
        return _refer_university(channel_hint="finance")
    
    tlow = (user_text or "").lower().strip().rstrip("?!.")
    ents = extract_entities(user_text)
    intent = detect_intent(user_text)

    has_units = bool(re.search(r"\b(unit|units|credit|load)\b", user_text.lower()))
    has_prereq = bool(re.search(r"\b(prereq|prerequisites?|requirements?)\b", user_text.lower()))
    
    c, match_type = find_course_any(data, user_text)
    
    if c and match_type in ("code", "exact_title", "exact_title_subset", "alias"):
        if has_units: return handle_units(user_text, ents, course_obj=c)
        if has_prereq: return handle_prereq(user_text, ents, course_obj=c)
        return (
            f"I found **{format_course(c)}**.\n\n"
            "What would you like to know about it? I can check its **units**, **prerequisites**, "
            "or verify if it's in your curriculum. "
        )
    
    if c and match_type == "fuzzy_code":
         return (
            f"I found a possible match: **{format_course(c)}**.\n\n"
            "Is this the course you're looking for? "
            "If yes, I can provide its **units** or **prerequisites**."
        )
         
    cleaned_q = _clean_course_query(user_text)
    words = cleaned_q.split()
    
    is_code = bool(CODE_RE.search(user_text)) or (len(words) == 1 and any(char.isdigit() for char in words[0]))

    if len(words) <= 1 and not is_code and not any(w in tlow for w in ["who", "what", "where", "when", "why", "how", "list", "show"]):
         if cleaned_q in GREETINGS:
             return "Hello! How can I help you today?"
         return "I'm not sure what you're asking about. Could you be more specific? (e.g., 'BS Psychology subjects', 'Intro to Psychology units')"

    if "curriculum" in tlow:
        return handle_curriculum(user_text, ents)

    if tlow in {"department heads", "dept heads", "dept. heads", "different department heads"}:
        return handle_dept_heads_list_or_clarify(user_text, ents)
    if intent == "courseinfo" and _is_dept_headish(user_text):
        if ents.get("department"): return handle_dept_head_one(user_text, ents)
        return handle_dept_heads_list_or_clarify(user_text, ents)
    if intent == "dept_heads_list": return handle_dept_heads_list_or_clarify(user_text, ents)
    if intent == "dept_head_one": return handle_dept_head_one(user_text, ents)

    plain = tlow
    nonnames = {"yes", "yeah", "yup", "ok", "okay", "sure", "thanks", "thank you"}
    if plain in nonnames:
        return "Got it. If you have a specific question about a course or program, feel free to ask!"

    if not ents.get("program") and intent == "units":
         prog_match = fuzzy_best_program(data["programs"], user_text, score_cutoff=85)
         if prog_match and not bool(CODE_RE.search(user_text)):
             _, _, p_row = prog_match
             ents["program"] = p_row["program_name"]

    if ents.get("program") and not bool(CODE_RE.search(user_text)):
        if intent == "units": return handle_units(user_text, ents)
        if intent == "curriculum" or intent == "courseinfo": 
            if intent == "curriculum": return handle_curriculum(user_text, ents)
            if intent == "courseinfo" and (ents.get("year_num") or ents.get("term_num")): 
                return handle_curriculum(user_text, ents)

    raw_hits = fuzzy_top_course_titles(data["courses"], user_text, limit=30, score_cutoff=65)
    
    hits = []
    seen_codes = set()
    for name, score, match_c in raw_hits:
        code = match_c.get("course_code")
        if code not in seen_codes:
            hits.append((name, score, match_c))
            seen_codes.add(code)

    if hits:
        def sort_key(item):
            name = item[0].lower()
            is_intro = 0 if "introduction" in name or "general" in name or "fundamentals" in name else 1
            return (item[1] * -1, is_intro, len(item[0]))

        hits.sort(key=sort_key)
        
        top_name, top_score, top_course = hits[0]
        
        is_perfect = (top_score >= 97) or (top_name.lower().strip() == user_text.lower().strip().replace("?", "").replace("subject", "").replace("prereq", "").strip())
        
        is_ambiguous = False
        if len(hits) > 1:
            second_score = hits[1][1]
            if top_score >= 85 and second_score >= 85:
                if (top_score - second_score) < 15:
                    is_ambiguous = True
                if len(user_text.split()) == 1 and top_score > 90 and second_score > 90:
                    is_ambiguous = True

        if is_ambiguous:
            lines = ["I found a few courses that look similar. Which one did you mean?"]
            for i in range(min(len(hits), 6)):
                match_c = hits[i][2]
                lines.append(f"• **{format_course(match_c)}**")
            return "\n".join(lines)

        if top_score >= 92 or is_perfect:
             c = top_course
             if has_units: return handle_units(user_text, ents, course_obj=c)
             if has_prereq: return handle_prereq(user_text, ents, course_obj=c)
             return (
                f"I found **{format_course(c)}**.\n\n"
                "What would you like to know about it? I can check its **units**, **prerequisites**, "
                "or verify if it's in your curriculum. "
            )

        if top_score >= 65:
            lines = ["I found a few courses that look similar. Which one did you mean?"]
            for i in range(min(len(hits), 6)):
                match_c = hits[i][2]
                lines.append(f"• **{format_course(match_c)}**")
            return "\n".join(lines)

    if intent == "units": return handle_units(user_text, ents)
    if intent == "prerequisites": return handle_prereq(user_text, ents)

    if ents.get("program"):
         return "I'm not totally sure which part of that program you need. Could you specify subjects or prerequisites?"

    return (
        "I'm not totally sure what you need yet based on that message.\n\n"
        "Could you rephrase it with more detail? For example:\n"
        "• BS Biology subjects?\n"
        "• Prerequisite of Purposive Communication?"
    )


placeholder = "Say hello, share your name, or ask about prerequisites, unit loads, or department leadership…"
prompt = st.chat_input(placeholder)
if prompt:
    if st.session_state.user_name is None:
        st.session_state.chat.append({"sender": "You", "message": prompt})
        render_message("You", prompt)
        if _looks_like_greeting(prompt):
            reply = "Hi! What name should I use to address you?"
            st.session_state.chat.append({"sender": "CASmate", "message": reply})
            render_message("CASmate", reply)
        else:
            maybe_name = _extract_name(prompt)
            if maybe_name:
                st.session_state.user_name = maybe_name
                opening = (
                    f"Nice to meet you, {maybe_name}! "
                    "Here's how I can help: outline course prerequisites, summarize unit loads by year and program, "
                    "and identify department leadership including the CAS Dean. "
                    "If I need more details, I'll ask; and if something's better handled elsewhere, I'll point you to the right office."
                )
                st.session_state.chat.append({"sender": "CASmate", "message": opening})
                render_message("CASmate", opening)
            elif _looks_like_question(prompt):
                reply = route(prompt)
                st.session_state.chat.append({"sender": "CASmate", "message": reply})
                render_message("CASmate", reply)
                nudge = "By the way, how should I address you?"
                st.session_state.chat.append({"sender": "CASmate", "message": nudge})
                render_message("CASmate", nudge)
            else:
                ask = "Thanks! Could you share your preferred name?"
                st.session_state.chat.append({"sender": "CASmate", "message": ask})
                render_message("CASmate", ask)
    else:
        st.session_state.chat.append({"sender": "You", "message": prompt})
        render_message("You", prompt)
        reply = route(prompt)
        st.session_state.chat.append({"sender": "CASmate", "message": reply})
        render_message("CASmate", reply)
