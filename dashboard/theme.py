"""GréineQ visual theme — mission-control dark (Figma Make design)."""

from __future__ import annotations

import base64
import html as html_lib
from pathlib import Path

import streamlit as st

NAVY = "#0f172a"
NAVY_PANEL = "#1e293b"
NAVY_RAISE = "#334155"
AMBER = "#f59e0b"
AMBER_DEEP = "#d97706"
AMBER_GLOW = "#fde68a"
TEXT = "#e2e8f0"
TEXT_MUTED = "#cbd5e1"
BORDER = "rgba(148, 163, 184, 0.22)"
SUCCESS = "#10b981"
DANGER = "#ef4444"
# Action badges / charts: Hold grey · Solar yellow · Grid blue · Discharge purple · Export green
CHARGE = "#eab308"
DISCHARGE = "#a855f7"
HOLD = "#64748b"
GRID_CHARGE = "#3b82f6"
EXPORT = "#10b981"

ACTION_COLORS = {
    "hold": HOLD,
    "charge": CHARGE,
    "discharge": DISCHARGE,
    "grid_charge": GRID_CHARGE,
    "export": EXPORT,
}

MISSION_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Barlow:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Barlow', sans-serif;
    }

    .stApp {
        background:
            radial-gradient(900px 480px at 8% -5%, rgba(245, 158, 11, 0.07), transparent 55%),
            radial-gradient(700px 400px at 95% 0%, rgba(16, 185, 129, 0.05), transparent 50%),
            linear-gradient(180deg, #0f172a 0%, #1e293b 48%, #0f172a 100%);
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
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
    }

    section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"].st-key-sidebar_scroll {
        flex: 1 1 auto !important;
        min-height: 0 !important;
        max-height: none !important;
        overflow-x: hidden !important;
        overflow-y: auto !important;
        overscroll-behavior: contain;
        -webkit-overflow-scrolling: touch;
        padding: 0.15rem 0.1rem 1.25rem !important;
    }

    section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"].st-key-sidebar_scroll > [data-testid="stVerticalBlock"] {
        overflow: visible !important;
        min-height: min-content !important;
        height: auto !important;
        padding-bottom: 1.5rem !important;
    }

    /* Footer lives inside the scroll region — do not pin/hide it */
    section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"].st-key-sidebar_footer {
        flex: 0 0 auto !important;
        overflow: visible !important;
        margin-top: 0.75rem !important;
        padding: 0.5rem 0.15rem 1.25rem !important;
        background: transparent !important;
        box-shadow: none !important;
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
        width: 6px;
    }

    .st-key-sidebar_scroll::-webkit-scrollbar-thumb,
    section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"].st-key-sidebar_scroll::-webkit-scrollbar-thumb {
        background: rgba(148, 163, 184, 0.4);
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

    /* Keep system-flow replay visible in the sidebar */
    section[data-testid="stSidebar"] iframe {
        display: block !important;
        max-width: 100% !important;
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
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.55rem;
        margin-bottom: 0.65rem;
        width: 100%;
    }

    .gq-kpi-card {
        background: linear-gradient(145deg, #0c1424 0%, #111827 100%);
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 10px;
        padding: 0.5rem 0.7rem 0.55rem;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
        border-top: 2px solid rgba(245, 156, 26, 0.45);
        min-width: 0;
    }

    .gq-kpi-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.62rem;
        color: #64748b;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 0.15rem;
        line-height: 1.3;
        word-wrap: break-word;
    }

    .gq-kpi-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.2rem;
        font-weight: 600;
        color: #f59c1a;
        line-height: 1.15;
        word-break: break-word;
    }

    .gq-kpi-delta {
        font-size: 0.72rem;
        color: #10b981;
        margin-top: 0.2rem;
        font-family: 'JetBrains Mono', monospace;
        line-height: 1.3;
    }

    .gq-kpi-delta.neutral { color: #cbd5e1; }

    /* Unified nav + context */
    .gq-nav-brand {
        display: flex;
        align-items: center;
        min-height: 2.6rem;
        padding-right: 0.35rem;
    }
    .gq-nav-brand img { max-height: 36px !important; }
    .gq-nav-divider {
        height: 1px;
        margin: 0.35rem 0 0.65rem;
        background: rgba(148, 163, 184, 0.2);
    }
    .gq-context-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin: 0 0 0.75rem;
        padding: 0.45rem 0.15rem;
    }
    .gq-ctx-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.28rem 0.65rem;
        border-radius: 999px;
        background: rgba(30, 41, 59, 0.95);
        border: 1px solid rgba(148, 163, 184, 0.28);
        color: #e2e8f0;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
    }
    .gq-winner-strip {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.55rem 0.85rem;
        margin: 0 0 0.7rem;
        padding: 0.65rem 0.85rem;
        border-radius: 12px;
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.28);
    }
    .gq-winner-strip-badge {
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #f59e0b;
        font-family: 'JetBrains Mono', monospace;
    }
    .gq-winner-strip-name {
        font-weight: 700;
        color: #6ee7b7;
        font-size: 1.02rem;
    }
    .gq-winner-strip-meta {
        color: #cbd5e1;
        font-size: 0.84rem;
        margin-left: auto;
    }

    /* Controller comparison HTML table */
    .gq-cmp-wrap {
        margin: 0.35rem 0 0.9rem;
        border-radius: 12px;
        border: 1px solid rgba(148, 163, 184, 0.22);
        overflow: hidden;
        background: rgba(15, 23, 42, 0.65);
    }
    table.gq-cmp-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
    }
    table.gq-cmp-table th,
    table.gq-cmp-table td {
        padding: 0.7rem 1rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.14);
        color: #e2e8f0;
    }
    table.gq-cmp-table th {
        background: rgba(30, 41, 59, 0.9);
        color: #cbd5e1;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-weight: 600;
    }
    table.gq-cmp-table th.name,
    table.gq-cmp-table td.name { text-align: left; }
    table.gq-cmp-table th.num,
    table.gq-cmp-table td.num {
        text-align: right;
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
    }
    table.gq-cmp-table th.soc,
    table.gq-cmp-table td.soc {
        text-align: left;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        color: #cbd5e1;
        min-width: 9.5rem;
    }
    table.gq-cmp-table tr.winner td {
        background: rgba(16, 185, 129, 0.1);
        font-weight: 600;
    }
    table.gq-cmp-table td.sav-pos { color: #10b981; font-weight: 600; }
    table.gq-cmp-table td.sav-neg { color: #ef4444; font-weight: 600; }
    table.gq-cmp-table tr:last-child td { border-bottom: none; }
    .soc-bar { letter-spacing: 0.02em; color: #94a3b8; }

    /* Chart tabs as segmented control */
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 0.15rem !important;
        background: rgba(30, 41, 59, 0.85);
        padding: 0.25rem;
        border-radius: 10px;
        border: 1px solid rgba(148, 163, 184, 0.2);
        width: fit-content;
        max-width: 100%;
    }
    div[data-testid="stTabs"] [data-baseweb="tab"] {
        border-radius: 8px !important;
        padding: 0.4rem 0.9rem !important;
    }
    div[data-testid="stTabs"] [aria-selected="true"] {
        background: rgba(245, 158, 11, 0.18) !important;
        color: #fde68a !important;
    }

    /* Primary CTA contrast in sidebar */
    [data-testid="stSidebar"] .stButton > button[kind="primary"],
    [data-testid="stSidebar"] button[data-testid="baseButton-primary"] {
        background: linear-gradient(180deg, #f59e0b 0%, #d97706 100%) !important;
        color: #0f172a !important;
        border: none !important;
        font-weight: 700 !important;
        letter-spacing: 0.02em;
    }

    [data-testid="stMetricDelta"] svg { display: none; }
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.15rem !important;
        color: #f8fafc !important;
    }
    [data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
    }
    [data-testid="stMetricDelta"] {
        color: #10b981 !important;
    }

    .gq-compact-topbar {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.45rem 1rem;
        padding: 0.25rem 0 0.5rem;
        margin: 0 0 0.35rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.14);
    }

    .gq-compact-topbar .gq-ct-title {
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 700;
        font-size: 1rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #f8fafc;
        margin: 0;
    }

    .gq-compact-topbar .gq-ct-meta {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        color: #94a3b8;
    }

    .gq-compact-topbar .gq-ct-action {
        margin-left: auto;
        font-size: 0.78rem;
        color: #fde68a;
        font-weight: 600;
    }

    .gq-winner-line {
        margin: 0.1rem 0 0.5rem;
        padding: 0.4rem 0.65rem;
        border-radius: 8px;
        background: rgba(34, 197, 94, 0.08);
        border: 1px solid rgba(34, 197, 94, 0.22);
        color: #e2e8f0;
        font-size: 0.86rem;
    }

    .gq-winner-line strong { color: #86efac; }

    .gq-winner-badge {
        margin: 0.15rem 0 0.65rem;
        padding: 0.55rem 0.8rem;
        border-radius: 10px;
        background: rgba(34, 197, 94, 0.07);
        border: 1px solid rgba(34, 197, 94, 0.2);
    }
    .gq-winner-badge-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #bbf7d0;
        margin-bottom: 0.15rem;
    }
    .gq-winner-badge-sub {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        color: #cbd5e1;
    }

    .gq-action-badge {
        display: inline-block;
        padding: 0.12rem 0.45rem;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 600;
        white-space: nowrap;
    }

    table.gq-step-inspector {
        width: 100%;
        border-collapse: collapse;
        margin: 0.4rem 0 0.8rem;
        font-size: 0.88rem;
    }
    table.gq-step-inspector th,
    table.gq-step-inspector td {
        padding: 0.45rem 0.55rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.16);
        text-align: left;
        color: #e2e8f0;
    }
    table.gq-step-inspector th {
        color: #cbd5e1;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .gq-live-banner {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.75rem;
        margin: 0.35rem 0 0.85rem;
    }
    .gq-live-banner-note {
        color: #cbd5e1;
        font-size: 0.85rem;
    }
    .gq-decision-card {
        margin-top: 0.85rem;
        padding: 0.75rem 0.9rem;
        border-radius: 10px;
        background: linear-gradient(145deg, #0c1424 0%, #111827 100%);
        border: 1px solid rgba(245, 156, 26, 0.28);
        border-left: 3px solid #f59c1a;
    }
    .gq-decision-title {
        font-weight: 600;
        color: #fde68a;
        margin-bottom: 0.25rem;
    }
    .gq-decision-sub {
        color: #cbd5e1;
        font-size: 0.86rem;
        line-height: 1.45;
    }

    .gq-settings-dirty {
        margin: 0.4rem 0 0.75rem;
        padding: 0.55rem 0.75rem;
        border-radius: 8px;
        background: rgba(245, 158, 26, 0.1);
        border: 1px solid rgba(245, 158, 26, 0.35);
        color: #fde68a;
        font-size: 0.88rem;
    }

    /* Stronger caption contrast */
    [data-testid="stCaptionContainer"] p,
    .stCaption, div[data-testid="stCaption"] {
        color: #cbd5e1 !important;
    }

    @media (max-width: 900px) {
        .gq-kpi-grid { grid-template-columns: 1fr; }
    }

    /* ---- Play vs Agent ---- */
    .gq-play-tagline {
        color: #e2e8f0 !important;
        font-size: 0.98rem;
        margin: 0.15rem 0 0.45rem;
        line-height: 1.4;
    }
    .gq-play-meta {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        color: #cbd5e1;
        margin-bottom: 0.55rem;
    }
    .gq-play-progress {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin: 0.15rem 0 0.65rem;
        flex-wrap: wrap;
    }
    .gq-play-progress-bar {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: #f59e1a;
        letter-spacing: -0.04em;
        overflow: hidden;
        white-space: nowrap;
    }
    .gq-play-progress-pct {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: #94a3b8;
    }
    .gq-energy-badge {
        display: inline-block;
        margin: 0.25rem 0 0.65rem;
        padding: 0.28rem 0.65rem;
        border-radius: 8px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .gq-energy-badge.deficit {
        background: rgba(248, 113, 113, 0.12);
        border: 1px solid rgba(248, 113, 113, 0.35);
        color: #fecaca;
    }
    .gq-energy-badge.surplus {
        background: rgba(34, 197, 94, 0.12);
        border: 1px solid rgba(34, 197, 94, 0.35);
        color: #bbf7d0;
    }
    .gq-energy-badge.flat {
        background: rgba(148, 163, 184, 0.12);
        border: 1px solid rgba(148, 163, 184, 0.28);
        color: #cbd5e1;
    }
    .gq-play-feedback {
        margin: 0.35rem 0 0.55rem;
        padding: 0.55rem 0.7rem;
        border-radius: 10px;
        background: rgba(245, 158, 26, 0.08);
        border: 1px solid rgba(245, 158, 26, 0.28);
    }
    .gq-play-feedback.agent {
        background: rgba(99, 102, 241, 0.1);
        border-color: rgba(99, 102, 241, 0.3);
    }
    .gq-play-feedback-title {
        font-weight: 600;
        color: #fde68a;
        margin-bottom: 0.15rem;
    }
    .gq-play-feedback.agent .gq-play-feedback-title { color: #c7d2fe; }
    .gq-play-feedback-body {
        font-size: 0.84rem;
        color: #e2e8f0;
        line-height: 1.4;
    }

    .st-key-play_act_hold button {
        background: #64748b !important;
        border-color: #64748b !important;
        color: #f8fafc !important;
    }
    .st-key-play_act_charge button {
        background: #eab308 !important;
        border-color: #ca8a04 !important;
        color: #0f172a !important;
    }
    .st-key-play_act_discharge button {
        background: #a855f7 !important;
        border-color: #9333ea !important;
        color: #f8fafc !important;
    }
    .st-key-play_act_grid button {
        background: #3b82f6 !important;
        border-color: #2563eb !important;
        color: #f8fafc !important;
    }
    .st-key-play_act_export button {
        background: #22c55e !important;
        border-color: #16a34a !important;
        color: #0f172a !important;
    }
    .st-key-play_act_hold button:disabled,
    .st-key-play_act_charge button:disabled,
    .st-key-play_act_discharge button:disabled,
    .st-key-play_act_grid button:disabled,
    .st-key-play_act_export button:disabled {
        opacity: 0.42 !important;
    }
    .st-key-play_act_reset button {
        font-size: 1.25rem !important;
        font-weight: 600 !important;
        min-height: 2.5rem !important;
        padding-left: 0.35rem !important;
        padding-right: 0.35rem !important;
        color: #cbd5e1 !important;
        border-color: rgba(148, 163, 184, 0.35) !important;
        background: rgba(15, 23, 42, 0.65) !important;
    }

    .gq-results-headline {
        margin: 0.35rem 0 0.85rem;
        padding: 0.7rem 0.9rem;
        border-radius: 10px;
        background: rgba(34, 197, 94, 0.07);
        border: 1px solid rgba(34, 197, 94, 0.22);
    }
    .gq-results-headline-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #bbf7d0;
        margin-bottom: 0.2rem;
    }
    .gq-results-headline-sub {
        color: #e2e8f0;
        font-size: 0.9rem;
        line-height: 1.4;
    }
    .gq-results-diagnostic {
        margin: 0.15rem 0 0.85rem;
        padding: 0.55rem 0.75rem;
        border-radius: 8px;
        background: rgba(248, 113, 113, 0.08);
        border: 1px solid rgba(248, 113, 113, 0.28);
        color: #fecaca;
        font-size: 0.88rem;
    }
    .gq-results-diagnostic-note {
        display: block;
        margin-top: 0.2rem;
        color: #cbd5e1;
        font-size: 0.78rem;
    }
    .gq-interpret-card {
        height: 100%;
        min-height: 300px;
        margin-top: 0.2rem;
        padding: 0.85rem 1rem;
        border-radius: 12px;
        background: linear-gradient(160deg, #0c1424 0%, #111827 100%);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-left: 3px solid #f59e1a;
    }
    .gq-interpret-title {
        font-weight: 700;
        color: #fde68a;
        margin-bottom: 0.55rem;
        font-size: 1rem;
    }
    .gq-interpret-card ul {
        margin: 0 0 0.75rem 1.1rem;
        padding: 0;
        color: #e2e8f0;
        font-size: 0.88rem;
        line-height: 1.5;
    }
    .gq-interpret-card li { margin-bottom: 0.4rem; }
    .gq-interpret-next {
        padding-top: 0.55rem;
        border-top: 1px solid rgba(148, 163, 184, 0.18);
        color: #cbd5e1;
        font-size: 0.86rem;
        line-height: 1.45;
    }

    .gq-results-loader {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        min-height: 220px;
        margin: 0.75rem 0 1.25rem;
        padding: 1.5rem 1rem;
        border-radius: 14px;
        border: 1px solid rgba(148, 163, 184, 0.18);
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.92), rgba(12, 20, 36, 0.98));
    }

    .gq-results-loader-spinner {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        border: 3px solid rgba(148, 163, 184, 0.25);
        border-top-color: #fbbf24;
        animation: gq-spin 0.8s linear infinite;
    }

    .gq-results-loader-text {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 1.15rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #f8fafc;
    }

    .gq-results-loader-sub {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: #94a3b8;
    }

    @keyframes gq-spin {
        to { transform: rotate(360deg); }
    }

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

    /* One scrollbar only: Streamlit's dataframe already scrolls internally */
    [data-testid="stDataFrame"],
    [data-testid="stDataFrame"] > div,
    [data-testid="stExpander"] [data-testid="stDataFrame"] {
        max-width: 100%;
        overflow: visible !important;
    }

    [data-testid="stDataFrame"] [data-testid="stDataFrameResizable"] {
        overflow: auto !important;
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
        margin: 0 0.35rem 0.55rem;
    }

    .st-key-sidebar_footer [data-testid="stCaptionContainer"] {
        margin: 0 0 0.15rem !important;
        text-align: center;
    }

    .st-key-sidebar_footer iframe {
        display: block !important;
        margin: 0 auto !important;
        min-height: 160px !important;
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


def render_sidebar_footer(preview_trace=None, *, preview_label: str | None = None) -> None:
    """Pinned sidebar footer: energy-flow replay animation (no back button)."""
    with st.container(key="sidebar_footer"):
        st.markdown('<div class="gq-sidebar-footer-divider"></div>', unsafe_allow_html=True)
        if preview_trace is None or len(preview_trace) == 0:
            return
        try:
            from dashboard.dispatch_widget import render_topbar_dispatch

            caption = f"System flow · {preview_label}" if preview_label else "System flow"
            st.caption(caption)
            render_topbar_dispatch(
                preview_trace["action"].tolist(),
                preview_trace["time_label"].tolist(),
                preview_trace["soc_pct"].tolist(),
                show_action_badge=False,
            )
        except Exception:
            st.caption("Replay unavailable")


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


def render_compact_topbar(
    title: str,
    day: str,
    action_label: str | None = None,
    status: str = "Replay ready",
) -> None:
    """One-row digital-twin header (no embedded animation)."""
    safe_title = html_lib.escape(title)
    safe_day = html_lib.escape(str(day))
    safe_status = html_lib.escape(status)
    action_html = (
        f'<span class="gq-ct-action">{html_lib.escape(action_label)}</span>'
        if action_label
        else ""
    )
    st.markdown(
        f"""
        <div class="gq-compact-topbar">
            <h2 class="gq-ct-title">{safe_title}</h2>
            <span class="gq-ct-meta">Day {safe_day}</span>
            <span class="gq-ct-meta">{safe_status}</span>
            {action_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_winner_line(text: str) -> None:
    import re

    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    st.markdown(f'<div class="gq-winner-line">{html}</div>', unsafe_allow_html=True)


def render_kpi_cards(cards: list[tuple[str, str, str | None, str | None]]) -> None:
    """Render compact KPI grid (up to 3 cards)."""
    import html as html_lib

    parts: list[str] = []
    for label, value, benchmark, help_text in cards[:3]:
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
