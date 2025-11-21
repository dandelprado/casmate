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
    get_prerequisites,
    course_by_alias,
    find_course_any,
    units_by_program_year,
    units_by_program_year_with_exclusions,
    list_department_heads,
    get_department_head_by_name,
    department_lookup,
    get_dept_role_label,
    get_cas_dean,
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

CODE_RE = re.compile(r"\b([A-Za-z]{2,4})-?(\d{2,3})\b")
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
    """
    Return True if the course is one of the diagnostic-based review subjects
    (English Review IENG or Math Review IMAT).
    """
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
    """
    Return 'Course Title (CODE)' or fall back sensibly if title/code are missing.
    Includes a CAS-specific cleanup for NSTP 2 so ROTC is not shown.
    """
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


def _is_generic_pathfit_query(user_text: str) -> bool:
    """
    Return True when the user is asking a very general PATHFIT question like
    'what is the prerequisite of pathfit', without specifying PATHFIT 1/2/3/4.
    """
    if not user_text:
        return False

    t = re.sub(r"[^a-z0-9\s]", " ", user_text.lower())
    tokens = [tok for tok in t.split() if tok]

    if "pathfit" not in tokens:
        return False

    # If they explicitly mention a number (e.g., 'pathfit 2'), treat it as specific.
    if any(tok in {"1", "2", "3", "4", "1st", "2nd", "3rd", "4th"} for tok in tokens):
        return False

    allowed = {
        "what", "whats", "what's",
        "is", "are",
        "the", "a", "an",
        "of", "for",
        "subject", "course", "subject?", "course?",
        "prereq", "prereqs", "prerequisite", "prerequisites",
        "requirement", "requirements",
        "in", "about",
        "this", "that",
    }

    others = [tok for tok in tokens if tok not in allowed and tok != "pathfit"]
    return len(others) == 0


def _is_generic_nstp_query(user_text: str) -> bool:
    """
    Return True when the user is asking a very general NSTP question like
    'what is the prerequisite of nstp', without specifying NSTP 1 or NSTP 2.
    """
    if not user_text:
        return False

    t = re.sub(r"[^a-z0-9\s]", " ", user_text.lower())
    tokens = [tok for tok in t.split() if tok]

    if "nstp" not in tokens:
        return False

    # If they explicitly mention 1 or 2 (e.g., 'nstp 2'), treat it as specific.
    if any(tok in {"1", "2", "1st", "2nd"} for tok in tokens):
        return False

    allowed = {
        "what", "whats", "what's",
        "is", "are",
        "the", "a", "an",
        "of", "for",
        "subject", "course", "subject?", "course?",
        "prereq", "prereqs", "prerequisite", "prerequisites",
        "requirement", "requirements",
        "in", "about",
        "this", "that",
    }

    others = [tok for tok in tokens if tok not in allowed and tok != "nstp"]
    return len(others) == 0


def _build_nstp_overview() -> str:
    """
    Summarize NSTP 1 and NSTP 2, showing that NSTP 2 requires NSTP 1.
    """
    courses = data["courses"]
    prereqs = data["prereqs"]

    nstp1 = find_course_by_code(courses, "NSTP 1")
    nstp2 = find_course_by_code(courses, "NSTP 2")

    lines: list[str] = [
        "The National Service Training Program (NSTP) at NWU has two components:"
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

    return "\n".join(lines)

def _is_generic_thesis_query(user_text: str) -> bool:
    """
    Return True when the user is asking a very general 'thesis' question,
    like 'what is the prerequisite of thesis', without specifying program
    or a particular thesis course.
    """
    if not user_text:
        return False

    t = re.sub(r"[^a-z\s]", " ", user_text.lower())
    tokens = [tok for tok in t.split() if tok]

    if "thesis" not in tokens:
        return False

    # Words that are allowed in a generic thesis question.
    allowed = {
        "what", "whats", "what's",
        "is", "are",
        "the", "a", "an",
        "of", "for",
        "subject", "course", "subject?", "course?",
        "prereq", "prereqs", "prerequisite", "prerequisites",
        "requirement", "requirements",
        "in", "about",
        "this", "that",
    }

    others = [tok for tok in tokens if tok not in allowed and tok != "thesis"]
    # If they only say things like "what is the prerequisite of thesis",
    # treat it as a generic thesis overview question.
    return len(others) == 0


def _build_pathfit_overview() -> str:
    """
    Summarize PATHFIT 1–4, showing their prerequisites from the CAS data.
    """
    courses = data["courses"]
    prereqs = data["prereqs"]

    # Collect PATHFIT courses by code.
    pathfit_courses = []
    for c in courses:
        code = (c.get("course_code") or c.get("course_id") or "").strip().upper()
        if code.startswith("PATHFIT"):
            pathfit_courses.append(c)

    if not pathfit_courses:
        return (
            "There are no PATHFIT courses listed in the current CAS curriculum data."
        )

    # Sort them by numeric suffix (1–4) if possible.
    def _pathfit_key(c: dict) -> int:
        code = (c.get("course_code") or c.get("course_id") or "").strip().upper()
        parts = code.split()
        for p in parts:
            if p.isdigit():
                return int(p)
        return 0

    pathfit_courses = sorted(pathfit_courses, key=_pathfit_key)

    lines: list[str] = [
        "The PATHFIT (Physical Fitness) subjects are sequential:"
    ]

    for c in pathfit_courses:
        name_code = format_course_name_then_code(c)
        needed = get_prerequisites(prereqs, courses, c.get("course_id"))

        if not needed:
            lines.append(f"• {name_code} – no listed prerequisites.")
        elif len(needed) == 1:
            lines.append(
                f"• {name_code} – prerequisite: "
                f"{format_course_name_then_code(needed[0])}."
            )
        else:
            prereq_list = ", ".join(
                format_course_name_then_code(p) for p in needed
            )
            lines.append(
                f"• {name_code} – prerequisites: {prereq_list}."
            )

    return "\n".join(lines)


def _build_thesis_overview() -> str:
    """
    Build an overview answer listing all thesis- and thesis-like courses
    across CAS, grouped by program, each with its prerequisites (if any).
    """
    courses = data["courses"]
    prereqs = data["prereqs"]
    programs = data["programs"]
    plan = data["plan"]

    # 1) Collect all thesis / thesis-like courses.
    thesis_courses_by_code: dict[str, dict] = {}
    for c in courses:
        title = (c.get("course_title") or "").strip().lower()
        code = (c.get("course_code") or c.get("course_id") or "").strip().upper()
        if not code:
            continue

        if "thesis" in title:
            thesis_courses_by_code[code] = c
            continue
        if "thesis/special project" in title:
            thesis_courses_by_code[code] = c
            continue
        if "research in psychology" in title:
            thesis_courses_by_code[code] = c
            continue

    if not thesis_courses_by_code:
        return (
            "There are no thesis or thesis-related research courses listed in the "
            "current CAS curriculum data."
        )

    thesis_codes = set(thesis_courses_by_code.keys())

    # 2) Map each thesis course code to the program(s) it appears in using the flattened plan.
    course_programs: dict[str, set[str]] = {}
    for entry in plan:
        cid = (entry.get("course_id") or "").strip().upper()
        if cid in thesis_codes:
            pid = entry.get("program_id")
            if not pid:
                continue
            course_programs.setdefault(cid, set()).add(pid)

    # 3) Group thesis courses by program, preserving program order as in programs.json.
    lines: list[str] = [
        "Here are thesis and thesis-related research courses across CAS, "
        "grouped by program, with their prerequisites if any:"
    ]

    program_by_id = {p.get("program_id"): p for p in programs}

    # Helper: sort thesis courses within a program by year/term order from the plan.
    def _sorted_thesis_for_program(pid: str) -> list[dict]:
        rows = []
        for entry in plan:
            if entry.get("program_id") != pid:
                continue
            cid = (entry.get("course_id") or "").strip().upper()
            if cid not in thesis_codes:
                continue
            rows.append(
                (
                    int(entry.get("year_level") or 0),
                    int(entry.get("term") or 0),
                    cid,
                )
            )
        seen = set()
        ordered: list[dict] = []
        for year, term, cid in sorted(rows):
            if cid in seen:
                continue
            seen.add(cid)
            course = thesis_courses_by_code.get(cid)
            if course:
                ordered.append(course)
        return ordered

    any_output = False

    for prog in programs:
        pid = prog.get("program_id")
        pname = prog.get("program_name") or ""
        if not pid:
            continue

        thesis_for_prog = _sorted_thesis_for_program(pid)
        if not thesis_for_prog:
            continue

        any_output = True
        lines.append("")
        lines.append(
            f"For {pname}, the thesis and thesis-related research courses are:"
        )

        for c in thesis_for_prog:
            name_code = format_course_name_then_code(c)
            needed = get_prerequisites(prereqs, courses, c.get("course_id"))

            if not needed:
                lines.append(f"• {name_code} – no listed prerequisites.")
            elif len(needed) == 1:
                lines.append(
                    f"• {name_code} – prerequisite: "
                    f"{format_course_name_then_code(needed[0])}."
                )
            else:
                prereq_list = ", ".join(
                    format_course_name_then_code(p) for p in needed
                )
                lines.append(
                    f"• {name_code} – prerequisites: {prereq_list}."
                )

    # 4) Handle any thesis courses that, for some reason, are not tied to a program in the plan.
    leftover = [
        c for code, c in thesis_courses_by_code.items()
        if code not in course_programs
    ]
    if leftover:
        lines.append("")
        lines.append(
            "The following thesis or thesis-related courses are listed but not "
            "mapped to a specific CAS program in the current plan:"
        )
        for c in leftover:
            name_code = format_course_name_then_code(c)
            needed = get_prerequisites(prereqs, courses, c.get("course_id"))
            if not needed:
                lines.append(f"• {name_code} – no listed prerequisites.")
            elif len(needed) == 1:
                lines.append(
                    f"• {name_code} – prerequisite: "
                    f"{format_course_name_then_code(needed[0])}."
                )
            else:
                prereq_list = ", ".join(
                    format_course_name_then_code(p) for p in needed
                )
                lines.append(
                    f"• {name_code} – prerequisites: {prereq_list}."
                )

    if not any_output:
        # Fallback, though this shouldn't normally happen.
        return (
            "There are thesis and thesis-related research courses in the data, "
            "but they are not currently mapped to any CAS program in the curriculum plan."
        )

    return "\n".join(lines)


def handle_prereq(user_text: str, ents: dict) -> str:
    courses = data["courses"]
    prereqs = data["prereqs"]

    # Special cases: generic thesis and generic NSTP questions.
    if _is_generic_thesis_query(user_text):
        return _build_thesis_overview()

    if _is_generic_nstp_query(user_text):
        return _build_nstp_overview()

    if _is_generic_pathfit_query(user_text):
        return _build_pathfit_overview()

    course = None

    # 1) If NLU extracted a course code, use that first.
    if ents.get("course_code"):
        course = find_course_by_code(courses, ents["course_code"])

    # 2) If NLU extracted a course title span, try fuzzy-match on that.
    if not course and ents.get("course_title"):
        fb = fuzzy_best_course_title(courses, ents["course_title"], score_cutoff=70)
        if fb:
            course = fb[2]

    # 3) Fallback: search anywhere in the user text.
    if not course:
        course = find_course_any(data, user_text)

    if not course:
        return (
            "Which course do you mean? "
            "Include the course code (e.g., CS 101) or the full title."
        )

    course_code = (course.get("course_code") or course.get("course_id") or "").strip().upper()

    # Special case: user is asking directly about English Review or Math Review.
    if course_code == "IENG":
        return (
            "English Review (IENG) is a diagnostic-placement subject based on your "
            "English diagnostic test results. Please inquire with the Guidance Office "
            "via their Facebook page https://www.facebook.com/NWUGuidance to confirm "
            "whether you need to take it."
        )

    if course_code == "IMAT":
        return (
            "Math Review (IMAT) is a diagnostic-placement subject based on your "
            "Math diagnostic test results. Please inquire with the Guidance Office "
            "via their Facebook page https://www.facebook.com/NWUGuidance to confirm "
            "whether you need to take it."
        )

    needed = get_prerequisites(prereqs, courses, course.get("course_id"))
    if not needed:
        heading = format_course_name_then_code(course)
        return f"{heading} has no listed prerequisites."

    heading = format_course_name_then_code(course)

    if len(needed) == 1:
        lines: list[str] = [f"Prerequisite of {heading}:"]
    else:
        lines = [f"Prerequisites of {heading}:"]

    has_diagnostic = False
    diag_codes: set[str] = set()

    for c in needed:
        c_code = (c.get("course_code") or c.get("course_id") or "").strip().upper()

        # Always use "• Name (CODE)" for bullets.
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
            lines.append(
                "Note: English Review (IENG) depends on your English diagnostic "
                "test results. Please inquire with the Guidance Office via their "
                "Facebook page https://www.facebook.com/NWUGuidance."
            )
        elif diag_codes == {"IMAT"}:
            lines.append(
                "Note: Math Review (IMAT) depends on your Math diagnostic "
                "test results. Please inquire with the Guidance Office via their "
                "Facebook page https://www.facebook.com/NWUGuidance."
            )
        else:
            lines.append(
                "Note: English Review (IENG) and Math Review (IMAT) depend on your "
                "diagnostic test results. Please inquire with the Guidance Office "
                "via their Facebook page https://www.facebook.com/NWUGuidance."
            )

    return "\n".join(lines)


def handle_units(user_text: str, ents: dict) -> str:
    programs = data["programs"]
    plan = data["plan"]
    courses = data["courses"]
    prog_row = None
    if ents.get("program"):
        res = fuzzy_best_program(programs, ents["program"], score_cutoff=60)
        if res:
            _, _, prog_row = res
    if not prog_row:
        res = fuzzy_best_program(programs, user_text, score_cutoff=60)
        if res:
            _, _, prog_row = res
    year = ents.get("year_num")
    if not prog_row or not year:
        return "Please specify a program and year, e.g., 'How many units does 1st year Computer Science take?'."
    # Get units with diagnostic course exclusions
    total, by_sem, diagnostic_excluded = units_by_program_year_with_exclusions(
        plan, courses, prog_row["program_id"], year
    )
    if total == 0:
        return f"No curriculum entries found for {prog_row['program_name']} year {year}."
    # Convert year number to ordinal words
    year_labels = {1: "first", 2: "second", 3: "third", 4: "fourth"}
    year_text = year_labels.get(year, f"year {year}")
    lines = [f"For {year_text} year {prog_row['program_name']}, the total is {total} units.\n"]
    if by_sem:
        trimester_names = {
            "1": "First Trimester",
            "2": "Second Trimester",
            "3": "Third Trimester"
        }
        for sem in sorted(by_sem.keys(), key=int):
            tri_name = trimester_names.get(sem, f"Trimester {sem}")
            lines.append(f"  • {tri_name}: {by_sem[sem]} units")
    # Disclaimer about diagnostic exclusion
    if diagnostic_excluded:
        lines.append(
            "\nNote: Math Review (IMAT) and English Review (IENG) are not included in this count. "
            "These courses are only required based on your diagnostic exam results. "
            "For more information, contact the NWU Guidance Office via their Facebook page: "
            "https://www.facebook.com/NWUGuidance"
        )
    return "\n".join(lines)


def handle_dept_heads_list_or_clarify(user_text: str, ents: dict) -> str:
    tlow = (user_text or "").lower().strip()
    college = _detect_college(user_text)
    if college and college != "CAS":
        return _refer_university()
    if "all" in tlow or "cas" in tlow or "entire" in tlow or "everyone" in tlow or college == "CAS":
        rows = list_department_heads(data["departments"])
        if not rows:
            return "No department heads found."
        lines = ["Department heads (including Dean):"]
        for r in rows:
            lines.append(f"- {_format_head_row(r)}")
        return "\n".join(lines)
    st.session_state.awaiting_college_scope = True
    st.session_state.pending_intent = "dept_heads_college"
    return "Do you mean CAS department heads, or heads from another college (e.g., CCJE, COL, COBE, COME, CTE, CAHS, CIHTM, CEAT)?"


def handle_dept_head_one(user_text: str, ents: dict) -> str:
    tlow = (user_text or "").lower()
    college = _detect_college(user_text)
    if "dean" in tlow:
        if college == "CAS" or (college is None):
            dean_row = get_cas_dean(data["departments"])
            if dean_row and dean_row.get("department_head"):
                return f"The dean is {dean_row.get('department_head')}."
            return "No dean is recorded."
        if college and college != "CAS":
            return _refer_university()
        st.session_state.awaiting_college_scope = True
        st.session_state.pending_intent = "ask_dean_college"
        return "Which college dean are you referring to? CAS, or another college (CCJE, COL, COBE, COME, CTE, CAHS, CIHTM, CEAT)?"
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
    return f"The {role.lower()} is {head}."


def resolve_pending(user_text: str) -> Optional[str]:
    tlow = (user_text or "").lower().strip()
    if st.session_state.pending_intent == "dept_heads_list":
        st.session_state.awaiting_dept_scope = False
        st.session_state.pending_intent = None
        if "all" in tlow or "cas" in tlow or "everything" in tlow or "everyone" in tlow:
            rows = list_department_heads(data["departments"])
            if not rows:
                return "No department heads found."
            lines = ["Department heads (including Dean):"]
            for r in rows:
                lines.append(f"- {_format_head_row(r)}")
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
                if not rows:
                    return "No department heads found."
                lines = ["Department heads (including Dean):"]
                for r in rows:
                    lines.append(f"- {_format_head_row(r)}")
                return "\n".join(lines)
        if college and college != "CAS":
            return _refer_university()
        return "Thanks. Please specify a college (CAS, CCJE, COL, COBE, COME, CTE, CAHS, CIHTM, CEAT)."
    return None


def route(user_text: str) -> str:
    if st.session_state.awaiting_dept_scope or st.session_state.awaiting_college_scope:
        resolved = resolve_pending(user_text)
        if resolved:
            return resolved
    if _looks_like_payment(user_text):
        return _refer_university(channel_hint="finance")
    intent = detect_intent(user_text)
    ents = extract_entities(user_text)
    tlow = (user_text or "").lower().strip().rstrip("?!.")
    if tlow in {"department heads", "dept heads", "dept. heads", "different department heads"}:
        return handle_dept_heads_list_or_clarify(user_text, ents)
    if intent == "courseinfo" and _is_dept_headish(user_text):
        if ents.get("department"):
            return handle_dept_head_one(user_text, ents)
        return handle_dept_heads_list_or_clarify(user_text, ents)
    if intent == "prerequisites":
        return handle_prereq(user_text, ents)
    if intent == "units":
        return handle_units(user_text, ents)
    if intent == "dept_heads_list":
        return handle_dept_heads_list_or_clarify(user_text, ents)
    if intent == "dept_head_one":
        return handle_dept_head_one(user_text, ents)
    c = find_course_any(data, user_text)
    if c:
        return f"{format_course(c)} — {c.get('units', 'N/A')} units."
    return "Could you clarify what you need? Happy to help with prerequisites, unit loads, or department leadership."


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

