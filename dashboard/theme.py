"""GréineQ visual theme — aligned with brand infographic (sunny solar + sky battery)."""

from __future__ import annotations

import streamlit as st
CREAM = "#FBF6EA"
SAND = "#F1E7D2"
GOLD_LIGHT = "#E6C074"
GOLD = "#D9A94E"
GOLD_DEEP = "#C6923A"
GLOW = "#F0DCA8"
TECH_DEEP = "#3B4A5C"
TECH = "#5E7690"
TECH_MID = "#8CA0B8"
TECH_LIGHT = "#B9CADC"
TEXT = "#37475A"
TEXT_SUB = "#6C7A88"
PANEL_DARK = "#1E2733"
PANEL_MID = "#3B4A5C"
CHARGE = "#5FB07E"
DISCHARGE = "#E68A4E"
HOLD = "#93A3B5"

ACTION_COLORS = {"hold": HOLD, "charge": CHARGE, "discharge": DISCHARGE}

SUNNY_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    .stApp {
        background:
            radial-gradient(1100px 520px at 10% -8%, rgba(240, 220, 168, 0.55), transparent 60%),
            radial-gradient(900px 480px at 100% 0%, rgba(185, 202, 220, 0.35), transparent 62%),
            linear-gradient(160deg, #F4F1EA 0%, #FBF6EA 32%, #FAF2E1 68%, #F0E6D0 100%);
        background-attachment: fixed;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F6F2E8 0%, #F1EAD9 58%, #EFE6D4 100%);
        border-right: 1px solid rgba(94, 118, 144, 0.16);
        min-width: 20rem !important;
    }

    /* Keep sidebar reachable on every screen (Overview ↔ Digital Twin) */
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] {
        visibility: visible !important;
        pointer-events: auto !important;
    }

    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #37475A;
    }

    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #FFFFFF, #FBF7EE);
        border: 1px solid rgba(94, 118, 144, 0.20);
        border-radius: 12px;
        padding: 0.65rem 1rem;
        box-shadow: 0 6px 18px rgba(94, 118, 144, 0.10);
    }

    div[data-testid="stMetric"] label {
        color: #6C7A88 !important;
        font-size: 0.78rem !important;
    }

    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #C6923A !important;
        font-weight: 700 !important;
    }

    .stTabs [data-baseweb="tab-list"] { gap: 6px; background: transparent; }

    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.65);
        border-radius: 10px 10px 0 0;
        border: 1px solid rgba(94, 118, 144, 0.20);
        color: #37475A;
    }

    .stTabs [aria-selected="true"] {
        background: #5E7690 !important;
        color: #FBF6EA !important;
        border-color: #5E7690 !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #E6C074 0%, #D9A94E 55%, #C6923A 100%);
        color: #4A3410;
        border: none;
        border-radius: 12px;
        font-weight: 700;
        box-shadow: 0 4px 16px rgba(198, 146, 58, 0.30);
    }

    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 22px rgba(198, 146, 58, 0.42);
        color: #4A3410;
    }

    .gq-hero {
        background: linear-gradient(105deg, rgba(255,255,255,0.88) 0%, rgba(251,246,234,0.92) 100%);
        border-radius: 20px;
        padding: 1.5rem 2rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(217, 169, 78, 0.30);
        box-shadow: 0 10px 40px rgba(94, 118, 144, 0.12);
        position: relative;
        overflow: hidden;
    }

    .gq-hero::before {
        content: "";
        position: absolute;
        top: -40px;
        left: -20px;
        width: 140px;
        height: 140px;
        background: radial-gradient(circle, rgba(240,220,168,0.9) 0%, rgba(217,169,78,0.4) 45%, transparent 70%);
        pointer-events: none;
    }

    .gq-hero-kicker {
        margin: 0 0 0.25rem 0;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #5E7690;
    }

    .gq-hero h1 {
        margin: 0 0 0.3rem 0;
        font-size: 2.1rem;
        font-weight: 700;
        color: #37475A;
        letter-spacing: -0.02em;
    }

    .gq-hero h1 span {
        color: #C6923A;
    }

    .gq-hero p {
        margin: 0;
        color: #5A6875;
        font-size: 1rem;
        max-width: 36rem;
        line-height: 1.55;
    }

    .gq-feature {
        background: rgba(255, 255, 255, 0.86);
        border-radius: 14px;
        padding: 1rem 1.1rem;
        height: 100%;
        border: 1px solid rgba(94, 118, 144, 0.16);
        box-shadow: 0 4px 14px rgba(94, 118, 144, 0.07);
    }

    .gq-feature-solar { border-top: 3px solid #D9A94E; }
    .gq-feature-balance { border-top: 3px solid #5FB07E; }
    .gq-feature-interface { border-top: 3px solid #5E7690; }

    .gq-feature-icon {
        font-size: 1.35rem;
        margin-bottom: 0.35rem;
    }

    .gq-feature h4 {
        margin: 0 0 0.4rem 0;
        color: #37475A;
        font-size: 0.92rem;
        font-weight: 700;
    }

    .gq-feature p {
        margin: 0;
        color: #6C7A88;
        font-size: 0.84rem;
        line-height: 1.45;
    }

    .gq-card {
        background: rgba(255, 255, 255, 0.86);
        border-radius: 14px;
        padding: 1rem 1.15rem;
        margin-bottom: 0.75rem;
        border: 1px solid rgba(217, 169, 78, 0.24);
        box-shadow: 0 4px 14px rgba(198, 146, 58, 0.06);
    }

    .gq-card h4 {
        margin: 0 0 0.5rem 0;
        color: #9A7326;
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    .gq-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.32rem 0.7rem;
        border-radius: 999px;
        font-size: 0.86rem;
        font-weight: 600;
        margin: 0.2rem 0;
        width: 100%;
    }

    .gq-pill-charge { background: rgba(95, 176, 126, 0.16); color: #2F6B48; }
    .gq-pill-discharge { background: rgba(230, 138, 78, 0.16); color: #9A552A; }
    .gq-pill-hold { background: rgba(147, 163, 181, 0.20); color: #4B5867; }

    .gq-dot {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        flex-shrink: 0;
    }

    .gq-subheader {
        color: #37475A;
        font-weight: 700;
        font-size: 1.05rem;
        margin: 0.25rem 0 0.75rem 0;
    }

    .gq-twin-banner {
        background: linear-gradient(90deg, #3B4A5C 0%, #4A5E74 55%, #5E7690 100%);
        border-radius: 14px;
        padding: 1rem 1.35rem;
        margin-bottom: 1rem;
        border-left: 4px solid #D9A94E;
        box-shadow: 0 8px 24px rgba(59, 74, 92, 0.22);
    }

    .gq-twin-banner h2 {
        margin: 0;
        color: #FBF6EA;
        font-size: 1.45rem;
    }

    .gq-twin-banner p {
        margin: 0.25rem 0 0 0;
        color: #B9CADC;
        font-size: 0.9rem;
    }

    .gq-chart-panel {
        background: linear-gradient(180deg, #3B4A5C 0%, #2A3746 100%);
        border-radius: 12px 12px 0 0;
        padding: 0.65rem 1rem 0.5rem;
        border: 1px solid rgba(140, 160, 184, 0.28);
        border-bottom: none;
        margin-bottom: 0;
    }

    .gq-chart-panel-label {
        color: #B9CADC;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        padding: 0 0.75rem 0.5rem;
    }

    .gq-infographic-wrap {
        border-radius: 18px;
        overflow: hidden;
        border: 1px solid rgba(94, 118, 144, 0.2);
        box-shadow: 0 12px 36px rgba(94, 118, 144, 0.12);
        margin-bottom: 1rem;
    }

    hr { border-color: rgba(94, 118, 144, 0.20) !important; }

    /* Compact top — remove empty header / toolbar gap */
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 0 !important;
        min-height: 0 !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }

    [data-testid="stDecoration"] {
        display: none !important;
    }

    [data-testid="stToolbar"] {
        top: 0.15rem !important;
        right: 0.35rem !important;
        z-index: 999 !important;
    }

    section.main > div.block-container,
    .stMainBlockContainer.block-container,
    div[data-testid="stAppViewContainer"] .block-container {
        padding-top: 0.15rem !important;
        padding-bottom: 0.5rem !important;
    }

    [data-testid="stAppViewContainer"] > section.main {
        padding-top: 0 !important;
    }

    [data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"] {
        gap: 0.35rem !important;
    }

    [data-testid="stStatusWidget"] {
        margin-bottom: 0 !important;
    }
</style>
"""


def inject_theme() -> None:
    st.markdown(SUNNY_CSS, unsafe_allow_html=True)


def render_hero() -> None:
    st.markdown(
        """
        <div class="gq-hero">
            <p class="gq-hero-kicker">Intelligent Solar &amp; Battery Management</p>
            <h1><span>Gréine</span>Q</h1>
            <p>Q-Learning demand agent for autonomous hold / charge / discharge decisions
            on real Ausgrid household data and AEMO wholesale prices.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_feature_pillars() -> None:
    st.markdown(
        """
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem;margin-bottom:1rem;">
            <div class="gq-feature gq-feature-solar">
                <div class="gq-feature-icon">☀️</div>
                <h4>Dual-source integration</h4>
                <p>Synchronises rooftop solar generation with home battery storage for a balanced power loop.</p>
            </div>
            <div class="gq-feature gq-feature-balance">
                <div class="gq-feature-icon">⚡</div>
                <h4>Automated energy balancing</h4>
                <p>Analyses demand patterns to switch between solar supply and stored battery reserves each step.</p>
            </div>
            <div class="gq-feature gq-feature-interface">
                <div class="gq-feature-icon">📊</div>
                <h4>Industrial interface</h4>
                <p>Digital-twin replay with live KPIs, policy comparison, and exportable session logs.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_infographic() -> None:
    """Deprecated — landing uses built UI, not static artwork."""
    pass


def render_twin_banner(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="gq-twin-banner">
            <h2>{title}</h2>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chart_panel_open(label: str = "Energy monitoring — live replay") -> None:
    st.markdown(
        f"""
        <div class="gq-chart-panel">
            <div class="gq-chart-panel-label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_info_card(title: str, body_html: str) -> None:
    st.markdown(
        f'<div class="gq-card"><h4>{title}</h4>{body_html}</div>',
        unsafe_allow_html=True,
    )


def render_action_legend() -> None:
    st.markdown(
        """
        <div class="gq-card">
            <h4>Agent actions</h4>
            <div class="gq-pill gq-pill-charge">
                <span class="gq-dot" style="background:#22C55E"></span> Charge — store surplus solar
            </div>
            <div class="gq-pill gq-pill-discharge">
                <span class="gq-dot" style="background:#F97316"></span> Discharge — offset load
            </div>
            <div class="gq-pill gq-pill-hold">
                <span class="gq-dot" style="background:#94A3B8"></span> Hold — idle
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
