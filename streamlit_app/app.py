"""
⚡ ElectricAI — Electricity Cost Intelligence Platform (Streamlit MVP)

AI-powered electricity bill analysis, sensitivity simulation,
geographic comparison, and forecasting for NJ PSE&G customers.

IMPORTANT: Core analytics logic is imported from shared.bill_analytics
           (the single source of truth — also used by the FastAPI backend).
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# ── path setup so shared/ and data_pipeline/ are importable ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_loader import load_or_generate_data

# ── Shared analytics (SINGLE SOURCE OF TRUTH) ──
from shared.bill_analytics import (
    compute_contributions, contributions_to_df,
    run_sensitivity, sensitivity_to_df, sensitivity_summary,
    simulate_bill, generate_insights, classify_components,
    COMPONENT_REGISTRY, get_component_meta,
    compute_historical_contributions,
)
from shared.geo_analytics import (
    zip_to_county, estimate_county_bill, get_all_county_estimates,
    build_choropleth_data, load_nj_geojson, NJ_COUNTY_FIPS,
)

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="ElectricAI — Electricity Cost Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
.stApp { font-family: 'Inter', sans-serif; }
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3,
section[data-testid="stSidebar"] label {
    color: #e2e8f0 !important;
}
.kpi-card {
    background: linear-gradient(135deg, #1e293b, #334155);
    border: 1px solid #475569; border-radius: 16px;
    padding: 20px 24px; text-align: center;
    transition: transform 0.2s, box-shadow 0.2s;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(59,130,246,0.15);
}
.kpi-icon { font-size: 28px; margin-bottom: 6px; }
.kpi-label { color: #94a3b8; font-size: 13px; font-weight: 500;
             text-transform: uppercase; letter-spacing: 0.5px; }
.kpi-value { color: #f1f5f9; font-size: 28px; font-weight: 700; margin: 4px 0; }
.kpi-sub { color: #64748b; font-size: 12px; }
.insight-box {
    background: linear-gradient(135deg, #0f172a, #1e293b);
    border-left: 4px solid #3b82f6; border-radius: 0 12px 12px 0;
    padding: 16px 20px; margin: 8px 0; color: #e2e8f0;
    font-size: 15px; line-height: 1.6;
}
.section-header {
    background: linear-gradient(90deg, #3b82f6, #8b5cf6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-size: 32px; font-weight: 800; margin-bottom: 4px;
}
.section-sub { color: #94a3b8; font-size: 15px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data():
    return load_or_generate_data()

billing, benchmark, plans = load_data()

# ─────────────────────────────────────────────
# PLOTLY THEME
# ─────────────────────────────────────────────
PL = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(15,23,42,0.0)",
    plot_bgcolor="rgba(15,23,42,0.4)",
    font=dict(family="Inter, sans-serif", color="#e2e8f0"),
    margin=dict(l=40, r=20, t=40, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)
COLORS = ["#3b82f6","#8b5cf6","#06b6d4","#10b981","#f59e0b",
          "#ef4444","#ec4899","#6366f1","#14b8a6","#f97316"]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def kpi(icon, label, value, sub=""):
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>{sub_html}
    </div>""", unsafe_allow_html=True)

def insight_box(text):
    st.markdown(f'<div class="insight-box">{text}</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("# ⚡ ElectricAI")
    st.markdown("**Electricity Cost Intelligence**")
    st.markdown("---")
    page = st.radio("Navigate", [
        "📊 Bill Analysis",
        "🎛️ Sensitivity Simulator",
        "🔮 Forecast",
        "🗺️ NJ Geo Map",
        "💡 Plan Comparison",
    ], label_visibility="collapsed")
    st.markdown("---")
    uploaded = st.file_uploader("Upload CSV (optional)", type=["csv"])
    if uploaded:
        try:
            user_df = pd.read_csv(uploaded)
            user_df["date"] = pd.to_datetime(user_df["date"])
            if "total_bill" in user_df.columns:
                billing = user_df
                st.success(f"✅ Loaded {len(billing)} rows")
        except Exception as e:
            st.error(f"Error: {e}")
    st.markdown("---")
    st.caption(f"📅 {billing['date'].min().strftime('%b %Y')} — {billing['date'].max().strftime('%b %Y')}")
    st.caption(f"📊 {len(billing)} monthly records · PSE&G (NJ)")


# ═══════════════════════════════════════════════════════
# PAGE 1: BILL ANALYSIS  (contribution + classification)
# ═══════════════════════════════════════════════════════
if page == "📊 Bill Analysis":
    st.markdown('<div class="section-header">Bill Component Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Quantify each component\'s contribution to your total bill</div>', unsafe_allow_html=True)

    # Month selector
    month_idx = st.slider("Select month (0 = latest)", 0, len(billing)-1, 0, format="-%d")
    actual_idx = -(month_idx + 1)
    row = billing.iloc[actual_idx]
    contribs = compute_contributions(row)
    insights = generate_insights(contribs, bill_row=row)

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("💰", "Total Bill", f"${row['total_bill']:.2f}")
    with c2: kpi("⚡", "Usage", f"{row['usage_kwh']:.0f} kWh")
    with c3: kpi("📊", "Eff. Rate", f"${row['total_bill']/max(row['usage_kwh'],1):.4f}/kWh")
    date_str = row['date'].strftime('%b %Y') if hasattr(row['date'], 'strftime') else str(row['date'])
    with c4: kpi("📅", "Bill Date", date_str)

    st.markdown("")
    for ins in insights[:3]:
        insight_box(ins)

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🍩 Component Breakdown")
        pos = [c for c in contribs if c.value > 0]
        fig = go.Figure(go.Pie(
            labels=[c.label for c in pos],
            values=[c.value for c in pos],
            hole=0.45,
            marker=dict(colors=COLORS[:len(pos)]),
            textinfo="label+percent", textfont=dict(size=11),
        ))
        fig.update_layout(**PL, height=420, title=f"Bill Composition — {date_str}")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 📊 Contribution Bar Chart")
        contrib_df = contributions_to_df(contribs)
        fig2 = go.Figure(go.Bar(
            y=contrib_df["Component"], x=contrib_df["Amount ($)"],
            orientation="h",
            marker_color=[COLORS[i % len(COLORS)] for i in range(len(contrib_df))],
            text=contrib_df["Amount ($)"].apply(lambda v: f"${v:.2f}"),
            textposition="outside",
        ))
        fig2.update_layout(**PL, height=420, title="Component Values",
                           xaxis_title="Amount ($)", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig2, use_container_width=True)

    # Classification table
    st.markdown("### 🏷️ Component Classification")
    groups = classify_components()
    c1, c2, c3 = st.columns(3)
    for col_ui, (cat, items) in zip([c1, c2, c3], groups.items()):
        with col_ui:
            st.markdown(f"**{cat.replace('_',' ').title()}**")
            for item in items:
                st.markdown(f"- **{item['label']}** — _{item['driver']}_")

    # Data table
    with st.expander("📋 Full Contribution Table"):
        st.dataframe(contrib_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════
# PAGE 2: SENSITIVITY SIMULATOR
# ═══════════════════════════════════════════════════════
elif page == "🎛️ Sensitivity Simulator":
    st.markdown('<div class="section-header">Sensitivity Simulator</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">See how changing each component affects your total bill</div>', unsafe_allow_html=True)

    row = billing.iloc[-1]
    base_total = float(row["total_bill"])

    tab1, tab2 = st.tabs(["📈 Auto Sensitivity", "🎛️ Interactive Sliders"])

    # ── TAB 1: Auto sensitivity ──
    with tab1:
        pct = st.slider("Percentage change to simulate", 1, 30, 10, 1)

        results = run_sensitivity(row, pct_changes=[-pct, pct])
        contribs = compute_contributions(row)
        insights = generate_insights(contribs, results, row)

        for ins in insights:
            insight_box(ins)

        # Summary table
        summary = sensitivity_summary(results, pct=float(pct))
        st.markdown(f"### Impact of +{pct}% Change Per Component")
        st.dataframe(summary, use_container_width=True, hide_index=True)

        # Tornado chart
        up = [r for r in results if r.pct_change == pct]
        down = [r for r in results if r.pct_change == -pct]
        up.sort(key=lambda r: abs(r.total_delta))
        down.sort(key=lambda r: abs(r.total_delta))

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=[r.label for r in up],
            x=[r.total_delta for r in up],
            orientation="h", name=f"+{pct}%",
            marker_color="#ef4444",
        ))
        fig.add_trace(go.Bar(
            y=[r.label for r in down],
            x=[r.total_delta for r in down],
            orientation="h", name=f"-{pct}%",
            marker_color="#10b981",
        ))
        fig.update_layout(**PL, barmode="overlay", height=450,
                          title="Tornado Chart — Bill Impact ($)",
                          xaxis_title="Change in Total Bill ($)")
        st.plotly_chart(fig, use_container_width=True)

        # Elasticity chart
        st.markdown("### 📐 Elasticity (% bill change / % component change)")
        elast_data = [{"Component": r.label, "Elasticity": r.elasticity}
                      for r in up if r.elasticity > 0]
        elast_df = pd.DataFrame(elast_data).sort_values("Elasticity", ascending=False)
        fig_e = go.Figure(go.Bar(
            x=elast_df["Component"], y=elast_df["Elasticity"],
            marker_color="#8b5cf6",
            text=elast_df["Elasticity"].apply(lambda v: f"{v:.3f}"),
            textposition="outside",
        ))
        fig_e.update_layout(**PL, height=380, title="Component Elasticity",
                            yaxis_title="Elasticity")
        st.plotly_chart(fig_e, use_container_width=True)

    # ── TAB 2: Interactive sliders ──
    with tab2:
        st.markdown("### Adjust component values to see real-time bill impact")
        st.markdown(f"**Base total: ${base_total:.2f}**")

        overrides = {}
        slider_cols = st.columns(2)
        for i, meta in enumerate(COMPONENT_REGISTRY):
            base_val = float(row.get(meta.key, 0))
            if base_val == 0:
                continue
            with slider_cols[i % 2]:
                new_val = st.slider(
                    f"{meta.label} (${base_val:.2f})",
                    min_value=round(base_val * 0.5, 2),
                    max_value=round(base_val * 1.5, 2),
                    value=round(base_val, 2),
                    step=0.5,
                    key=f"slider_{meta.key}",
                )
                if abs(new_val - base_val) > 0.01:
                    overrides[meta.key] = new_val

        sim = simulate_bill(row, overrides=overrides if overrides else None)

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1: kpi("💰", "New Total", f"${sim['total']:.2f}")
        with c2:
            delta_color = "🔴" if sim["delta"] > 0 else "🟢" if sim["delta"] < 0 else "⚪"
            kpi(delta_color, "Change", f"${sim['delta']:+.2f}", f"{sim['delta_pct']:+.1f}%")
        with c3: kpi("📊", "Base Total", f"${sim['base_total']:.2f}")

        # Updated breakdown
        sim_comps = sim["components"]
        fig_sim = go.Figure(go.Bar(
            x=list(sim_comps.values()),
            y=list(sim_comps.keys()),
            orientation="h",
            marker_color=COLORS[:len(sim_comps)],
            text=[f"${v:.2f}" for v in sim_comps.values()],
            textposition="outside",
        ))
        fig_sim.update_layout(**PL, height=400, title="Simulated Bill Breakdown",
                              xaxis_title="Amount ($)", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_sim, use_container_width=True)


# ═══════════════════════════════════════════════════════
# PAGE 3: FORECAST
# ═══════════════════════════════════════════════════════
elif page == "🔮 Forecast":
    st.markdown('<div class="section-header">Cost Forecast</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">SARIMA-based predictions with 95% confidence intervals</div>', unsafe_allow_html=True)

    horizon = st.selectbox("Forecast Horizon", [6, 12, 18, 24], index=1)
    run_btn = st.button("🚀 Run Forecast", type="primary")

    if run_btn or "fc" in st.session_state:
        if run_btn:
            with st.spinner("Training SARIMA model..."):
                from analytics import run_forecast as _run_forecast
                fc_df, metrics, hist, fc_insight = _run_forecast(billing, horizon)
            st.session_state["fc"] = (fc_df, metrics, hist, fc_insight)

        fc_df, metrics, hist, fc_insight = st.session_state["fc"]
        insight_box(fc_insight)

        mc = st.columns(4)
        for i, (k, v) in enumerate(metrics.items()):
            mc[i].metric(k, v)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist.index, y=hist.values,
                                 mode="lines+markers", name="Historical",
                                 line=dict(color="#3b82f6", width=2), marker=dict(size=3)))
        fig.add_trace(go.Scatter(x=fc_df["date"], y=fc_df["forecast"],
                                 mode="lines+markers", name="Forecast",
                                 line=dict(color="#8b5cf6", width=3), marker=dict(size=5)))
        fig.add_trace(go.Scatter(
            x=pd.concat([fc_df["date"], fc_df["date"][::-1]]),
            y=pd.concat([fc_df["upper_95"], fc_df["lower_95"][::-1]]),
            fill="toself", fillcolor="rgba(139,92,246,0.15)",
            line=dict(color="rgba(0,0,0,0)"), name="95% CI",
        ))
        fig.update_layout(**PL, height=500, title="Historical vs Forecast",
                          xaxis_title="Date", yaxis_title="Total Bill ($)")
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════
# PAGE 4: NJ GEO MAP
# ═══════════════════════════════════════════════════════
elif page == "🗺️ NJ Geo Map":
    st.markdown('<div class="section-header">NJ Geographic Comparison</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">County-level bill estimates across New Jersey</div>', unsafe_allow_html=True)

    base_bill = float(billing.iloc[-1]["total_bill"])

    # ZIP lookup
    col1, col2 = st.columns([1, 2])
    with col1:
        zip_input = st.text_input("Enter NJ ZIP Code", "07102", max_chars=5)
        county = zip_to_county(zip_input)
        if county:
            est = estimate_county_bill(base_bill, county)
            st.success(f"📍 **{county} County**")
            kpi("🏠", "Estimated Bill", f"${est['estimated_bill']:.2f}",
                f"{'↑' if est['difference']>0 else '↓'} ${abs(est['difference']):.2f} vs NJ avg")
            st.metric("vs NJ Average", f"{est['difference_pct']:+.1f}%")
            st.metric("Rate Factor", f"{est['rate_factor']:.2f}x")
        else:
            st.warning("ZIP not found in NJ database")

    with col2:
        # Choropleth
        choro_df, _ = build_choropleth_data(base_bill)

        @st.cache_data(ttl=86400)
        def _load_geo():
            return load_nj_geojson()

        geojson = _load_geo()
        if geojson:
            fig_map = px.choropleth(
                choro_df, geojson=geojson, locations="fips",
                color="estimated_bill",
                color_continuous_scale="RdYlGn_r",
                hover_name="county",
                hover_data={"estimated_bill": ":.2f", "vs_avg_pct": ":.1f", "fips": False},
                labels={"estimated_bill": "Est. Bill ($)", "vs_avg_pct": "vs Avg (%)"},
            )
            fig_map.update_geos(fitbounds="locations", visible=False)
            fig_map.update_layout(
                **PL, height=500, title="NJ County Bill Estimates",
                coloraxis_colorbar=dict(title="Bill ($)"),
                geo=dict(bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info("GeoJSON loading failed — showing table instead")

    # All counties table
    st.markdown("### 📋 All Counties")
    county_df = get_all_county_estimates(base_bill)
    fig_bar = go.Figure(go.Bar(
        x=county_df["County"], y=county_df["Est. Bill ($)"],
        marker_color=[
            "#f59e0b" if c == (county or "") else "#3b82f6"
            for c in county_df["County"]
        ],
        text=county_df["Est. Bill ($)"].apply(lambda v: f"${v:.0f}"),
        textposition="outside",
    ))
    fig_bar.add_hline(y=base_bill, line_dash="dash", line_color="#ef4444",
                      annotation_text=f"NJ Avg: ${base_bill:.0f}")
    fig_bar.update_layout(**PL, height=450, title="Estimated Bill by County",
                          xaxis_title="County", yaxis_title="Bill ($)")
    fig_bar.update_xaxes(tickangle=45)
    st.plotly_chart(fig_bar, use_container_width=True)

    with st.expander("📋 Full County Table"):
        st.dataframe(county_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════
# PAGE 5: PLAN COMPARISON
# ═══════════════════════════════════════════════════════
elif page == "💡 Plan Comparison":
    st.markdown('<div class="section-header">Retail Plan Comparison</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Compare fixed vs variable electricity supply plans</div>', unsafe_allow_html=True)

    from analytics import compare_plans as _compare_plans

    c1, c2 = st.columns(2)
    with c1: usage = st.number_input("Monthly Usage (kWh)", 100, 5000, 750, 50)
    with c2: compare_btn = st.button("⚡ Compare Plans", type="primary", use_container_width=True)

    if compare_btn or "plan" in st.session_state:
        if compare_btn:
            comp_df, plan_insight = _compare_plans(plans, usage)
            st.session_state["plan"] = (comp_df, plan_insight)
        comp_df, plan_insight = st.session_state["plan"]
        insight_box(plan_insight)

        col1, col2 = st.columns(2)
        with col1:
            colors_bar = ["#10b981" if t == "fixed" else "#f59e0b" for t in comp_df["type_raw"]]
            fig = go.Figure(go.Bar(
                x=comp_df["Provider"], y=comp_df["annual_cost_val"],
                marker_color=colors_bar,
                text=comp_df["annual_cost_val"].apply(lambda x: f"${x:.0f}"),
                textposition="outside",
            ))
            fig.update_layout(**PL, height=450, title="Annual Cost by Plan",
                              yaxis_title="Annual Cost ($)")
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fixed = comp_df[comp_df["type_raw"]=="fixed"]["rate_val"]
            variable = comp_df[comp_df["type_raw"]=="variable"]["rate_val"]
            fig2 = go.Figure()
            fig2.add_trace(go.Box(y=fixed, name="Fixed", marker_color="#10b981", boxmean=True))
            fig2.add_trace(go.Box(y=variable, name="Variable", marker_color="#f59e0b", boxmean=True))
            fig2.update_layout(**PL, height=450, title="Rate Distribution",
                               yaxis_title="Rate ($/kWh)")
            st.plotly_chart(fig2, use_container_width=True)

        display = ["Provider","Type","Supply Rate","Monthly Est.","Annual Est.","Term","ETF","Green %","Risk"]
        st.dataframe(comp_df[display], use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.caption("⚡ ElectricAI MVP — Shared analytics engine (`shared.bill_analytics`) "
           "used by both Streamlit UI and FastAPI backend | Data: Synthetic PSE&G")
