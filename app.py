import streamlit as st

import database as db
from views import auth_view, citizen, admin

st.set_page_config(page_title="Smart Waste Management", page_icon="♻️", layout="wide")
db.init_db()

if "user" not in st.session_state:
    st.session_state.user = None

user = st.session_state.user
if not user:
    auth_view.render()
    st.stop()

st.sidebar.markdown("## ♻️ Smart Waste")
st.sidebar.write(f"**{user['name']}**  \n`{user['role']}`")

if user["role"] == "admin":
    pages = {"🏛️ Dashboard": admin.dashboard, "🛠️ Manage Reports": admin.manage_reports,
             "👷 Teams": admin.teams_page, "📊 Statistics": admin.statistics}
else:
    pages = {"🏠 Home": lambda: citizen.home(user), "📢 Report Problem": lambda: citizen.report_problem(user),
             "📋 My Complaints": lambda: citizen.my_complaints(user)}

choice = st.sidebar.radio("Navigation", list(pages), label_visibility="collapsed")
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()
pages[choice]()
