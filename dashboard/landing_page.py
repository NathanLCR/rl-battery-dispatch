"""GréineQ landing page — Q-Agent control-centre hero layout."""

from __future__ import annotations

import streamlit as st

from dashboard.dispatch_widget import render_landing_dispatch
from dashboard.theme import brand_logo_html

LANDING_CSS = """
<style>
    section.main > div.block-container {
        padding-top: 0 !important;
        max-width: min(1180px, 100%) !important;
        width: 100% !important;
        padding-left: clamp(0.65rem, 2.5vw, 1.5rem) !important;
        padding-right: clamp(0.65rem, 2.5vw, 1.5rem) !important;
    }

    .gq-card {
        background: linear-gradient(180deg, #0c1424 0%, #070d1a 100%);
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 16px 48px rgba(0, 0, 0, 0.45);
        border: 1px solid rgba(245, 156, 26, 0.18);
        margin-bottom: 0.35rem;
    }

    .gq-title-bar {
        padding: 1.5rem 1.5rem 1rem;
        text-align: center;
    }

    .gq-logo-wrap {
        display: flex;
        justify-content: center;
        margin-bottom: 0.5rem;
    }

    .gq-logo-wrap img {
        width: min(280px, 88vw);
        height: auto;
        filter: drop-shadow(0 4px 24px rgba(245, 156, 26, 0.25));
    }

    .gq-tagline {
        margin: 0;
        font-size: clamp(0.88rem, 2vw, 1rem);
        font-weight: 500;
        color: #94a3b8;
        letter-spacing: 0.04em;
    }

    .gq-title-divider {
        width: 72px;
        height: 2px;
        background: linear-gradient(90deg, transparent, #f59c1a, transparent);
        border-radius: 99px;
        margin: 0.85rem auto 0.5rem;
    }

    .st-key-enter_twin_main,
    .st-key-enter_play_main {
        max-width: 13.5rem;
        margin: 0.15rem auto 0.35rem;
    }

    .st-key-enter_twin_main button,
    .st-key-enter_play_main button {
        width: 100% !important;
        border-radius: 8px !important;
        padding: 0.45rem 0.75rem !important;
        font-family: 'Barlow Condensed', sans-serif !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        min-height: 2.15rem !important;
        box-shadow: none !important;
    }

    .st-key-enter_twin_main button {
        background: linear-gradient(135deg, #fbbf24 0%, #f59e1a 55%, #d97706 100%) !important;
        color: #1c1917 !important;
        border: none !important;
    }

    .st-key-enter_twin_main button:hover {
        box-shadow: 0 4px 14px rgba(245, 156, 26, 0.35) !important;
        transform: translateY(-1px) !important;
    }

    .st-key-enter_play_main button {
        background: rgba(15, 23, 42, 0.55) !important;
        color: #e2e8f0 !important;
        border: 1px solid rgba(148, 163, 184, 0.35) !important;
    }

    .st-key-enter_play_main button:hover {
        border-color: rgba(245, 156, 26, 0.4) !important;
        color: #fde68a !important;
    }

    .gq-landing-cta-row {
        display: flex;
        justify-content: center;
        gap: 0.65rem;
        flex-wrap: wrap;
        margin: 0.15rem 0 0.75rem;
    }

    .st-key-gq_hero {
        background: linear-gradient(175deg, #0a1020 0%, #0c1424 50%, #070d1a 100%);
        border: 1px solid rgba(245, 156, 26, 0.15);
        border-radius: 16px;
        padding: 0.35rem 0.5rem 0.5rem;
        margin-bottom: 0.65rem;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
    }

    .st-key-gq_hero [data-testid="stIFrame"],
    .st-key-gq_hero iframe {
        border-radius: 12px;
        overflow: hidden;
        display: block;
        width: 100%;
        background: #0c1424;
        border: 1px solid rgba(245, 156, 26, 0.12);
    }

    .gq-explain {
        background: rgba(15, 23, 42, 0.65);
        border: 1px solid rgba(245, 156, 26, 0.18);
        border-radius: 12px;
        padding: 1rem 1.15rem;
        margin-bottom: 0.65rem;
    }

    .gq-explain h3 {
        margin: 0 0 0.45rem;
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #f59c1a;
    }

    .gq-explain p {
        margin: 0;
        font-size: 0.88rem;
        line-height: 1.55;
        color: #cbd5e1;
    }

    .gq-action-strip {
        display: flex;
        justify-content: center;
        gap: 0.55rem;
        flex-wrap: wrap;
        padding: 0.65rem 1rem 0.85rem;
        background: #070d1a;
        border-radius: 12px;
        border: 1px solid rgba(245, 156, 26, 0.15);
        margin-bottom: 0.75rem;
    }

    .gq-action-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.22rem 0.65rem;
        border-radius: 999px;
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }

    .gq-badge-charge    { background: rgba(34,197,94,0.12);  color: #4ade80; border: 1px solid rgba(34,197,94,0.3); }
    .gq-badge-discharge { background: rgba(245,156,26,0.12); color: #fbbf24; border: 1px solid rgba(245,156,26,0.35); }
    .gq-badge-hold      { background: rgba(100,116,139,0.14);color: #94a3b8; border: 1px solid rgba(100,116,139,0.3); }
    .gq-badge-grid_charge { background: rgba(14,165,233,0.12); color: #38bdf8; border: 1px solid rgba(14,165,233,0.35); }
    .gq-badge-export    { background: rgba(168,85,247,0.12); color: #c084fc; border: 1px solid rgba(168,85,247,0.35); }
    .gq-badge-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }

    .st-key-gq_hero iframe {
        min-height: 420px;
        max-height: 72vh;
    }

    @media (max-width: 768px) {
        .gq-title-bar { padding: 1.15rem 1rem 0.85rem; }
        .gq-explain { padding: 0.85rem 0.9rem; }
        .gq-explain p { font-size: 0.84rem; }
        .st-key-enter_twin_main,
        .st-key-enter_play_main { max-width: 100%; }
        .st-key-enter_twin_main { max-width: 100%; }
    }

    @media (max-width: 430px) {
        .gq-action-strip { gap: 0.4rem; padding: 0.55rem 0.65rem 0.7rem; }
        .gq-action-badge { font-size: 0.62rem; }
    }
</style>
"""


def render_landing_ctas(*, inject_css: bool = False) -> tuple[bool, bool]:
    """Compact entry buttons — place directly under the tagline."""
    if inject_css:
        st.markdown(LANDING_CSS, unsafe_allow_html=True)
    # Narrow centred pair — not full-bleed wide buttons
    _l, c1, c2, _r = st.columns([1.1, 1.15, 1.15, 1.1])
    with c1:
        twin = st.button(
            "Digital Twin →",
            type="primary",
            width="stretch",
            key="enter_twin_main",
        )
    with c2:
        play = st.button(
            "Play vs Agent",
            type="secondary",
            width="stretch",
            key="enter_play_main",
        )
    return twin, play


def render_landing_header(*, show_cta: bool = True, inject_css: bool = True) -> bool:
    if inject_css:
        st.markdown(LANDING_CSS, unsafe_allow_html=True)

    st.markdown(
        f"""<div class="gq-card">
<div class="gq-title-bar">
<div class="gq-logo-wrap">{brand_logo_html(max_width=280)}</div>
<p class="gq-tagline">Reinforcement learning for solar battery dispatch</p>
<div class="gq-title-divider"></div>
</div>""",
        unsafe_allow_html=True,
    )

    if not show_cta:
        return False
    return st.button(
        "Digital Twin →",
        type="primary",
        width="stretch",
        key="enter_twin_main",
    )


def render_landing_body(trace, demo_day: str = "") -> None:
    with st.container(key="gq_hero"):
        render_landing_dispatch(trace, demo_day)

    st.markdown(
        """<div class="gq-explain">
<h3>What you are seeing</h3>
<p>GréineQ replays a historical solar-battery day in 30-minute steps. At each step the agent
sees solar generation, household demand, battery charge level, and grid price — then chooses
hold, charge from solar, discharge to the home, grid-charge (buy), or export (sell).
Grid-charge and export enable price arbitrage: buy low, use or sell later.</p>
</div>
<div class="gq-action-strip">
<span class="gq-action-badge gq-badge-hold"><span class="gq-badge-dot" style="background:#64748b"></span>Hold</span>
<span class="gq-action-badge gq-badge-charge"><span class="gq-badge-dot" style="background:#22c55e"></span>Charge battery</span>
<span class="gq-action-badge gq-badge-discharge"><span class="gq-badge-dot" style="background:#f59e1a"></span>Discharge battery</span>
<span class="gq-action-badge gq-badge-grid_charge"><span class="gq-badge-dot" style="background:#0ea5e9"></span>Grid-charge (buy)</span>
<span class="gq-action-badge gq-badge-export"><span class="gq-badge-dot" style="background:#a855f7"></span>Export (sell)</span>
</div>""",
        unsafe_allow_html=True,
    )
