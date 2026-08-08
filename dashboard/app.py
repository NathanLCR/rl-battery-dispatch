"""GréineQ — Streamlit digital twin dashboard."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config import load_config
from src.data_loader import get_episode, load_customer_dataset
from src.constants import ACTION_NAMES
from src.discretizer import fit_discretizer, state_index
from src.environment import MicrogridEnv
from src.live_feed import LiveFeedError, current_local_hour, fetch_latest_price, typical_pv_load_for_time
from src.oracle import no_battery_import_cost, oracle_perfect_foresight_import
from src.replay import q_values_for_state, trace_episode
from src.rule_baseline import greedy_self_consumption_action, price_arbitrage_action_fn, rule_action
from src.train import greedy_action_fn, load_trained_agent
from dashboard.landing_animation import pick_demo_day
from dashboard.landing_page import render_landing_body, render_landing_ctas, render_landing_header
from dashboard.play_vs_agent import render_play_vs_agent
from dashboard.theme import (
    ACTION_COLORS,
    HOLD,
    inject_theme,
    render_kpi_cards,
    render_sidebar_footer,
    render_sidebar_header,
)
from dashboard.twin_panels import (
    render_chart_tabs,
    render_comparison_table,
    render_context_toolbar,
    render_detailed_metrics_tabs,
    render_live_price_monitor,
    render_timestep_inspector,
    render_winner_kpi_strip,
)

DEFAULT_Q = "Q_q_learning_20260704_115627_main.npy"
DEFAULT_SARSA = "Q_sarsa_20260704_115834_main.npy"

SPLIT_LABELS = {
    "test": "Test days (held out)",
    "val": "Validation days",
    "train": "Training days",
}
SIMULATION_DATASET_HELP = (
    "Which group of historical days to replay. Test days were not used for training — "
    "best for demos and fair comparison."
)
REWARD_LABELS = {
    "battery_aware": "Cost + battery wear",
    "cost_only": "Grid cost only",
}
ACTION_DISPLAY = {
    "hold": "Hold",
    "charge": "Solar charge",
    "discharge": "Discharge",
    "grid_charge": "Grid charge",
    "export": "Export",
}

# Full internal policy name → short table label (one glossary for Twin / Play / tables)
POLICY_SHORT_NAMES = {
    "Greedy 5-action (current price)": "Greedy (5-action)",
    "Current-price Q-Learning": "Current Q",
    "Privileged Q-Learning (4h foresight)": "Privileged Q — true 4h signal",
    "Greedy self-consumption baseline": "Solar-only greedy",
    "Rule-based baseline": "Tertile rule",
    "SARSA": "SARSA",
    "Double Q-Learning": "Double Q",
}

POLICY_DETAIL_COLUMNS = {
    "grid_import_kwh": "Grid import (kWh)",
    "export_kwh": "Export (kWh)",
    "export_revenue_aud": "Export revenue (AUD)",
    "grid_charge_cost_aud": "Grid-charge cost (AUD)",
    "net_arbitrage_profit_aud": "Arbitrage balance (AUD)",
    "self_consumption_rate": "Solar self-use (%)",
    "self_sufficiency": "Self-sufficiency (%)",
    "battery_throughput_kwh": "Throughput (kWh)",
    "n_grid_charge_actions": "# grid-charge steps",
    "n_export_actions": "# export steps",
    "total_reward": "Episode reward",
    "solar_waste_kwh": "Solar waste (kWh)",
    "evening_peak_import_kwh": "Evening import (kWh)",
}
TRACE_COLUMN_LABELS = {
    "step": "Timestep",
    "time_label": "Time of day",
    "action": "Action",
    "soc_pct": "Battery SOC (%)",
    "pv_kwh": "Solar (kWh)",
    "load_kwh": "Demand (kWh)",
    "price_per_kwh": "Wholesale (AUD/kWh)",
    "grid_import_kwh": "Grid import (kWh)",
    "solar_waste_kwh": "Solar waste (kWh)",
    "reward": "Step score",
    "state": "State index",
}


@st.cache_resource(show_spinner="Loading GréineQ data…")
def load_resources():
    """Load dataset, day split, and discretiser thresholds once per session."""
    cfg = load_config()
    df, split = load_customer_dataset(cfg)
    thresholds = fit_discretizer(df, cfg)
    return cfg, df, split, thresholds


def list_models(cfg) -> list[Path]:
    """Return trained Q-table files, newest first."""
    models_dir = cfg.results_models
    if not models_dir.exists():
        return []
    return sorted(models_dir.glob("Q_*.npy"), key=lambda p: p.stat().st_mtime, reverse=True)


def models_for_agent(agent: str, all_models: list[Path]) -> list[Path]:
    """Filter model files by agent type inferred from the filename."""
    name = agent.lower()
    if name == "sarsa":
        filtered = [p for p in all_models if "sarsa" in p.name.lower()]
    elif name == "double_q_learning":
        filtered = [p for p in all_models if "double_q" in p.name.lower()]
    else:
        filtered = [
            p for p in all_models
            if "q_learning" in p.name.lower()
            and "double_q" not in p.name.lower()
            and "sarsa" not in p.name.lower()
        ]
    return filtered or all_models


@st.cache_resource(show_spinner="Loading trained agent…")
def load_rl_agent(agent_name: str, model_path: str, _cache_key: str):
    cfg = load_config()
    return load_trained_agent(agent_name, Path(model_path), cfg)


def _show_results_loader(message: str = "Loading results…") -> None:
    """Always-visible loading panel (spinner alone can flash too briefly)."""
    st.markdown(
        f"""
        <div class="gq-results-loader">
            <div class="gq-results-loader-spinner"></div>
            <div class="gq-results-loader-text">{message}</div>
            <div class="gq-results-loader-sub">Comparing controllers · please wait</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def greedy_policy_fn(thresholds, cfg):
    def policy(env: MicrogridEnv) -> int:
        row = env.episode_df.iloc[env._step_idx]
        return greedy_self_consumption_action(
            env._soc_pct,
            float(row["pv_kwh"]),
            float(row["load_kwh"]),
            thresholds,
            min_soc_pct=cfg.min_soc_pct,
            max_soc_pct=cfg.max_soc_pct,
        )

    return policy


def rule_policy_fn(thresholds):
    def policy(env: MicrogridEnv) -> int:
        row = env.episode_df.iloc[env._step_idx]
        return rule_action(
            env._soc_pct,
            float(row["pv_kwh"]),
            float(row["load_kwh"]),
            thresholds,
        )

    return policy


def arbitrage_rule_policy_fn():
    """CA2 heuristic: greedy self-consumption plus price-timed grid-charge/export."""
    return price_arbitrage_action_fn


def plot_day(
    traces: dict[str, pd.DataFrame],
    episode_df: pd.DataFrame,
    retail_margin: float,
    *,
    dark: bool = False,
) -> plt.Figure:
    """Four-panel day view: load/PV, price, SOC, and actions."""
    n_steps = len(episode_df)
    timesteps = list(range(1, n_steps + 1))
    x_max = max(48, n_steps)

    if dark:
        sunny = {
            "figure.facecolor": "#070d1a",
            "axes.facecolor": "#0c1424",
            "axes.edgecolor": "#1e293b",
            "axes.labelcolor": "#94a3b8",
            "text.color": "#e2e8f0",
            "xtick.color": "#64748b",
            "ytick.color": "#64748b",
            "grid.color": "#1e293b",
            "legend.facecolor": "#0c1424",
            "legend.edgecolor": "#334155",
            "legend.labelcolor": "#e2e8f0",
        }
        solar_color, load_color = "#f59c1a", "#6366f1"
        wholesale_color, retail_color = "#f87171", "#fb923c"
    else:
        sunny = {
            "figure.facecolor": "#FFFBEB",
            "axes.facecolor": "#FFFDF7",
            "axes.edgecolor": "#FDE68A",
            "axes.labelcolor": "#78350F",
            "text.color": "#78350F",
            "xtick.color": "#92400E",
            "ytick.color": "#92400E",
            "grid.color": "#FDE68A",
            "legend.framealpha": 0.92,
        }
        solar_color, load_color = "#F59E0B", "#0284C7"
        wholesale_color, retail_color = "#FB7185", "#E11D48"

    policy_colors = ["#f59c1a", "#6366f1", "#22c55e", "#fb923c", "#a78bfa"]

    with plt.rc_context(sunny):
        fig_h = 9.5 if len(traces) <= 2 else 10.5
        fig, axes = plt.subplots(4, 1, figsize=(10, fig_h), sharex=True)
        fig.subplots_adjust(hspace=0.38, top=0.98, bottom=0.08)

        retail_price = episode_df["price_per_kwh"] + retail_margin
        legend_fs = 7 if len(traces) > 2 else 8

        ax = axes[0]
        ax.fill_between(timesteps, episode_df["pv_kwh"], alpha=0.25, color=solar_color)
        ax.plot(timesteps, episode_df["pv_kwh"], label="Solar generation", color=solar_color, linewidth=2.2)
        ax.plot(timesteps, episode_df["load_kwh"], label="Household demand", color=load_color, linewidth=2.0)
        ax.set_ylabel("Energy (kWh)", fontsize=9)
        ax.legend(loc="upper right", fontsize=legend_fs, frameon=True, ncol=1)
        ax.grid(True, alpha=0.45)
        ax.set_title("Solar generation and household demand", fontweight="600", pad=8, fontsize=10)
        ax.set_xlim(0.5, x_max + 0.5)
        ax.tick_params(labelsize=8)

        ax = axes[1]
        ax.plot(timesteps, episode_df["price_per_kwh"], label="Wholesale price", color=wholesale_color, linestyle="--", linewidth=1.6)
        ax.plot(timesteps, retail_price, label="Estimated retail price", color=retail_color, linewidth=2.0)
        ax.set_ylabel("Price (AUD/kWh)", fontsize=9)
        ax.legend(loc="upper right", fontsize=legend_fs, frameon=True, ncol=1)
        ax.grid(True, alpha=0.45)
        ax.set_title("Electricity price", fontweight="600", pad=8, fontsize=10)
        ax.tick_params(labelsize=8)

        ax = axes[2]
        for i, (name, trace) in enumerate(traces.items()):
            ax.plot(
                trace["step"],
                trace["soc_pct"],
                label=_short_policy(name),
                linewidth=2.0,
                color=policy_colors[i % len(policy_colors)],
            )
        ax.set_ylabel("Battery SOC (%)", fontsize=9)
        ax.set_ylim(0, 100)
        ax.legend(loc="upper right", fontsize=legend_fs, frameon=True, ncol=1)
        ax.grid(True, alpha=0.45)
        ax.set_title("Battery state of charge (SOC)", fontweight="600", pad=8, fontsize=10)
        ax.tick_params(labelsize=8)

        ax = axes[3]
        bar_w = 0.25
        for i, (name, trace) in enumerate(traces.items()):
            offset = (i - len(traces) / 2 + 0.5) * bar_w
            colors = [ACTION_COLORS.get(a, HOLD) for a in trace["action"]]
            xs = trace["step"].tolist()
            ax.bar([xi + offset for xi in xs], [1] * len(xs), width=bar_w, color=colors, alpha=0.9, label=_short_policy(name))
        ax.set_yticks([])
        ax.set_xlabel("Time of day (30-minute timesteps)", fontsize=9)
        ax.set_title(
            "Actions by controller",
            fontweight="600",
            pad=8,
            fontsize=9,
        )
        ax.set_xlim(0.5, x_max + 0.5)
        ax.tick_params(labelsize=8)

        tick_steps = [s for s in (1, 12, 24, 36, n_steps) if s <= n_steps]
        tick_labels = []
        for step in tick_steps:
            ts = episode_df.iloc[step - 1]["timestamp"]
            tick_labels.append(ts.strftime("%H:%M"))
        axes[-1].set_xticks(tick_steps)
        axes[-1].set_xticklabels(tick_labels, fontsize=7)

        fig.tight_layout()
    return fig


def _render_chart_panel_label(label: str = "Energy Flow Simulation Replay") -> None:
    st.markdown(
        f"""
        <div class="gq-chart-panel">
            <div class="gq-chart-panel-label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _format_action(action: str) -> str:
    return ACTION_DISPLAY.get(str(action).lower(), str(action))


def _pick_preview_trace(traces: dict[str, pd.DataFrame] | None) -> tuple[str | None, pd.DataFrame | None]:
    if not traces:
        return None, None
    preferred = (
        "Greedy 5-action (current price)",
        "Current-price Q-Learning",
        "Privileged Q-Learning (4h foresight)",
        "Greedy self-consumption baseline",
        "SARSA",
        "Double Q-Learning",
        "Rule-based baseline",
    )
    name = next((n for n in preferred if n in traces), next(iter(traces), None))
    return (name, traces.get(name)) if name else (None, None)


def _short_policy(name: str) -> str:
    return POLICY_SHORT_NAMES.get(name, name)


def _fmt2(value: object, suffix: str = "") -> str:
    try:
        return f"{float(value):.2f}{suffix}"
    except (TypeError, ValueError):
        return "—"


def _format_policy_metric(column: str, value: object) -> str:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return "—"
    if column == "total_reward":
        return f"{x:.2f}"
    if column.endswith("_aud"):
        return f"{x:.2f}"
    if column in ("grid_import_kwh", "solar_waste_kwh", "evening_peak_import_kwh", "export_kwh", "battery_throughput_kwh"):
        return f"{x:.2f}"
    if column in ("self_consumption_rate", "self_sufficiency"):
        return f"{x * 100:.2f}%"
    if column == "final_soc_pct":
        return f"{x:.2f}%"
    if column.endswith("_actions"):
        return f"{int(round(x))}"
    return f"{x:.2f}"


def build_policy_display_table(
    summary_df: pd.DataFrame,
    metric_cols: list[str],
    column_labels: dict[str, str],
) -> pd.DataFrame:
    """Format policy summary metrics for presentation tables."""
    out = summary_df.reset_index()
    if "policy" in out.columns:
        out = out.rename(columns={"policy": "Policy"})
    keep = ["Policy"] + [c for c in metric_cols if c in out.columns]
    out = out[keep].copy()
    out["Policy"] = out["Policy"].map(_short_policy)
    for col in metric_cols:
        if col in out.columns:
            out[col] = out[col].map(lambda v, c=col: _format_policy_metric(c, v))
    rename = {"Policy": "Policy", **{k: column_labels[k] for k in metric_cols if k in column_labels}}
    return out.rename(columns=rename)


def render_policy_comparison_table(summary_df: pd.DataFrame, no_bat: float) -> None:
    """Controller table + tabbed detailed metrics."""
    render_comparison_table(summary_df, no_bat, _short_policy)
    render_detailed_metrics_tabs(summary_df, _short_policy)


def format_trace(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "step", "time_label", "action", "soc_pct", "pv_kwh", "load_kwh",
        "price_per_kwh", "grid_import_kwh", "solar_waste_kwh", "reward",
    ]
    out = df[[c for c in cols if c in df.columns]].copy()
    if "action" in out.columns:
        out["action"] = out["action"].map(_format_action)
    out["soc_pct"] = out["soc_pct"].map(lambda x: f"{float(x):.2f}")
    out["pv_kwh"] = out["pv_kwh"].map(lambda x: f"{float(x):.2f}")
    out["load_kwh"] = out["load_kwh"].map(lambda x: f"{float(x):.2f}")
    out["price_per_kwh"] = out["price_per_kwh"].map(lambda x: f"{float(x):.2f}")
    out["grid_import_kwh"] = out["grid_import_kwh"].map(lambda x: f"{float(x):.2f}")
    out["solar_waste_kwh"] = out["solar_waste_kwh"].map(lambda x: f"{float(x):.2f}")
    out["reward"] = out["reward"].map(lambda x: f"{float(x):.2f}")
    rename = {k: v for k, v in TRACE_COLUMN_LABELS.items() if k in out.columns}
    return out.rename(columns=rename)


def _friendly_model_label(path: Path, agent_label: str) -> str:
    """Turn a Q-table filename into a presentation-friendly label."""
    match = re.search(r"(\d{8})", path.stem)
    if match:
        trained = datetime.strptime(match.group(1), "%Y%m%d").strftime("%d %b %Y")
        return f"{agent_label} model — trained {trained}"
    return f"{agent_label} model"


def _winner_summary(summary_df: pd.DataFrame, no_bat: float) -> tuple[str, str]:
    """Return (short winner line, longer why text)."""
    if summary_df.empty:
        return ("No policies selected.", "")
    best_name = summary_df["grid_cost_aud"].idxmin()
    best_cost = float(summary_df.loc[best_name, "grid_cost_aud"])
    saved = no_bat - best_cost
    short = (
        f"**Winner: {_short_policy(str(best_name))}** — "
        f"lowest net cost AUD {best_cost:.2f} "
        f"(saves AUD {saved:.2f} vs no battery)."
    )
    why = (
        f"**What won:** {_short_policy(str(best_name))} had the lowest net electricity cost "
        f"(AUD {best_cost:.2f}) on this day.\n\n"
        f"**Vs no battery:** AUD {no_bat:.2f} → saved AUD {saved:.2f}.\n\n"
        "**Caveat:** Under this experimental wholesale export tariff, simple self-use + "
        "price heuristics often beat tabular RL when foresight is coarse."
    )
    return short, why


def _model_selectbox(label: str, agent_label: str, models: list[Path], default_name: str) -> str | None:
    names = [p.name for p in models]
    if not names:
        return None
    default = default_name if default_name in names else names[0]
    by_name = {p.name: p for p in models}
    return st.selectbox(
        label,
        names,
        index=names.index(default),
        format_func=lambda n: _friendly_model_label(by_name[n], agent_label),
    )


def main() -> None:
    st.set_page_config(
        page_title="GréineQ — Digital Twin",
        layout="wide",
        page_icon="☀️",
        initial_sidebar_state="expanded",
    )
    inject_theme()

    if "view" not in st.session_state:
        st.session_state.view = "home"

    try:
        if st.session_state.view == "home":
            _hide_landing_sidebar()
            _render_landing()
        elif st.session_state.view == "play":
            _ensure_dashboard_sidebar()
            _render_play()
        elif st.session_state.view == "results":
            _ensure_dashboard_sidebar()
            _render_results()
        elif st.session_state.view == "live":
            _ensure_dashboard_sidebar()
            _render_live()
        else:
            _ensure_dashboard_sidebar()
            _render_app()
    except Exception as exc:
        st.error(f"Dashboard failed to load: {exc}")
        st.info(
            "Run from the project folder:\n\n"
            "`cd rl-battery-dispatch`\n\n"
            "`python -m streamlit run dashboard/app.py`\n\n"
            "Or double-click **`run_dashboard.bat`** — then open **http://localhost:8501**"
        )


DEMO_VERSION = "live-html-v2-arbitrage"


@st.cache_data(show_spinner="Loading agent animation…")
def get_demo_trace(_version: str) -> tuple[object, str]:
    """Load one-day price-arbitrage trace for the landing dispatch animation
    (CA2: showcases grid-charge/export alongside the CA1 solar-only actions)."""
    cfg, df, split, thresholds = load_resources()
    test_days = sorted(split.test)
    day = pick_demo_day(df, test_days)
    episode_df = get_episode(df, day)
    policy = arbitrage_rule_policy_fn()
    trace, _ = trace_episode(episode_df, thresholds, policy, cfg)
    return trace, day


def _hide_landing_sidebar() -> None:
    """Overview is full-width; settings sidebar appears only inside the dashboard."""
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _ensure_dashboard_sidebar() -> None:
    """Keep replay/settings sidebar open on laptop/desktop; allow collapse on small screens."""
    st.markdown(
        """
        <style>
        @media (min-width: 768px) {
            [data-testid="stSidebar"] {
                display: block !important;
                min-width: min(20rem, 28vw) !important;
                transform: translateX(0px) !important;
                visibility: visible !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_landing() -> None:
    # Logo + tagline, then compact CTAs, then hero replay
    render_landing_header(show_cta=False, inject_css=True)
    twin_clicked, play_clicked = render_landing_ctas(inject_css=False)
    if twin_clicked:
        st.session_state.view = "twin"
        st.rerun()
    if play_clicked:
        st.session_state.view = "play"
        st.rerun()
    with st.spinner("Loading day replay…"):
        trace, demo_day = get_demo_trace(DEMO_VERSION)
    render_landing_body(trace, demo_day)


def _simulate_episode(
    cfg,
    df: pd.DataFrame,
    thresholds,
    *,
    day: str,
    reward_mode: str,
    show_greedy: bool,
    show_rule: bool,
    show_arbitrage: bool,
    show_q: bool,
    show_q_privileged: bool,
    show_sarsa: bool,
    show_dq: bool,
    q_model_name: str | None,
    q_priv_model_name: str | None,
    sarsa_model_name: str | None,
    dq_model_name: str | None,
) -> tuple[pd.DataFrame | None, dict[str, object], dict[str, pd.DataFrame], list[dict], float, float, int]:
    """Build policy traces for the selected simulation day."""
    step_count = len(df[df["episode_day"] == day])
    if step_count != 48:
        return None, {}, {}, [], 0.0, 0.0, step_count

    try:
        episode_df = get_episode(df, day)
    except ValueError:
        return None, {}, {}, [], 0.0, 0.0, step_count

    no_bat = no_battery_import_cost(episode_df, cfg)
    oracle = oracle_perfect_foresight_import(episode_df, cfg)

    forecast_model = None
    if show_q_privileged and cfg.forecast_mode == "forecast":
        from src.price_forecast import PriceForecastModel, fit_price_forecast

        fp = cfg.artifacts_dir / "price_forecast.json"
        if fp.exists():
            forecast_model = PriceForecastModel.load(fp)
        else:
            forecast_model = fit_price_forecast(
                df,
                horizon_steps=cfg.forecast_horizon_steps,
                persistence_alpha=cfg.forecast_persistence_alpha,
                noise_scale=cfg.forecast_noise_scale,
            )

    # (policy_name, action_fn, privileged, foresight_mode)
    policies: dict[str, tuple[object, bool, str]] = {}
    if show_greedy:
        policies["Greedy self-consumption baseline"] = (greedy_policy_fn(thresholds, cfg), False, "none")
    if show_rule:
        policies["Rule-based baseline"] = (rule_policy_fn(thresholds), False, "none")
    if show_arbitrage:
        policies["Greedy 5-action (current price)"] = (arbitrage_rule_policy_fn(), False, "none")
    if show_q and q_model_name:
        q_agent = load_rl_agent("q_learning", str(cfg.results_models / q_model_name), q_model_name)
        policies["Current-price Q-Learning"] = (greedy_action_fn(q_agent), False, "none")
    if show_q_privileged and q_priv_model_name:
        qp_agent = load_rl_agent(
            "q_learning", str(cfg.results_models / q_priv_model_name), q_priv_model_name
        )
        fm = cfg.forecast_mode if cfg.forecast_mode in ("oracle", "forecast") else "forecast"
        policies["Privileged Q-Learning (4h foresight)"] = (greedy_action_fn(qp_agent), True, fm)
    if show_sarsa and sarsa_model_name:
        s_agent = load_rl_agent("sarsa", str(cfg.results_models / sarsa_model_name), sarsa_model_name)
        policies["SARSA"] = (greedy_action_fn(s_agent), False, "none")
    if show_dq and dq_model_name:
        dq_agent = load_rl_agent("double_q_learning", str(cfg.results_models / dq_model_name), dq_model_name)
        policies["Double Q-Learning"] = (greedy_action_fn(dq_agent), False, "none")

    traces: dict[str, pd.DataFrame] = {}
    summaries: list[dict] = []
    if policies:
        for name, (policy, privileged, foresight) in policies.items():
            trace, summary = trace_episode(
                episode_df,
                thresholds,
                policy,
                cfg,
                reward_mode,
                privileged=privileged,
                foresight_mode=foresight,
                forecast_model=forecast_model if foresight == "forecast" else None,
            )
            trace["policy"] = name
            traces[name] = trace
            summary["policy"] = name
            summaries.append(summary)

    policy_fns = {name: fn for name, (fn, _, _) in policies.items()}
    return episode_df, policy_fns, traces, summaries, no_bat, oracle, step_count


@st.cache_data(ttl=30, show_spinner=False)
def get_live_price():
    """Cached live AEMO NSW1 price fetch (30s TTL). Returns None on any failure —
    live mode is a best-effort add-on and must never break the core dashboard."""
    try:
        return fetch_latest_price()
    except LiveFeedError:
        return None


def render_live_signal_panel(cfg, df, thresholds, q_models: list[Path]) -> None:
    """Live AEMO panel — used by Live Price Monitor view only."""
    render_live_price_monitor(
        cfg,
        df,
        thresholds,
        q_models,
        get_live_price=get_live_price,
        load_rl_agent=load_rl_agent,
        state_index_fn=state_index,
        action_names=ACTION_NAMES,
        action_display=ACTION_DISPLAY,
    )


def _render_top_nav(active: str) -> None:
    """Primary tabs + Overview — no brand logo in the main chrome."""
    tabs, right = st.columns([5.2, 0.9])
    with tabs:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button(
                "Digital Twin",
                type="primary" if active == "twin" else "secondary",
                use_container_width=True,
                key="nav_twin",
            ):
                st.session_state.view = "twin"
                st.rerun()
        with c2:
            if st.button(
                "Price Monitor",
                type="primary" if active == "live" else "secondary",
                use_container_width=True,
                key="nav_live",
            ):
                st.session_state.view = "live"
                st.rerun()
        with c3:
            if st.button(
                "Agent Play",
                type="primary" if active == "play" else "secondary",
                use_container_width=True,
                key="nav_play",
            ):
                st.session_state.view = "play"
                st.rerun()
        with c4:
            if st.button(
                "Results",
                type="primary" if active == "results" else "secondary",
                use_container_width=True,
                key="nav_results",
            ):
                st.session_state.view = "results"
                st.rerun()
    with right:
        if st.button("Overview", use_container_width=True, key=f"nav_home_{active}"):
            st.session_state.view = "home"
            st.rerun()
    st.markdown('<div class="gq-nav-divider"></div>', unsafe_allow_html=True)


# Headline experiment numbers (wholesale-export, true-direction privileged, 53 test days)
RESULTS_NO_BAT = 160.75
RESULTS_ORACLE = 74.92
RESULTS_GREEDY = 90.39
RESULTS_CURRENT = 124.23
RESULTS_CURRENT_STD = 11.65
RESULTS_PRIV = 139.68
RESULTS_PRIV_STD = 5.55


def _render_results_chart():
    """Horizontal net-cost bar chart — lowest cost at top."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    labels = [
        "Perfect foresight (bound)",
        "Greedy",
        "Current Q",
        "Privileged Q — true 4h",
        "No-battery reference",
    ]
    costs = [
        RESULTS_ORACLE,
        RESULTS_GREEDY,
        RESULTS_CURRENT,
        RESULTS_PRIV,
        RESULTS_NO_BAT,
    ]
    err = [0.0, 0.0, RESULTS_CURRENT_STD, RESULTS_PRIV_STD, 0.0]
    colors = ["#64748b", "#22c55e", "#6366f1", "#38bdf8", "#94a3b8"]

    fig = go.Figure(
        go.Bar(
            y=labels[::-1],
            x=costs[::-1],
            orientation="h",
            marker_color=colors[::-1],
            error_x=dict(
                type="data",
                array=err[::-1],
                visible=True,
                color="#cbd5e1",
                thickness=1.2,
                width=4,
            ),
            text=[f"{c:.2f}" for c in costs[::-1]],
            textposition="outside",
            textfont=dict(color="#e2e8f0", size=12),
            hovertemplate="%{y}<br>AUD %{x:.2f}<extra></extra>",
            cliponaxis=False,
        )
    )
    fig.update_layout(
        template="plotly_dark",
        height=360,
        margin=dict(l=10, r=70, t=10, b=40),
        paper_bgcolor="#070d1a",
        plot_bgcolor="#0c1424",
        title=None,
        xaxis=dict(title="Net cost (AUD)", range=[0, 195], gridcolor="#1e293b"),
        yaxis=dict(title="", tickfont=dict(size=12)),
        showlegend=False,
    )
    return fig


def _render_results() -> None:
    """Experiment-results dashboard: headline, KPIs, chart + interpretation, compact table."""
    _render_top_nav("results")

    st.markdown("### Experiment Results")
    st.caption(
        "Wholesale-export tariff · 53 held-out days · 5 training seeds · Lower cost is better"
    )

    st.success(
        "**Greedy remained the best deployable controller**  \n"
        "True four-hour price-direction information did not improve Q-Learning under this experimental setup."
    )

    sav_aud = RESULTS_NO_BAT - RESULTS_GREEDY
    sav_pct = sav_aud / RESULTS_NO_BAT * 100.0
    gap_oracle = RESULTS_GREEDY - RESULTS_ORACLE
    priv_vs_cur = RESULTS_PRIV - RESULTS_CURRENT

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Best deployable", f"Greedy · {RESULTS_GREEDY:.2f}", help="Lowest net cost among deployable controllers (AUD).")
    k2.metric(
        "Savings vs no battery",
        f"{sav_aud:.2f} AUD",
        f"{sav_pct:.2f}%",
        help=f"No battery reference: AUD {RESULTS_NO_BAT:.2f}",
    )
    k3.metric(
        "Gap to oracle",
        f"{gap_oracle:.2f} AUD",
        help=f"Perfect foresight bound: AUD {RESULTS_ORACLE:.2f}",
    )
    k4.metric(
        "Privileged vs Current Q",
        f"+{priv_vs_cur:.2f} AUD",
        "signal made cost worse",
        delta_color="inverse",
        help="True four-hour three-bin direction raised average cost vs Current Q.",
    )

    st.markdown("")  # vertical spacer
    st.markdown("##### Aggregate net cost · Lower is better")

    left, right = st.columns([1.55, 1.0], gap="large")
    with left:
        fig = _render_results_chart()
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.warning("Install plotly to view the results chart.")
    with right:
        cur_gap = RESULTS_CURRENT - RESULTS_GREEDY
        priv_gap = RESULTS_PRIV - RESULTS_GREEDY
        with st.container(border=True):
            st.markdown("**What did we learn?**")
            st.markdown(
                f"""
- Greedy captured **{sav_pct:.2f}%** savings against no battery.
- Current Q cost **AUD {cur_gap:.2f}** more than Greedy.
- Privileged Q cost **AUD {priv_gap:.2f}** more than Greedy.
- A three-bin direction signal did not provide enough information about the
  *magnitude* or *timing* of future price opportunities.
"""
            )
            st.caption(
                "**Next experiment:** add future peak magnitude and time-to-peak bins."
            )

    st.markdown("##### Results table")
    rows = [
        {
            "Controller": "Perfect foresight bound",
            "Net cost": f"AUD {RESULTS_ORACLE:.2f}",
            "Savings vs no battery": f"{(RESULTS_NO_BAT - RESULTS_ORACLE) / RESULTS_NO_BAT * 100:.2f}%",
            "Gap to oracle": "—",
            "_sort": RESULTS_ORACLE,
        },
        {
            "Controller": "🏆 Greedy",
            "Net cost": f"AUD {RESULTS_GREEDY:.2f}",
            "Savings vs no battery": f"{sav_pct:.2f}%",
            "Gap to oracle": f"AUD {gap_oracle:.2f}",
            "_sort": RESULTS_GREEDY,
        },
        {
            "Controller": "Current Q",
            "Net cost": f"AUD {RESULTS_CURRENT:.2f} ± {RESULTS_CURRENT_STD:.2f}",
            "Savings vs no battery": f"{(RESULTS_NO_BAT - RESULTS_CURRENT) / RESULTS_NO_BAT * 100:.2f}%",
            "Gap to oracle": f"AUD {RESULTS_CURRENT - RESULTS_ORACLE:.2f}",
            "_sort": RESULTS_CURRENT,
        },
        {
            "Controller": "Privileged Q — true 4h",
            "Net cost": f"AUD {RESULTS_PRIV:.2f} ± {RESULTS_PRIV_STD:.2f}",
            "Savings vs no battery": f"{(RESULTS_NO_BAT - RESULTS_PRIV) / RESULTS_NO_BAT * 100:.2f}%",
            "Gap to oracle": f"AUD {RESULTS_PRIV - RESULTS_ORACLE:.2f}",
            "_sort": RESULTS_PRIV,
        },
        {
            "Controller": "No-battery reference",
            "Net cost": f"AUD {RESULTS_NO_BAT:.2f}",
            "Savings vs no battery": "0.00%",
            "Gap to oracle": f"AUD {RESULTS_NO_BAT - RESULTS_ORACLE:.2f}",
            "_sort": RESULTS_NO_BAT,
        },
    ]
    table = pd.DataFrame(rows).sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)

    def _hl(row: pd.Series) -> list[str]:
        if "🏆" in str(row["Controller"]):
            return ["background-color: rgba(34,197,94,0.12); font-weight: 600"] * len(row)
        return [""] * len(row)

    try:
        st.dataframe(table.style.apply(_hl, axis=1), width="stretch", hide_index=True)
    except Exception:
        st.dataframe(table, width="stretch", hide_index=True)
    st.caption("Q-Learning values show mean ± standard deviation across five training seeds.")

    with st.expander("Experiment setup", expanded=False):
        st.markdown(
            """
- Same tariff, battery physics and **53** held-out test days for every controller
- **Greedy:** current observations and fixed decision rules (self-use + price-timed buy/sell)
- **Current Q:** current-state features only (tabular Q-Learning, 10k episodes × 5 seeds)
- **Privileged Q:** additional **true** four-hour, three-bin price-direction feature
- Headline privileged results use the oracle-direction probe — not the realistic forecast mode
"""
        )

    csv_path = REPO_ROOT / "results" / "tables" / "forecast_info_by_seed.csv"
    if csv_path.exists():
        with st.expander("Methodology · per-seed cost table", expanded=False):
            csv_df = pd.read_csv(csv_path)
            preferred = [
                c
                for c in (
                    "seed",
                    "controller",
                    "agent",
                    "policy",
                    "mean_grid_cost_aud",
                    "grid_cost_aud",
                    "total_grid_cost_aud",
                    "win_rate",
                    "foresight",
                )
                if c in csv_df.columns
            ]
            st.dataframe(csv_df[preferred] if preferred else csv_df, width="stretch", hide_index=True)


def _render_play() -> None:
    with st.spinner("Loading Play vs Agent…"):
        cfg, df, split, thresholds = load_resources()
        all_models = list_models(cfg)
        q_models = models_for_agent("q_learning", all_models)

    with st.sidebar:
        render_sidebar_header()

    _render_top_nav("play")
    render_play_vs_agent(cfg=cfg, df=df, split=split, thresholds=thresholds, q_models=q_models)

    with st.sidebar:
        render_sidebar_footer()


def _render_live() -> None:
    """Top-level Live Price Monitor — separate from historical Twin."""
    with st.spinner("Loading live feed…"):
        cfg, df, _split, thresholds = load_resources()
        all_models = list_models(cfg)
        q_models = models_for_agent("q_learning", all_models)

    with st.sidebar:
        render_sidebar_header()
        st.caption("Live Price Monitor uses AEMO NSW1. Open Digital Twin for historical day replay.")
        render_sidebar_footer()

    _render_top_nav("live")
    render_live_signal_panel(cfg, df, thresholds, q_models)


def _render_app() -> None:
    with st.spinner("Loading Digital Twin…"):
        cfg, df, split, thresholds = load_resources()
        all_models = list_models(cfg)

    q_models = models_for_agent("q_learning", all_models)
    sarsa_models = models_for_agent("sarsa", all_models)
    dq_models = models_for_agent("double_q_learning", all_models)

    with st.sidebar:
        render_sidebar_header()

        with st.container(key="sidebar_scroll"):
            with st.container(border=True):
                st.markdown("**Simulation setup**")
                split_name = st.selectbox(
                    "Day split",
                    ["test", "val", "train"],
                    index=0,
                    format_func=lambda x: SPLIT_LABELS.get(x, x),
                    help=SIMULATION_DATASET_HELP,
                    key="twin_split",
                )
                days = sorted(split.days(split_name))  # type: ignore[arg-type]
                if "twin_day" in st.session_state and st.session_state.twin_day not in days:
                    del st.session_state["twin_day"]
                day = str(st.selectbox("Simulation day", days, key="twin_day"))

            with st.container(border=True):
                st.markdown("**Controllers**")
                show_arbitrage = st.checkbox(
                    "Greedy (5-action)",
                    value=True,
                    key="twin_show_arbitrage",
                    help="Self-use surplus solar, plus price-timed grid-charge / export.",
                )
                show_q = st.checkbox(
                    "Current Q",
                    value=True,
                    key="twin_show_q",
                    help="Q-Learning that sees the current price only.",
                )
                show_q_privileged = st.checkbox(
                    "Privileged Q — true 4h signal",
                    value=True,
                    key="twin_show_q_priv",
                    help="Q-Learning with the true next-four-hour three-bin price-direction feature (not the realistic forecast).",
                )

            run_clicked = st.button(
                "Run comparison",
                type="primary",
                use_container_width=True,
                key="twin_run_btn",
            )
            st.caption("Loads on first open. Click again after changing settings.")

            reward_mode = "battery_aware"
            show_greedy = False
            show_rule = False
            show_sarsa = False
            show_dq = False
            q_model_name = None
            q_priv_model_name = None
            sarsa_model_name = None
            dq_model_name = None
            show_q_table = False

            with st.expander("Experiment settings", expanded=False):
                reward_mode = st.selectbox(
                    "Reward function",
                    ["battery_aware", "cost_only"],
                    index=0,
                    format_func=lambda x: REWARD_LABELS.get(x, x),
                    key="twin_reward",
                    help="Battery-aware includes cycling cost and terminal SOC valuation.",
                )
                st.markdown("**Extra baselines**")
                show_greedy = st.checkbox(
                    "Solar-only greedy",
                    value=False,
                    key="twin_show_greedy",
                    help="Self-consumption only — no grid-charge / export arbitrage.",
                )
                show_rule = st.checkbox("Tertile rule baseline", value=False, key="twin_show_rule")
                st.markdown("**Additional RL agents**")
                show_sarsa = st.checkbox("SARSA", value=False, key="twin_show_sarsa")
                show_dq = st.checkbox("Double Q-Learning", value=False, key="twin_show_dq")

                q_current_models = [p for p in q_models if "privileged" not in p.name.lower()]
                q_priv_models = [p for p in q_models if "privileged" in p.name.lower()]
                if not q_priv_models:
                    q_priv_models = q_models

                need_models = show_q or show_q_privileged or show_sarsa or show_dq
                if need_models and not all_models:
                    st.error("No trained models in results/models/. Run training first.")
                    show_q = show_q_privileged = show_sarsa = show_dq = False

                if show_q:
                    q_model_name = _model_selectbox(
                        "Current Q model", "Current Q", q_current_models, DEFAULT_Q
                    )
                if show_q_privileged:
                    q_priv_model_name = _model_selectbox(
                        "Privileged Q model",
                        "Privileged Q — true 4h signal",
                        q_priv_models,
                        q_priv_models[0].name if q_priv_models else "",
                    )
                if show_sarsa:
                    sarsa_model_name = _model_selectbox(
                        "SARSA model", "SARSA", sarsa_models, DEFAULT_SARSA
                    )
                if show_dq:
                    dq_model_name = _model_selectbox("Double Q model", "Double Q", dq_models, "")

                show_q_table = st.checkbox(
                    "Show Q-values in download / diagnostics",
                    value=False,
                    key="twin_show_qvals",
                )

            sidebar_preview = None
            sidebar_preview_label = None
            if "twin_run" in st.session_state:
                _run = st.session_state.twin_run
                if _run and len(_run) >= 4 and isinstance(_run[2], dict):
                    sidebar_preview_label, sidebar_preview = _pick_preview_trace(_run[2])
                    if sidebar_preview_label:
                        sidebar_preview_label = _short_policy(sidebar_preview_label)
            render_sidebar_footer(sidebar_preview, preview_label=sidebar_preview_label)

    run_key = (
        day,
        split_name,
        reward_mode,
        show_greedy,
        show_rule,
        show_arbitrage,
        show_q,
        show_q_privileged,
        show_sarsa,
        show_dq,
        q_model_name,
        q_priv_model_name,
        sarsa_model_name,
        dq_model_name,
    )
    settings_dirty = st.session_state.get("twin_run_key") != run_key
    # First visit: auto-run so the page is not blank. After that, only Run comparison
    # (or a settings change + Run) refreshes results.
    needs_run = bool(run_clicked) or ("twin_run" not in st.session_state)
    st.session_state.pop("twin_loading", None)
    st.session_state.pop("twin_compute_pending", None)

    _render_top_nav("twin")

    if needs_run:
        # Avoid st.empty()+container()+empty() — that triggers Streamlit's
        # frontend "'setIn' cannot be called on an ElementNode" error.
        _show_results_loader("Loading comparison results…")
        try:
            with st.spinner("Running controllers on the selected day…"):
                result = _simulate_episode(
                    cfg,
                    df,
                    thresholds,
                    day=str(day),
                    reward_mode=reward_mode,
                    show_greedy=show_greedy,
                    show_rule=show_rule,
                    show_arbitrage=show_arbitrage,
                    show_q=show_q,
                    show_q_privileged=show_q_privileged,
                    show_sarsa=show_sarsa,
                    show_dq=show_dq,
                    q_model_name=q_model_name,
                    q_priv_model_name=q_priv_model_name,
                    sarsa_model_name=sarsa_model_name,
                    dq_model_name=dq_model_name,
                )
        except Exception as exc:  # noqa: BLE001
            st.session_state.pop("twin_run", None)
            st.session_state.pop("twin_run_key", None)
            st.error(f"Comparison failed: {exc}")
            st.caption("Fix the issue above, then click **Run comparison** again.")
            return
        st.session_state.twin_run = result
        st.session_state.twin_run_key = run_key
        settings_dirty = False
        st.rerun()

    if "twin_run" not in st.session_state:
        st.info("Select controllers in the sidebar, then click **Run comparison**.")
        return

    if settings_dirty and not run_clicked:
        st.markdown(
            '<div class="gq-settings-dirty">Settings changed — run again to update results.</div>',
            unsafe_allow_html=True,
        )

    episode_df, policies, traces, summaries, no_bat, oracle, step_count = st.session_state.twin_run

    if step_count != 48:
        st.warning("This simulation day has incomplete interval data.")
        if step_count == 0:
            st.error("No interval data is available for this simulation day.")
            return

    if episode_df is None:
        st.error(f"This simulation day has incomplete interval data ({step_count}/48 intervals).")
        return

    if not policies:
        st.warning("Select at least one controller in the sidebar, then Run comparison.")
        return

    summary_df = pd.DataFrame(summaries).set_index("policy")
    best_name = summary_df["grid_cost_aud"].idxmin()
    preview_name, _preview_trace = _pick_preview_trace(traces)
    display_day = st.session_state.get("twin_run_key", (day,))[0] if isinstance(st.session_state.get("twin_run_key"), tuple) else day

    render_context_toolbar(
        day=str(display_day),
        mode="Historical replay",
        preview=_short_policy(str(preview_name)),
    )
    render_winner_kpi_strip(summary_df, no_bat, _short_policy)
    with st.expander(f"Why did {_short_policy(str(best_name))} win?", expanded=False):
        _short_win, why_win = _winner_summary(summary_df, no_bat)
        st.markdown(why_win)
        st.caption(f"Perfect-information lower-cost bound (import oracle): AUD {oracle:.2f}")

    st.markdown("##### Controller comparison")
    render_policy_comparison_table(summary_df, no_bat)

    # --- Charts (tabbed); v-line follows twin_step from the inspector below ---
    step_hl = int(st.session_state.get("twin_step", 24))
    render_chart_tabs(
        traces,
        episode_df,
        cfg.tariff.retail_margin_per_kwh,
        _short_policy,
        highlight_step=step_hl,
    )

    if episode_df[["pv_kwh", "load_kwh"]].isna().any().any():
        st.caption("Some intervals contain missing solar or load data for this simulation day.")

    # --- Timestep inspector ---
    render_timestep_inspector(traces, _short_policy, _format_action, key_prefix="twin")

    with st.expander("Diagnostics & download", expanded=False):
        tab_log, tab_dl = st.tabs(["Step log", "Download data"])
        with tab_log:
            policy_pick = st.selectbox(
                "Selected controller",
                list(traces.keys()),
                format_func=_short_policy,
                key="twin_diag_policy",
            )
            st.dataframe(format_trace(traces[policy_pick]), width="stretch", height=360, hide_index=True)
            if show_q_table and (
                ("Current-price Q-Learning" in policy_pick and q_model_name)
                or ("Privileged Q-Learning" in policy_pick and q_priv_model_name)
            ):
                with st.expander("Q-values for selected timestep", expanded=True):
                    step_idx = st.slider("Timestep for Q-value lookup", 1, 48, int(step_hl), key="twin_q_step") - 1
                    row = traces[policy_pick].iloc[step_idx]
                    state = int(row["state"])
                    model_name = q_priv_model_name if "Privileged" in policy_pick else q_model_name
                    q_agent = load_rl_agent(
                        "q_learning", str(cfg.results_models / model_name), model_name
                    )
                    q_vals = q_values_for_state(q_agent.q, state)
                    best_action = max(q_vals, key=q_vals.get)
                    st.markdown(
                        f"**Timestep {step_idx + 1}** ({row['time_label']}) · "
                        f"state `{state}` · chosen **{_format_action(row['action'])}**"
                    )
                    st.markdown(
                        f"Greedy Q-argmax would pick **{ACTION_DISPLAY.get(best_action, best_action)}** "
                        f"(Q={q_vals[best_action]:.2f})."
                    )
                    st.json({k: round(float(v), 2) for k, v in q_vals.items()})
        with tab_dl:
            export_payload = {
                "episode_day": display_day,
                "split": split_name,
                "reward_mode": reward_mode,
                "bounds": {"no_battery_cost_aud": no_bat, "oracle_cost_aud": oracle},
                "summaries": summaries,
                "traces": {name: t.to_dict(orient="records") for name, t in traces.items()},
            }
            st.download_button(
                "Download simulation data (JSON)",
                data=json.dumps(export_payload, indent=2, default=str),
                file_name=f"GreineQ_replay_{display_day}.json",
                mime="application/json",
                key="twin_download_json",
            )

    st.caption("Live AEMO prices are on **Live Price Monitor** — this page is historical simulation only.")


main()
