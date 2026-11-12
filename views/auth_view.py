import re
import streamlit as st
import database as db


def render():
    st.markdown("## ♻️ Smart Waste Management System")
    st.caption("Report waste problems in your area. Municipal teams track and resolve them.")
    t_login, t_reg = st.tabs(["🔐 Login", "📝 Citizen Registration"])

    with t_login:
        with st.form("login"):
            email = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                user = db.authenticate(email, pw)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
        st.info("Admin demo login: **admin@city.gov** / **admin123**")

    with t_reg:
        with st.form("register"):
            name = st.text_input("Full name")
            email = st.text_input("Email address", key="reg_email")
            phone = st.text_input("Phone number")
            pw = st.text_input("Password (min 6 characters)", type="password", key="reg_pw")
            pw2 = st.text_input("Confirm password", type="password")
            if st.form_submit_button("Create account"):
                if not (name.strip() and email.strip() and pw):
                    st.error("Name, email and password are required.")
                elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()):
                    st.error("Enter a valid email address.")
                elif len(pw) < 6:
                    st.error("Password must be at least 6 characters.")
                elif pw != pw2:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = db.create_user(name, email, phone, pw)
                    (st.success if ok else st.error)(msg)
