"""GréineQ visual theme — mission-control dark (Figma Make design)."""

from __future__ import annotations

import base64
import html as html_lib
from pathlib import Path

import streamlit as st

NAVY = "#070d1a"
NAVY_PANEL = "#0c1424"
NAVY_RAISE = "#111827"
AMBER = "#f59c1a"
AMBER_DEEP = "#d97706"
AMBER_GLOW = "#fde68a"
TEXT = "#e2e8f0"
TEXT_MUTED = "#94a3b8"
BORDER = "rgba(148, 163, 184, 0.18)"
CHARGE = "#22c55e"
DISCHARGE = "#f59c1a"
HOLD = "#64748b"

ACTION_COLORS = {"hold": HOLD, "charge": CHARGE, "discharge": DISCHARGE}

MISSION_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Barlow:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Barlow', sans-serif;
    }

    .stApp {
        background:
            radial-gradient(900px 480px at 8% -5%, rgba(245, 156, 26, 0.08), transparent 55%),
            radial-gradient(700px 400px at 95% 0%, rgba(99, 102, 241, 0.06), transparent 50%),
            linear-gradient(180deg, #070d1a 0%, #0a1020 45%, #070d1a 100%);
        background-attachment: fixed;
        color: #e2e8f0;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a1020 0%, #070d1a 100%) !important;
        border-right: 1px solid rgba(245, 156, 26, 0.15) !important;
        min-width: min(20rem, 28vw) !important;
        transform: translateX(0) !important;
        visibility: visible !important;
        overflow: hidden !important;
        height: 100dvh !important;
        max-height: 100dvh !important;
        display: flex !important;
        flex-direction: column !important;
    }

    section[data-testid="stSidebar"] > div {
        display: flex !important;
        flex-direction: column !important;
        flex: 1 1 auto !important;
        min-height: 0 !important;
        height: 100% !important;
        max-height: 100dvh !important;
        overflow: hidden !important;
    }

    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        display: flex !important;
        flex-direction: column !important;
        flex: 1 1 auto !important;
        min-height: 0 !important;
        height: 100% !important;
        max-height: 100dvh !important;
        overflow: hidden !important;
        padding: 0.65rem 0.65rem 0 !important;
    }

    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] > [data-testid="stVerticalBlock"] {
        display: flex !important;
        flex-direction: column !important;
        flex: 1 1 auto !important;
        min-height: 0 !important;
        height: 100% !important;
        max-height: 100% !important;
        overflow: hidden !important;
        gap: 0 !important;
    }

    section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"].st-key-sidebar_header {
        flex: 0 0 auto !important;
        flex-shrink: 0 !important;
        overflow: visible !important;
        z-index: 12 !important;
        background: linear-gradient(180deg, #0a1020 0%, #0c1424 100%) !important;
    }

    section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"].st-key-sidebar_scroll {
        flex: 1 1 auto !important;
        min-height: 0 !important;
        max-height: 100% !important;
        overflow-x: hidden !important;
        overflow-y: auto !important;
        overscroll-behavior: contain;
        -webkit-overflow-scrolling: touch;
        padding: 0.15rem 0.1rem 0.5rem !important;
    }

    section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"].st-key-sidebar_scroll > [data-testid="stVerticalBlock"] {
        overflow: visible !important;
        min-height: min-content !important;
        height: auto !important;
    }

    section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"].st-key-sidebar_footer {
        flex: 0 0 auto !important;
        flex-shrink: 0 !important;
        overflow: visible !important;
        z-index: 12 !important;
        margin-top: auto !important;
        padding: 0.75rem 0.15rem 1rem !important;
        background: linear-gradient(180deg, rgba(10, 16, 32, 0.92) 0%, #070d1a 35%) !important;
        box-shadow: 0 -8px 24px rgba(7, 13, 26, 0.85);
    }

    .st-key-sidebar_header {
        margin: 0 !important;
        padding: 0.35rem 0.15rem 0 !important;
        width: 100% !important;
    }

    .st-key-sidebar_scroll {
        margin: 0 !important;
    }

    .st-key-sidebar_scroll::-webkit-scrollbar,
    section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"].st-key-sidebar_scroll::-webkit-scrollbar {
        width: 5px;
    }

    .st-key-sidebar_scroll::-webkit-scrollbar-thumb,
    section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"].st-key-sidebar_scroll::-webkit-scrollbar-thumb {
        background: rgba(148, 163, 184, 0.28);
        border-radius: 99px;
    }

    .st-key-sidebar_scroll::-webkit-scrollbar-track,
    section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"].st-key-sidebar_scroll::-webkit-scrollbar-track {
        background: transparent;
    }

    .st-key-sidebar_footer {
        margin: 0 !important;
        padding: 0 !important;
    }

    /* Hide decorative iframes/orb if any remain in sidebar */
    section[data-testid="stSidebar"] iframe[height="150"],
    section[data-testid="stSidebar"] iframe[height="320"] {
        display: none !important;
    }

    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
        height: 0 !important;
        min-height: 0 !important;
        overflow: hidden !important;
    }

    @media (max-width: 767px) {
        section[data-testid="stSidebar"] {
            min-width: min(18rem, 100vw) !important;
        }

        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"],
        section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
            display: flex !important;
            visibility: visible !important;
            pointer-events: auto !important;
            height: auto !important;
            min-height: unset !important;
            overflow: visible !important;
        }
    }

    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #f59c1a !important;
        font-family: 'Barlow Condensed', sans-serif !important;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        font-size: 0.85rem !important;
    }

    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p {
        color: #94a3b8 !important;
    }

    [data-testid="stSidebar"] .stButton > button {
        background: rgba(245, 156, 26, 0.12) !important;
        color: #fde68a !important;
        border: 1px solid rgba(245, 156, 26, 0.35) !important;
        border-radius: 8px !important;
        font-family: 'Barlow Condensed', sans-serif !important;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-weight: 700 !important;
    }

    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #0c1424, #111827);
        border: 1px solid rgba(245, 156, 26, 0.2);
        border-radius: 10px;
        padding: 0.65rem 1rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
    }

    div[data-testid="stMetric"] label {
        color: #64748b !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.68rem !important;
        letter-spacing: 0.04em;
    }

    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #f59c1a !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 600 !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.75rem;
        background: transparent;
        border-bottom: 1px solid rgba(148, 163, 184, 0.18);
        padding: 0.35rem 0 0;
        margin: 0.5rem 0 0.85rem;
    }

    .stTabs [data-baseweb="tab"] {
        background: rgba(12, 20, 36, 0.55);
        border-radius: 10px 10px 0 0;
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-bottom: 2px solid transparent;
        color: #94a3b8;
        font-family: 'Barlow', sans-serif;
        font-weight: 600;
        letter-spacing: 0.01em;
        text-transform: none;
        font-size: 0.9rem;
        padding: 0.6rem 1.25rem !important;
        min-height: 2.35rem;
        margin-bottom: -1px;
        transition: color 0.15s ease, background 0.15s ease, border-color 0.15s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #cbd5e1;
        background: rgba(245, 156, 26, 0.06);
    }

    .stTabs [aria-selected="true"] {
        background: rgba(245, 156, 26, 0.11) !important;
        color: #fbbf24 !important;
        border-color: rgba(245, 156, 26, 0.32) !important;
        border-bottom: 2px solid #f59c1a !important;
        box-shadow: inset 0 1px 0 rgba(245, 156, 26, 0.12);
    }

    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 0.5rem;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        background-color: transparent !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #fbbf24 0%, #f59c1a 55%, #d97706 100%);
        color: #1c1917;
        border: none;
        border-radius: 10px;
        font-weight: 700;
        font-family: 'Barlow Condensed', sans-serif;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        box-shadow: 0 4px 20px rgba(245, 156, 26, 0.35);
    }

    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 28px rgba(245, 156, 26, 0.5);
        color: #1c1917;
    }

    .gq-mission-topbar {
        display: flex;
        flex-wrap: wrap;
        align-items: flex-start;
        justify-content: space-between;
        gap: 0.65rem 1rem;
        background: linear-gradient(90deg, #0c1424, #111827);
        border: 1px solid rgba(245, 156, 26, 0.22);
        border-radius: 12px;
        padding: 0.75rem 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }

    .gq-mission-topbar-left {
        flex: 1 1 220px;
        min-width: 0;
    }

    .gq-mission-topbar-left h2 {
        margin: 0;
        font-family: 'Barlow Condensed', sans-serif;
        font-size: clamp(1.05rem, 2.8vw, 1.35rem);
        font-weight: 700;
        letter-spacing: 0.04em;
        color: #f8fafc;
        line-height: 1.2;
        word-wrap: break-word;
    }

    .gq-mission-topbar-left p {
        margin: 0.15rem 0 0;
        font-size: clamp(0.68rem, 1.8vw, 0.78rem);
        color: #64748b;
        font-family: 'JetBrains Mono', monospace;
        line-height: 1.45;
        word-wrap: break-word;
    }

    .gq-mission-topbar-right {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 0.75rem;
        flex: 0 0 auto;
    }

    .st-key-mission_topbar {
        background: linear-gradient(90deg, #0c1424, #111827);
        border: 1px solid rgba(245, 156, 26, 0.22);
        border-radius: 12px;
        padding: 0.55rem 1rem 0.65rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }

    .st-key-mission_topbar [data-testid="stHorizontalBlock"] {
        align-items: center !important;
        gap: 0.5rem;
    }

    .st-key-mission_topbar [data-testid="stColumn"] {
        min-width: 0;
    }

    .st-key-mission_topbar iframe {
        border: none !important;
        background: transparent !important;
        display: block;
        width: 100%;
        max-width: 100%;
        min-height: 102px;
    }

    .st-key-mission_topbar [data-testid="stIFrame"] {
        background: transparent !important;
    }

    @media (max-width: 900px) {
        .st-key-mission_topbar [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
        }
        .st-key-mission_topbar [data-testid="column"]:nth-child(2) {
            flex: 1 1 100% !important;
            order: 3;
        }
    }

    .gq-live-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        background: rgba(34, 197, 94, 0.12);
        border: 1px solid rgba(34, 197, 94, 0.35);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        font-weight: 600;
        color: #4ade80;
        letter-spacing: 0.06em;
    }

    .gq-live-dot {
        width: 7px; height: 7px; border-radius: 50%;
        background: #22c55e;
        animation: gq-live-pulse 1.6s infinite;
    }

    @keyframes gq-live-pulse {
        0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.5); }
        70% { box-shadow: 0 0 0 8px rgba(34, 197, 94, 0); }
        100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
    }

    .gq-kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 0.75rem;
        margin-bottom: 1rem;
        width: 100%;
    }

    .gq-kpi-card {
        background: linear-gradient(145deg, #0c1424 0%, #111827 100%);
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 12px;
        padding: 0.85rem 1rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        border-top: 2px solid rgba(245, 156, 26, 0.45);
        min-width: 0;
    }

    .gq-kpi-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: clamp(0.58rem, 1.6vw, 0.68rem);
        color: #64748b;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
        line-height: 1.35;
        word-wrap: break-word;
    }

    .gq-kpi-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: clamp(1.15rem, 3.2vw, 1.75rem);
        font-weight: 600;
        color: #f59c1a;
        line-height: 1.15;
        word-break: break-word;
    }

    .gq-kpi-delta {
        font-size: clamp(0.58rem, 1.5vw, 0.68rem);
        color: #4ade80;
        margin-top: 0.3rem;
        font-family: 'JetBrains Mono', monospace;
        line-height: 1.35;
    }

    .gq-kpi-delta.neutral { color: #64748b; }

    .gq-twin-banner {
        display: none;
    }

    .gq-chart-panel {
        background: linear-gradient(180deg, #0c1424 0%, #070d1a 100%);
        border-radius: 12px 12px 0 0;
        padding: 0.65rem 1rem 0.5rem;
        border: 1px solid rgba(245, 156, 26, 0.18);
        border-bottom: none;
    }

    .gq-chart-panel-label {
        color: #f59c1a;
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }

    .gq-subheader {
        color: #e2e8f0;
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 700;
        font-size: 0.95rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin: 0.5rem 0 0.75rem 0;
    }

    .gq-policy-note {
        color: #94a3b8;
        font-size: 0.82rem;
        line-height: 1.45;
        margin: 0.35rem 0 0.65rem;
    }

    .gq-insight-box {
        background: rgba(245, 156, 26, 0.08);
        border: 1px solid rgba(245, 156, 26, 0.22);
        border-left: 3px solid #f59c1a;
        border-radius: 8px;
        padding: 0.85rem 1rem;
        margin: 0.25rem 0 1rem;
        color: #e2e8f0;
        font-size: 0.86rem;
        line-height: 1.5;
    }

    .gq-insight-box strong { color: #fde68a; font-weight: 600; }

    .gq-system-status {
        margin-top: 0.75rem;
        padding: 0.65rem 0.75rem;
        border-radius: 8px;
        background: rgba(34, 197, 94, 0.08);
        border: 1px solid rgba(34, 197, 94, 0.25);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.58rem;
        color: #4ade80;
        letter-spacing: 0.04em;
    }

    .gq-system-status span { color: #64748b; display: block; margin-top: 0.2rem; }

    hr { border-color: rgba(148, 163, 184, 0.12) !important; }

    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 0 !important;
        min-height: 0 !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }

    [data-testid="stDecoration"] { display: none !important; }

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
        padding-left: clamp(0.65rem, 2.5vw, 1.5rem) !important;
        padding-right: clamp(0.65rem, 2.5vw, 1.5rem) !important;
        max-width: min(1280px, 100%) !important;
        width: 100% !important;
    }

    .stApp, [data-testid="stAppViewContainer"], section.main {
        overflow-x: hidden !important;
        max-width: 100vw;
    }

    [data-testid="stTable"] {
        display: block;
        width: 100%;
        max-width: 100%;
        overflow-x: auto;
        overflow-y: hidden;
        -webkit-overflow-scrolling: touch;
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-radius: 10px;
        margin-bottom: 0.35rem;
    }

    [data-testid="stTable"] table {
        width: 100%;
        min-width: 540px;
        border-collapse: collapse;
        font-family: 'JetBrains Mono', monospace;
        font-size: clamp(0.72rem, 1.8vw, 0.82rem);
    }

    [data-testid="stExpander"] [data-testid="stTable"] {
        overflow-x: auto;
    }

    [data-testid="stPyplot"] {
        width: 100% !important;
        max-width: 100% !important;
        overflow-x: auto;
    }

    [data-testid="stPyplot"] img {
        max-width: 100% !important;
        height: auto !important;
    }

    [data-testid="stDataFrame"] {
        max-width: 100%;
        overflow-x: auto;
    }

    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stSelectbox,
    [data-testid="stSidebar"] .stCheckbox {
        max-width: 100%;
        word-wrap: break-word;
    }

    @media (max-width: 1199px) {
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-size: clamp(1rem, 2.8vw, 1.35rem) !important;
        }
    }

    @media (max-width: 767px) {
        .gq-kpi-grid {
            grid-template-columns: 1fr;
        }

        .gq-mission-topbar {
            padding: 0.65rem 0.85rem;
        }

        .gq-mission-topbar-right {
            width: 100%;
        }

        .gq-live-badge {
            font-size: 0.62rem;
        }

        .stTabs [data-baseweb="tab-list"] {
            flex-wrap: wrap;
            gap: 0.4rem;
        }

        .stTabs [data-baseweb="tab"] {
            font-size: 0.82rem !important;
            padding: 0.5rem 0.85rem !important;
            min-height: 2rem;
        }

        [data-testid="stSidebar"] .stButton > button {
            font-size: 0.72rem !important;
        }
    }

    @media (max-width: 430px) {
        section.main > div.block-container,
        .stMainBlockContainer.block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }

        .gq-subheader {
            font-size: 0.82rem;
        }
    }

    [data-testid="stAppViewContainer"] > section.main { padding-top: 0 !important; }

    [data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"] { gap: 0.35rem !important; }

    [data-testid="stDataFrame"] { border: 1px solid rgba(148,163,184,0.12); border-radius: 8px; }

    [data-testid="stTable"] th {
        background: rgba(245, 156, 26, 0.1);
        color: #fbbf24;
        font-family: 'Barlow', sans-serif;
        font-weight: 600;
        font-size: 0.78rem;
        padding: 0.55rem 0.75rem;
        text-align: left;
        border-bottom: 1px solid rgba(245, 156, 26, 0.22);
    }

    [data-testid="stTable"] td {
        color: #e2e8f0;
        padding: 0.5rem 0.75rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.1);
        vertical-align: top;
    }

    [data-testid="stTable"] tr:last-child td {
        border-bottom: none;
    }

    .stAlert { background: rgba(245,156,26,0.08) !important; border-color: rgba(245,156,26,0.25) !important; }

    .st-key-sidebar_header .stMarkdown,
    .st-key-sidebar_header .stElementContainer,
    .st-key-sidebar_header [data-testid="stMarkdownContainer"] {
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
    }

    .gq-sidebar-logo-wrap {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        padding: 0.35rem 0.15rem 0.55rem;
        box-sizing: border-box;
    }

    .gq-sidebar-logo-wrap--sidebar {
        padding: 0.45rem 0.1rem 0.5rem;
    }

    .gq-sidebar-logo-wrap img {
        width: 100%;
        max-width: 168px;
        height: auto;
        display: block;
        margin: 0 auto;
        object-fit: contain;
    }

    .gq-sidebar-divider {
        height: 1px;
        background: linear-gradient(
            90deg,
            transparent 0%,
            rgba(245, 156, 26, 0.35) 20%,
            rgba(148, 163, 184, 0.25) 50%,
            rgba(245, 156, 26, 0.35) 80%,
            transparent 100%
        );
        margin: 0 0.5rem 0.85rem;
    }

    .gq-sidebar-footer-divider {
        height: 1px;
        background: linear-gradient(
            90deg,
            transparent 0%,
            rgba(245, 156, 26, 0.35) 20%,
            rgba(148, 163, 184, 0.25) 50%,
            rgba(245, 156, 26, 0.35) 80%,
            transparent 100%
        );
        margin: 0 0.35rem 0.75rem;
    }

    .st-key-sidebar_footer [data-testid="stButton"],
    .st-key-sidebar_footer .stButton {
        margin: 0 !important;
        width: 100% !important;
    }

    .st-key-sidebar_footer .stButton > button,
    .st-key-sidebar_footer button {
        width: 100% !important;
        background: rgba(15, 23, 42, 0.75) !important;
        color: #cbd5e1 !important;
        border: 1px solid rgba(245, 156, 26, 0.22) !important;
        border-radius: 8px !important;
        font-family: 'Barlow', sans-serif !important;
        font-size: 0.74rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.02em !important;
        text-transform: none !important;
        padding: 0.55rem 0.75rem !important;
        box-shadow: none !important;
    }

    .st-key-sidebar_footer .stButton > button:hover,
    .st-key-sidebar_footer button:hover {
        background: rgba(245, 156, 26, 0.1) !important;
        color: #fde68a !important;
        border-color: rgba(245, 156, 26, 0.35) !important;
    }

    .st-key-sidebar_header + div hr {
        display: none !important;
    }
</style>
"""


def inject_theme() -> None:
    st.markdown(MISSION_CSS, unsafe_allow_html=True)


def brand_logo_html(max_width: int = 190, *, sidebar: bool = False) -> str:
    """Return centred brand logo markup for landing or sidebar."""
    logo_path = Path(__file__).resolve().parent / "assets" / "greineq_logo.svg"
    svg = logo_path.read_text(encoding="utf-8")
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    wrap_class = "gq-sidebar-logo-wrap gq-sidebar-logo-wrap--sidebar" if sidebar else "gq-sidebar-logo-wrap"
    img_max = min(max_width, 168) if sidebar else max_width
    return (
        f'<div class="{wrap_class}">'
        f'<img src="data:image/svg+xml;base64,{encoded}" alt="GréineQ" '
        f'style="max-width:{img_max}px;width:100%;height:auto;" />'
        f"</div>"
    )


def _sidebar_logo_markup() -> str:
    return brand_logo_html(sidebar=True)


def render_sidebar_header() -> None:
    """Sidebar brand block: centred logo and divider."""
    with st.container(key="sidebar_header"):
        st.markdown(_sidebar_logo_markup(), unsafe_allow_html=True)
        st.markdown('<div class="gq-sidebar-divider"></div>', unsafe_allow_html=True)


def render_sidebar_footer() -> bool:
    """Fixed sidebar footer: divider and return-to-landing control."""
    with st.container(key="sidebar_footer"):
        st.markdown('<div class="gq-sidebar-footer-divider"></div>', unsafe_allow_html=True)
        return st.button(
            "← Back to Landing Page",
            key="back_overview_nav",
            help="Return to the landing page",
            width="stretch",
        )


def render_sidebar_brand() -> None:
    """Deprecated — use render_sidebar_header()."""
    render_sidebar_header()


def render_mission_topbar(
    title: str,
    subtitle: str,
    live_label: str = "Simulation Replay",
    preview_trace=None,
) -> None:
    """Dashboard header with optional Q-Agent replay animation in the centre."""
    from dashboard.dispatch_widget import render_topbar_dispatch

    safe_title = html_lib.escape(title)
    safe_subtitle = html_lib.escape(subtitle)
    safe_label = html_lib.escape(live_label)

    with st.container(key="mission_topbar"):
        col_title, col_anim, col_badge = st.columns([2.1, 2.2, 1], vertical_alignment="center")
        with col_title:
            st.markdown(
                f"""
                <div class="gq-mission-topbar-left">
                    <h2>{safe_title}</h2>
                    <p>{safe_subtitle}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_anim:
            if preview_trace is not None:
                try:
                    render_topbar_dispatch(
                        preview_trace["action"].tolist(),
                        preview_trace["time_label"].tolist(),
                        preview_trace["soc_pct"].tolist(),
                    )
                except Exception:
                    st.markdown(
                        '<div class="gq-topbar-orb-fallback" style="text-align:center;color:#f59e1a;font-size:1.5rem;">Q</div>',
                        unsafe_allow_html=True,
                    )
        with col_badge:
            st.markdown(
                f"""
                <div class="gq-mission-topbar-right">
                    <span class="gq-live-badge"><span class="gq-live-dot"></span>{safe_label}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_kpi_cards(cards: list[tuple[str, str, str | None, str | None]]) -> None:
    """Render responsive KPI grid: label, value, optional benchmark, optional help tooltip."""
    import html as html_lib

    parts: list[str] = []
    for label, value, benchmark, help_text in cards[:4]:
        bench_html = (
            f'<div class="gq-kpi-delta">{html_lib.escape(benchmark)}</div>' if benchmark else ""
        )
        title_attr = f' title="{html_lib.escape(help_text)}"' if help_text else ""
        parts.append(
            f'<div class="gq-kpi-card"{title_attr}>'
            f'<div class="gq-kpi-label">{html_lib.escape(label)}</div>'
            f'<div class="gq-kpi-value">{html_lib.escape(value)}</div>'
            f"{bench_html}</div>"
        )
    st.markdown(f'<div class="gq-kpi-grid">{"".join(parts)}</div>', unsafe_allow_html=True)


def render_policy_note(text: str) -> None:
    st.markdown(f'<p class="gq-policy-note">{text}</p>', unsafe_allow_html=True)


def render_demo_insight(text: str) -> None:
    """Highlighted insight box; supports lightweight markdown (**bold**)."""
    import re

    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    st.markdown(f'<div class="gq-insight-box">{html}</div>', unsafe_allow_html=True)


def render_system_status(panels_online: int = 24) -> None:
    st.markdown(
        f"""
        <div class="gq-system-status">
            ● Simulation active
            <span>{panels_online} solar panels · RL agent loaded · replay mode</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_twin_banner(title: str, subtitle: str) -> None:
    render_mission_topbar(title, subtitle)


def render_chart_panel_open(label: str = "Energy Flow Simulation Replay") -> None:
    st.markdown(
        f"""
        <div class="gq-chart-panel">
            <div class="gq-chart-panel-label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
