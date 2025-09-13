import streamlit as st
import requests
from datetime import datetime
from chat_ui import get_chat_bubble_html, get_footer_html

st.set_page_config(page_title="CASmate Chat", layout="centered")
st.title("🎓 CASmate - Northwestern University of Laoag CAS Chatbot")

# Initialize session state
if "chat" not in st.session_state:
    st.session_state.chat = []
if "asked_name" not in st.session_state:
    st.session_state.asked_name = False
if "got_name" not in st.session_state:
    st.session_state.got_name = False


def get_time_greeting():
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        return "Good morning"
    elif 12 <= current_hour < 18:
        return "Good afternoon"
    else:
        return "Hello"


if not st.session_state.asked_name:
    greeting = get_time_greeting()
    st.session_state.chat.append(("CASmate", f"{greeting}! What's your name?"))
    st.session_state.asked_name = True

for sender, msg in st.session_state.chat:
    st.markdown(get_chat_bubble_html(sender, msg), unsafe_allow_html=True)

if not st.session_state.got_name:
    name = st.text_input("You:", key="name_input")
    if name:
        st.session_state.chat.append(("Student", name))
        st.session_state.got_name = True
        st.session_state.chat.append(("CASmate", f"Hi, {name}."))
        try:
            response = requests.get("https://uselessfacts.jsph.pl/random.json?language=en", timeout=3)
            if response.status_code == 200:
                fact = response.json().get("text", "Here's a fun fact for you!")
            else:
                fact = "Here's a fun fact for you!"
        except Exception:
            fact = "Here's a fun fact for you!"
        st.session_state.chat.append(("CASmate", f"Did you know? _{fact}_"))
        st.session_state.chat.append(("CASmate", "How can I assist you today?"))

else:
    question = st.text_input("You:", key="question_input")
    if question:
        st.session_state.chat.append(("Student", question))
        st.session_state.chat.append(("CASmate", "CASmate is currently in development and will soon be able to answer your questions."))
        st.experimental_rerun()

st.markdown(get_footer_html(), unsafe_allow_html=True)

