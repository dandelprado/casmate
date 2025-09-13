import streamlit as st
import requests
import random

st.title("CASmate - CAS Chatbot")

name = st.text.input("What's your name?")

if name:
    st.write(f"Hello, {name}! Welcome to the College of Arts and Sciences.")

    try:
        response = requests.get("https://uselessfacts.jsph.pl/random.json?language=en")
        if response.status_code == 200:
            data = response.json()
            fact = data.get("text", "Here's a fun fact for you!")
        else:
            fact = "Here's a fun fact for you!"
    except Exception:
        fact = "Here's a fun fact for you!"

    st.markdown(f"**Did you know?** {fact}")

    question = st.text_input("Feel free to ask me anything about CAS")

    if question:
        st.write(f"Thanks for your question: _{question}_")
        st.info("CASmate is still in development.")
else:
    st.write("Please enter your name to continue.")
