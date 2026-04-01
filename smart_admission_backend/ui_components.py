"""
ui_components.py
─────────────────────────────────────────────────────────────────────────────
All Streamlit UI rendering functions for Smart Admission Architect.
Each function is self-contained and takes DataFrames/engine as input.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


# ── Colour helpers ────────────────────────────────────────────────────────────

TIER_COLOURS = {
    "safe":   {"bg": "#d1fae5", "text": "#065f46", "dot": "#10b981", "label": "✅ Safe bet"},
    "target": {"bg": "#fef3c7", "text": "#92400e", "dot": "#f59e0b", "label": "🎯 Target"},
    "reach":  {"bg": "#fee2e2", "text": "#991b1b", "dot": "#ef4444", "label": "🚀 Reach"},
}

CHART_PALETTE = ["#2563eb", "#ef4444", "#10b981", "#f59e0b"]


# ── Header ────────────────────────────────────────────────────────────────────

def render_header():
    st.markdown(
        """
        <div class="hero-header">
            <div class="hero-title">Smart Admission <span class="brand">Architect</span></div>
            <div class="hero-sub">MHT-CET 2026 · Data-driven college predictor for Maharashtra</div>
            <span class="hero-badge">🟢 CAP Round 2026</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Input Panel ───────────────────────────────────────────────────────────────

def render_input_panel(engine):
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        percentile = st.number_input(
            "Your Percentile",
            min_value=0.0,
            max_value=100.0,
            value=94.5,
            step=0.01,
            format="%.2f",
            help="Enter your MHT-CET 2026 percentile",
        )
    with col2:
        category = st.selectbox(
            "Category",
            options=engine.available_categories(),
            index=0,
            help="Your reservation category",
        )
    with col3:
        branch = st.selectbox(
            "Dream Branch",
            options=engine.available_branches(),
            index=0,
            help="Choose your preferred engineering branch",
        )

    return percentile, category, branch


# ── Sidebar Filters ───────────────────────────────────────────────────────────

def render_sidebar_filters(results_df: pd.DataFrame):
    st.sidebar.markdown("## 🔍 Filters")

    tier_filter = st.sidebar.radio(
        "Tier",
        options=["All", "Safe", "Target", "Reach"],
        index=0,
    )

    locations = ["All"] + sorted(results_df["location"].dropna().unique().tolist())
    location_filter = st.sidebar.selectbox("Location", options=locations, index=0)

    auto_filter = st.sidebar.checkbox("Autonomous colleges only", value=False)

    st.sidebar.divider()
    st.sidebar.markdown("### 📊 About this tool")
    st.sidebar.info(
        "Predictions use 3-year cutoff trend analysis (2023–2025) "
        "and linear extrapolation to estimate 2026 cutoffs. "
        "ROI = Avg Package ÷ Annual Fee."
    )

    return tier_filter, location_filter, auto_filter


# ── Metrics ───────────────────────────────────────────────────────────────────

def render_metrics(results_df: pd.DataFrame):
    total  = len(results_df)
    safe   = len(results_df[results_df["tier"] == "safe"])
    target = len(results_df[results_df["tier"] == "target"])
    reach  = len(results_df[results_df["tier"] == "reach"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🎓 Colleges matched", total,  help="Total colleges matching your branch & category")
    c2.metric("✅ Safe bets",         safe,   help="Chance > 75%")
    c3.metric("🎯 On the edge",       target, help="Chance between 40–75%")
    c4.metric("🚀 Reach / Dream",     reach,  help="Chance < 40%")


# ── College Cards ─────────────────────────────────────────────────────────────

def render_college_cards(df: pd.DataFrame):
    if df.empty:
        st.warning("No colleges match the current filters.")
        return

    # Display as a styled dataframe for interaction
    display_cols = {
        "short_name":       "College",
        "location":         "Location",
        "chance":           "Chance %",
        "tier":             "Tier",
        "predicted_2026":   "Predicted Cutoff 2026",
        "annual_shift":     "Annual Shift",
        "avg_package_lpa":  "Avg Pkg (LPA)",
        "annual_fee":       "Annual Fee (₹)",
        "roi_score":        "ROI",
        "naac_grade":       "NAAC",
    }

    display_df = df[list(display_cols.keys())].copy()
    display_df.rename(columns=display_cols, inplace=True)
    display_df["Annual Fee (₹)"] = display_df["Annual Fee (₹)"].apply(
        lambda x: f"₹{int(x):,}" if pd.notna(x) else "—"
    )
    display_df["Predicted Cutoff 2026"] = display_df["Predicted Cutoff 2026"].apply(
        lambda x: f"{x:.2f}%" if pd.notna(x) else "—"
    )
    display_df["Annual Shift"] = display_df["Annual Shift"].apply(
        lambda x: f"+{x:.2f}" if x > 0 else f"{x:.2f}" if pd.notna(x) else "—"
    )
    display_df["Avg Pkg (LPA)"] = display_df["Avg Pkg (LPA)"].apply(
        lambda x: f"{x:.1f}" if pd.notna(x) else "—"
    )

    # Colour map rows by tier
    def row_style(row):
        tier = row["Tier"]
        cfg = TIER_COLOURS.get(tier, {})
        bg = cfg.get("bg", "")
        color = cfg.get("text", "")
        return [f"background-color: {bg}; color: {color}"] * len(row)

    styled = display_df.style.apply(row_style, axis=1).format({"Chance %": "{:.0f}%", "ROI": "{:.1f}x"})
    st.dataframe(styled, use_container_width=True, hide_index=True, height=420)

    # Expandable detail cards below the table
    st.markdown("##### Detailed cards")
    for _, row in df.iterrows():
        tier = row.get("tier", "safe")
        cfg  = TIER_COLOURS.get(tier, TIER_COLOURS["safe"])

        with st.expander(f"{cfg['label']}  {row['short_name']}  —  {row['chance']}% chance"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Predicted Cutoff 2026", f"{row['predicted_2026']:.2f}%ile")
            c2.metric("Annual Shift",          f"{row['annual_shift']:+.2f}%/yr")
            c3.metric("Avg Package",           f"{row['avg_package_lpa']:.1f} LPA" if pd.notna(row.get('avg_package_lpa')) else "—")
            c4.metric("ROI Score",             f"{row['roi_score']:.1f}x")

            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Annual Fee",   f"₹{int(row['annual_fee']):,}" if pd.notna(row.get('annual_fee')) else "—")
            c6.metric("4-yr Total",   f"₹{int(row['total_4yr_fee']):,}" if pd.notna(row.get('total_4yr_fee')) else "—")
            c7.metric("Placement %",  f"{row['placement_pct']:.0f}%" if pd.notna(row.get('placement_pct')) else "—")
            c8.metric("NAAC Grade",   row.get("naac_grade", "—"))

            recruiters = row.get("top_recruiters", [])
            if isinstance(recruiters, list) and recruiters:
                st.markdown("**Top Recruiters:** " + " · ".join(recruiters))

            scholarship = row.get("scholarship_available", False)
            autonomous  = row.get("autonomous", False)
            tags = []
            if scholarship:  tags.append("🎓 Scholarship available")
            if autonomous:   tags.append("🏛 Autonomous")
            if tags:
                st.markdown(" &nbsp; ".join(tags), unsafe_allow_html=True)


# ── ROI Chart ─────────────────────────────────────────────────────────────────

def render_roi_chart(results_df: pd.DataFrame):
    if results_df.empty or "roi_score" not in results_df.columns:
        st.info("No ROI data available.")
        return

    top = results_df.nlargest(8, "roi_score")[["short_name", "roi_score"]].dropna()

    fig = go.Figure(go.Bar(
        x=top["roi_score"],
        y=top["short_name"],
        orientation="h",
        marker=dict(
            color=top["roi_score"],
            colorscale=[[0, "#93c5fd"], [1, "#1d4ed8"]],
            showscale=False,
        ),
        text=top["roi_score"].apply(lambda x: f"{x:.1f}x"),
        textposition="outside",
    ))
    fig.update_layout(
        margin=dict(l=0, r=40, t=10, b=10),
        height=280,
        xaxis=dict(showgrid=False, visible=False),
        yaxis=dict(autorange="reversed", tickfont=dict(size=11)),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Trend Chart ───────────────────────────────────────────────────────────────

def render_trend_chart(engine, selected_colleges: list):
    if not selected_colleges:
        st.info("Select at least one college above.")
        return

    fig = go.Figure()
    years = [2023, 2024, 2025]

    for i, college_name in enumerate(selected_colleges):
        series = engine.get_trend_series(college_name, category="OPEN")
        if series.empty:
            continue
        color = CHART_PALETTE[i % len(CHART_PALETTE)]
        fig.add_trace(go.Scatter(
            x=series.index.tolist(),
            y=series.values.tolist(),
            mode="lines+markers",
            name=college_name,
            line=dict(color=color, width=2),
            marker=dict(size=6, color=color),
        ))

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=10),
        height=220,
        xaxis=dict(
            tickvals=years,
            ticktext=[str(y) for y in years],
            showgrid=False,
        ),
        yaxis=dict(
            title="Percentile",
            ticksuffix="%",
            showgrid=True,
            gridcolor="#f1f5f9",
        ),
        legend=dict(font=dict(size=10), orientation="h", yanchor="bottom", y=1.02),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Compare Matrix ────────────────────────────────────────────────────────────

def render_compare_matrix(results_df: pd.DataFrame, name_a: str, name_b: str):
    row_a = results_df[results_df["short_name"] == name_a].iloc[0]
    row_b = results_df[results_df["short_name"] == name_b].iloc[0]

    fields = [
        ("Predicted Cutoff 2026",  lambda r: f"{r['predicted_2026']:.2f}%ile"),
        ("Annual Shift",           lambda r: f"{r['annual_shift']:+.2f}%/yr"),
        ("Admission Chance",       lambda r: f"{r['chance']}%"),
        ("Tier",                   lambda r: TIER_COLOURS[r['tier']]['label']),
        ("Avg Package",            lambda r: f"{r['avg_package_lpa']:.1f} LPA" if pd.notna(r.get('avg_package_lpa')) else "—"),
        ("Highest Package",        lambda r: f"{r['highest_package_lpa']:.1f} LPA" if pd.notna(r.get('highest_package_lpa')) else "—"),
        ("Placement %",            lambda r: f"{r['placement_pct']:.0f}%" if pd.notna(r.get('placement_pct')) else "—"),
        ("Annual Fee",             lambda r: f"₹{int(r['annual_fee']):,}" if pd.notna(r.get('annual_fee')) else "—"),
        ("Total 4-yr Fee",         lambda r: f"₹{int(r['total_4yr_fee']):,}" if pd.notna(r.get('total_4yr_fee')) else "—"),
        ("ROI Score",              lambda r: f"{r['roi_score']:.1f}x"),
        ("Location",               lambda r: str(r.get('location', '—'))),
        ("NAAC Grade",             lambda r: str(r.get('naac_grade', '—'))),
        ("Autonomous",             lambda r: "Yes" if r.get('autonomous') else "No"),
        ("Scholarship",            lambda r: "Yes" if r.get('scholarship_available') else "No"),
    ]

    rows = []
    for label, fn in fields:
        val_a = fn(row_a)
        val_b = fn(row_b)
        rows.append({"Metric": label, name_a: val_a, name_b: val_b})

    compare_df = pd.DataFrame(rows)

    def highlight_better(row):
        """Highlight numerically better values in green."""
        styles = [""] * len(row)
        return styles

    st.dataframe(compare_df, use_container_width=True, hide_index=True)

    # Visual: fees vs package bar chart
    st.markdown("##### Fees vs Avg Package")
    fig = go.Figure()
    colleges = [name_a, name_b]
    fees = [row_a.get("annual_fee", 0) / 100_000, row_b.get("annual_fee", 0) / 100_000]
    pkgs = [row_a.get("avg_package_lpa", 0), row_b.get("avg_package_lpa", 0)]

    fig.add_trace(go.Bar(name="Annual Fee (Lakhs)", x=colleges, y=fees,
                         marker_color="#93c5fd", text=[f"₹{v:.1f}L" for v in fees], textposition="outside"))
    fig.add_trace(go.Bar(name="Avg Package (LPA)",  x=colleges, y=pkgs,
                         marker_color="#2563eb",    text=[f"{v:.1f} LPA" for v in pkgs], textposition="outside"))

    fig.update_layout(
        barmode="group",
        margin=dict(l=0, r=0, t=10, b=10),
        height=260,
        yaxis=dict(title="Lakhs", showgrid=True, gridcolor="#f1f5f9"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
