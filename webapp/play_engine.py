"""Server-side Play vs Agent engine for the web UI."""

from __future__ import annotations

import uuid
from typing import Any

from src.constants import CHARGE, DISCHARGE, EXPORT, GRID_CHARGE, HOLD
from src.data_loader import get_episode
from src.discretizer import FUTURE_SIGNAL_NAMES, future_signal_bin
from src.environment import MicrogridEnv
from src.price_forecast import fit_price_forecast
from src.rule_baseline import price_arbitrage_action_fn
from src.train import greedy_action_fn, load_trained_agent

ACTION_DISPLAY = {
    "hold": "Hold",
    "charge": "Solar charge",
    "discharge": "Discharge",
    "grid_charge": "Grid charge",
    "export": "Export",
}

ACTION_BUTTONS = [
    {"id": HOLD, "key": "hold", "label": "1 · Hold", "help": "No battery movement"},
    {"id": CHARGE, "key": "charge", "label": "2 · Solar charge", "help": "Store surplus solar"},
    {"id": DISCHARGE, "key": "discharge", "label": "3 · Discharge", "help": "Supply household demand"},
    {"id": GRID_CHARGE, "key": "grid", "label": "4 · Grid charge", "help": "Buy electricity for later"},
    {"id": EXPORT, "key": "export", "label": "5 · Export", "help": "Sell stored electricity"},
]

_SESSIONS: dict[str, dict[str, Any]] = {}
_FORECAST = None


def _forecast(cfg, df):
    global _FORECAST
    if _FORECAST is None:
        _FORECAST = fit_price_forecast(
            df,
            horizon_steps=cfg.forecast_horizon_steps,
            persistence_alpha=cfg.forecast_persistence_alpha,
            noise_scale=cfg.forecast_noise_scale,
        )
    return _FORECAST


def _availability(soc_pct: float, pv_kwh: float, load_kwh: float, cfg) -> dict[str, dict]:
    surplus = max(0.0, pv_kwh - load_kwh)
    deficit = max(0.0, load_kwh - pv_kwh)
    at_max = soc_pct >= float(cfg.max_soc_pct) - 1e-6
    at_min = soc_pct <= float(cfg.min_soc_pct) + 1e-6
    raw = {
        HOLD: (True, ""),
        CHARGE: (
            surplus > 1e-9 and not at_max,
            "No surplus solar" if surplus <= 1e-9 else "Battery at max SOC",
        ),
        DISCHARGE: (
            deficit > 1e-9 and not at_min,
            "No demand deficit" if deficit <= 1e-9 else "Battery at min SOC",
        ),
        GRID_CHARGE: (not at_max, "Battery at max SOC"),
        EXPORT: (not at_min, "Battery at min SOC"),
    }
    return {
        ACTION_BUTTONS[i]["key"]: {"ok": raw[aid][0], "reason": raw[aid][1], "id": aid}
        for i, aid in enumerate([HOLD, CHARGE, DISCHARGE, GRID_CHARGE, EXPORT])
    }


def _agent_reason(action_name: str, price: float, retail: float) -> str:
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
    return f"highest Q-value pointed to {ACTION_DISPLAY.get(action_name, action_name)}."


def _rollout_n(env: MicrogridEnv, action_fn, n_steps: int):
    env.reset()
    last = None
    costs: list[float] = []
    socs: list[float] = []
    times: list[str] = []
    for _ in range(max(0, n_steps)):
        row = env.episode_df.iloc[env._step_idx]
        action = action_fn(env)
        _, _, done, info = env.step(action)
        last = info["action_name"]
        costs.append(round(float(env.total_grid_cost), 3))
        socs.append(round(float(env._soc_pct), 1))
        ts = row["timestamp"]
        times.append(ts.strftime("%H:%M") if hasattr(ts, "strftime") else str(row.get("time_label", "")))
        if done:
            break
    return float(env.total_grid_cost), last, float(env._soc_pct), costs, socs, times


def _rollout_full(env: MicrogridEnv, action_fn):
    env.reset()
    total_reward = 0.0
    done = False
    trace: list[dict[str, Any]] = []
    while not done:
        row = env.episode_df.iloc[env._step_idx]
        action = action_fn(env)
        _, reward, done, info = env.step(action)
        total_reward += reward
        ts = row["timestamp"]
        trace.append(
            {
                "time": ts.strftime("%H:%M") if hasattr(ts, "strftime") else str(row.get("time_label", "")),
                "action": info["action_name"],
                "soc_pct": round(float(env._soc_pct), 1),
                "cost": round(float(env.total_grid_cost), 3),
                "reward": round(float(reward), 4),
            }
        )
    return {
        "grid_cost_aud": float(env.total_grid_cost),
        "export_revenue_aud": float(env.total_export_revenue),
        "grid_charge_cost_aud": float(getattr(env, "total_grid_charge_cost", 0.0)),
        "final_soc_pct": float(env._soc_pct),
        "battery_throughput_kwh": float(getattr(env, "total_throughput_kwh", 0.0)),
        "total_reward": float(total_reward),
        "trace": trace,
    }


def _replay_human(env: MicrogridEnv, actions: list[int]):
    env.reset()
    total_reward = 0.0
    trace: list[dict[str, Any]] = []
    for action in actions:
        row = env.episode_df.iloc[env._step_idx]
        _, reward, done, info = env.step(action)
        total_reward += reward
        ts = row["timestamp"]
        trace.append(
            {
                "time": ts.strftime("%H:%M") if hasattr(ts, "strftime") else str(row.get("time_label", "")),
                "action": info["action_name"],
                "soc_pct": round(float(env._soc_pct), 1),
                "cost": round(float(env.total_grid_cost), 3),
                "reward": round(float(reward), 4),
            }
        )
        if done:
            break
    return {
        "grid_cost_aud": float(env.total_grid_cost),
        "export_revenue_aud": float(env.total_export_revenue),
        "grid_charge_cost_aud": float(getattr(env, "total_grid_charge_cost", 0.0)),
        "final_soc_pct": float(env._soc_pct),
        "battery_throughput_kwh": float(getattr(env, "total_throughput_kwh", 0.0)),
        "total_reward": float(total_reward),
        "trace": trace,
    }


def _snapshot_view(resources, session: dict) -> dict[str, Any]:
    cfg, df, thresholds = resources[0], resources[1], resources[3]
    day = session["day"]
    episode_df = get_episode(df, day)
    use_priv = session["use_privileged"]
    model_name = session["model_name"]
    agent = load_trained_agent("q_learning", cfg.results_models / model_name, cfg, privileged=use_priv)
    agent_fn = greedy_action_fn(agent)
    forecast = _forecast(cfg, df)
    foresight = "oracle" if use_priv else "none"

    human_env = MicrogridEnv(episode_df, thresholds, cfg, privileged=False, foresight_mode="none")
    if session["human_actions"]:
        human_env.reset()
        for a in session["human_actions"]:
            human_env.step(a)
    else:
        human_env.reset()

    n_taken = len(session["human_actions"])
    agent_env = MicrogridEnv(
        episode_df,
        thresholds,
        cfg,
        privileged=use_priv,
        foresight_mode=foresight if use_priv else "none",
    )
    greedy_env = MicrogridEnv(episode_df, thresholds, cfg, privileged=False)
    agent_cost, agent_last, agent_soc, a_costs, a_socs, a_times = _rollout_n(agent_env, agent_fn, n_taken)
    greedy_cost, greedy_last, greedy_soc, g_costs, g_socs, g_times = _rollout_n(
        greedy_env, price_arbitrage_action_fn, n_taken
    )
    human_cost = float(human_env.total_grid_cost)

    # Human step series for live charts
    h_costs: list[float] = []
    h_socs: list[float] = []
    h_times: list[str] = []
    if n_taken:
        h_env = MicrogridEnv(episode_df, thresholds, cfg, privileged=False, foresight_mode="none")
        h_env.reset()
        for a in session["human_actions"]:
            row_h = h_env.episode_df.iloc[h_env._step_idx]
            h_env.step(a)
            h_costs.append(round(float(h_env.total_grid_cost), 3))
            h_socs.append(round(float(h_env._soc_pct), 1))
            ts_h = row_h["timestamp"]
            h_times.append(
                ts_h.strftime("%H:%M") if hasattr(ts_h, "strftime") else str(row_h.get("time_label", ""))
            )

    if session["done"] and session.get("summaries") is None:
        a_env = MicrogridEnv(
            episode_df, thresholds, cfg, privileged=use_priv, foresight_mode=foresight if use_priv else "none"
        )
        g_env = MicrogridEnv(episode_df, thresholds, cfg, privileged=False)
        h_env = MicrogridEnv(episode_df, thresholds, cfg, privileged=False)
        session["summaries"] = {
            "you": _replay_human(h_env, session["human_actions"]),
            "rl": _rollout_full(a_env, agent_fn),
            "greedy": _rollout_full(g_env, price_arbitrage_action_fn),
        }

    if session["done"] and session.get("summaries"):
        s = session["summaries"]
        costs = {"You": s["you"]["grid_cost_aud"], "RL": s["rl"]["grid_cost_aud"], "Greedy": s["greedy"]["grid_cost_aud"]}
        winner = min(costs, key=costs.get)
        return {
            "session_id": session["id"],
            "started": True,
            "done": True,
            "day": day,
            "agent_label": session["agent_label"],
            "winner": winner,
            "summaries": s,
            "costs": costs,
            "oversight_note": (
                "You always see a realistic 4h forecast. Privileged opponents may use a true direction signal — "
                "oversight demo, not a fair contest."
            ),
        }

    step = session["step"]
    idx = min(step, 47)
    row = episode_df.iloc[idx]
    ts = row["timestamp"]
    price = float(row["price_per_kwh"])
    retail = price + cfg.tariff.retail_margin_per_kwh
    export_px = price if cfg.tariff.export_pricing == "wholesale" else float(cfg.tariff.feed_in_per_kwh)
    pv = float(row["pv_kwh"])
    load = float(row["load_kwh"])
    soc = float(human_env._soc_pct)
    surplus = max(0.0, pv - load)
    deficit = max(0.0, load - pv)

    # Forecast for human
    fc = forecast.forecast_series_for_episode(episode_df, min(step, 47), add_noise=False)
    forecast_payload = []
    signal = None
    headline = None
    if not fc.empty:
        f_high = float(fc["forecast_price"].max())
        f_low = float(fc["forecast_price"].min())
        delta = f_high - price
        signal = FUTURE_SIGNAL_NAMES[future_signal_bin(delta, thresholds)]
        if delta <= 0:
            headline = "Next 4 hours: price expected to fall or stay flat"
        else:
            headline = "Next 4 hours: price expected to rise"
        for _, fr in fc.head(8).iterrows():
            forecast_payload.append(
                {
                    "time": str(fr.get("time_label", fr.get("step", ""))),
                    "price": round(float(fr["forecast_price"]), 4),
                }
            )

    # Q-values for agent decision tab (same inspect step as Streamlit)
    from src.replay import q_values_for_state

    q_env = MicrogridEnv(
        episode_df,
        thresholds,
        cfg,
        privileged=use_priv,
        foresight_mode=foresight if use_priv else "none",
    )
    q_env.reset()
    inspect_step = 0 if n_taken == 0 else min(n_taken - 1, 47)
    for _t in range(inspect_step):
        q_env.step(agent_fn(q_env))
    state = q_env._observe()
    q_table = agent.q if hasattr(agent, "q") else getattr(agent, "q1", None)
    q_vals = q_values_for_state(q_table, state) if q_table is not None else {}
    q_payload = [
        {"action": ACTION_DISPLAY.get(k, k), "q": round(float(v), 3)}
        for k, v in sorted(q_vals.items(), key=lambda x: -x[1])
    ]

    labels = h_times or a_times or g_times
    return {
        "session_id": session["id"],
        "started": True,
        "done": False,
        "paused": session.get("paused", False),
        "day": day,
        "agent_label": session["agent_label"],
        "use_privileged": use_priv,
        "step": step + 1,
        "time_label": ts.strftime("%H:%M"),
        "progress_pct": int(round(100 * step / 48)),
        "state": {
            "soc_pct": round(soc, 1),
            "soc_kwh": round(soc / 100.0 * float(cfg.battery_capacity_kwh), 2),
            "pv_kwh": round(pv, 3),
            "load_kwh": round(load, 3),
            "wholesale": round(price, 4),
            "retail": round(retail, 4),
            "export": round(export_px, 4),
            "surplus": round(surplus, 3),
            "deficit": round(deficit, 3),
        },
        "actions": ACTION_BUTTONS,
        "availability": _availability(soc, pv, load, cfg),
        "scoreboard": {
            "you": {"cost": round(human_cost, 2), "soc": round(soc, 1), "last": session.get("last_human")},
            "rl": {
                "cost": round(agent_cost, 2),
                "soc": round(agent_soc, 1),
                "last": ACTION_DISPLAY.get(agent_last or "—", agent_last or "—"),
            },
            "greedy": {
                "cost": round(greedy_cost, 2),
                "soc": round(greedy_soc, 1),
                "last": ACTION_DISPLAY.get(greedy_last or "—", greedy_last or "—"),
            },
        },
        "feedback": session.get("feedback"),
        "forecast": {"signal": signal, "headline": headline, "points": forecast_payload},
        "history": {
            "labels": labels,
            "you_cost": h_costs,
            "rl_cost": a_costs,
            "greedy_cost": g_costs,
            "you_soc": h_socs,
            "rl_soc": a_socs,
            "greedy_soc": g_socs,
        },
        "q_values": q_payload,
        "oversight_note": (
            "You see a realistic 4-hour forecast. "
            + (
                "Opponent is Privileged Q with a true four-hour direction signal — oversight demo."
                if use_priv
                else "Opponent is Current Q (current state only)."
            )
        ),
    }


def start_game(resources, *, day: str, use_privileged: bool, model_name: str) -> dict:
    sid = uuid.uuid4().hex
    session = {
        "id": sid,
        "day": day,
        "use_privileged": use_privileged,
        "model_name": model_name,
        "agent_label": "Privileged Q — true 4h signal" if use_privileged else "Current Q",
        "started": True,
        "step": 0,
        "done": False,
        "paused": False,
        "human_actions": [],
        "feedback": None,
        "last_human": None,
        "summaries": None,
    }
    _SESSIONS[sid] = session
    return _snapshot_view(resources, session)


def get_game(resources, session_id: str) -> dict:
    session = _SESSIONS.get(session_id)
    if not session:
        raise KeyError("Session not found")
    return _snapshot_view(resources, session)


def step_game(resources, session_id: str, action_key: str) -> dict:
    session = _SESSIONS.get(session_id)
    if not session:
        raise KeyError("Session not found")
    if session["done"]:
        return _snapshot_view(resources, session)
    if session.get("paused"):
        raise RuntimeError("Game is paused")

    cfg, df, thresholds = resources[0], resources[1], resources[3]
    day = session["day"]
    episode_df = get_episode(df, day)
    key_to_id = {b["key"]: b["id"] for b in ACTION_BUTTONS}
    if action_key not in key_to_id:
        raise ValueError(f"Unknown action {action_key}")
    action = key_to_id[action_key]

    human_env = MicrogridEnv(episode_df, thresholds, cfg, privileged=False, foresight_mode="none")
    human_env.reset()
    for a in session["human_actions"]:
        human_env.step(a)

    row = episode_df.iloc[min(session["step"], 47)]
    price = float(row["price_per_kwh"])
    retail = price + cfg.tariff.retail_margin_per_kwh
    soc_before = human_env._soc_pct
    avail = _availability(soc_before, float(row["pv_kwh"]), float(row["load_kwh"]), cfg)
    if not avail[action_key]["ok"]:
        raise RuntimeError(avail[action_key]["reason"] or "Action unavailable")

    _, reward, step_done, info = human_env.step(action)
    session["human_actions"].append(action)
    session["step"] = human_env._step_idx
    session["last_human"] = ACTION_DISPLAY.get(info["action_name"], info["action_name"])

    use_priv = session["use_privileged"]
    agent = load_trained_agent(
        "q_learning", cfg.results_models / session["model_name"], cfg, privileged=use_priv
    )
    agent_fn = greedy_action_fn(agent)
    a_env = MicrogridEnv(
        episode_df,
        thresholds,
        cfg,
        privileged=use_priv,
        foresight_mode="oracle" if use_priv else "none",
    )
    _, agent_act, _, _, _, _ = _rollout_n(a_env, agent_fn, len(session["human_actions"]))

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

    session["feedback"] = {
        "human_action": ACTION_DISPLAY.get(info["action_name"], info["action_name"]),
        "human_detail": " · ".join(detail_bits),
        "agent_action": ACTION_DISPLAY.get(agent_act or "hold", agent_act or "hold"),
        "agent_reason": _agent_reason(agent_act or "hold", price, retail),
    }
    if step_done:
        session["done"] = True
    return _snapshot_view(resources, session)


def toggle_pause(session_id: str) -> dict:
    session = _SESSIONS.get(session_id)
    if not session:
        raise KeyError("Session not found")
    session["paused"] = not session.get("paused", False)
    return {"paused": session["paused"]}


def quit_game(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)
