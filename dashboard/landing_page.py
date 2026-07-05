"""GréineQ landing page — infographic-style layout with live animation in the core."""

from __future__ import annotations

import streamlit as st

LANDING_CSS = """
<style>
    section.main > div.block-container {
        padding-top: 0 !important;
        max-width: 1180px;
    }

    .gq-card {
        background: linear-gradient(180deg, #FFFFFF 0%, #FDFAF3 100%);
        border-radius: 20px;
        overflow: hidden;
        box-shadow: 0 16px 48px rgba(94, 118, 144, 0.14);
        border: 1px solid rgba(94, 118, 144, 0.14);
        margin-bottom: 0.35rem;
    }

    .gq-sky-section {
        background: linear-gradient(175deg, #EDF0F3 0%, #F1EDE3 34%, #FAF3E4 70%, #F4EBD6 100%);
        padding: 1.75rem 1.5rem 1.25rem;
        position: relative;
        border: 1px solid rgba(94, 118, 144, 0.14);
        border-radius: 20px 20px 0 0;
    }

    .gq-title-bar {
        padding: 1.5rem 1.5rem 1.25rem;
        text-align: center;
    }

    .gq-brand-row {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        margin-bottom: 0.35rem;
    }

    .gq-brand-sun {
        width: 36px;
        height: 36px;
        background: radial-gradient(circle, #F0DCA8 30%, #D9A94E 72%);
        border-radius: 50%;
        box-shadow: 0 0 0 3px rgba(217, 169, 78, 0.22);
        flex-shrink: 0;
    }

    .gq-brand-name {
        margin: 0;
        font-size: clamp(2rem, 4.5vw, 2.75rem);
        font-weight: 900;
        letter-spacing: -0.03em;
        line-height: 1;
        color: #37475A;
    }

    .gq-brand-name em {
        font-style: normal;
        color: #C6923A;
    }

    .gq-tagline {
        margin: 0;
        font-size: clamp(0.95rem, 2vw, 1.12rem);
        font-weight: 600;
        color: #55636F;
        letter-spacing: -0.01em;
    }

    .gq-title-divider {
        width: 64px;
        height: 3px;
        background: linear-gradient(90deg, #E6C074, #C6923A);
        border-radius: 99px;
        margin: 0.85rem auto 0.5rem;
    }

    /* Entry button — gold pill directly under the title */
    .st-key-enter_twin_main {
        max-width: 20rem;
        margin: 0.25rem auto 1rem;
    }

    .st-key-enter_twin_main button {
        width: 100%;
        background: linear-gradient(135deg, #E6C074 0%, #D9A94E 55%, #C6923A 100%) !important;
        color: #4A3410 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.8rem 1.25rem !important;
        font-size: 0.82rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
        box-shadow: 0 6px 20px rgba(198, 146, 58, 0.38) !important;
        transition: transform 0.12s ease, box-shadow 0.12s ease !important;
    }

    .st-key-enter_twin_main button:hover {
        background: linear-gradient(135deg, #EFCE86 0%, #E6C074 55%, #D9A94E 100%) !important;
        color: #4A3410 !important;
        box-shadow: 0 9px 26px rgba(198, 146, 58, 0.48) !important;
        transform: translateY(-1px) !important;
    }

    .st-key-enter_twin_main button:focus,
    .st-key-enter_twin_main button:active {
        color: #4A3410 !important;
        box-shadow: 0 6px 20px rgba(198, 146, 58, 0.38) !important;
    }

    .gq-sky-inner {
        display: grid;
        grid-template-columns: minmax(120px, 180px) 1fr minmax(100px, 160px);
        gap: 1rem 1.25rem;
        align-items: start;
    }

    @media (max-width: 900px) {
        .gq-sky-inner { grid-template-columns: 1fr; }
    }

    .gq-side-col {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.55rem;
        padding-top: 0.5rem;
    }

    .gq-solar-panel {
        width: 148px;
        height: 100px;
        background: linear-gradient(135deg, #3B4A5C 0%, #4A5E74 45%, #5E7690 100%);
        border-radius: 10px;
        border: 2px solid rgba(59, 74, 92, 0.30);
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        grid-template-rows: repeat(3, 1fr);
        gap: 3px;
        padding: 6px;
        box-shadow: 0 8px 22px rgba(59, 74, 92, 0.20);
    }

    .gq-solar-cell {
        background: linear-gradient(135deg, #4A5E74, #7B93AD);
        border-radius: 3px;
        border: 1px solid rgba(185, 202, 220, 0.40);
    }

    .gq-side-label {
        font-size: 0.76rem;
        font-weight: 600;
        color: #37475A;
        text-align: center;
    }

    .gq-battery-unit {
        width: 92px;
        height: 118px;
        background: linear-gradient(180deg, #FDFBF6 0%, #EDE7DB 100%);
        border-radius: 10px;
        border: 2px solid rgba(147, 163, 181, 0.45);
        box-shadow: 0 8px 22px rgba(94, 118, 144, 0.14);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 6px;
    }

    .gq-battery-bolt { font-size: 1.75rem; line-height: 1; }

    .gq-battery-bars {
        display: flex;
        flex-direction: column;
        gap: 4px;
        width: 58%;
    }

    .gq-battery-bar-h {
        height: 5px;
        border-radius: 3px;
        background: linear-gradient(90deg, #5FB07E, #3E9A63);
    }

    .gq-core-center {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        gap: 0.45rem;
    }

    .gq-core-title {
        margin: 0;
        font-size: 1rem;
        font-weight: 700;
        color: #37475A;
    }

    .gq-core-sub {
        margin: 0;
        font-size: 0.78rem;
        font-weight: 600;
        color: #5E7690;
    }

    .gq-core-desc {
        margin: 0.15rem 0 0;
        font-size: 0.76rem;
        color: #5A6875;
        max-width: 26rem;
        line-height: 1.45;
    }

    /* Sky section wrapper (Streamlit container by key) */
    .st-key-gq_sky {
        background: linear-gradient(175deg, #EDF0F3 0%, #F1EDE3 34%, #FAF3E4 70%, #F4EBD6 100%);
        border: 1px solid rgba(94, 118, 144, 0.14);
        border-radius: 20px 20px 0 0;
        padding: 1.5rem 1.5rem 1.25rem;
    }

    /* Dark monitor frame around the agent animation (container by key) */
    .st-key-gq_agent_screen {
        background: linear-gradient(160deg, #4A5E74, #1E2733);
        border-radius: 14px;
        padding: 8px;
        box-shadow: 0 0 0 1px rgba(185, 202, 220, 0.28), 0 12px 32px rgba(30, 39, 51, 0.32);
        margin: 0.35rem 0 0.15rem;
    }

    .st-key-gq_agent_screen [data-testid="stImage"],
    .st-key-gq_agent_screen img {
        border-radius: 8px;
        overflow: hidden;
        display: block;
        width: 100%;
        height: auto;
    }

    .gq-core-head {
        text-align: center;
        margin-bottom: 0.25rem;
    }

    /* Monitor header bar inside the dark frame */
    .gq-monitor-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.1rem 0.35rem 0.5rem;
        margin-bottom: 6px;
        border-bottom: 1px solid rgba(185, 202, 220, 0.20);
    }

    .gq-monitor-id {
        display: flex;
        align-items: center;
        gap: 0.55rem;
    }

    .gq-monitor-badge {
        width: 32px;
        height: 32px;
        border-radius: 9px;
        background: radial-gradient(circle at 30% 25%, #B9CADC, #3B4A5C 92%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.05rem;
        box-shadow: 0 0 0 1px rgba(185, 202, 220, 0.45), 0 3px 12px rgba(94, 118, 144, 0.32);
        flex-shrink: 0;
    }

    .gq-monitor-text {
        display: flex;
        flex-direction: column;
        line-height: 1.15;
        text-align: left;
    }

    .gq-monitor-title {
        font-size: 0.76rem;
        font-weight: 800;
        color: #F1EEE6;
        letter-spacing: 0.01em;
    }

    .gq-monitor-sub {
        font-size: 0.58rem;
        font-weight: 600;
        color: #E6C074;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    .gq-live {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.58rem;
        font-weight: 800;
        color: #A6D8BA;
        letter-spacing: 0.14em;
    }

    .gq-live-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #5FB07E;
        animation: gqpulse 1.6s infinite;
    }

    @keyframes gqpulse {
        0%   { box-shadow: 0 0 0 0 rgba(95, 176, 126, 0.55); }
        70%  { box-shadow: 0 0 0 7px rgba(95, 176, 126, 0); }
        100% { box-shadow: 0 0 0 0 rgba(95, 176, 126, 0); }
    }

    /* Three-state legend cards (matches infographic) */
    .gq-states {
        display: flex;
        justify-content: center;
        gap: 0.45rem;
        margin: 0.7rem auto 0;
        max-width: 520px;
        width: 100%;
    }

    .gq-state {
        flex: 1;
        border-radius: 11px;
        padding: 0.5rem 0.4rem;
        text-align: center;
        border: 1px solid;
        transition: transform 0.12s ease, box-shadow 0.12s ease;
    }

    .gq-state:hover {
        transform: translateY(-2px);
    }

    .gq-state .gq-state-ic { font-size: 1.05rem; line-height: 1; }

    .gq-state .gq-state-lbl {
        font-size: 0.6rem;
        font-weight: 800;
        letter-spacing: 0.07em;
        text-transform: uppercase;
        margin-top: 3px;
    }

    .gq-state .gq-state-dsc {
        font-size: 0.56rem;
        color: #6C7A88;
        line-height: 1.25;
        margin-top: 2px;
    }

    .gq-state-charge {
        border-color: rgba(95, 176, 126, 0.40);
        background: rgba(95, 176, 126, 0.10);
    }
    .gq-state-charge .gq-state-lbl { color: #2F6B48; }

    .gq-state-discharge {
        border-color: rgba(230, 138, 78, 0.40);
        background: rgba(230, 138, 78, 0.10);
    }
    .gq-state-discharge .gq-state-lbl { color: #9A552A; }

    .gq-state-hold {
        border-color: rgba(147, 163, 181, 0.45);
        background: rgba(147, 163, 181, 0.12);
    }
    .gq-state-hold .gq-state-lbl { color: #4B5867; }

    .gq-animation-caption {
        margin: 0.25rem 0 0;
        font-size: 0.68rem;
        color: #6C7A88;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-align: center;
    }

    .gq-dual-pill {
        background: linear-gradient(90deg, #F5EAD1, #EFDCB0);
        border: 1px solid rgba(198, 146, 58, 0.30);
        border-radius: 12px;
        padding: 0.55rem 1rem;
        text-align: center;
        box-shadow: 0 4px 14px rgba(198, 146, 58, 0.12);
        margin-top: 1rem;
        max-width: 520px;
        width: 100%;
    }

    .gq-dual-pill h4 {
        margin: 0 0 0.2rem;
        font-size: 0.86rem;
        font-weight: 700;
        color: #9A7326;
    }

    .gq-dual-pill p {
        margin: 0;
        font-size: 0.74rem;
        color: #6B531B;
        line-height: 1.45;
    }

    .gq-ribbon {
        background: linear-gradient(90deg, #F0DCA8 0%, #E6C074 38%, #D9A94E 68%, #F0DCA8 100%);
        padding: 0.45rem 1rem;
        text-align: center;
        border-left: 1px solid rgba(94, 118, 144, 0.14);
        border-right: 1px solid rgba(94, 118, 144, 0.14);
    }

    .gq-ribbon-solo {
        border: 1px solid rgba(94, 118, 144, 0.14);
        border-bottom: none;
        border-radius: 16px 16px 0 0;
        padding-top: 0.6rem;
        padding-bottom: 0.6rem;
    }

    .gq-ribbon span {
        font-size: 0.6rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #6B531B;
    }

    .gq-action-strip {
        display: flex;
        justify-content: center;
        gap: 0.55rem;
        flex-wrap: wrap;
        padding: 0.65rem 1rem 0.85rem;
        background: #FBF6EA;
        border-radius: 0 0 20px 20px;
        border: 1px solid rgba(94, 118, 144, 0.14);
        border-top: none;
        box-shadow: 0 16px 48px rgba(94, 118, 144, 0.12);
        margin-bottom: 0.75rem;
    }

    .gq-action-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.22rem 0.65rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
    }

    .gq-badge-charge    { background: rgba(95,176,126,0.16);  color: #2F6B48; border: 1px solid rgba(95,176,126,0.30); }
    .gq-badge-discharge { background: rgba(230,138,78,0.16); color: #9A552A; border: 1px solid rgba(230,138,78,0.30); }
    .gq-badge-hold      { background: rgba(147,163,181,0.16);color: #4B5867; border: 1px solid rgba(147,163,181,0.30); }
    .gq-badge-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
</style>
"""


def _solar_panel_html() -> str:
    cells = "".join('<div class="gq-solar-cell"></div>' for _ in range(9))
    return f'<div class="gq-solar-panel">{cells}</div>'


def _battery_unit_html() -> str:
    bars = (
        '<div class="gq-battery-bars">'
        '<div class="gq-battery-bar-h" style="width:100%"></div>'
        '<div class="gq-battery-bar-h" style="width:75%"></div>'
        '<div class="gq-battery-bar-h" style="width:50%;opacity:0.65"></div>'
        "</div>"
    )
    return (
        '<div class="gq-battery-unit">'
        '<div class="gq-battery-bolt">⚡</div>'
        + bars
        + "</div>"
    )


def render_landing_header() -> bool:
    """Title + compact entry button — renders immediately (before GIF load)."""
    st.markdown(LANDING_CSS, unsafe_allow_html=True)

    st.markdown(
        """<div class="gq-card">
<div class="gq-title-bar">
<div class="gq-brand-row">
<div class="gq-brand-sun"></div>
<h1 class="gq-brand-name"><em>Gréine</em>Q</h1>
</div>
<p class="gq-tagline">Intelligent Solar &amp; Battery Management</p>
<div class="gq-title-divider"></div>
</div>""",
        unsafe_allow_html=True,
    )

    clicked = st.button(
        "Enter Interactive Digital Twin  →",
        type="primary",
        width="stretch",
        key="enter_twin_main",
    )
    return clicked


def render_landing_body(gif_bytes: bytes, demo_day: str = "") -> None:
    """Sky section with the Q-Learning agent animation inside a dark monitor frame."""
    solar = _solar_panel_html()
    battery = _battery_unit_html()
    day_line = f" · {demo_day}" if demo_day else ""

    with st.container(key="gq_sky"):
        c_solar, c_core, c_batt = st.columns([1, 2.4, 1], vertical_alignment="center")

        with c_solar:
            st.markdown(
                f'<div class="gq-side-col">{solar}'
                '<div class="gq-side-label">☀️ &nbsp;Solar Generation</div></div>',
                unsafe_allow_html=True,
            )

        with c_core:
            st.markdown(
                '<div class="gq-core-head">'
                '<p class="gq-core-title">The Intelligent Core</p></div>',
                unsafe_allow_html=True,
            )
            with st.container(key="gq_agent_screen"):
                st.markdown(
                    '<div class="gq-monitor-bar">'
                    '<div class="gq-monitor-id">'
                    '<div class="gq-monitor-badge">🧠</div>'
                    '<div class="gq-monitor-text">'
                    '<span class="gq-monitor-title">Q-Learning Intelligence</span>'
                    '<span class="gq-monitor-sub">Three-State Power Management</span>'
                    "</div></div>"
                    '<div class="gq-live"><span class="gq-live-dot"></span>LIVE</div>'
                    "</div>",
                    unsafe_allow_html=True,
                )
                st.image(gif_bytes, width="stretch")
            st.markdown(
                f'<p class="gq-animation-caption">Live dispatch replay{day_line} · '
                "48 intervals · 30-min precision</p>"
                '<div class="gq-states">'
                '<div class="gq-state gq-state-charge">'
                '<div class="gq-state-ic">🔆</div>'
                '<div class="gq-state-lbl">Charging</div>'
                '<div class="gq-state-dsc">Absorbing excess solar</div></div>'
                '<div class="gq-state gq-state-discharge">'
                '<div class="gq-state-ic">⚡</div>'
                '<div class="gq-state-lbl">Discharging</div>'
                '<div class="gq-state-dsc">Supplying load / grid</div></div>'
                '<div class="gq-state gq-state-hold">'
                '<div class="gq-state-ic">⏸️</div>'
                '<div class="gq-state-lbl">Holding</div>'
                '<div class="gq-state-dsc">Preserving for peak</div></div>'
                "</div>",
                unsafe_allow_html=True,
            )

        with c_batt:
            st.markdown(
                f'<div class="gq-side-col">{battery}'
                '<div class="gq-side-label">🔋 &nbsp;Battery Storage</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        """<div class="gq-ribbon gq-ribbon-solo">
<span>⚡ Automated Energy Flow · Intelligent Dispatch · Real-time Optimisation · Ausgrid + AEMO NSW1 ⚡</span>
</div>
<div class="gq-action-strip">
<span class="gq-action-badge gq-badge-charge"><span class="gq-badge-dot" style="background:#5FB07E"></span>Charge</span>
<span class="gq-action-badge gq-badge-discharge"><span class="gq-badge-dot" style="background:#E68A4E"></span>Discharge</span>
<span class="gq-action-badge gq-badge-hold"><span class="gq-badge-dot" style="background:#93A3B5"></span>Hold</span>
</div>""",
        unsafe_allow_html=True,
    )
