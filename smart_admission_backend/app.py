import streamlit as st
import pandas as pd
from engine import PredictionEngine
from ui_components import (
    render_header,
    render_input_panel,
    render_metrics,
    render_college_cards,
    render_roi_chart,
    render_trend_chart,
    render_compare_matrix,
    render_sidebar_filters,
)

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Smart Admission Architect",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load CSS ─────────────────────────────────────────────────────────────────
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Init Engine ───────────────────────────────────────────────────────────────
@st.cache_resource
def load_engine():
    return PredictionEngine("data.json")

engine = load_engine()

# ── Header ────────────────────────────────────────────────────────────────────
render_header()

# ── Input Panel ───────────────────────────────────────────────────────────────
percentile, category, branch = render_input_panel(engine)

# ── Run Prediction ────────────────────────────────────────────────────────────
results_df = engine.predict(percentile, category, branch)

# ── Sidebar Filters ───────────────────────────────────────────────────────────
tier_filter, location_filter, auto_filter = render_sidebar_filters(results_df)

# Apply filters
filtered_df = results_df.copy()
if tier_filter != "All":
    filtered_df = filtered_df[filtered_df["tier"].str.title() == tier_filter]
if location_filter != "All":
    filtered_df = filtered_df[filtered_df["location"] == location_filter]
if auto_filter:
    filtered_df = filtered_df[filtered_df["autonomous"] == True]

# ── Metrics Row ───────────────────────────────────────────────────────────────
render_metrics(results_df)

st.divider()

# ── Main Layout ───────────────────────────────────────────────────────────────
col_left, col_right = st.columns([2, 1], gap="large")

with col_left:
    st.markdown("#### 🏫 College Results")
    st.caption(f"Showing {len(filtered_df)} colleges · Click a row in the table to compare")
    render_college_cards(filtered_df)

with col_right:
    st.markdown("#### 📈 ROI Score")
    render_roi_chart(results_df)

    st.markdown("#### 📉 Cutoff Trend (2023–2025)")
    selected_colleges = st.multiselect(
        "Select colleges to plot",
        options=results_df["short_name"].tolist(),
        default=results_df["short_name"].tolist()[:2],
        max_selections=4,
        label_visibility="collapsed",
    )
    render_trend_chart(engine, selected_colleges)

st.divider()

# ── Compare Matrix ────────────────────────────────────────────────────────────
st.markdown("#### ⚖️ Side-by-side Comparison")
compare_options = results_df["short_name"].tolist()
col_a, col_b = st.columns(2)
with col_a:
    college_a = st.selectbox("College A", compare_options, index=0)
with col_b:
    college_b = st.selectbox("College B", compare_options, index=min(1, len(compare_options) - 1))

if college_a != college_b:
    render_compare_matrix(results_df, college_a, college_b)
else:
    st.info("Select two different colleges to compare.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='text-align:center; color:#94a3b8; font-size:12px; margin-top:2rem;'>"
    "Smart Admission Architect · Dummy data for demo · MHT-CET 2026"
    "</div>",
    unsafe_allow_html=True,
)
