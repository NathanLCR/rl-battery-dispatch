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
from src.discretizer import fit_discretizer
from src.environment import MicrogridEnv
from src.oracle import no_battery_import_cost, oracle_perfect_foresight_import
from src.replay import q_values_for_state, trace_episode
from src.rule_baseline import greedy_self_consumption_action, rule_action
from src.train import greedy_action_fn, load_trained_agent
from dashboard.landing_animation import pick_demo_day
from dashboard.landing_page import render_landing_body, render_landing_header
from dashboard.theme import (
    ACTION_COLORS,
    HOLD,
    inject_theme,
    render_demo_insight,
    render_kpi_cards,
    render_mission_topbar,
    render_policy_note,
    render_sidebar_footer,
    render_sidebar_header,
)

DEFAULT_Q = "Q_q_learning_20260704_115627_main.npy"
DEFAULT_SARSA = "Q_sarsa_20260704_115834_main.npy"

SPLIT_LABELS = {
    "test": "Test days",
    "val": "Validation days",
    "train": "Training days",
}
SIMULATION_DATASET_HELP = (
    "Choose which group of historical days to replay. Test days were not used during "
    "training and are best for final demonstration."
)
REWARD_LABELS = {
    "battery_aware": "Cost + battery health reward",
    "cost_only": "Grid cost only",
}
ACTION_DISPLAY = {
    "hold": "Hold",
    "charge": "Charge battery",
    "discharge": "Discharge battery",
}
POLICY_MAIN_COLUMNS = {
    "grid_cost_aud": "Cost (AUD)",
    "grid_import_kwh": "Import (kWh)",
    "self_consumption_rate": "Solar use (%)",
    "self_sufficiency": "Self-suff. (%)",
    "final_soc_pct": "Final SOC",
}
POLICY_DETAIL_COLUMNS = {
    "total_reward": "Reward",
    "solar_waste_kwh": "Waste (kWh)",
    "evening_peak_import_kwh": "Evening import",
}
POLICY_TABLE_NOTE = (
    "Lower grid cost is the main performance metric. Total reward is negative because the "
    "reward function penalises grid cost, solar waste, and battery degradation."
)
TRACE_COLUMN_LABELS = {
    "step": "Timestep",
    "time_label": "Time of day",
    "action": "Action",
    "soc_pct": "Battery state of charge (%)",
    "pv_kwh": "Solar generation (kWh)",
    "load_kwh": "Household demand (kWh)",
    "price_per_kwh": "Wholesale price (AUD/kWh)",
    "grid_import_kwh": "Grid import (kWh)",
    "solar_waste_kwh": "Solar waste (kWh)",
    "reward": "Step reward",
    "state": "State index",
}


@st.cache_resource
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


@st.cache_resource
def load_rl_agent(agent_name: str, model_path: str, _cache_key: str):
    cfg = load_config()
    return load_trained_agent(agent_name, Path(model_path), cfg)


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
                label=name,
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
            ax.bar([xi + offset for xi in xs], [1] * len(xs), width=bar_w, color=colors, alpha=0.9, label=name)
        ax.set_yticks([])
        ax.set_xlabel("Time of day (30-minute timesteps)", fontsize=9)
        ax.set_title(
            "Battery actions (grey = Hold, green = Charge, orange = Discharge)",
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


def _format_policy_metric(column: str, value: object) -> str:
    x = float(value)
    if column == "total_reward":
        return f"{x:.3f}"
    if column == "grid_cost_aud":
        return f"{x:.2f}"
    if column in ("grid_import_kwh", "solar_waste_kwh", "evening_peak_import_kwh"):
        return f"{x:.2f}"
    if column in ("self_consumption_rate", "self_sufficiency"):
        return f"{x * 100:.1f}%"
    if column == "final_soc_pct":
        return f"{x:.1f}%"
    return str(value)


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
    for col in metric_cols:
        if col in out.columns:
            out[col] = out[col].map(lambda v, c=col: _format_policy_metric(c, v))
    rename = {"Policy": "Policy", **{k: column_labels[k] for k in metric_cols if k in column_labels}}
    return out.rename(columns=rename)


def render_policy_comparison_table(summary_df: pd.DataFrame) -> None:
    """Main policy metrics table plus optional detailed metrics expander."""
    main_metrics = [c for c in POLICY_MAIN_COLUMNS if c in summary_df.columns]
    main_table = build_policy_display_table(summary_df, main_metrics, POLICY_MAIN_COLUMNS)
    st.table(main_table)

    detail_metrics = [c for c in POLICY_DETAIL_COLUMNS if c in summary_df.columns]
    if detail_metrics:
        with st.expander("Detailed metrics", expanded=False):
            detail_table = build_policy_display_table(summary_df, detail_metrics, POLICY_DETAIL_COLUMNS)
            st.table(detail_table)


def format_trace(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "step", "time_label", "action", "soc_pct", "pv_kwh", "load_kwh",
        "price_per_kwh", "grid_import_kwh", "solar_waste_kwh", "reward",
    ]
    out = df[[c for c in cols if c in df.columns]].copy()
    if "action" in out.columns:
        out["action"] = out["action"].map(_format_action)
    out["soc_pct"] = out["soc_pct"].map(lambda x: f"{x:.1f}")
    out["pv_kwh"] = out["pv_kwh"].map(lambda x: f"{x:.3f}")
    out["load_kwh"] = out["load_kwh"].map(lambda x: f"{x:.3f}")
    out["price_per_kwh"] = out["price_per_kwh"].map(lambda x: f"{x:.4f}")
    out["grid_import_kwh"] = out["grid_import_kwh"].map(lambda x: f"{x:.3f}")
    out["solar_waste_kwh"] = out["solar_waste_kwh"].map(lambda x: f"{x:.3f}")
    out["reward"] = out["reward"].map(lambda x: f"{x:.4f}")
    rename = {k: v for k, v in TRACE_COLUMN_LABELS.items() if k in out.columns}
    return out.rename(columns=rename)


def _friendly_model_label(path: Path, agent_label: str) -> str:
    """Turn a Q-table filename into a presentation-friendly label."""
    match = re.search(r"(\d{8})", path.stem)
    if match:
        trained = datetime.strptime(match.group(1), "%Y%m%d").strftime("%d %b %Y")
        return f"{agent_label} model — trained {trained}"
    return f"{agent_label} model"


def _demo_insight(summary_df: pd.DataFrame) -> str:
    """Build a short insight about the best policy on the selected day."""
    if summary_df.empty:
        return (
            "Key observation: Compare greedy self-consumption, rule-based baseline, and RL policies "
            "to see how each strategy manages solar generation, battery state of charge (SOC), and grid import."
        )
    best = summary_df["grid_cost_aud"].idxmin()
    greedy = "Greedy self-consumption baseline"
    if best == greedy:
        return (
            "Key observation: On this simulation day, the greedy self-consumption baseline achieves the "
            "lowest grid cost by using available solar energy directly and minimising grid import. "
            "Q-Learning still demonstrates learned battery-dispatch behaviour, although its performance "
            "is limited by the coarse state discretisation used in the tabular model."
        )
    return (
        f"Key observation: On this simulation day, **{best}** achieves the lowest grid cost among the "
        f"selected policies. Compare against the greedy self-consumption baseline and rule-based baseline "
        f"to see how learned dispatch differs from hand-crafted heuristics."
    )


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
        page_title="GréineQ Microgrid Control",
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
        else:
            _ensure_dashboard_sidebar()
            _render_app()
    except Exception as exc:
        st.error(f"Dashboard failed to load: {exc}")
        st.info(
            "Run from the project folder:\n\n"
            "`cd rl-battery-dispatch-review`\n\n"
            "`python -m streamlit run dashboard/app.py`\n\n"
            "Or double-click **`run_dashboard.bat`** — then open **http://localhost:8501**"
        )


DEMO_VERSION = "live-html-v1"


@st.cache_data(show_spinner="Loading agent animation…")
def get_demo_trace(_version: str) -> tuple[object, str]:
    """Load one-day greedy-SC trace for the landing dispatch animation."""
    cfg, df, split, thresholds = load_resources()
    test_days = sorted(split.test)
    day = pick_demo_day(df, test_days)
    episode_df = get_episode(df, day)
    policy = greedy_policy_fn(thresholds, cfg)
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
    if render_landing_header():
        st.session_state.view = "twin"
        st.rerun()

    with st.spinner("Loading agent animation…"):
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
    show_q: bool,
    show_sarsa: bool,
    show_dq: bool,
    q_model_name: str | None,
    sarsa_model_name: str | None,
    dq_model_name: str | None,
) -> tuple[pd.DataFrame | None, dict[str, object], dict[str, pd.DataFrame], list[dict], float, float, int]:
    """Build policy traces for the selected simulation day (unchanged RL pipeline)."""
    step_count = len(df[df["episode_day"] == day])
    if step_count != 48:
        return None, {}, {}, [], 0.0, 0.0, step_count

    try:
        episode_df = get_episode(df, day)
    except ValueError:
        return None, {}, {}, [], 0.0, 0.0, step_count

    no_bat = no_battery_import_cost(episode_df, cfg)
    oracle = oracle_perfect_foresight_import(episode_df, cfg)

    policies: dict[str, object] = {}
    if show_greedy:
        policies["Greedy self-consumption baseline"] = greedy_policy_fn(thresholds, cfg)
    if show_rule:
        policies["Rule-based baseline"] = rule_policy_fn(thresholds)
    if show_q and q_model_name:
        q_agent = load_rl_agent("q_learning", str(cfg.results_models / q_model_name), q_model_name)
        policies["Q-Learning"] = greedy_action_fn(q_agent)
    if show_sarsa and sarsa_model_name:
        s_agent = load_rl_agent("sarsa", str(cfg.results_models / sarsa_model_name), sarsa_model_name)
        policies["SARSA"] = greedy_action_fn(s_agent)
    if show_dq and dq_model_name:
        dq_agent = load_rl_agent("double_q_learning", str(cfg.results_models / dq_model_name), dq_model_name)
        policies["Double Q-Learning"] = greedy_action_fn(dq_agent)

    traces: dict[str, pd.DataFrame] = {}
    summaries: list[dict] = []
    if policies:
        for name, policy in policies.items():
            trace, summary = trace_episode(episode_df, thresholds, policy, cfg, reward_mode)
            trace["policy"] = name
            traces[name] = trace
            summary["policy"] = name
            summaries.append(summary)

    return episode_df, policies, traces, summaries, no_bat, oracle, step_count


def _render_app() -> None:
    cfg, df, split, thresholds = load_resources()
    all_models = list_models(cfg)

    q_models = models_for_agent("q_learning", all_models)
    sarsa_models = models_for_agent("sarsa", all_models)
    dq_models = models_for_agent("double_q_learning", all_models)

    with st.sidebar:
        render_sidebar_header()

        with st.container(key="sidebar_scroll"):
            split_name = st.selectbox(
                "Simulation dataset",
                ["test", "val", "train"],
                index=0,
                format_func=lambda x: SPLIT_LABELS.get(x, x),
                help=SIMULATION_DATASET_HELP,
            )
            days = sorted(split.days(split_name))  # type: ignore[arg-type]
            day = st.selectbox("Simulation day", days)
            reward_mode = st.selectbox(
                "Reward function",
                ["battery_aware", "cost_only"],
                index=0,
                format_func=lambda x: REWARD_LABELS.get(x, x),
            )

            st.subheader("Policies to compare")
            show_greedy = st.checkbox("Greedy self-consumption baseline", value=True)
            show_rule = st.checkbox("Rule-based baseline", value=False)
            show_q = st.checkbox("Q-Learning", value=True)
            show_sarsa = st.checkbox("SARSA", value=False)
            show_dq = st.checkbox("Double Q-Learning", value=False)

            need_models = show_q or show_sarsa or show_dq
            if need_models and not all_models:
                st.error("No trained models in results/models/. Run training first.")
                show_q = show_sarsa = show_dq = False

            q_model_name = (
                _model_selectbox("Selected Q-Learning model", "Q-Learning", q_models, DEFAULT_Q) if show_q else None
            )
            sarsa_model_name = (
                _model_selectbox("Selected SARSA model", "SARSA", sarsa_models, DEFAULT_SARSA) if show_sarsa else None
            )
            dq_model_name = (
                _model_selectbox("Selected Double Q-Learning model", "Double Q-Learning", dq_models, "")
                if show_dq
                else None
            )

            show_q_table = st.checkbox("Show learned Q-values for selected timestep", value=False)

            if show_q or show_sarsa or show_dq:
                with st.expander("Technical details", expanded=False):
                    if show_q and q_model_name:
                        st.caption(f"Q-Learning file: `{q_model_name}`")
                    if show_sarsa and sarsa_model_name:
                        st.caption(f"SARSA file: `{sarsa_model_name}`")
                    if show_dq and dq_model_name:
                        st.caption(f"Double Q-Learning file: `{dq_model_name}`")

        if render_sidebar_footer():
            st.session_state.view = "home"
            st.rerun()

    episode_df, policies, traces, summaries, no_bat, oracle, step_count = _simulate_episode(
        cfg,
        df,
        thresholds,
        day=day,
        reward_mode=reward_mode,
        show_greedy=show_greedy,
        show_rule=show_rule,
        show_q=show_q,
        show_sarsa=show_sarsa,
        show_dq=show_dq,
        q_model_name=q_model_name,
        sarsa_model_name=sarsa_model_name,
        dq_model_name=dq_model_name,
    )

    if step_count != 48:
        st.warning("This simulation day has incomplete interval data.")
        if step_count == 0:
            st.error("No interval data is available for this simulation day.")
            return

    if episode_df is None:
        st.error(f"This simulation day has incomplete interval data ({step_count}/48 intervals).")
        return

    if not policies:
        st.warning("Select at least one policy to compare in the sidebar.")
        return

    split_label = SPLIT_LABELS.get(split_name, split_name)
    preview_name = next(
        (
            n
            for n in (
                "Q-Learning",
                "Greedy self-consumption baseline",
                "SARSA",
                "Double Q-Learning",
                "Rule-based baseline",
            )
            if n in traces
        ),
        next(iter(traces), None),
    )
    preview_trace = traces.get(preview_name) if preview_name else None
    render_mission_topbar(
        "GréineQ Microgrid Control Dashboard",
        f"Household {cfg.primary_customer_id} · Simulation day: {day} · {split_label}",
        preview_trace=preview_trace,
    )

    summary_df = pd.DataFrame(summaries).set_index("policy")
    best_row = summary_df.loc[summary_df["grid_cost_aud"].idxmin()] if len(summary_df) else None

    pv_total = float(episode_df["pv_kwh"].sum())
    if best_row is not None:
        render_kpi_cards([
            (
                "Daily grid cost",
                f"{best_row['grid_cost_aud']:.2f} AUD",
                f"Best possible cost: {oracle:.2f} AUD",
                "Estimated cost of electricity imported from the grid for the selected day.",
            ),
            (
                "Energy imported from grid",
                f"{best_row['grid_import_kwh']:.2f} kWh",
                f"No-battery cost: {no_bat:.2f} AUD",
                "Total energy bought from the grid after solar and battery actions.",
            ),
            (
                "End-of-day battery charge",
                f"{best_row.get('final_soc_pct', 0):.0f}%",
                "Battery charge remaining at the end of the day",
                "Battery state of charge (SOC) at the end of the simulation day.",
            ),
            (
                "Solar self-consumption rate",
                f"{best_row.get('self_consumption_rate', 0):.0%}",
                f"Solar energy used on-site: {pv_total:.1f} kWh",
                "Percentage of generated solar energy used locally instead of wasted or exported.",
            ),
        ])
    else:
        bound_cols = st.columns(2)
        bound_cols[0].metric(
            "No-battery baseline cost",
            f"{no_bat:.2f} AUD",
            help="Grid import cost if no battery were available.",
        )
        bound_cols[1].metric(
            "Best possible cost",
            f"{oracle:.2f} AUD",
            help="Theoretical best result using perfect future knowledge; used only as a benchmark.",
        )

    st.markdown('<p class="gq-subheader">Policy Performance Comparison</p>', unsafe_allow_html=True)

    span = no_bat - oracle
    if span > 0 and summaries:
        best = min(s["grid_cost_aud"] for s in summaries)
        st.caption(
            f"Best policy captures {(no_bat - best) / span * 100:.1f}% of available oracle savings."
        )

    render_policy_comparison_table(summary_df)
    render_policy_note(POLICY_TABLE_NOTE)
    render_demo_insight(_demo_insight(summary_df))

    _render_chart_panel_label("Energy Flow Simulation Replay")
    fig = plot_day(traces, episode_df, cfg.tariff.retail_margin_per_kwh, dark=True)
    st.pyplot(fig, clear_figure=True, width="stretch")
    plt.close(fig)
    if episode_df[["pv_kwh", "load_kwh"]].isna().any().any():
        st.caption("Some intervals contain missing solar or load data for this simulation day.")
    else:
        st.caption(
            "All 48 half-hour timesteps are plotted. Solar generation drops to zero after sunset; "
            "household demand continues through the evening."
        )

    tab_compare, tab_steps, tab_export = st.tabs(["Actions", "Step Log", "Export"])

    with tab_compare:
        ref_trace = traces[list(traces.keys())[0]]
        compare = pd.DataFrame({
            "Timestep": ref_trace["step"],
            "Time of day": ref_trace["time_label"],
        })
        for name, trace in traces.items():
            compare[name] = trace["action"].map(_format_action)
        st.dataframe(compare, width="stretch", height=400)

    with tab_steps:
        policy_pick = st.selectbox("Selected policy", list(traces.keys()))
        trace = traces[policy_pick]
        st.dataframe(format_trace(trace), width="stretch", height=420)

        if show_q_table and show_q and q_model_name:
            with st.expander("Q-value lookup (technical)", expanded=False):
                step_idx = st.slider("Timestep for Q-value lookup", 1, 48, 24) - 1
                state = int(trace.iloc[step_idx]["state"])
                q_agent = load_rl_agent("q_learning", str(cfg.results_models / q_model_name), q_model_name)
                q_vals = q_values_for_state(q_agent.q, state)
                st.markdown(
                    f"Discretised state index **{state}** at timestep {step_idx + 1} "
                    f"({trace.iloc[step_idx]['time_label']})"
                )
                st.json(q_vals)

    with tab_export:
        export_payload = {
            "episode_day": day,
            "split": split_name,
            "reward_mode": reward_mode,
            "bounds": {"no_battery_cost_aud": no_bat, "oracle_cost_aud": oracle},
            "summaries": summaries,
            "traces": {name: t.to_dict(orient="records") for name, t in traces.items()},
        }
        st.download_button(
            "Download simulation data (JSON)",
            data=json.dumps(export_payload, indent=2, default=str),
            file_name=f"GreineQ_replay_{day}.json",
            mime="application/json",
        )


main()
