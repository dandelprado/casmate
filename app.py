import streamlit as st
import requests

st.set_page_config(page_title="CASmate Chat", layout="centered")

st.title("CASmate - Northwestern University of Laoag CAS Chatbot")

if "chat" not in st.session_state:
    st.session_state.chat = []

if "name" not in st.session_state:
    st.session_state.name = ""

if st.session_state.name == "":
    name = st.text_input("What's your name?")
    if name:
        st.session_state.name = name
else:
    st.markdown(f"<b>Student:</b> {st.session_state.name}", unsafe_allow_html=True)


def chat_bubble(sender, message):
    align = "left" if sender == "CASmate" else "right"
    bgcolor = "#e0f7fa" if sender == "CASmate" else "#c8e6c9"
    sender_label = f"<b style='color:#006064'>CASmate:</b>" if sender == "CASmate" else f"<b style='color:#2e7d32'>Student:</b>"
    st.markdown(f"""
    <div style="
        background-color:{bgcolor};
        padding:10px 15px;
        border-radius:15px;
        margin:10px 0;
        max-width:80%;
        float:{align};
        clear:both;
        ">
        {sender_label} {message}
    </div>
    """, unsafe_allow_html=True)


for sender, msg in st.session_state.chat:

    chat_bubble(sender, msg)

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

    question = st.text_input("❓ Ask me anything about CAS")
    if question:
        st.session_state.chat.append(("Student", question))
        st.session_state.chat.append(("CASmate", "⚙️ CASmate is still in development and will soon be able to answer your queries better."))
        st.experimental_rerun()
else:
    st.info("👋 Please enter your name above to get started.")

st.markdown("""<hr style="margin-top:3rem;">
<p style='text-align:center; font-size:12px; color:gray; margin-top:1rem;'>
Developed by Dan del Prado &nbsp; • &nbsp; Northwestern University of Laoag
</p>""", unsafe_allow_html=True)
