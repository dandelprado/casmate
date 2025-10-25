import re
from pathlib import Path
import streamlit as st

from chat_ui import getchatbubblehtml, getfooterhtml
from data_api import (
    load_all, find_course_by_code, courses_for_plan, fuzzy_best_program,
    fuzzy_top_programs, fuzzy_best_course_title, fuzzy_top_course_titles,
    get_prerequisites, course_by_alias
)
from nlu_rules import (
    build_gazetteers, detect_intent, extract_entities
)

def load_css_rel_path(css_path: Path):
    relpath = (Path(__file__).parent / css_path).resolve()
    if relpath.exists():
        css = relpath.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

st.set_page_config(page_title="CASmate Chat", layout="centered")
st.markdown("<h1 class='main-title'>CASmate - Northwestern University CAS Chatbot</h1>", unsafe_allow_html=True)
load_css_rel_path(Path("styles.css"))

if "data" not in st.session_state:
    st.session_state.data = load_all()

data = st.session_state.data
departments = data["departments"]
programs = data["programs"]
courses = data["courses"]
plan = data["plan"]
prereqs = data.get("prereqs", [])
synonyms = data.get("synonyms", [])

build_gazetteers(programs, courses, synonyms)

st.session_state.setdefault("chat", [])
st.session_state.setdefault("asked_name", False)
st.session_state.setdefault("user_name", None)
st.session_state.setdefault("last_context", {"type": None, "course": None, "program": None})

def set_context(ctx_type=None, course=None, program=None):
    if ctx_type: st.session_state.last_context["type"] = ctx_type
    if course is not None: st.session_state.last_context["course"] = course
    if program is not None: st.session_state.last_context["program"] = program

if not st.session_state.chat:
    intro = (
        "Good afternoon! I'm CASmate, a chatbot built to assist students of the College of Arts and Sciences with quick course and curriculum questions. "
        "What's your name?"
    )
    st.session_state.chat.append({"sender": "CASmate", "message": intro, "source": None})

ORD = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
SEM_MAP = {"first": 1, "1st": 1, "sem 1": 1, "semester 1": 1, "sem1": 1,
           "second": 2, "2nd": 2, "sem 2": 2, "semester 2": 2, "sem2": 2,
           "third": 3, "3rd": 3, "sem 3": 3, "semester 3": 3, "sem3": 3}
YEAR_MAP = {"first": 1, "1st": 1, "year 1": 1, "yr 1": 1,
            "second": 2, "2nd": 2, "year 2": 2, "yr 2": 2,
            "third": 3, "3rd": 3, "year 3": 3, "yr 3": 3,
            "fourth": 4, "4th": 4, "year 4": 4, "yr 4": 4}

def parse_year_sem(text: str):
    t = (text or "").lower()
    year = None
    sem = None
    for k, v in YEAR_MAP.items():
        if k in t:
            year = v
            break
    for k, v in SEM_MAP.items():
        if k in t or f"{v}nd sem" in t or f"{v}st sem" in t or f"{v}rd sem" in t or f"{v}th sem" in t:
            sem = v
            break
    m_y = re.search(r"(1st|2nd|3rd|4th)\s*(yr|year)", t)
    if m_y and not year:
        year = {"1st": 1, "2nd": 2, "3rd": 3, "4th": 4}[m_y.group(1)]
    m_s = re.search(r"(1st|2nd|3rd)\s*sem", t)
    if m_s and not sem:
        sem = {"1st": 1, "2nd": 2, "3rd": 3}[m_s.group(1)]
    return year, sem


def source_for_program(program_row: dict | None) -> str:
    deptid = (program_row or {}).get("department_id")
    if deptid:
        dept = next((d for d in departments if d["department_id"] == deptid), None)
        if dept:
            return f"Department Head, {dept['department_name']}"
    dean = next((d for d in departments if (d.get("dean_flag") or '').upper() == "Y"), None)
    name = (dean or {}).get("department_name", "CAS Dean's Office")
    return name


def resolve_program_row(name: str | None):
    if not name:
        return None
    dn = name.strip().lower()
    row = next((p for p in programs if p["program_name"].strip().lower() == dn), None)
    if row:
        return row
    row = next((p for p in programs if p["program_name"].strip().lower().endswith(dn)), None)
    if row:
        return row
    return next((p for p in programs if dn in p["program_name"].strip().lower()), None)


def add_message(sender: str, message: str, source: str | None = None):
    st.session_state.chat.append({"sender": sender, "message": message, "source": source})


def handle_smalltalk():
    return "Hello! How can CASmate help with your courses or curriculum today?", None

def handle_goodbye():
    return "Thank you! If you have more questions about your courses, just message again.", None

def handle_confirm():
    lc = st.session_state.last_context
    if lc["type"] == "prereq" and lc["course"]:
        row = lc["course"]
        reqs = get_prerequisites(prereqs, courses, row["course_id"])
        if not reqs:
            return f"Yes—{row.get('course_code') or row['course_id']} {row['course_title']} has no listed prerequisites.", None
        parts = ", ".join(f"{r['course_code']} {r['course_title']}" for r in reqs)
        return f"Yes—prerequisites for {row.get('course_code') or row['course_id']} {row['course_title']} are: {parts}.", None
    return "Sure—what would you like me to double‑check?", None

def handle_confusion():
    return "I understand you'd like more information. Could you please provide the specific courjse code (e.g., CS102) or the exact course title?", None

def handle_out_of_scope():
    """
    Handle queries that don't match any intent or have no recognized entities
    """
    return (
        "I'm sorry, I didn't understand that. I can help you with:\n\n"
        "• Course prerequisites (e.g., 'What's the prerequisite for CS102?')\n"
        "• Program courses (e.g., 'What courses for Computer Science?')\n"
        "• Curriculum plans (e.g., 'Courses for CS 1st year 1st semester')\n"
        "• Faculty information (e.g., 'Who teaches CS101?')\n\n"
        "Please ask your question in English."
    ), None


def handle_plan_query(q: str):
    ents = extract_entities(q)
    progname = ents.get("program")
    progrow = resolve_program_row(progname) if progname else None
    if not progrow:
        best = fuzzy_best_program(programs, q, score_cutoff=70 if len((q or '').strip()) >= 6 else 60)
        if best:
            _, _, progrow = best
    if not progrow:
        return "Please mention a valid program (e.g., Psychology, Computer Science).", None
    year, sem = parse_year_sem(q)
    if year and not sem:
        sem = 1
    if not year:
        return "Please include a year level (e.g., first year, 2nd year).", None
    if not sem:
        return "Please include a semester (e.g., first sem, 2nd sem).", None
    rows = courses_for_plan(plan, courses, progrow["program_id"], year, sem)
    if not rows:
        return f"No plan entries found for {progrow['program_name']} year {year} semester {sem}.", source_for_program(progrow)
    yearstr = ORD.get(year, f"{year}th")
    semstr = "1st" if sem == 1 else "2nd" if sem == 2 else f"{sem}th"
    items = [f"- {(r.get('course_code') or r['course_id'])} {r['course_title']}" for r in rows]
    msg = f"These are the courses for {yearstr} year {progrow['program_name']} {semstr} semester:\n\n" + "\n".join(items)
    set_context(ctx_type="plan", program=progrow)
    return msg, source_for_program(progrow)


def handle_program_courses_query(q: str):
    """
    Handle queries asking for all courses in a program (not semester-specific)
    Examples: "courses in CS", "what courses for computer science", "CS courses"
    """
    ents = extract_entities(q)
    progname = ents.get("program")
    progrow = resolve_program_row(progname) if progname else None
    
    if not progrow:
        best = fuzzy_best_program(programs, q, score_cutoff=70 if len((q or '').strip()) >= 6 else 60)
        if best:
            _, _, progrow = best
    
    if not progrow:
        return "Please mention a valid program (e.g., Psychology, Computer Science).", None
    
    # Get curriculum plan data for this program
    plan_courses = [p for p in plan if p.get("program_id") == progrow["program_id"]]
    
    if not plan_courses:
        # Fallback: get all courses for this program
        prog_courses = [c for c in courses if c.get("program_id") == progrow["program_id"]]
        if not prog_courses:
            return f"No courses found for {progrow['program_name']}.", source_for_program(progrow)
        items = [f"- {c.get('course_code') or c['course_id']} {c['course_title']}" for c in prog_courses]
        msg = f"Courses for {progrow['program_name']}:\n\n" + "\n".join(items)
        set_context(ctx_type="plan", program=progrow)
        return msg, source_for_program(progrow)
    
    # Organize by year and semester
    year_sem_courses = {}
    for p in plan_courses:
        year = p.get("year_level")
        sem = p.get("semester")
        course_id = p.get("course_id")
        
        course = next((c for c in courses if c["course_id"] == course_id), None)
        if course and year and sem:
            key = (year, sem)
            if key not in year_sem_courses:
                year_sem_courses[key] = []
            # Avoid duplicates
            if course not in year_sem_courses[key]:
                year_sem_courses[key].append(course)
    
    if not year_sem_courses:
        return f"No curriculum plan found for {progrow['program_name']}.", source_for_program(progrow)
    
    # Build the formatted response
    lines = [f"Here are the courses for {progrow['program_name']} by year level:\n"]
    
    # Sort by year, then semester
    sorted_keys = sorted(year_sem_courses.keys())
    
    for year, sem in sorted_keys:
        # Format year: 1st, 2nd, 3rd, 4th
        if year == 1:
            year_str = "1st"
        elif year == 2:
            year_str = "2nd"
        elif year == 3:
            year_str = "3rd"
        elif year == 4:
            year_str = "4th"
        else:
            year_str = f"{year}th"
        
        # Format semester: 1st, 2nd, 3rd
        if sem == 1:
            sem_str = "1st"
        elif sem == 2:
            sem_str = "2nd"
        elif sem == 3:
            sem_str = "3rd"
        else:
            sem_str = f"{sem}th"
        
        lines.append(f"\n{year_str} Year, {sem_str} Semester:")
        
        for c in year_sem_courses[(year, sem)]:
            lines.append(f"- {c.get('course_code') or c['course_id']} {c['course_title']}")
    
    set_context(ctx_type="plan", program=progrow)
    return "\n".join(lines), source_for_program(progrow)


def handle_faculty_query(q: str):
    """
    Handle queries about CAS Dean, department heads, or course instructors
    """
    q_lower = q.lower()
    
    dean_keywords = ["cas dean", "dean of cas", "who is the dean", "current dean", 
                    "dean of the university", "dean of university", "university dean"]
    is_dean_query = any(kw in q_lower for kw in dean_keywords)
    
    if is_dean_query:
        dean_row = next((d for d in departments if d.get("dean_flag", "").upper() == "Y"), None)
        if dean_row:
            return (
                f"The CAS Dean is {dean_row.get('department_head', 'Not available')}.",
                "CAS Dean's Office"
            )
        return "CAS Dean information not available.", None
    
    dept_keywords = {
        "computer science": "D-CS",
        "cs": "D-CS",
        "comp sci": "D-CS",
        "social sciences": "D-SS",
        "social": "D-SS",
        "language and literature": "D-LL",
        "language": "D-LL",
        "literature": "D-LL",
        "natural sciences": "D-NS",
        "natural": "D-NS",
        "mathematics": "D-MATH",
        "math": "D-MATH"
    }
    
    for keyword, dept_id in dept_keywords.items():
        if f"head of {keyword}" in q_lower or f"{keyword} head" in q_lower or f"head {keyword}" in q_lower:
            dept = next((d for d in departments if d.get("department_id") == dept_id), None)
            if dept:
                return (
                    f"The head of {dept.get('department_name', keyword)} is {dept.get('department_head', 'Not available')}.",
                    f"Department Head, {dept.get('department_name', '')}"
                )
            return f"Department head information for {keyword} not available.", None
    
    m = re.search(r'([A-Za-z]{2,4})-?(\d{2,3})', q or '')
    if m:
        code = f"{m.group(1).upper()}-{m.group(2)}"
        c = find_course_by_code(courses, code)
        if c:
            prog = next((p for p in programs if p["program_id"] == c.get("program_id")), None)
            set_context(ctx_type="courseinfo", course=c, program=prog)
            return (
                f"{c.get('course_code') or c['course_id']} {c['course_title']} instructor assignment will be provided when section data becomes available.",
                source_for_program(prog)
            )
    
    return (
        "I can provide information about:\n"
        "• CAS Dean (ask 'Who is the CAS Dean?')\n"
        "• Department heads (ask 'Who is the head of Computer Science?')\n"
        "Please specify which information you need."
    ), None

def normalize_course_query(text: str) -> str:
    t = (text or "").lower()
    t = re.sub(r'\b(the|of|a|an|for|to|in)\b', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def handle_prereq_query(q: str):
    ents = extract_entities(q)
    code = ents.get("coursecode")
    row = find_course_by_code(courses, code) if code else None
    
    if not row and ents.get("coursetitle"):
        title_lower = ents["coursetitle"].lower()
        row = next((x for x in courses if (x.get("course_title") or "").lower() == title_lower), None)
        
        if not row:
            norm_query = normalize_course_query(ents["coursetitle"])
            for c in courses:
                norm_title = normalize_course_query(c.get("course_title", ""))
                if norm_query == norm_title or norm_query in norm_title or norm_title in norm_query:
                    row = c
                    break
    
    if not row:
        alias_hit = course_by_alias(data, q.strip())
        if alias_hit:
            row = alias_hit
        else:
            norm_q = normalize_course_query(q)
            alias_hit = course_by_alias(data, norm_q)
            if alias_hit:
                row = alias_hit
    
    if not row:
        q_norm = normalize_course_query(q)
        for c in courses:
            title_norm = normalize_course_query(c.get("course_title", ""))
            if len(q_norm) > 5 and (q_norm in title_norm or title_norm in q_norm):
                row = c
                break
            q_words = set(q_norm.split())
            title_words = set(title_norm.split())
            if len(q_words) >= 2 and q_words.issubset(title_words):
                row = c
                break
    
    if not row:
        best = fuzzy_best_course_title(courses, q, score_cutoff=50)
        if best:
            _, _, row = best
    
    if not row:
        q_lower = q.lower()
        term_map = {
            "data struct": "CS-002", "datastruct": "CS-002", "data structure": "CS-002",
            "calculus": "MATH-002", "calc": "MATH-002",
            "psychology": "PSY-001", "psych": "PSY-001",
            "biology": "BIO-001", "bio": "BIO-001",
        }
        
        for term, course_id in term_map.items():
            if term in q_lower:
                row = next((c for c in courses if c.get("course_id") == course_id), None)
                if row:
                    break
    
    if not row:
        return "Could not identify the course to check prerequisites. Please mention the exact title or code.", None
    
    reqs = get_prerequisites(prereqs, courses, row["course_id"])
    prog = next((p for p in programs if p["program_id"] == row.get("program_id")), None)
    set_context(ctx_type="prereq", course=row, program=prog)
    
    if not reqs:
        return f"{row.get('course_code') or row['course_id']} {row['course_title']} has no listed prerequisites.", source_for_program(prog)
    
    parts = [f"- {it['course_code']} {it['course_title']}" for it in reqs]
    return f"Prerequisites for {row.get('course_code') or row['course_id']} {row['course_title']}:\n\n" + "\n".join(parts), source_for_program(prog)

def handle_courseinfo_query(q: str):
    """
    Handle generic course info queries - with out-of-scope detection
    """
    m = re.search(r'([A-Za-z]{2,4})-?(\d{2,3})', q or '')
    
    english_keywords = ["course", "class", "subject", "program", "prerequisite", 
                       "prereq", "requirement", "semester", "year", "courses"]
    has_english_keyword = any(kw in q.lower() for kw in english_keywords)
    
    ents = extract_entities(q)
    has_entities = ents.get("course_title") or ents.get("program")
    
    if not m and not has_english_keyword and not has_entities:
        return handle_out_of_scope()
    
    if m:
        code = f"{m.group(1).upper()}-{m.group(2)}"
        c = find_course_by_code(courses, code)
        if c:
            prog = next((p for p in programs if p["program_id"] == c.get("program_id")), None)
            set_context(ctx_type="courseinfo", course=c, program=prog)
            return (
                f"{c.get('course_code') or c['course_id']} {c['course_title']} is a {c.get('units', '?')} unit course.",
                source_for_program(prog)
            )
    
    return "Hmm, not sure which course you mean—try a course code like CS102.", None


def route_intent(text: str):
    """
    Route user query to the appropriate handler
    """
    intent = detect_intent(text)
    text_lower = text.lower().strip()
    
    if intent == "smalltalk": 
        return handle_smalltalk()
    if intent == "goodbye": 
        return handle_goodbye()
    if intent == "confirm": 
        return handle_confirm()
    if intent == "confusion": 
        return handle_confusion()
    if intent == "prerequisites": 
        return handle_prereq_query(text)
    if intent == "facultylookup": 
        return handle_faculty_query(text)
    
    program_query_patterns = [
        r'courses?\s+(?:for|in|of|under)\s+(?:the\s+)?(\w+(?:\s+\w+)?)\s*(?:program|degree|major)?',
        r'what\s+courses?\s+(?:for|in|if|when|to\s+take|i\s+need)\s+(?:i\s+)?(?:take|study|choose|as|for)\s+(\w+(?:\s+\w+)?)',
        r'(\w+(?:\s+\w+)?)\s+(?:program|degree|major)\s+courses?',
        r'courses?\s+(?:for|in|to\s+take\s+as|i\s+need\s+(?:to\s+)?take\s+as)\s+(\w+(?:\s+\w+)?)',
        r'courses?\s+(?:i\s+need\s+to\s+take|to\s+take)\s+(?:as|for|in)\s+(\w+(?:\s+\w+)?)',
    ]
    
    for pattern in program_query_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            return handle_program_courses_query(text)
    
    if intent == "planlookup":
        year, sem = parse_year_sem(text)
        
        if not year and not sem:
            return handle_program_courses_query(text)
        
        return handle_plan_query(text)
    
    for prog in programs:
        prog_name_lower = prog["program_name"].lower()
        prog_words = set(prog_name_lower.split())
        text_words = set(text_lower.split())
        
        key_words = prog_words - {"in", "bs", "ba", "of", "the", "and"}
        if len(key_words) > 0 and key_words.issubset(text_words):
            return handle_program_courses_query(text)
    
    program_codes = {
        "cs": "computer science",
        "psych": "psychology",
        "psy": "psychology",
        "pols": "political science",
        "polsci": "political science",
        "bio": "biology",
        "eng": "english",
        "comm": "communication"
    }
    
    for code, full_name in program_codes.items():
        if code == text_lower or code in text_lower.split():
            return handle_program_courses_query(text)
    
    return handle_courseinfo_query(text)


for msg in st.session_state.chat:
    html = getchatbubblehtml(
        msg["sender"],
        msg["message"],
        msg.get("source"),
        st.session_state.user_name
    )
    st.markdown(html, unsafe_allow_html=True)

st.markdown('<div class="input-section"><div class="input-label">You:</div></div>', unsafe_allow_html=True)
prompt = st.chat_input("Ask in English (e.g., 'prereq of calc 1?', 'courses for CS 1st yr 1st sem')")

if prompt is not None:
    user_text = prompt.strip()
    if user_text:
        if not st.session_state.asked_name:
            st.session_state.user_name = user_text
            st.session_state.asked_name = True
            add_message("CASmate", f"Nice to meet you, {st.session_state.user_name}. How can I help?")
        else:
            add_message(st.session_state.user_name, user_text)
            reply, source = route_intent(user_text)
            add_message("CASmate", reply, source=source)
        st.rerun()

st.markdown(getfooterhtml(), unsafe_allow_html=True)

