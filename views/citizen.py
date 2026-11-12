import streamlit as st
import database as db
from classifier import classify_priority
from config import CATEGORIES, PRIORITIES, STATUSES, DEFAULT_LAT, DEFAULT_LON
from views.common import status_badge, report_map


def home(user):
    st.title(f"👋 Welcome, {user['name']}")
    df = db.get_reports(user_id=user["id"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("My reports", len(df))
    c2.metric("Pending", int((df.status == "Pending").sum()) if len(df) else 0)
    c3.metric("In progress", int(df.status.isin(["Assigned", "In Progress"]).sum()) if len(df) else 0)
    c4.metric("Collected", int((df.status == "Collected").sum()) if len(df) else 0)
    st.subheader("Your reports on the map")
    report_map(df, height=360)


def report_problem(user):
    st.title("📢 Report a Waste Problem")

    # --- click-to-pick location on the map (outside the form so clicks work) ---
    st.session_state.setdefault("rep_lat", DEFAULT_LAT)
    st.session_state.setdefault("rep_lon", DEFAULT_LON)
    st.markdown("**📍 Pick the waste location on the map** (click on the map, or type coordinates below)")
    try:
        import folium
        from streamlit_folium import st_folium
        m = folium.Map(location=[st.session_state.rep_lat, st.session_state.rep_lon], zoom_start=14)
        folium.Marker([st.session_state.rep_lat, st.session_state.rep_lon], tooltip="Selected location",
                      icon=folium.Icon(color="green", icon="trash", prefix="fa")).add_to(m)
        out = st_folium(m, height=320, use_container_width=True, returned_objects=["last_clicked"], key="pick_map")
        click = out.get("last_clicked") if out else None
        if click and click != st.session_state.get("last_click"):
            st.session_state.last_click = click
            st.session_state.rep_lat, st.session_state.rep_lon = click["lat"], click["lng"]
            st.rerun()
    except ImportError:
        st.warning("Install `streamlit-folium` to enable click-to-pick map.")

    with st.form("report", clear_on_submit=True):
        title = st.text_input("Problem title *", placeholder="e.g. Bin overflowing near market")
        category = st.selectbox("Waste category *", CATEGORIES)
        description = st.text_area("Describe the problem", height=120)
        address = st.text_input("Location / address *", placeholder="House, road, area")
        c1, c2 = st.columns(2)
        lat = c1.number_input("Latitude", value=float(st.session_state.rep_lat), format="%.5f")
        lon = c2.number_input("Longitude", value=float(st.session_state.rep_lon), format="%.5f")
        photo = st.file_uploader("Upload waste-site photograph", type=["jpg", "jpeg", "png"])
        prio_choice = st.selectbox("Priority", ["Auto-detect (recommended)"] + PRIORITIES)
        submitted = st.form_submit_button("Submit report")

    if submitted:
        if not (title.strip() and address.strip()):
            st.error("Title and location/address are required.")
            return
        auto, score, reason = classify_priority(title, description, category)
        priority = auto if prio_choice.startswith("Auto") else prio_choice
        data = photo.getvalue() if photo else None
        rid = db.add_report(user["id"], title.strip(), description.strip(), category, address.strip(),
                            lat, lon, priority, data, photo.name if photo else None)
        st.success(f"Report #{rid} submitted with **{priority}** priority.")
        if prio_choice.startswith("Auto"):
            st.caption(f"🤖 Priority auto-classified from {reason} (score {score}).")


def my_complaints(user):
    st.title("📋 My Complaints")
    c1, c2, c3 = st.columns([2, 1, 1])
    search = c1.text_input("🔍 Search", placeholder="title, address, report ID")
    status = c2.multiselect("Status", STATUSES)
    category = c3.multiselect("Category", CATEGORIES)
    df = db.get_reports(user_id=user["id"], search=search, status=status, category=category)
    st.caption(f"{len(df)} report(s)")
    if df.empty:
        st.info("No complaints found.")
        return
    for _, r in df.iterrows():
        with st.expander(f"#{r['id']} · {r['title']} — {status_badge(r['status'])} · {r['priority']}"):
            st.write(f"**Category:** {r['category']}  \n**Address:** {r['address']}  \n**Submitted:** {r['created_at']}")
            if r["description"]:
                st.write(r["description"])
            if r["team"]:
                st.write(f"**Assigned team:** {r['team']}")
            if r["admin_note"]:
                st.info(f"Admin note: {r['admin_note']}")
            if r["has_photo"]:
                st.image(db.get_photo(int(r["id"])), width=320)
            st.dataframe(db.get_status_log(int(r["id"])), hide_index=True)
