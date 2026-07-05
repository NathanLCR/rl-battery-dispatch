"""GréineQ — Streamlit digital twin dashboard."""

from __future__ import annotations

import json
import sys
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
from dashboard.landing_animation import build_demo_gif, pick_demo_day

DEFAULT_Q = "Q_q_learning_20260704_115627_main.npy"
DEFAULT_SARSA = "Q_sarsa_20260704_115834_main.npy"
ACTION_COLORS = {"hold": "#94a3b8", "charge": "#22c55e", "discharge": "#f97316"}


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


def plot_day(traces: dict[str, pd.DataFrame], episode_df: pd.DataFrame, retail_margin: float) -> plt.Figure:
    """Four-panel day view: load/PV, wholesale and retail price, SOC, and actions."""
    fig, axes = plt.subplots(4, 1, figsize=(10, 11), sharex=True)

    hours = episode_df["timestamp"].apply(lambda t: t.hour + t.minute / 60.0)
    retail_price = episode_df["price_per_kwh"] + retail_margin

    ax = axes[0]
    ax.plot(hours, episode_df["pv_kwh"], label="Solar (kWh)", color="#facc15")
    ax.plot(hours, episode_df["load_kwh"], label="Load (kWh)", color="#6366f1")
    ax.set_ylabel("Energy (kWh)")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_title("Solar and load")

    ax = axes[1]
    ax.plot(hours, episode_df["price_per_kwh"], label="Wholesale", color="#ef4444", linestyle="--")
    ax.plot(hours, retail_price, label=f"Retail (+{retail_margin:.2f})", color="#b91c1c")
    ax.set_ylabel("Price (AUD/kWh)")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_title("Grid price")

    ax = axes[2]
    for name, trace in traces.items():
        ax.plot(trace["step"], trace["soc_pct"], label=name, linewidth=1.8)
    ax.set_ylabel("SOC (%)")
    ax.set_ylim(0, 100)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_title("Battery state of charge")

    ax = axes[3]
    bar_w = 0.25
    x = range(1, 49)
    for i, (name, trace) in enumerate(traces.items()):
        offset = (i - len(traces) / 2 + 0.5) * bar_w
        colors = [ACTION_COLORS.get(a, "#64748b") for a in trace["action"]]
        ax.bar([xi + offset for xi in x], [1] * 48, width=bar_w, color=colors, alpha=0.85, label=name)
    ax.set_yticks([])
    ax.set_xlabel("Step (30-min intervals)")
    ax.set_title("Actions (green=charge, orange=discharge, grey=hold)")
    ax.set_xlim(0.5, 48.5)

    fig.tight_layout()
    return fig


def format_summary(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "total_reward" in out.columns:
        out["total_reward"] = out["total_reward"].map(lambda x: f"{x:.3f}")
    if "grid_cost_aud" in out.columns:
        out["grid_cost_aud"] = out["grid_cost_aud"].map(lambda x: f"{x:.4f}")
    if "grid_import_kwh" in out.columns:
        out["grid_import_kwh"] = out["grid_import_kwh"].map(lambda x: f"{x:.3f}")
    if "solar_waste_kwh" in out.columns:
        out["solar_waste_kwh"] = out["solar_waste_kwh"].map(lambda x: f"{x:.3f}")
    if "final_soc_pct" in out.columns:
        out["final_soc_pct"] = out["final_soc_pct"].map(lambda x: f"{x:.1f}")
    if "self_consumption_rate" in out.columns:
        out["self_consumption_rate"] = out["self_consumption_rate"].map(lambda x: f"{x:.1%}")
    if "self_sufficiency" in out.columns:
        out["self_sufficiency"] = out["self_sufficiency"].map(lambda x: f"{x:.1%}")
    if "evening_peak_import_kwh" in out.columns:
        out["evening_peak_import_kwh"] = out["evening_peak_import_kwh"].map(lambda x: f"{x:.3f}")
    return out


def format_trace(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "step", "time_label", "action", "soc_pct", "pv_kwh", "load_kwh",
        "price_per_kwh", "grid_import_kwh", "solar_waste_kwh", "reward", "state",
    ]
    out = df[[c for c in cols if c in df.columns]].copy()
    out["soc_pct"] = out["soc_pct"].map(lambda x: f"{x:.1f}")
    out["pv_kwh"] = out["pv_kwh"].map(lambda x: f"{x:.3f}")
    out["load_kwh"] = out["load_kwh"].map(lambda x: f"{x:.3f}")
    out["price_per_kwh"] = out["price_per_kwh"].map(lambda x: f"{x:.4f}")
    out["grid_import_kwh"] = out["grid_import_kwh"].map(lambda x: f"{x:.3f}")
    out["solar_waste_kwh"] = out["solar_waste_kwh"].map(lambda x: f"{x:.3f}")
    out["reward"] = out["reward"].map(lambda x: f"{x:.4f}")
    return out


def _model_selectbox(label: str, agent: str, models: list[Path], default_name: str) -> str | None:
    names = [p.name for p in models]
    if not names:
        return None
    default = default_name if default_name in names else names[0]
    return st.selectbox(label, names, index=names.index(default))


def main() -> None:
    st.set_page_config(page_title="GréineQ", layout="wide")

    if "view" not in st.session_state:
        st.session_state.view = "home"

    try:
        if st.session_state.view == "home":
            _render_landing()
        else:
            _render_app()
    except Exception as exc:
        st.error(f"Dashboard failed to load: {exc}")
        st.info(
            "Run from the project folder:\n\n"
            "`cd rl-battery-dispatch-review`\n\n"
            "`python -m streamlit run dashboard/app.py`\n\n"
            "Or double-click **`run_dashboard.bat`** — then open **http://localhost:8501**"
        )


@st.cache_data(show_spinner="Building demo animation (first load may take ~30 s)...")
def get_demo_gif(_version: str) -> bytes:
    cfg, df, split, thresholds = load_resources()
    test_days = sorted(split.test)
    day = pick_demo_day(df, test_days)
    episode_df = get_episode(df, day)
    policy = greedy_policy_fn(thresholds, cfg)
    trace, _ = trace_episode(episode_df, thresholds, policy, cfg)
    cache_path = cfg.artifacts_dir / "demo_dispatch.gif"
    return build_demo_gif(
        trace, episode_df, day, cfg.tariff.retail_margin_per_kwh, fps=4, cache_path=cache_path
    )


def _render_landing() -> None:
    st.title("GréineQ")
    st.caption("Reinforcement learning for home battery dispatch · Ausgrid + AEMO data")

    intro, action = st.columns([5, 2])
    with intro:
        st.markdown(
            "Each day is a **48-step episode** (30-minute intervals). At every step the agent "
            "observes battery state, solar generation, household load, and grid price, then selects "
            "one of three actions: **hold**, **charge** from surplus solar, or **discharge** to meet load."
        )
    with action:
        if st.button("Open Digital Twin →", type="primary", use_container_width=True):
            st.session_state.view = "twin"
            st.rerun()

    st.divider()
    anim_col, legend_col = st.columns([7, 3])

    with anim_col:
        st.subheader("Animated dispatch demo")
        st.image(
            get_demo_gif("v1"),
            caption="Sunny test day replay — greedy self-consumption policy",
        )

    with legend_col:
        st.subheader("Actions")
        st.markdown(
            "**Charge** — store surplus solar  \n\n"
            "**Discharge** — offset household load  \n\n"
            "**Hold** — no battery operation"
        )
        st.subheader("Timeline grid")
        st.markdown(
            "Each cell is one 30-minute interval across the day. Colour indicates the "
            "action at that step; the highlighted cell is the current timestep."
        )
        st.subheader("State space")
        st.markdown(
            "SOC, PV, load, price, and time-of-day are discretised into **324 tabular states** "
            "for Q-Learning and SARSA."
        )

    st.divider()
    if st.button("Launch interactive replay", use_container_width=False):
        st.session_state.view = "twin"
        st.rerun()


def _render_app() -> None:
    cfg, df, split, thresholds = load_resources()
    all_models = list_models(cfg)

    q_models = models_for_agent("q_learning", all_models)
    sarsa_models = models_for_agent("sarsa", all_models)
    dq_models = models_for_agent("double_q_learning", all_models)

    with st.sidebar:
        if st.button("← Back to overview"):
            st.session_state.view = "home"
            st.rerun()
        st.header("Digital Twin")
        split_name = st.selectbox("Day split", ["test", "val", "train"], index=0)
        days = sorted(split.days(split_name))  # type: ignore[arg-type]
        day = st.selectbox("Episode day", days)
        reward_mode = st.selectbox("Reward mode", ["battery_aware", "cost_only"])

        st.subheader("Policies")
        show_greedy = st.checkbox("Greedy self-consumption", value=True)
        show_rule = st.checkbox("Rule baseline (tertile)", value=False)
        show_q = st.checkbox("Q-Learning", value=True)
        show_sarsa = st.checkbox("SARSA", value=False)
        show_dq = st.checkbox("Double Q-Learning", value=False)

        need_models = show_q or show_sarsa or show_dq
        if need_models and not all_models:
            st.error("No trained models in results/models/. Run training first.")
            show_q = show_sarsa = show_dq = False

        q_model_name = _model_selectbox("Q-Learning model", "q_learning", q_models, DEFAULT_Q) if show_q else None
        sarsa_model_name = (
            _model_selectbox("SARSA model", "sarsa", sarsa_models, DEFAULT_SARSA) if show_sarsa else None
        )
        dq_model_name = _model_selectbox("Double Q-Learning model", "double_q_learning", dq_models, "") if show_dq else None

        show_q_table = st.checkbox("Show Q-values for selected step", value=False)

    episode_df = get_episode(df, day)
    no_bat = no_battery_import_cost(episode_df, cfg)
    oracle = oracle_perfect_foresight_import(episode_df, cfg)

    st.title("Digital Twin")
    st.caption(f"Replay and compare policies · Customer {cfg.primary_customer_id}")

    policies: dict[str, object] = {}
    if show_greedy:
        policies["Greedy SC"] = greedy_policy_fn(thresholds, cfg)
    if show_rule:
        policies["Rule (tertile)"] = rule_policy_fn(thresholds)
    if show_q and q_model_name:
        q_agent = load_rl_agent("q_learning", str(cfg.results_models / q_model_name), q_model_name)
        policies["Q-Learning"] = greedy_action_fn(q_agent)
    if show_sarsa and sarsa_model_name:
        s_agent = load_rl_agent("sarsa", str(cfg.results_models / sarsa_model_name), sarsa_model_name)
        policies["SARSA"] = greedy_action_fn(s_agent)
    if show_dq and dq_model_name:
        dq_agent = load_rl_agent("double_q_learning", str(cfg.results_models / dq_model_name), dq_model_name)
        policies["Double Q-Learning"] = greedy_action_fn(dq_agent)

    if not policies:
        st.warning("Select at least one policy in the sidebar.")
        return

    traces: dict[str, pd.DataFrame] = {}
    summaries: list[dict] = []
    for name, policy in policies.items():
        trace, summary = trace_episode(episode_df, thresholds, policy, cfg, reward_mode)
        trace["policy"] = name
        traces[name] = trace
        summary["policy"] = name
        summaries.append(summary)

    summary_df = pd.DataFrame(summaries).set_index("policy")
    st.subheader(f"Day summary — {day} ({split_name})")

    bound_cols = st.columns(3)
    bound_cols[0].metric("No battery (import cost)", f"{no_bat:.2f} AUD")
    bound_cols[1].metric("Oracle (perfect foresight)", f"{oracle:.2f} AUD")
    span = no_bat - oracle
    if span > 0 and summaries:
        best = min(s["grid_cost_aud"] for s in summaries)
        bound_cols[2].metric("Best policy capture", f"{(no_bat - best) / span * 100:.1f}% of oracle gap")

    display_cols = [
        c for c in [
            "total_reward", "grid_cost_aud", "grid_import_kwh", "solar_waste_kwh",
            "self_consumption_rate", "self_sufficiency", "evening_peak_import_kwh", "final_soc_pct",
        ] if c in summary_df.columns
    ]
    st.dataframe(format_summary(summary_df[display_cols]), width="stretch")

    fig = plot_day(traces, episode_df, cfg.tariff.retail_margin_per_kwh)
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)

    tab_compare, tab_steps, tab_export = st.tabs(["Action comparison", "Step log", "Export"])

    with tab_compare:
        compare = pd.DataFrame({"step": range(1, 49), "time": traces[list(traces.keys())[0]]["time_label"]})
        for name, trace in traces.items():
            compare[name] = trace["action"]
        st.dataframe(compare, width="stretch", height=400)

    with tab_steps:
        policy_pick = st.selectbox("Policy trace", list(traces.keys()))
        trace = traces[policy_pick]
        st.dataframe(format_trace(trace), width="stretch", height=420)

        if show_q_table and show_q and q_model_name:
            step_idx = st.slider("Step for Q-value lookup", 1, 48, 24) - 1
            state = int(trace.iloc[step_idx]["state"])
            q_agent = load_rl_agent("q_learning", str(cfg.results_models / q_model_name), q_model_name)
            q_vals = q_values_for_state(q_agent.q, state)
            st.write(f"State index **{state}** at step {step_idx + 1} ({trace.iloc[step_idx]['time_label']})")
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
            "Download replay JSON",
            data=json.dumps(export_payload, indent=2, default=str),
            file_name=f"GreineQ_replay_{day}.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
