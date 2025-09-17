import re
from datetime import datetime
from pathlib import Path

import streamlit as st

from chat_ui import get_chat_bubble_html, get_footer_html
from data_api import (
    load_all, find_course_by_code, courses_for_plan,
    fuzzy_best_program, fuzzy_top_programs,
    fuzzy_best_course_title, fuzzy_top_course_titles,
    get_prerequisites
)
from nlu_rules import nlp, matcher, phrase_matcher, build_gazetteers, detect_intent, extract_entities


def load_css(rel_path: str):
    css_path = (Path(__file__).parent / rel_path).resolve()
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

st.set_page_config(page_title="CASmate Chat", layout="centered")
st.title("CASmate - Northwestern University of Laoag CAS Chatbot")
load_css("ui/styles.css")

if "data" not in st.session_state:
    st.session_state.data = load_all()
data = st.session_state.data
departments = data["departments"]
programs = data["programs"]
courses = data["courses"]
plan = data["plan"]
prereqs = data.get("prereqs", [])

build_gazetteers(programs, courses)

st.session_state.setdefault("chat", [])
st.session_state.setdefault("asked_name", False)
st.session_state.setdefault("user_name", "")
st.session_state.setdefault("clarify", None)

GOODBYES = {"bye","goodbye","thanks","thank you","no","none","nothing","that's all","thats all","nope","nah"}
FINANCE_KEYWORDS = {"finance","billing","payment","payments","pay","cashier","tuition","fees","fee","balance","statement","downpayment","installment","overdue","surcharge"}

def time_greeting():
    h = datetime.now().hour
    if 5 <= h < 12: return "Good morning"
    if 12 <= h < 18: return "Good afternoon"
    return "Hello"

def push(sender: str, msg: str, source: str | None = None):
    sentences = re.split(r'(?<=[.!?])\s+', (msg or "").strip())
    sentences = [s for s in sentences if s]
    text = " ".join(sentences[:3]) if sentences else msg
    st.session_state.chat.append((sender, text, (source or "").strip()))

def push_sys(msg: str):
    push("CASmate", msg, source="")


def first_name(user) -> str:
    user = user if isinstance(user, str) else " ".join(map(str, user)) if isinstance(user, (list, tuple)) else str(user or "")
    user = user.strip()
    return user.split()[0] if user else ""


def source_for_program(program_row: dict | None) -> str:
    dept_id = (program_row or {}).get("department_id")
    dept = next((d for d in departments if d["department_id"] == dept_id), None)
    if dept:
        return f"Department Head, {dept['department_name']} (internal)"
    cas = next((d for d in departments if (d.get("dean_flag") or "").upper() == "Y"), None)
    return f"{(cas or {}).get('department_name', 'CAS Dean’s Office')} (internal)"

SEM_MAP = {"first sem":1,"1st sem":1,"first semester":1,"semester 1":1,"sem 1":1,"second sem":2,"2nd sem":2,"second semester":2,"semester 2":2,"sem 2":2}
YEAR_MAP = {"first":1,"1st":1,"year 1":1,"second":2,"2nd":2,"year 2":2,"third":3,"3rd":3,"year 3":3,"fourth":4,"4th":4,"year 4":4}

def parse_year_sem(text: str):
    t = (text or "").lower()
    sem = next((v for k,v in SEM_MAP.items() if k in t), None)
    year = next((v for k,v in YEAR_MAP.items() if k in t), None)
    return year, sem


def handle_plan_query(q: str):
    best = fuzzy_best_program(programs, q, score_cutoff=0)
    if best:
        prog_name, score, prog_row = best

        if score < 60:
            top = fuzzy_top_programs(programs, q, limit=3, score_cutoff=60)
            if top:
                st.session_state.clarify = {"type": "program", "options": top}
                return "Did you mean one of these programs? " + "; ".join(top), ""

        year, sem = parse_year_sem(q)

        if year and not sem:
            sem = 1

        if not year:
            return "Please include a year level (e.g., first year, 2nd year).", source_for_program(prog_row)
        if not sem:
            return "Please include a semester or trimester (e.g., first semester, 2nd sem).", source_for_program(prog_row)

        rows = courses_for_plan(plan, courses, prog_row["program_id"], year, sem)
        if not rows:
            return f"No plan entries found for {prog_name} year {year} semester {sem}.", source_for_program(prog_row)

        ord_map = {1: '1st', 2: '2nd', 3: '3rd', 4: '4th'}
        year_str = ord_map.get(year, f"{year}th")
        sem_str = f"{sem}st" if sem == 1 else f"{sem}nd" if sem == 2 else f"{sem}th"

        items = [f"{r['course_code'] or r['course_id']} {r['course_title']} ({r['units']} units)" for r in rows]

        return (f"These are the courses you will be taking as a {year_str} year {prog_name} student "
                f"during the {sem_str} semester: {', '.join(items)}."), source_for_program(prog_row)

    return "Please mention a program (e.g., Psychology, Computer Science).", ""


def handle_faculty_query(q: str):
    m = re.search(r'\b([A-Za-z]{2,}\s*\d{2,3})\b', q or "")
    if m:
        code = m.group(1)
        c = find_course_by_code(courses, code)
        if c:
            prog = next((p for p in programs if p["program_id"] == c.get("program_id")), None)
            return f"{c['course_code'] or c['course_id']}: {c['course_title']} — instructor assignment will be provided when class_sections.csv is available.", source_for_program(prog)
    best = fuzzy_best_course_title(courses, q, score_cutoff=0)
    if not best:
        return "Could not find a matching course.", ""
    title, score, row = best
    prog = next((p for p in programs if p["program_id"] == row.get("program_id")), None)
    if score >= 85:
        return f"{row['course_code'] or row['course_id']}: {row['course_title']} — instructor assignment will be provided when class_sections.csv is available.", source_for_program(prog)
    elif score >= 60:
        top = fuzzy_top_course_titles(courses, q, limit=3, score_cutoff=60)
        if top:
            options = [f"{t} ({r['course_code'] or r['course_id']})" for (t, s, r) in top]
            st.session_state.clarify = {"type":"course_title","options":options}
            return "Did you mean: " + "; ".join(options) + "?", ""
        return "Could not find a close enough match.", ""
    else:
        return "Could not find a close enough match.", ""

def handle_prereq_query(q: str):
    ents = extract_entities(q)
    code = ents.get("course_code")
    c = find_course_by_code(courses, code) if code else None
    row = c
    if not row and ents.get("course_title"):
        row = next((x for x in courses if x["course_title"].lower() == ents["course_title"].lower()), None)
    if not row:
        best = fuzzy_best_course_title(courses, q, score_cutoff=70)
        if best:
            _title, _score, row = best
    if not row:
        return "Could not identify the course to check prerequisites. Please mention the exact title or code.", ""
    reqs = get_prerequisites(prereqs, courses, row["course_id"])
    prog = next((p for p in programs if p["program_id"] == row.get("program_id")), None)
    if not reqs:
        return f"{row['course_code'] or row['course_id']} {row['course_title']} has no listed prerequisites.", source_for_program(prog)
    parts = [f"{it['course_code']} {it['course_title']}" for it in reqs]
    return f"Prerequisites for {row['course_code'] or row['course_id']} {row['course_title']}: {', '.join(parts)}.", source_for_program(prog)

def finance_redirect(q: str):
    t = (q or "").lower()
    if any(k in t for k in FINANCE_KEYWORDS):
        return ('For tuition, fees, and payments, please reach the NWU Finance Office: '
                '<a href="https://www.facebook.com/NWUFinance" target="_blank" rel="noopener">facebook.com/NWUFinance</a>'), ""
    return None, None

def route_intent(q: str):
    msg, src = finance_redirect(q)
    if msg is not None:
        return msg, src
    intent = detect_intent(q)
    if intent == "small_talk":
        return "Hi! How can I help today?", ""
    if intent == "goodbye":
        return "Thanks for chatting—take care!", ""
    if intent == "plan_lookup":
        return handle_plan_query(q)
    if intent == "faculty_lookup":
        return handle_faculty_query(q)
    if intent == "prerequisites":
        return handle_prereq_query(q)
    ents = extract_entities(q)
    code = ents.get("course_code")
    if code:
        c = find_course_by_code(courses, code)
        if c:
            prog = next((p for p in programs if p["program_id"] == c.get("program_id")), None)
            return f"{c['course_code']}: {c['course_title']} — {c['units']} units.", source_for_program(prog)
    if ents.get("course_title"):
        row = next((x for x in courses if x["course_title"].lower() == ents["course_title"].lower()), None)
        if row:
            prog = next((p for p in programs if p["program_id"] == row.get("program_id")), None)
            return f"{row['course_code']}: {row['course_title']} — {row['units']} units.", source_for_program(prog)
    best = fuzzy_best_course_title(courses, q, score_cutoff=65)
    if best:
        _title, _score, row = best
        prog = next((p for p in programs if p["program_id"] == row.get("program_id")), None)
        return f"{row['course_code']}: {row['course_title']} — {row['units']} units.", source_for_program(prog)
    return "Could not find a close enough match.", ""

def needs_clarification(msg: str) -> bool:
    triggers = [
        "please mention a program",
        "please include a year",
        "could not identify the course",
        "could not find a matching course",
        "could not find a close enough match"
    ]
    return any(t in (msg or "").lower() for t in triggers)


def submit_name():
    name = st.session_state.get("name_input", "")
    if isinstance(name, (list, tuple)):
        name = " ".join(map(str, name))
    name = name.strip()
    if not name:
        return
    st.session_state.user_name = name
    fname = first_name(name)
    push_sys(f"Nice to meet you, {fname}. How can I help?")
    st.session_state.name_input = ""



def submit_question():
    q = st.session_state.get("question_input", "").strip()
    if not q:
        return
    lower = q.lower()
    if lower in (x for x in GOODBYES) or any(w in lower for w in ["bye","goodbye"]):
        push_sys("Thanks for chatting—take care!")
        st.session_state.question_input = ""
        return

    st.session_state.chat.append(("Student", q, None))
    ans, src = route_intent(q)
    push("CASmate", ans, src)

    if not needs_clarification(ans):
        push_sys("Anything else I can help with?")

    st.session_state.question_input = ""


if not st.session_state.asked_name:
    push_sys(f"{time_greeting()}! I’m CASmate, a chatbot built to assist students of the College of Arts and Sciences with quick course and curriculum questions. What’s your name?")
    st.session_state.asked_name = True

for sender, msg, src in st.session_state.chat:
    label = sender if sender != "Student" or not st.session_state.user_name else st.session_state.user_name
    st.markdown(
        get_chat_bubble_html(
            sender if sender != "Student" else (st.session_state.user_name or "Student"),
            msg, label, source=src),
        unsafe_allow_html=True,
    )

if not st.session_state.user_name:
    st.text_input("You:", key="name_input", on_change=submit_name)
else:
    st.text_input("You:", key="question_input", on_change=submit_question)

st.markdown(get_footer_html(), unsafe_allow_html=True)

