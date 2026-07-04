"""GréineGrid AI — Streamlit digital twin dashboard."""

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
from src.replay import q_values_for_state, trace_episode
from src.rule_baseline import rule_action
from src.train import greedy_action_fn, make_agent

DEFAULT_Q = "Q_q_learning_20260704_082920.npy"
DEFAULT_SARSA = "Q_sarsa_20260704_083128.npy"
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


@st.cache_resource
def load_rl_agent(agent_name: str, model_path: str, cfg_hash: str):
    cfg = load_config()
    agent = make_agent(agent_name, cfg)
    agent.q = agent.q.load(Path(model_path))
    agent.epsilon = 0.0
    return agent


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


def plot_day(traces: dict[str, pd.DataFrame], episode_df: pd.DataFrame) -> plt.Figure:
    """Four-panel day view: load/PV, price, SOC trajectories, and action timeline."""
    fig, axes = plt.subplots(4, 1, figsize=(10, 11), sharex=True)

    hours = episode_df["timestamp"].apply(lambda t: t.hour + t.minute / 60.0)

    ax = axes[0]
    ax.plot(hours, episode_df["pv_kwh"], label="Solar (kWh)", color="#facc15")
    ax.plot(hours, episode_df["load_kwh"], label="Load (kWh)", color="#6366f1")
    ax.set_ylabel("Energy (kWh)")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_title("Solar & load")

    ax = axes[1]
    ax.plot(hours, episode_df["price_per_kwh"], color="#ef4444")
    ax.set_ylabel("Price (AUD/kWh)")
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
    out["total_reward"] = out["total_reward"].map(lambda x: f"{x:.3f}")
    out["grid_cost_aud"] = out["grid_cost_aud"].map(lambda x: f"{x:.4f}")
    out["grid_import_kwh"] = out["grid_import_kwh"].map(lambda x: f"{x:.3f}")
    out["solar_waste_kwh"] = out["solar_waste_kwh"].map(lambda x: f"{x:.3f}")
    out["final_soc_pct"] = out["final_soc_pct"].map(lambda x: f"{x:.1f}")
    return out


def format_trace(df: pd.DataFrame) -> pd.DataFrame:
    out = df[
        [
            "step",
            "time_label",
            "action",
            "soc_pct",
            "pv_kwh",
            "load_kwh",
            "price_per_kwh",
            "grid_import_kwh",
            "solar_waste_kwh",
            "reward",
            "state",
        ]
    ].copy()
    out["soc_pct"] = out["soc_pct"].map(lambda x: f"{x:.1f}")
    out["pv_kwh"] = out["pv_kwh"].map(lambda x: f"{x:.3f}")
    out["load_kwh"] = out["load_kwh"].map(lambda x: f"{x:.3f}")
    out["price_per_kwh"] = out["price_per_kwh"].map(lambda x: f"{x:.4f}")
    out["grid_import_kwh"] = out["grid_import_kwh"].map(lambda x: f"{x:.3f}")
    out["solar_waste_kwh"] = out["solar_waste_kwh"].map(lambda x: f"{x:.3f}")
    out["reward"] = out["reward"].map(lambda x: f"{x:.4f}")
    return out


def main() -> None:
    st.set_page_config(page_title="GréineGrid Digital Twin", layout="wide")
    st.title("GréineGrid AI — Digital Twin")
    st.caption("Replay home battery dispatch on real Ausgrid + AEMO data (Customer 1)")

    try:
        _render_app()
    except Exception as exc:
        st.error(f"Dashboard failed to load: {exc}")
        st.info(
            "Run from the project folder:\n\n"
            "`cd rl-battery-dispatch-review`\n\n"
            "`python -m streamlit run dashboard/app.py`\n\n"
            "Or double-click **`run_dashboard.bat`** — then open **http://localhost:8501**"
        )


def _render_app() -> None:
    """Main dashboard layout: sidebar controls, summary metrics, and replay tabs."""
    cfg, df, split, thresholds = load_resources()
    models = list_models(cfg)
    model_names = [p.name for p in models]

    with st.sidebar:
        st.header("Settings")
        split_name = st.selectbox("Day split", ["test", "val", "train"], index=0)
        days = sorted(split.days(split_name))  # type: ignore[arg-type]
        day = st.selectbox("Episode day", days)
        reward_mode = st.selectbox("Reward mode", ["battery_aware", "cost_only"])

        st.subheader("Policies")
        show_rule = st.checkbox("Rule baseline", value=True)
        show_q = st.checkbox("Q-Learning", value=True)
        show_sarsa = st.checkbox("SARSA", value=True)

        q_default = DEFAULT_Q if DEFAULT_Q in model_names else (model_names[0] if model_names else "")
        sarsa_default = DEFAULT_SARSA if DEFAULT_SARSA in model_names else (
            model_names[1] if len(model_names) > 1 else q_default
        )

        if (show_q or show_sarsa) and not model_names:
            st.error("No trained models in results/models/. Run training first.")
            show_q = False
            show_sarsa = False

        q_model_name = (
            st.selectbox(
                "Q-Learning model",
                model_names,
                index=model_names.index(q_default) if q_default in model_names else 0,
            )
            if show_q and model_names
            else None
        )
        sarsa_model_name = (
            st.selectbox(
                "SARSA model",
                model_names,
                index=model_names.index(sarsa_default) if sarsa_default in model_names else 0,
            )
            if show_sarsa and model_names
            else None
        )

        show_q_table = st.checkbox("Show Q-values for selected step", value=False)

    episode_df = get_episode(df, day)
    policies: dict[str, object] = {}

    if show_rule:
        policies["Rule"] = rule_policy_fn(thresholds)
    if show_q and q_model_name:
        q_path = cfg.results_models / q_model_name
        q_agent = load_rl_agent("q_learning", str(q_path), q_model_name)
        policies["Q-Learning"] = greedy_action_fn(q_agent)
    if show_sarsa and sarsa_model_name:
        s_path = cfg.results_models / sarsa_model_name
        s_agent = load_rl_agent("sarsa", str(s_path), sarsa_model_name)
        policies["SARSA"] = greedy_action_fn(s_agent)

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
    st.dataframe(
        format_summary(summary_df[["total_reward", "grid_cost_aud", "grid_import_kwh", "solar_waste_kwh", "final_soc_pct"]]),
        width="stretch",
    )

    fig = plot_day(traces, episode_df)
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
            "summaries": summaries,
            "traces": {name: t.to_dict(orient="records") for name, t in traces.items()},
        }
        st.download_button(
            "Download replay JSON",
            data=json.dumps(export_payload, indent=2, default=str),
            file_name=f"greinegrid_replay_{day}.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
