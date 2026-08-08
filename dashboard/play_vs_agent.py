"""Play vs Agent — human operates one battery; RL + greedy run identical twins."""

from __future__ import annotations

import html as html_lib
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.constants import CHARGE, DISCHARGE, EXPORT, GRID_CHARGE, HOLD
from src.data_loader import get_episode
from src.discretizer import FUTURE_SIGNAL_NAMES, future_price_delta, future_signal_bin
from src.environment import MicrogridEnv
from src.price_forecast import PriceForecastModel, fit_price_forecast
from src.replay import q_values_for_state
from src.rule_baseline import price_arbitrage_action_fn
from src.train import greedy_action_fn, load_trained_agent

# Action UI: (id, label, helper, css_key)
ACTION_BUTTONS = [
    (HOLD, "1 · Hold", "No battery movement", "play_act_hold"),
    (CHARGE, "2 · Solar charge", "Store surplus solar", "play_act_charge"),
    (DISCHARGE, "3 · Discharge", "Supply household demand", "play_act_discharge"),
    (GRID_CHARGE, "4 · Grid charge", "Buy electricity for later", "play_act_grid"),
    (EXPORT, "5 · Export", "Sell stored electricity", "play_act_export"),
]

SIGNAL_FRIENDLY = {
    "FALL_OR_FLAT": "Falling or stable",
    "MODERATE_RISE": "Moderate rise expected",
    "STRONG_RISE": "Strong rise expected",
}

ACTION_DISPLAY = {
    "hold": "Hold",
    "charge": "Solar charge",
    "discharge": "Discharge",
    "grid_charge": "Grid charge",
    "export": "Export",
}


def _init_game_state(day: str, *, started: bool = False) -> None:
    st.session_state.play = {
        "day": day,
        "started": started,
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
        "feedback": None,
        "paused": False,
    }


def _env_snapshot(env: MicrogridEnv, action_name: str, info: dict, reward: float) -> dict:
    return {
        "step": info["step"],
        "action": action_name,
        "soc_pct": info["soc_pct"],
        "price_per_kwh": info["price_per_kwh"],
        "export_price_per_kwh": info["export_price_per_kwh"],
        "export_revenue_aud": info.get("export_revenue_aud", 0.0),
        "grid_charge_cost_aud": info.get("grid_charge_cost_aud", 0.0),
        "grid_charge_kwh": info.get("grid_charge_kwh", 0.0),
        "export_kwh": info.get("export_kwh", 0.0),
        "grid_import_kwh": info["grid_import_kwh"],
        "reward": reward,
        "pv_kwh": info["pv_kwh"],
        "load_kwh": info["load_kwh"],
        "charge_kwh": info.get("charge_kwh", 0.0),
        "discharge_kwh": info.get("discharge_kwh", 0.0),
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


def _rollout_n(
    env: MicrogridEnv, action_fn, n_steps: int
) -> tuple[list[dict], float, str | None]:
    """Roll policy for n_steps (or until done). Returns trace, cost so far, last action."""
    env.reset()
    trace: list[dict] = []
    last_action = None
    for _ in range(max(0, n_steps)):
        action = action_fn(env)
        _, reward, done, info = env.step(action)
        last_action = info["action_name"]
        trace.append(_env_snapshot(env, info["action_name"], info, reward))
        if done:
            break
    return trace, float(env.total_grid_cost), last_action


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
        soc_before = env._soc_pct
        _, reward, done, info = env.step(action)
        total_reward += reward
        snap = _env_snapshot(env, info["action_name"], info, reward)
        snap["soc_before"] = soc_before
        trace.append(snap)
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


def _action_availability(soc_pct: float, pv_kwh: float, load_kwh: float, cfg) -> dict[int, tuple[bool, str]]:
    surplus = max(0.0, pv_kwh - load_kwh)
    deficit = max(0.0, load_kwh - pv_kwh)
    at_max = soc_pct >= float(cfg.max_soc_pct) - 1e-6
    at_min = soc_pct <= float(cfg.min_soc_pct) + 1e-6
    return {
        HOLD: (True, ""),
        CHARGE: (
            surplus > 1e-9 and not at_max,
            "Unavailable: no surplus solar at this step."
            if surplus <= 1e-9
            else "Unavailable: battery at maximum SOC.",
        ),
        DISCHARGE: (
            deficit > 1e-9 and not at_min,
            "Unavailable: no demand deficit to cover."
            if deficit <= 1e-9
            else "Unavailable: battery at minimum SOC.",
        ),
        GRID_CHARGE: (not at_max, "Unavailable: battery at maximum SOC."),
        EXPORT: (not at_min, "Unavailable: battery at minimum SOC."),
    }


def _agent_reason(action_name: str, price: float, retail: float) -> str:
    pretty = ACTION_DISPLAY.get(action_name, action_name)
    if action_name == "hold":
        return "current price is not attractive relative to its learned Q-values."
    if action_name == "charge":
        return "surplus solar is available and charging improves the expected return."
    if action_name == "discharge":
        return "serving load from the battery avoids a higher retail import cost."
    if action_name == "grid_charge":
        return f"wholesale/retail ({retail:.3f} AUD/kWh) looks cheap enough to store energy."
    if action_name == "export":
        return f"selling at {price:.3f} AUD/kWh looks better than holding the charge."
    return f"highest Q-value among legal actions pointed to {pretty}."


def _friendly_signal(bin_name: str) -> str:
    return SIGNAL_FRIENDLY.get(bin_name, bin_name.replace("_", " ").title())


def _progress_bar_html(step_1based: int, total: int = 48) -> str:
    completed = max(0, min(total, step_1based - 1))
    pct = int(round(100 * completed / total))
    filled = max(0, min(40, int(round(40 * completed / total))))
    bar = "━" * filled + "●" + "━" * max(0, 40 - filled - 1)
    return (
        f'<div class="gq-play-progress">'
        f'<div class="gq-play-progress-bar">{html_lib.escape(bar)}</div>'
        f'<div class="gq-play-progress-pct">{pct}% complete</div>'
        f"</div>"
    )


def _format_day(day: str) -> str:
    try:
        return pd.Timestamp(day).strftime("%d %B %Y")
    except Exception:
        return str(day)


def render_play_vs_agent(
    *,
    cfg,
    df,
    split,
    thresholds,
    q_models: list[Path],
) -> None:
    """Streamlit Play vs Agent mode — decision-first layout."""
    st.markdown("### Play vs Agent")

    days = sorted(split.test)
    current_models = [p for p in q_models if "privileged" not in p.name.lower()]
    priv_models = [p for p in q_models if "privileged" in p.name.lower()]

    if "play" not in st.session_state:
        _init_game_state(str(days[0]) if days else "")

    play = st.session_state.play

    # --- Game setup (before start) ---
    if not play.get("started"):
        st.markdown(
            '<p class="gq-play-tagline">Operate the battery for 48 half-hour steps. '
            "Lowest adjusted electricity cost wins.</p>",
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            st.markdown("##### Game setup")
            c1, c2 = st.columns(2)
            with c1:
                day = st.selectbox("Test day", days, key="play_day_setup")
            with c2:
                agent_choice = st.selectbox(
                    "Opponent",
                    ["Current Q", "Privileged Q — true 4h signal"],
                    key="play_agent_setup",
                    help="Privileged Q sees a true four-hour direction feature. "
                    "You always receive a realistic forecast — this is an oversight demo, "
                    "not an equal-information contest.",
                )
            use_privileged = "Privileged" in agent_choice
            model_pool = priv_models if use_privileged and priv_models else current_models or q_models
            if not model_pool:
                st.error("No trained Q models. Train first.")
                return
            by_name = {p.name: p for p in model_pool}
            agent_label = (
                "Privileged Q — true 4h signal" if use_privileged else "Current Q"
            )
            model_name = st.selectbox(
                "Trained model",
                [p.name for p in model_pool],
                key="play_model_setup",
                format_func=lambda n: _play_model_label(by_name[n], agent_label),
            )
            st.caption(
                "You see a **realistic** 4-hour price forecast. "
                "If the opponent is Privileged Q, it uses a **true** four-hour direction signal — "
                "interactive demonstration, not a scientifically fair comparison."
            )
            if st.button("Start game", type="primary", use_container_width=True):
                _init_game_state(str(day), started=True)
                st.session_state.play_config = {
                    "day": str(day),
                    "agent_choice": agent_choice,
                    "use_privileged": use_privileged,
                    "model_name": model_name,
                    "agent_label": agent_label,
                }
                st.rerun()
        with st.sidebar:
            st.caption("Configure the match in **Game setup**, then Start game.")
        return

    # --- Active / finished game ---
    config = st.session_state.get("play_config") or {}
    day = config.get("day", play["day"])
    use_privileged = bool(config.get("use_privileged", False))
    model_name = config.get("model_name")
    agent_label = config.get(
        "agent_label",
        "Privileged Q — true 4h signal" if use_privileged else "Current Q",
    )

    if play.get("day") != day:
        _init_game_state(day, started=True)
        play = st.session_state.play

    with st.sidebar:
        st.markdown("**Match**")
        st.caption(f"Day {_format_day(day)}")
        st.caption(f"Opponent: {agent_label}")
        if st.button("Quit to setup", key="play_quit_side"):
            play["started"] = False
            st.session_state.play = play
            st.rerun()

    if not model_name:
        st.error("Missing model configuration. Return to setup.")
        return

    episode_df = get_episode(df, day)

    if "play_forecast" not in st.session_state:
        st.session_state.play_forecast = fit_price_forecast(
            df,
            horizon_steps=cfg.forecast_horizon_steps,
            persistence_alpha=cfg.forecast_persistence_alpha,
            noise_scale=cfg.forecast_noise_scale,
        )
    forecast_model: PriceForecastModel = st.session_state.play_forecast
    foresight = "oracle" if use_privileged else "none"

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
    n_taken = len(play["human_actions"])

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
    agent_trace, agent_cost, agent_last = _rollout_n(agent_env, agent_fn, n_taken)
    greedy_trace, greedy_cost, greedy_last = _rollout_n(
        greedy_env, price_arbitrage_action_fn, n_taken
    )
    play["agent_trace"] = agent_trace
    play["greedy_trace"] = greedy_trace

    # Compact header
    st.markdown(
        '<p class="gq-play-tagline">Operate the battery for 48 half-hour steps. '
        "Lowest adjusted electricity cost wins.</p>",
        unsafe_allow_html=True,
    )
    idx = min(step, 47)
    row = episode_df.iloc[idx]
    ts = row["timestamp"]
    time_label = ts.strftime("%H:%M")
    step_show = 48 if done else step + 1
    st.markdown(
        f'<div class="gq-play-meta">'
        f"Day: {_format_day(day)} · Opponent: {html_lib.escape(agent_label)} · "
        f"Step {step_show} of 48 · {time_label}"
        f"</div>",
        unsafe_allow_html=True,
    )

    prog_col, _ = st.columns([6.5, 0.1])
    with prog_col:
        st.markdown(f"**{time_label} · Step {step_show} of 48**")
        st.markdown(
            _progress_bar_html(49 if done else step_show),
            unsafe_allow_html=True,
        )

    # End-of-day finalisation
    if done and (play.get("finalizing") or play.get("agent_summary") is None):
        st.markdown(
            """
            <div class="gq-results-loader">
                <div class="gq-results-loader-spinner"></div>
                <div class="gq-results-loader-text">Loading comparison results…</div>
                <div class="gq-results-loader-sub">Finalising day · please wait</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.spinner("Running full-day agent and greedy baselines…"):
            a_env = MicrogridEnv(
                episode_df,
                thresholds,
                cfg,
                privileged=use_privileged,
                foresight_mode=foresight if use_privileged else "none",
                forecast_model=forecast_model if use_privileged else None,
            )
            g_env = MicrogridEnv(episode_df, thresholds, cfg, privileged=False)
            play["agent_trace"], play["agent_summary"] = _rollout_full(a_env, agent_fn)
            play["greedy_trace"], play["greedy_summary"] = _rollout_full(
                g_env, price_arbitrage_action_fn
            )
            h_env = MicrogridEnv(episode_df, thresholds, cfg, privileged=False)
            play["human_trace"], play["human_summary"] = _replay_human(
                h_env, play["human_actions"]
            )
            play["finalizing"] = False
        st.session_state.play = play
        st.rerun()

    if done and play.get("agent_summary") is not None:
        _render_end_screen(play, day, agent_label)
        return

    # Current state (4 cards)
    price = float(row["price_per_kwh"])
    retail = price + cfg.tariff.retail_margin_per_kwh
    export_px = (
        price if cfg.tariff.export_pricing == "wholesale" else cfg.tariff.feed_in_per_kwh
    )
    pv = float(row["pv_kwh"])
    load = float(row["load_kwh"])
    soc = float(human_env._soc_pct)
    soc_kwh = soc / 100.0 * float(cfg.battery_capacity_kwh)
    surplus = max(0.0, pv - load)
    deficit = max(0.0, load - pv)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Battery", f"{soc:.0f}% SOC · {soc_kwh:.1f} kWh")
    c2.metric("Solar / demand", f"{pv:.2f} / {load:.2f} kWh")
    c3.metric("Buy price", f"AUD {retail:.3f}/kWh")
    c4.metric("Sell price", f"AUD {export_px:.3f}/kWh")

    if deficit > 1e-9:
        st.markdown(
            f'<span class="gq-energy-badge deficit">Energy deficit: {deficit:.2f} kWh</span>',
            unsafe_allow_html=True,
        )
    elif surplus > 1e-9:
        st.markdown(
            f'<span class="gq-energy-badge surplus">Energy surplus: {surplus:.2f} kWh</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="gq-energy-badge flat">Solar ≈ demand</span>',
            unsafe_allow_html=True,
        )

    # Action area (visual focus) — five actions + icon restart on one row
    st.markdown("##### Choose your action")
    st.caption("Clicking an action advances time immediately. Numbered buttons: 1–5.")
    paused = bool(play.get("paused"))
    avail = _action_availability(soc, pv, load, cfg)
    chosen = None
    cols = st.columns([1, 1, 1, 1, 1, 0.45])
    for col, (aid, label, help_txt, css_key) in zip(cols[:5], ACTION_BUTTONS):
        ok, why = avail[aid]
        with col:
            with st.container(key=css_key):
                tip = help_txt if ok else why
                if st.button(
                    label,
                    key=f"play_act_{aid}",
                    help=tip,
                    use_container_width=True,
                    disabled=(not ok) or paused,
                ):
                    chosen = aid
    with cols[5]:
        with st.container(key="play_act_reset"):
            if st.button(
                "↻",
                key="play_restart",
                help="Restart day",
                use_container_width=True,
                type="secondary",
            ):
                _init_game_state(day, started=True)
                st.rerun()

    ctrl1, ctrl2 = st.columns([1.6, 1.2])
    with ctrl1:
        pause_label = "Resume" if paused else "Pause and inspect"
        if st.button(pause_label, key="play_pause"):
            play["paused"] = not paused
            st.session_state.play = play
            st.rerun()
    with ctrl2:
        if st.button("Quit game", key="play_quit"):
            play["started"] = False
            st.session_state.play = play
            st.rerun()

    fb = play.get("feedback")
    if fb:
        f1, f2 = st.columns(2)
        with f1:
            st.markdown(
                f'<div class="gq-play-feedback">'
                f'<div class="gq-play-feedback-title">You chose {html_lib.escape(fb["human_action"])}</div>'
                f'<div class="gq-play-feedback-body">{html_lib.escape(fb["human_detail"])}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
        with f2:
            st.markdown(
                f'<div class="gq-play-feedback agent">'
                f'<div class="gq-play-feedback-title">RL chose {html_lib.escape(fb["agent_action"])}</div>'
                f'<div class="gq-play-feedback-body">Reason: {html_lib.escape(fb["agent_reason"])}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

    # Live scoreboard
    st.markdown("##### Competition scoreboard")
    human_cost = float(human_env.total_grid_cost)
    human_last = play["human_trace"][-1]["action"] if play["human_trace"] else "—"
    board = pd.DataFrame(
        [
            {
                "Controller": "You",
                "Net cost": f"AUD {human_cost:.2f}",
                "SOC": f"{soc:.0f}%",
                "Last action": ACTION_DISPLAY.get(human_last, human_last),
                "_cost": human_cost,
            },
            {
                "Controller": "RL agent",
                "Net cost": f"AUD {agent_cost:.2f}",
                "SOC": (
                    f"{float(agent_trace[-1]['soc_pct']):.0f}%"
                    if agent_trace
                    else f"{cfg.initial_soc_pct:.0f}%"
                ),
                "Last action": ACTION_DISPLAY.get(agent_last or "—", agent_last or "—"),
                "_cost": agent_cost,
            },
            {
                "Controller": "Greedy",
                "Net cost": f"AUD {greedy_cost:.2f}",
                "SOC": (
                    f"{float(greedy_trace[-1]['soc_pct']):.0f}%"
                    if greedy_trace
                    else f"{cfg.initial_soc_pct:.0f}%"
                ),
                "Last action": ACTION_DISPLAY.get(greedy_last or "—", greedy_last or "—"),
                "_cost": greedy_cost,
            },
        ]
    )
    if n_taken > 0:
        leader = board.loc[board["_cost"].idxmin(), "Controller"]
        st.caption(
            f"**Current leader after Step {n_taken}** — {leader} · final results may change."
        )
    else:
        st.caption("Take an action to start the live comparison.")

    def _hl_board(r: pd.Series) -> list[str]:
        if n_taken > 0 and r["_cost"] == board["_cost"].min():
            return ["background-color: rgba(34,197,94,0.12)"] * len(r)
        return [""] * len(r)

    try:
        st.dataframe(
            board.style.apply(_hl_board, axis=1).hide(axis="columns", subset=["_cost"]),
            width="stretch",
            hide_index=True,
        )
    except Exception:
        st.dataframe(board.drop(columns=["_cost"]), width="stretch", hide_index=True)

    tab_fc, tab_agent = st.tabs(["Forecast & energy", "Agent decision"])
    with tab_fc:
        _render_compact_forecast(
            forecast_model,
            episode_df,
            thresholds,
            step,
            price,
            use_privileged,
            agent_label,
        )
    with tab_agent:
        _render_agent_decision_tab(
            agent,
            episode_df,
            thresholds,
            cfg,
            forecast_model,
            use_privileged,
            foresight,
            step,
            agent_label,
            n_taken,
            agent_trace,
        )

    with st.expander("Detailed history", expanded=False):
        if play["human_trace"]:
            hist = pd.DataFrame(play["human_trace"])
            cols_keep = [
                c
                for c in ("step", "action", "soc_pct", "reward", "pv_kwh", "load_kwh")
                if c in hist.columns
            ]
            st.dataframe(hist[cols_keep], width="stretch", hide_index=True, height=240)
        else:
            st.caption("No steps yet.")

    if chosen is not None and not paused:
        soc_before = human_env._soc_pct
        _, reward, step_done, info = human_env.step(chosen)
        play["human_actions"].append(chosen)
        snap = _env_snapshot(human_env, info["action_name"], info, reward)
        snap["soc_before"] = soc_before
        play["human_trace"].append(snap)
        play["step"] = human_env._step_idx

        a_env2 = MicrogridEnv(
            episode_df,
            thresholds,
            cfg,
            privileged=use_privileged,
            foresight_mode=foresight if use_privileged else "none",
            forecast_model=forecast_model if use_privileged else None,
        )
        _, _, a_last = _rollout_n(a_env2, agent_fn, len(play["human_actions"]))
        agent_act = a_last or "hold"
        human_pretty = ACTION_DISPLAY.get(info["action_name"], info["action_name"])
        detail_bits = []
        if info.get("grid_charge_kwh", 0) > 0:
            detail_bits.append(f"Bought {info['grid_charge_kwh']:.2f} kWh")
        if info.get("charge_kwh", 0) > 0:
            detail_bits.append(f"Stored {info['charge_kwh']:.2f} kWh solar")
        if info.get("discharge_kwh", 0) > 0:
            detail_bits.append(f"Discharged {info['discharge_kwh']:.2f} kWh")
        if info.get("export_kwh", 0) > 0:
            detail_bits.append(f"Exported {info['export_kwh']:.2f} kWh")
        if not detail_bits:
            detail_bits.append("No battery energy moved")
        detail_bits.append(f"SOC {soc_before:.0f}% → {info['soc_pct']:.0f}%")
        detail_bits.append(f"Step cost AUD {-float(reward):.2f}")
        play["feedback"] = {
            "human_action": human_pretty,
            "human_detail": " · ".join(detail_bits),
            "agent_action": ACTION_DISPLAY.get(agent_act, agent_act),
            "agent_reason": _agent_reason(agent_act, price, retail),
        }

        if step_done:
            play["done"] = True
            play["finalizing"] = True
        st.session_state.play = play
        st.rerun()


def _render_compact_forecast(
    forecast_model: PriceForecastModel,
    episode_df: pd.DataFrame,
    thresholds,
    step: int,
    price: float,
    use_privileged: bool,
    agent_label: str,
) -> None:
    fc = forecast_model.forecast_series_for_episode(episode_df, min(step, 47), add_noise=False)
    if fc.empty:
        st.caption("No future steps left in this day.")
        return

    f_low = float(fc["forecast_price"].min())
    f_high = float(fc["forecast_price"].max())
    delta = f_high - price
    bin_name = FUTURE_SIGNAL_NAMES[future_signal_bin(delta, thresholds)]
    friendly = _friendly_signal(bin_name)
    if delta <= 0:
        headline = "Next 4 hours: price expected to fall or stay flat"
        change_pct = ((f_low - price) / price * 100.0) if price > 1e-9 else 0.0
        ref = f_low
        ref_word = "low"
    else:
        headline = "Next 4 hours: price expected to rise"
        change_pct = ((f_high - price) / price * 100.0) if price > 1e-9 else 0.0
        ref = f_high
        ref_word = "peak"

    st.markdown(f"**{headline}**")
    st.markdown(
        f"Current wholesale: `{price:.3f}` → forecast {ref_word}: `{ref:.3f} AUD/kWh`  \n"
        f"Change: `{change_pct:+.1f}%` · Outlook: **{friendly}**"
    )
    st.caption(
        f"Internal forecast category: `{bin_name}` · You see a realistic forecast; "
        + (
            f"opponent **{agent_label}** uses a true direction signal."
            if use_privileged
            else "opponent Current Q uses current price only."
        )
    )
    chart_df = fc.set_index("time_label")[["forecast_price"]].rename(
        columns={"forecast_price": "Forecast AUD/kWh"}
    )
    st.line_chart(chart_df, height=200)
    with st.expander("View forecast values", expanded=False):
        show = fc[["time_label", "forecast_price"]].rename(
            columns={"time_label": "Time", "forecast_price": "Forecast AUD/kWh"}
        )
        show["Forecast AUD/kWh"] = show["Forecast AUD/kWh"].map(lambda x: f"{x:.4f}")
        st.dataframe(show, width="stretch", hide_index=True)
        with st.expander("How this forecast is built", expanded=False):
            st.markdown(
                "Climatology (typical price by time of day) blended with persistence "
                "from the current wholesale price over the next eight half-hours. "
                "The outlook category mirrors the three-bin direction feature used in training."
            )


def _render_agent_decision_tab(
    agent,
    episode_df,
    thresholds,
    cfg,
    forecast_model,
    use_privileged: bool,
    foresight: str,
    step: int,
    agent_label: str,
    n_taken: int,
    agent_trace: list[dict],
) -> None:
    st.markdown(f"**Opponent:** {agent_label}")
    if use_privileged:
        st.info(
            "Privileged Q — true four-hour direction signal. "
            "You receive a realistic forecast, so this is an interactive oversight "
            "demonstration rather than an equal-information scientific comparison."
        )

    a_env = MicrogridEnv(
        episode_df,
        thresholds,
        cfg,
        privileged=use_privileged,
        foresight_mode=foresight if use_privileged else "none",
        forecast_model=forecast_model if use_privileged else None,
    )
    a_env.reset()
    inspect_step = 0 if n_taken == 0 else min(n_taken - 1, 47)
    for _t in range(inspect_step):
        a_env.step(
            agent.greedy_action(a_env._observe())
            if hasattr(agent, "greedy_action")
            else agent.q.greedy_action(a_env._observe())
        )
    state = a_env._observe()
    q_vals = q_values_for_state(agent.q, state)
    best = max(q_vals, key=q_vals.get)
    selected = agent_trace[inspect_step]["action"] if inspect_step < len(agent_trace) else best

    row = episode_df.iloc[min(step, 47)]
    price = float(row["price_per_kwh"])
    st.markdown(
        f"- **Selected action:** {ACTION_DISPLAY.get(selected, selected)}  \n"
        f"- **Best Q-value:** `{best}` = {q_vals[best]:.3f}  \n"
        f"- **Current wholesale:** {price:.3f} AUD/kWh · **SOC:** {a_env._soc_pct:.0f}%"
    )
    if use_privileged:
        prices = episode_df["price_per_kwh"].to_numpy()
        delta = future_price_delta(prices, min(step, 47), cfg.forecast_horizon_steps)
        bin_name = FUTURE_SIGNAL_NAMES[future_signal_bin(float(delta), thresholds)]
        st.markdown(
            f"- **Foresight category:** {_friendly_signal(bin_name)} "
            f"(internal: `{bin_name}`)"
        )

    alt = pd.DataFrame(
        [
            {"Action": ACTION_DISPLAY.get(k, k), "Q-value": round(float(v), 3)}
            for k, v in sorted(q_vals.items(), key=lambda x: -x[1])
        ]
    )
    st.dataframe(alt, width="stretch", hide_index=True)
    sel_name = selected if isinstance(selected, str) else best
    st.caption(_agent_reason(sel_name, price, price + cfg.tariff.retail_margin_per_kwh))


def _render_end_screen(play: dict, day: str, agent_label: str) -> None:
    human_s = play["human_summary"]
    agent_s = play["agent_summary"]
    greedy_s = play["greedy_summary"]
    costs = {
        "You": human_s["grid_cost_aud"],
        "RL agent": agent_s["grid_cost_aud"],
        "Greedy": greedy_s["grid_cost_aud"],
    }
    winner = min(costs, key=costs.get)
    st.markdown(f"## {winner} won this day")
    st.caption(f"{_format_day(day)} · Opponent {agent_label}")

    results = pd.DataFrame(
        {
            "Result": [
                "Adjusted net cost",
                "Export revenue",
                "Grid-charge cost",
                "Final SOC",
                "Battery throughput",
            ],
            "You": [
                f"AUD {human_s['grid_cost_aud']:.2f}",
                f"AUD {human_s['export_revenue_aud']:.2f}",
                f"AUD {human_s['grid_charge_cost_aud']:.2f}",
                f"{human_s['final_soc_pct']:.1f}%",
                f"{human_s['battery_throughput_kwh']:.2f} kWh",
            ],
            "RL agent": [
                f"AUD {agent_s['grid_cost_aud']:.2f}",
                f"AUD {agent_s['export_revenue_aud']:.2f}",
                f"AUD {agent_s['grid_charge_cost_aud']:.2f}",
                f"{agent_s['final_soc_pct']:.1f}%",
                f"{agent_s['battery_throughput_kwh']:.2f} kWh",
            ],
            "Greedy": [
                f"AUD {greedy_s['grid_cost_aud']:.2f}",
                f"AUD {greedy_s['export_revenue_aud']:.2f}",
                f"AUD {greedy_s['grid_charge_cost_aud']:.2f}",
                f"{greedy_s['final_soc_pct']:.1f}%",
                f"{greedy_s['battery_throughput_kwh']:.2f} kWh",
            ],
        }
    )
    st.dataframe(results, width="stretch", hide_index=True)

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("Replay decisions", use_container_width=True):
            st.session_state.play_show_replay = True
    with b2:
        if st.button("Try another day", type="primary", use_container_width=True):
            play["started"] = False
            st.session_state.play = play
            st.session_state.pop("play_show_replay", None)
            st.rerun()
    with b3:
        payload = {
            "day": day,
            "opponent": agent_label,
            "human": human_s,
            "agent": agent_s,
            "greedy": greedy_s,
            "human_trace": play.get("human_trace"),
            "agent_trace": play.get("agent_trace"),
            "greedy_trace": play.get("greedy_trace"),
        }
        st.download_button(
            "Download results",
            data=json.dumps(payload, indent=2, default=str),
            file_name=f"GreineQ_play_{day}.json",
            mime="application/json",
            use_container_width=True,
        )

    if st.session_state.get("play_show_replay"):
        with st.expander("Replay decisions", expanded=True):
            for label, key in (
                ("You", "human_trace"),
                ("RL agent", "agent_trace"),
                ("Greedy", "greedy_trace"),
            ):
                st.markdown(f"**{label}**")
                tr = play.get(key) or []
                if tr:
                    df = pd.DataFrame(tr)[["step", "action", "soc_pct", "reward"]]
                    st.dataframe(df, width="stretch", hide_index=True, height=200)
