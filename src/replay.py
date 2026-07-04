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
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run one episode and return per-step trace + summary totals."""
    cfg = cfg or load_config()
    env = MicrogridEnv(episode_df, thresholds, cfg, reward_mode=reward_mode)
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
                "grid_import_kwh": info["grid_import_kwh"],
                "solar_waste_kwh": info["solar_waste_kwh"],
                "charge_kwh": info["charge_kwh"],
                "discharge_kwh": info["discharge_kwh"],
            }
        )

    summary = {
        "episode_day": env._episode_day,
        "total_reward": total_reward,
        "grid_cost_aud": env.total_grid_cost,
        "grid_import_kwh": env.total_grid_import_kwh,
        "solar_waste_kwh": env.total_solar_waste_kwh,
        "final_soc_pct": env._soc_pct,
    }
    return pd.DataFrame(rows), summary


def q_values_for_state(q_table, state: int) -> dict[str, float]:
    """Return Q(s, a) for every action at a discretised state index."""
    return {ACTION_NAMES[a]: float(q_table.table[state, a]) for a in ACTION_NAMES}
