import streamlit as st
import requests
from chat_ui import get_chat_bubble_html, get_footer_html

st.set_page_config(page_title="CASmate Chat", layout="centered")
st.title("CASmate - Northwestern University of Laoag CAS Chatbot")

if "name" not in st.session_state:
    st.session_state.name = ""
if "chat" not in st.session_state:
    st.session_state.chat = []

if st.session_state.name == "":
    name_input = st.text_input("What's your name?")
    if name_input:
        st.session_state.name = name_input
else:
    st.markdown(get_chat_bubble_html("Student", st.session_state.name), unsafe_allow_html=True)

for sender, msg in st.session_state.chat:
    st.markdown(get_chat_bubble_html(sender, msg), unsafe_allow_html=True)

if st.session_state.name:
    if not st.session_state.chat:
        st.session_state.chat.append(("CASmate", f"Hello, {st.session_state.name}! Welcome to the College of Arts and Sciences."))
        try:
            response = requests.get("https://uselessfacts.jsph.pl/random.json?language=en", timeout=3)
            if response.status_code == 200:
                fact = response.json().get("text", "Here's a fun fact for you!")
            else:
                fact = "Here's a fun fact for you!"
        except Exception:
            fact = "Here's a fun fact for you!"
        st.session_state.chat.append(("CASmate", f"💡 Did you know? _{fact}_"))

    question = st.text_input("Ask me anything about CAS.")
    if question:
        st.session_state.chat.append(("Student", question))
        st.session_state.chat.append(("CASmate", "CASmate is still in development and will soon be able to answer your queries better."))
        st.experimental_rerun()
else:
    st.info("Please enter your name above to get started.")

st.markdown(get_footer_html(), unsafe_allow_html=True)

