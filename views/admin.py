import pandas as pd
import streamlit as st

import database as db
from config import CATEGORIES, PRIORITIES, STATUSES
from views.common import status_badge, report_map


def dashboard():
    st.title("🏛️ Admin Dashboard")
    st.caption("Real-time overview of citizen complaints")
    df = db.get_reports()
    teams = db.get_teams()
    total = len(df)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total reports", total)
    c2.metric("Pending", int((df.status == "Pending").sum()) if total else 0)
    c3.metric("In progress", int(df.status.isin(["Assigned", "In Progress"]).sum()) if total else 0)
    c4.metric("Collected", int((df.status == "Collected").sum()) if total else 0)
    c5.metric("Critical / High", int(df.priority.isin(["Critical", "High"]).sum()) if total else 0)

    left, right = st.columns([3, 2])
    with left:
        st.subheader("🗺️ Reported waste locations")
        report_map(df)
    with right:
        st.subheader("Reports by status")
        if total:
            st.bar_chart(df.status.value_counts().reindex(STATUSES, fill_value=0))
        st.subheader("Reports by priority")
        if total:
            st.bar_chart(df.priority.value_counts().reindex(PRIORITIES, fill_value=0))
    st.subheader("🆕 Latest reports")
    st.dataframe(df[["id", "title", "category", "priority", "status", "team", "created_at"]].head(8),
                 hide_index=True)
    if st.sidebar.button("Load demo data"):
        db.seed_demo(); st.rerun()


def manage_reports():
    st.title("🛠️ Manage Reports")
    with st.expander("🔍 Search & filters", expanded=True):
        c1, c2 = st.columns([2, 1])
        search = c1.text_input("Search (ID, title, address, citizen)")
        team_df = db.get_teams()
        team_map = {"All teams": None, **dict(zip(team_df["name"], team_df["id"]))}
        team_sel = c2.selectbox("Team", list(team_map))
        c3, c4, c5 = st.columns(3)
        status = c3.multiselect("Status", STATUSES)
        category = c4.multiselect("Category", CATEGORIES)
        priority = c5.multiselect("Priority", PRIORITIES)
        d1, d2 = st.columns(2)
        date_from = d1.date_input("From date", value=None)
        date_to = d2.date_input("To date", value=None)
    df = db.get_reports(search=search, status=status, category=category, priority=priority,
                        team_id=team_map[team_sel], date_from=date_from, date_to=date_to)
    st.caption(f"{len(df)} report(s) found")
    show = df[["id", "title", "category", "address", "priority", "status", "team", "citizen", "created_at"]]
    st.dataframe(show, hide_index=True)
    st.download_button("⬇️ Export CSV", show.to_csv(index=False).encode(), "reports.csv", "text/csv")
    if df.empty:
        return

    st.divider()
    st.subheader("Update collection status / assign team")
    rid = st.selectbox("Select report", df["id"].tolist(),
                       format_func=lambda i: f"#{i} · {df.loc[df.id == i, 'title'].iloc[0]}")
    r = df[df.id == rid].iloc[0]
    left, right = st.columns([3, 2])
    with left:
        st.markdown(f"**{r['title']}**  \n📍 {r['address']}  \n🗂️ {r['category']} · 👤 {r['citizen']} ({r['citizen_email']})")
        st.write(r["description"] or "_No description_")
        st.write(f"Current: {status_badge(r['status'])} · Priority **{r['priority']}**")
        st.dataframe(db.get_status_log(int(rid)), hide_index=True)
    with right:
        if r["has_photo"]:
            st.image(db.get_photo(int(rid)), caption="Waste-site photograph")
    with st.form("update"):
        c1, c2, c3 = st.columns(3)
        new_status = c1.selectbox("Status", STATUSES, index=STATUSES.index(r["status"]))
        new_prio = c2.selectbox("Priority", PRIORITIES, index=PRIORITIES.index(r["priority"]))
        names = ["— Unassigned —"] + team_df["name"].tolist()
        cur = names.index(r["team"]) if r["team"] in names else 0
        new_team = c3.selectbox("Assign collection team", names, index=cur)
        note = st.text_input("Note to citizen", value=r["admin_note"] or "")
        if st.form_submit_button("Save changes"):
            tid = None if new_team.startswith("—") else int(team_df.loc[team_df.name == new_team, "id"].iloc[0])
            final = db.update_report(int(rid), new_status, new_prio, tid, note)
            st.success(f"Report #{rid} updated (status: {final}).")
            st.rerun()


def teams_page():
    st.title("👷 Collection Teams")
    st.dataframe(db.get_teams(), hide_index=True)
    with st.form("team", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Team name")
        area = c2.text_input("Service area")
        members = c3.number_input("Members", 1, 50, 3)
        if st.form_submit_button("Add team"):
            if name.strip() and db.add_team(name, area, int(members)):
                st.success("Team added."); st.rerun()
            else:
                st.error("Enter a unique team name.")


def statistics():
    st.title("📊 Waste Collection Statistics")
    df = db.get_reports()
    if df.empty:
        st.info("No data yet. Use **Load demo data** on the dashboard sidebar to preview charts.")
        return
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["updated_at"] = pd.to_datetime(df["updated_at"])
    done = df[df.status == "Collected"].copy()
    done["hours"] = (done.updated_at - done.created_at).dt.total_seconds() / 3600
    c1, c2, c3 = st.columns(3)
    c1.metric("Collection rate", f"{len(done) / len(df) * 100:.0f}%")
    c2.metric("Avg. resolution time", f"{done.hours.mean():.1f} h" if len(done) else "—")
    c3.metric("Rejected", int((df.status == "Rejected").sum()))

    a, b = st.columns(2)
    with a:
        st.subheader("Complaints trend (monthly)")
        st.line_chart(df.set_index("created_at").resample("MS").size().rename("reports"))
    with b:
        st.subheader("Reports by category")
        st.bar_chart(df.category.value_counts())
    a, b = st.columns(2)
    with a:
        st.subheader("Collected per team")
        if len(done) and done.team.notna().any():
            st.bar_chart(done.team.value_counts())
        else:
            st.caption("No collections recorded yet.")
    with b:
        st.subheader("Status by priority")
        st.bar_chart(pd.crosstab(df.priority, df.status).reindex(PRIORITIES).fillna(0))
