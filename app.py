import streamlit as st
import requests

st.set_page_config(page_title="CASmate - CAS Chatbot", layout="centered")

st.title("CASmate - Northwestern University CAS Chatbot")

if "name" not in st.session_state:
    st.session_state.name = ""

if st.session_state.name == "":
    name = st.text_input("👋 What's your name?")
    if name:
        st.session_state.name = name
else:
    st.markdown(f"**Name:** {st.session_state.name} _(locked)_")

if st.session_state.name:
    st.markdown(f"### Hello, {st.session_state.name}! Welcome to the College of Arts and Sciences.")
    try:
        response = requests.get("https://uselessfacts.jsph.pl/random.json?language=en", timeout=3)
        if response.status_code == 200:
            fact = response.json().get("text", "Here's a fun fact for you!")
        else:
            fact = "Here's a fun fact for you!"
    except Exception:
        fact = "Here's a fun fact for you!"
    st.markdown(f"💡 **Did you know?** _{fact}_")
    st.markdown("---")

    # Question input from user
    question = st.text_input("❓ Feel free to ask me anything about CAS or freshmen life")
    if question:
        st.write(f"Thank you for your question: _{question}_")
        st.info("⚙️ CASmate is currently under development and will soon be able to answer your queries better.")
else:
    st.info("👋 Please enter your name above to get started.")

st.markdown("""<hr style="margin-top:3rem;">
<p style='text-align:center; font-size:12px; color:gray; margin-top:1rem;'>
Developed by Dan del Prado &nbsp; • &nbsp; Northwestern University of Laoag
</p>""", unsafe_allow_html=True)

