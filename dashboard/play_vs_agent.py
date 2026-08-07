"""Play vs Agent — human operates one battery; RL + greedy run identical twins."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.constants import CHARGE, DISCHARGE, EXPORT, GRID_CHARGE, HOLD
from src.data_loader import get_episode
from src.discretizer import FUTURE_SIGNAL_NAMES, future_signal_bin
from src.environment import MicrogridEnv
from src.price_forecast import PriceForecastModel, fit_price_forecast
from src.replay import q_values_for_state
from src.rule_baseline import price_arbitrage_action_fn
from src.train import greedy_action_fn, load_trained_agent

ACTION_BUTTONS = [
    (HOLD, "Hold", "No battery activity"),
    (CHARGE, "Solar charge", "Store surplus PV"),
    (DISCHARGE, "Discharge", "Cover load from battery"),
    (GRID_CHARGE, "Grid-charge", "Import to charge (buy)"),
    (EXPORT, "Export", "Sell stored energy"),
]


def _init_game_state(day: str) -> None:
    st.session_state.play = {
        "day": day,
        "step": 0,
        "done": False,
        "finalizing": False,
        "human_actions": [],
        "human_trace": [],
        "agent_trace": [],
        "greedy_trace": [],
        "human_summary": None,
        "agent_summary": None,
        "greedy_summary": None,
    }


def _env_snapshot(env: MicrogridEnv, action_name: str, info: dict, reward: float) -> dict:
    return {
        "step": info["step"],
        "action": action_name,
        "soc_pct": info["soc_pct"],
        "price_per_kwh": info["price_per_kwh"],
        "export_price_per_kwh": info["export_price_per_kwh"],
        "export_revenue_aud": info.get("export_revenue_aud", 0.0),
        "grid_charge_kwh": info.get("grid_charge_kwh", 0.0),
        "export_kwh": info.get("export_kwh", 0.0),
        "grid_import_kwh": info["grid_import_kwh"],
        "reward": reward,
        "pv_kwh": info["pv_kwh"],
        "load_kwh": info["load_kwh"],
        "future_price_delta": info.get("future_price_delta"),
    }


def _summary_from_env(env: MicrogridEnv, total_reward: float) -> dict:
    return {
        "total_reward": total_reward,
        "grid_cost_aud": env.total_grid_cost,
        "export_revenue_aud": env.total_export_revenue,
        "grid_charge_cost_aud": env.total_grid_charge_cost,
        "net_arbitrage_profit_aud": env.net_arbitrage_profit,
        "grid_import_kwh": env.total_grid_import_kwh,
        "export_kwh": env.total_export_kwh,
        "final_soc_pct": env._soc_pct,
        "n_grid_charge_actions": env.n_grid_charge_actions,
        "n_export_actions": env.n_export_actions,
        "battery_throughput_kwh": env.total_throughput_kwh,
    }


def _rollout_full(env: MicrogridEnv, action_fn) -> tuple[list[dict], dict]:
    env.reset()
    trace: list[dict] = []
    total_reward = 0.0
    done = False
    while not done:
        action = action_fn(env)
        _, reward, done, info = env.step(action)
        total_reward += reward
        trace.append(_env_snapshot(env, info["action_name"], info, reward))
    return trace, _summary_from_env(env, total_reward)


def _replay_human(env: MicrogridEnv, actions: list[int]) -> tuple[list[dict], dict]:
    env.reset()
    trace: list[dict] = []
    total_reward = 0.0
    for action in actions:
        _, reward, done, info = env.step(action)
        total_reward += reward
        trace.append(_env_snapshot(env, info["action_name"], info, reward))
        if done:
            break
    return trace, _summary_from_env(env, total_reward)


def _play_model_label(path: Path, agent_label: str) -> str:
    import re
    from datetime import datetime

    match = re.search(r"(\d{8})", path.stem)
    if match:
        trained = datetime.strptime(match.group(1), "%Y%m%d").strftime("%d %b %Y")
        return f"{agent_label} — trained {trained}"
    return f"{agent_label} model"


def render_play_vs_agent(
    *,
    cfg,
    df,
    split,
    thresholds,
    q_models: list[Path],
) -> None:
    """Streamlit Play vs Agent mode."""
    st.markdown("### Play vs Agent")

    days = sorted(split.test)
    current_models = [p for p in q_models if "privileged" not in p.name.lower()]
    priv_models = [p for p in q_models if "privileged" in p.name.lower()]

    # Settings in sidebar so action buttons sit directly under the title.
    with st.sidebar:
        st.markdown("**Match setup**")
        day = st.selectbox("Test day", days, key="play_day")
        agent_choice = st.selectbox(
            "Opponent",
            ["Current Q", "Privileged Q (4h)"],
            key="play_agent_choice_v2",
        )
        use_privileged = "Privileged" in agent_choice
        model_pool = priv_models if use_privileged and priv_models else current_models or q_models
        if not model_pool:
            st.error("No trained Q models. Train first.")
            return
        by_name = {p.name: p for p in model_pool}
        agent_label = "Privileged Q" if use_privileged else "Current Q"
        model_name = st.selectbox(
            "Trained model",
            [p.name for p in model_pool],
            key="play_model",
            format_func=lambda n: _play_model_label(by_name[n], agent_label),
        )
        st.caption("Pick an action under the title.")

    if "play" not in st.session_state or st.session_state.play.get("day") != day:
        _init_game_state(day)

    play = st.session_state.play
    episode_df = get_episode(df, day)

    if "play_forecast" not in st.session_state:
        st.session_state.play_forecast = fit_price_forecast(
            df,
            horizon_steps=cfg.forecast_horizon_steps,
            persistence_alpha=cfg.forecast_persistence_alpha,
            noise_scale=cfg.forecast_noise_scale,
        )
    forecast_model: PriceForecastModel = st.session_state.play_forecast

    foresight = "forecast" if use_privileged else "none"
    human_env = MicrogridEnv(
        episode_df, thresholds, cfg, privileged=False, foresight_mode="none"
    )
    if play["human_actions"]:
        human_env.reset()
        for a in play["human_actions"]:
            human_env.step(a)
    else:
        human_env.reset()

    step = play["step"]
    done = play["done"]

    # --- Actions directly under the title ---
    chosen = None
    if not done:
        st.markdown("##### Choose your action")
        cols = st.columns(5)
        for col, (aid, label, help_txt) in zip(cols, ACTION_BUTTONS):
            with col:
                if st.button(label, key=f"play_act_{aid}", help=help_txt, use_container_width=True):
                    chosen = aid
        if st.button("Reset day", type="secondary"):
            _init_game_state(day)
            st.rerun()
    elif play.get("finalizing") or play.get("agent_summary") is None:
        st.markdown(
            """
            <div class="gq-results-loader">
                <div class="gq-results-loader-spinner"></div>
                <div class="gq-results-loader-text">Loading comparison results…</div>
                <div class="gq-results-loader-sub">Comparing controllers · please wait</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.success("Day complete — comparison below.")
        if st.button("Play another day / reset"):
            _init_game_state(day)
            st.rerun()

    # --- Status / context below the actions ---
    row = episode_df.iloc[min(step, 47)]
    ts = row["timestamp"]
    price = float(row["price_per_kwh"])
    retail = price + cfg.tariff.retail_margin_per_kwh
    export_px = price if cfg.tariff.export_pricing == "wholesale" else cfg.tariff.feed_in_per_kwh

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Step", f"{step + 1 if not done else 48} / 48")
    m2.metric("Your SOC", f"{human_env._soc_pct:.1f}%")
    m3.metric("Wholesale", f"{price:.3f} AUD/kWh")
    m4.metric("Retail import", f"{retail:.3f} AUD/kWh")
    m5.metric("Export price", f"{export_px:.3f} AUD/kWh")

    st.markdown(
        f"**{ts.strftime('%H:%M')}** · Solar {float(row['pv_kwh']):.2f} kWh · "
        f"Demand {float(row['load_kwh']):.2f} kWh · "
        f"Surplus {max(0, float(row['pv_kwh'])-float(row['load_kwh'])):.2f} kWh · "
        f"Deficit {max(0, float(row['load_kwh'])-float(row['pv_kwh'])):.2f} kWh"
    )

    with st.expander("How to play", expanded=False):
        st.markdown(
            """
- **Goal:** Beat the RL agent (and greedy baseline) — lowest **net grid cost** wins.
- **What you see:** Current solar, load, prices, and a realistic **4-hour price forecast**.
- **What the agent sees:** Its trained policy (Current Q or Privileged Q with 4h foresight).
- **Tariff:** Experimental wholesale export (not a household feed-in tariff).
"""
        )

    with st.expander("Your 4-hour price forecast", expanded=not done):
        fc = forecast_model.forecast_series_for_episode(episode_df, min(step, 47), add_noise=False)
        if fc.empty:
            st.caption("No future steps left in this day.")
        else:
            delta = float(fc["forecast_price"].max() - price)
            bin_name = FUTURE_SIGNAL_NAMES[future_signal_bin(delta, thresholds)]
            st.caption(
                f"Signal: max(next 4h forecast) − now = **{delta:+.3f} AUD/kWh** → `{bin_name}`. "
                "True future prices stay hidden until the day ends."
            )
            show = fc[["time_label", "forecast_price"]].rename(
                columns={"time_label": "Time", "forecast_price": "Forecast AUD/kWh"}
            )
            st.dataframe(show, width="stretch", hide_index=True)
            st.line_chart(fc.set_index("time_label")["forecast_price"])

    if chosen is not None:
        _, reward, step_done, info = human_env.step(chosen)
        play["human_actions"].append(chosen)
        play["human_trace"].append(_env_snapshot(human_env, info["action_name"], info, reward))
        play["step"] = human_env._step_idx
        if step_done:
            play["done"] = True
            play["finalizing"] = True
        st.session_state.play = play
        st.rerun()

    if done and (play.get("finalizing") or play.get("agent_summary") is None):
        with st.spinner("Running agent and greedy baselines…"):
            agent = load_trained_agent(
                "q_learning",
                cfg.results_models / model_name,
                cfg,
                privileged=use_privileged,
            )
            agent_fn = greedy_action_fn(agent)
            agent_env = MicrogridEnv(
                episode_df,
                thresholds,
                cfg,
                privileged=use_privileged,
                foresight_mode=foresight if use_privileged else "none",
                forecast_model=forecast_model if use_privileged else None,
            )
            greedy_env = MicrogridEnv(episode_df, thresholds, cfg, privileged=False)
            play["agent_trace"], play["agent_summary"] = _rollout_full(agent_env, agent_fn)
            play["greedy_trace"], play["greedy_summary"] = _rollout_full(
                greedy_env, price_arbitrage_action_fn
            )
            h_env = MicrogridEnv(episode_df, thresholds, cfg, privileged=False)
            play["human_trace"], play["human_summary"] = _replay_human(h_env, play["human_actions"])
            play["finalizing"] = False
        st.session_state.play = play
        st.rerun()

    if not done or play.get("agent_summary") is None:
        return

    human_s = play["human_summary"]
    agent_s = play["agent_summary"]
    greedy_s = play["greedy_summary"]

    compare = pd.DataFrame(
        [
            {
                "Controller": "You",
                "Net cost (AUD)": f"{human_s['grid_cost_aud']:.2f}",
                "Export revenue (AUD)": f"{human_s['export_revenue_aud']:.2f}",
                "Net arbitrage (AUD)": f"{human_s['net_arbitrage_profit_aud']:.2f}",
                "Import (kWh)": f"{human_s['grid_import_kwh']:.2f}",
                "Export (kWh)": f"{human_s['export_kwh']:.2f}",
                "Final SOC (%)": f"{human_s['final_soc_pct']:.1f}",
                "# grid-charge": int(human_s["n_grid_charge_actions"]),
                "# export": int(human_s["n_export_actions"]),
            },
            {
                "Controller": "RL agent",
                "Net cost (AUD)": f"{agent_s['grid_cost_aud']:.2f}",
                "Export revenue (AUD)": f"{agent_s['export_revenue_aud']:.2f}",
                "Net arbitrage (AUD)": f"{agent_s['net_arbitrage_profit_aud']:.2f}",
                "Import (kWh)": f"{agent_s['grid_import_kwh']:.2f}",
                "Export (kWh)": f"{agent_s['export_kwh']:.2f}",
                "Final SOC (%)": f"{agent_s['final_soc_pct']:.1f}",
                "# grid-charge": int(agent_s["n_grid_charge_actions"]),
                "# export": int(agent_s["n_export_actions"]),
            },
            {
                "Controller": "Greedy (5-action)",
                "Net cost (AUD)": f"{greedy_s['grid_cost_aud']:.2f}",
                "Export revenue (AUD)": f"{greedy_s['export_revenue_aud']:.2f}",
                "Net arbitrage (AUD)": f"{greedy_s['net_arbitrage_profit_aud']:.2f}",
                "Import (kWh)": f"{greedy_s['grid_import_kwh']:.2f}",
                "Export (kWh)": f"{greedy_s['export_kwh']:.2f}",
                "Final SOC (%)": f"{greedy_s['final_soc_pct']:.1f}",
                "# grid-charge": int(greedy_s["n_grid_charge_actions"]),
                "# export": int(greedy_s["n_export_actions"]),
            },
        ]
    )
    st.markdown("##### Final comparison")
    st.caption("Winner = lowest net grid cost (AUD).")
    st.dataframe(compare, width="stretch", hide_index=True)

    costs = {
        "You": human_s["grid_cost_aud"],
        "RL agent": agent_s["grid_cost_aud"],
        "Greedy (5-action)": greedy_s["grid_cost_aud"],
    }
    winner = min(costs, key=costs.get)
    st.info(f"**Lowest net cost:** {winner} — AUD {costs[winner]:.2f}")

    st.markdown("##### Agent decision at one step")
    agent = load_trained_agent(
        "q_learning", cfg.results_models / model_name, cfg, privileged=use_privileged
    )
    step_i = st.slider("Inspect timestep", 1, 48, 24) - 1
    a_env = MicrogridEnv(
        episode_df,
        thresholds,
        cfg,
        privileged=use_privileged,
        foresight_mode=foresight if use_privileged else "none",
        forecast_model=forecast_model if use_privileged else None,
    )
    a_env.reset()
    for _t in range(step_i):
        a_env.step(
            agent.greedy_action(a_env._observe())
            if hasattr(agent, "greedy_action")
            else agent.q.greedy_action(a_env._observe())
        )
    state = a_env._observe()
    q_vals = q_values_for_state(agent.q, state)
    best = max(q_vals, key=q_vals.get)
    human_act = play["human_trace"][step_i]["action"] if step_i < len(play["human_trace"]) else "—"
    agent_act = play["agent_trace"][step_i]["action"] if step_i < len(play["agent_trace"]) else "—"
    st.markdown(
        f"You chose **{human_act}** · agent chose **{agent_act}** · "
        f"highest Q-value action **{best}** ({q_vals[best]:.3f})"
    )
    q_table = pd.DataFrame(
        [{"Action": k, "Q-value": f"{v:.3f}"} for k, v in sorted(q_vals.items(), key=lambda x: -x[1])]
    )
    st.dataframe(q_table, width="stretch", hide_index=True)
    with st.expander("Raw state index", expanded=False):
        st.code(str(state))

    with st.expander("Reveal true vs forecast prices for this day"):
        rows = []
        for t in range(48):
            fc = forecast_model.forecast_prices(float(episode_df.iloc[t]["price_per_kwh"]), t)
            rows.append(
                {
                    "Time": episode_df.iloc[t]["timestamp"].strftime("%H:%M"),
                    "True price (AUD/kWh)": round(float(episode_df.iloc[t]["price_per_kwh"]), 4),
                    "Forecast peak 4h (AUD/kWh)": round(float(fc.max()), 4) if len(fc) else float("nan"),
                }
            )
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
