import streamlit as st
import requests
from datetime import datetime
from chat_ui import inject_css, get_chat_bubble_html, get_footer_html

st.set_page_config(page_title="CASmate Chat", layout="centered")
st.title("CASmate - Northwestern University of Laoag CAS Chatbot")

st.markdown(inject_css(), unsafe_allow_html=True)

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
    label = sender
    if sender == "Student" and st.session_state.user_name:
        label = st.session_state.user_name
    st.markdown(get_chat_bubble_html(sender if sender != "Student" else st.session_state.user_name or "Student",
                                     msg,
                                     display_label=label),
                unsafe_allow_html=True)

def submit_name():
    name = st.session_state.get("name_input", "").strip()
    if not name:
        return
    st.session_state.user_name = name
    st.session_state.chat.append(("Student", name))
    st.session_state.chat.append(("CASmate", f"Hi, {name}."))
    # Trivia
    fact = "Here's a fun fact for you!"
    try:
        r = requests.get("https://uselessfacts.jsph.pl/random.json?language=en", timeout=4)
        if r.status_code == 200:
            fact = r.json().get("text", fact)
    except Exception:
        pass
    st.session_state.chat.append(("CASmate", f"Did you know? {fact}"))
    st.session_state.chat.append(("CASmate", "How can I assist you today?"))
    st.session_state.awaiting_question = True
    st.session_state.name_input = "" 

def submit_question():
    q = st.session_state.get("question_input", "").strip()
    if not q:
        return
    st.session_state.chat.append(("Student", q))
    st.session_state.chat.append(("CASmate", "CASmate is currently in development. Please wait for the next update."))
    st.session_state.question_input = ""  

if not st.session_state.user_name:
    st.text_input("You:", key="name_input", on_change=submit_name)
else:
    st.text_input("You:", key="question_input", on_change=submit_question)

st.markdown(get_footer_html(), unsafe_allow_html=True)

