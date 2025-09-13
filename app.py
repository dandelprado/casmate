import re
import streamlit as st
from datetime import datetime
from chat_ui import inject_css, get_chat_bubble_html, get_footer_html
from data_api import load_all, find_program, find_course_by_code, courses_for_plan

st.set_page_config(page_title="CASmate Chat", layout="centered")
st.title("CASmate - Northwestern University Laoag CAS Chatbot")
st.markdown(inject_css(), unsafe_allow_html=True)

if "data" not in st.session_state:
    st.session_state.data = load_all()

data = st.session_state.data
programs = data["programs"]
courses = data["courses"]
plan = data["plan"]

if "chat" not in st.session_state:
    st.session_state.chat = []
if "asked_name" not in st.session_state:
    st.session_state.asked_name = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "awaiting_question" not in st.session_state:
    st.session_state.awaiting_question = False


def time_greeting():
    h = datetime.now().hour
    if 5 <= h < 12:
        return "Good morning"
    if 12 <= h < 18:
        return "Good afternoon"
    return "Hello"

if not st.session_state.asked_name:
    st.session_state.chat.append(("CASmate", f"{time_greeting()}! What's your name?"))
    st.session_state.asked_name = True

for sender, msg in st.session_state.chat:
    label = sender if sender != "Student" or not st.session_state.user_name else st.session_state.user_name
    st.markdown(get_chat_bubble_html(sender if sender != "Student" else (st.session_state.user_name or "Student"), msg, label), unsafe_allow_html=True)

YEAR_WORDS = {
        "first": 1, "1st": 1, "year 1": 1,
        "second": 2, "2nd": 2, "year 2": 2,
        "third": 3, "3rd": 3, "year 3": 3,
        "fourth": 4, "4th": 4, "year 4": 4,
}

SEM_WORDS = {
        "first sem": 1, "1st sem": 1, "first semester": 1, "semester 1": 1, "sem 1":1,
        "second sem": 2, "2nd sem": 2, "second semester": 2, "semester 2": 2, "sem 2": 2,
}


def parse_year_sem(text: str):
    t = text.lower()
    year = None
    sem = None

    for k, v in SEM_WORDS.items():
        if k in t:
            sem = v
            break

    for k, v in YEAR_WORDS.items():
        if k in t:
            year = v
            break

    return year, sem


def handle_plan_query(q: str):
    prog = None
    for p in programs:
        name = p["program_name"].lower()
        if name in q.lower():
            prog = p
            break
    if not prog:
        return "Please mention a program (e.g., Psychology, Computer Science)."

    year, sem = parse_year_sem(q)
    if not year or not sem:
        return "Please include a year level and semester (e.g., first year first semester)."

    rows = courses_for_plan(plan, courses, prog["program_id"], year, sem)
    if not rows:
        return f"No plan entries found for {prog['program_name']} year {year} semester {sem}."

    lines = [f"- {r['course_code'] or r['course_id']}: {r['course_title']} ({r['units']} units)" for r in rows]

    return "Here are the courses:\n" + "\n".join(lines)


def handle_faculty_query(q: str):

    m = re.search(r'\b([A-Za-z]{2,}\s*\d{2,3})\b', q)
    if not m:
        return "Please include a course code like CS102."
    code = m.group(1)
    c = find_course_by_code(courses, code)
    if not c:
        return f"Could not find course {code}."

    return f"{c['course_code'] or c['course_id']}: {c['course_title']} is currently listed in the catalog."


def route_intent(q: str):
    ql = q.lower()
    if any(w in ql for w in ["first sem", "second sem", "semester", "sem"]) and any(w in ql for w in ["first year", "second year", "third year", "fourth year", "1st", "2nd", "3rd", "4th"]):
        return handle_plan_query(q)
    if any(w in ql for w in ["who teaches", "instructor", "handled by", "handles"]):
        return handle_faculty_query(q)

    resp = handle_plan_query(q)
    return resp


def submit_name():
    name = st.session_state.get("name_input", "").strip()
    if not name:
        return
    st.session_state.user_name = name
    st.session_state.chat.append(("Student", name))
    st.session_state.chat.append(("CASmate", f"Hi, {name}."))
    st.session_state.chat.append(("CASmate", "How can I assist you today?"))
    st.session_state.name_input = ""


def submit_question():
    q = st.session_state.get("question_input", "").strip()
    if not q:
        return
    st.session_state.chat.append(("Student", q))
    answer = route_intent(q)
    st.session_state.chat.append(("CASmate", answer))
    st.session_state.question_input = ""


if not st.session_state.user_name:
    st.text_input("You:", key="name_input", on_change=submit_name)
else:
    st.text_input("You:", key="question_input", on_change=submit_question)

st.markdown(get_footer_html(), unsafe_allow_html=True)
