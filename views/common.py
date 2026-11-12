import pandas as pd
import pydeck as pdk
import streamlit as st

from config import PRIORITY_COLORS, DEFAULT_LAT, DEFAULT_LON

STATUS_ICON = {"Pending": "🟡", "Assigned": "🔵", "In Progress": "🟠", "Collected": "🟢", "Rejected": "🔴"}


def status_badge(s):
    return f"{STATUS_ICON.get(s, '⚪')} {s}"


def report_map(df: pd.DataFrame, height=420):
    """Interactive map of reported waste locations (bonus feature)."""
    d = df.dropna(subset=["lat", "lon"]).copy()
    if d.empty:
        st.info("No geo-located reports to display yet.")
        return
    d["color"] = d["priority"].map(lambda p: PRIORITY_COLORS.get(p, [100, 100, 100]))
    layer = pdk.Layer("ScatterplotLayer", d, get_position="[lon, lat]", get_fill_color="color",
                      get_radius=90, radius_min_pixels=6, radius_max_pixels=18, pickable=True, opacity=0.85)
    view = pdk.ViewState(latitude=float(d["lat"].mean()) if len(d) else DEFAULT_LAT,
                         longitude=float(d["lon"].mean()) if len(d) else DEFAULT_LON, zoom=10.5)
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view,
                             tooltip={"html": "<b>#{id} {title}</b><br/>{category}<br/>Priority: {priority}<br/>Status: {status}<br/>{address}"}),
                    height=height)
    st.caption("🟢 Low  🟡 Medium  🟠 High  🔴 Critical")
