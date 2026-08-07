"""Step-by-step episode replay for the dashboard."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from src.config import Config, load_config
from src.constants import ACTION_NAMES
from src.environment import MicrogridEnv
from src.discretizer import BinThresholds

ActionFn = Callable[[MicrogridEnv], int]


def trace_episode(
    episode_df: pd.DataFrame,
    thresholds: BinThresholds,
    action_fn: ActionFn,
    cfg: Config | None = None,
    reward_mode: str = "battery_aware",
    privileged: bool = False,
    foresight_mode: str | None = None,
    forecast_model=None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run one episode and return per-step trace + summary totals."""
    cfg = cfg or load_config()
    env = MicrogridEnv(
        episode_df,
        thresholds,
        cfg,
        reward_mode=reward_mode,
        privileged=privileged,
        foresight_mode=foresight_mode,
        forecast_model=forecast_model,
    )
    env.reset()

    rows: list[dict[str, Any]] = []
    total_reward = 0.0
    done = False

    while not done:
        row = env.episode_df.iloc[env._step_idx]
        state = env._observe()
        action = action_fn(env)
        _, reward, done, info = env.step(action)
        total_reward += reward

        ts = row["timestamp"]
        rows.append(
            {
                "step": info["step"],
                "timestamp": ts,
                "time_label": ts.strftime("%H:%M"),
                "state": state,
                "action": info["action_name"],
                "action_id": info["action"],
                "reward": reward,
                "soc_pct": info["soc_pct"],
                "pv_kwh": info["pv_kwh"],
                "load_kwh": info["load_kwh"],
                "price_per_kwh": info["price_per_kwh"],
                "retail_price_per_kwh": info["retail_price_per_kwh"],
                "export_price_per_kwh": info.get("export_price_per_kwh", info.get("feed_in_price_per_kwh")),
                "export_revenue_aud": info.get("export_revenue_aud", 0.0),
                "grid_import_kwh": info["grid_import_kwh"],
                "solar_waste_kwh": info["solar_waste_kwh"],
                "charge_kwh": info["charge_kwh"],
                "discharge_kwh": info["discharge_kwh"],
                "grid_charge_kwh": info.get("grid_charge_kwh", 0.0),
                "export_kwh": info.get("export_kwh", 0.0),
                "future_price_delta": info.get("future_price_delta"),
            }
        )

    trace_df = pd.DataFrame(rows)
    total_pv = trace_df["pv_kwh"].sum()
    total_load = trace_df["load_kwh"].sum()
    evening_mask = trace_df["timestamp"].apply(
        lambda t: t.hour + t.minute / 60.0 >= 17.0
    )
    evening_import = trace_df.loc[evening_mask, "grid_import_kwh"].sum()

    summary = {
        "episode_day": env._episode_day,
        "total_reward": total_reward,
        "grid_cost_aud": env.total_grid_cost,
        "grid_import_kwh": env.total_grid_import_kwh,
        "solar_waste_kwh": env.total_solar_waste_kwh,
        "export_revenue_aud": env.total_export_revenue,
        "grid_charge_cost_aud": env.total_grid_charge_cost,
        "net_arbitrage_profit_aud": env.net_arbitrage_profit,
        "export_kwh": env.total_export_kwh,
        "grid_charge_kwh": env.total_grid_charge_kwh,
        "battery_throughput_kwh": env.total_throughput_kwh,
        "n_grid_charge_actions": env.n_grid_charge_actions,
        "n_export_actions": env.n_export_actions,
        "final_soc_pct": env._soc_pct,
        "self_consumption_rate": (total_pv - env.total_solar_waste_kwh) / total_pv if total_pv > 0 else 0.0,
        "self_sufficiency": (total_load - (env.total_grid_import_kwh - env.total_grid_charge_kwh)) / total_load if total_load > 0 else 0.0,
        "evening_peak_import_kwh": evening_import,
    }
    return trace_df, summary


def q_values_for_state(q_table, state: int) -> dict[str, float]:
    """Return Q(s, a) for every action at a discretised state index."""
    return {ACTION_NAMES[a]: float(q_table.table[state, a]) for a in ACTION_NAMES}
