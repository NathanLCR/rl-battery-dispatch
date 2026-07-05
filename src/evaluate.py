"""Evaluate a policy on train/val/test days."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from src.config import Config, RewardWeights, load_config
from src.data_loader import DaySplit, get_episode, load_customer_dataset
from src.discretizer import BinThresholds, fit_discretizer
from src.environment import MicrogridEnv
from src.oracle import no_battery_import_cost, oracle_perfect_foresight_import
from src.rule_baseline import run_rule_episode


ActionFn = Callable[[MicrogridEnv], int]

EVENING_HOUR = 17.0


def _is_evening_step(timestamp) -> bool:
    hour = timestamp.hour + timestamp.minute / 60.0
    return hour >= EVENING_HOUR


def run_episode_with_policy(
    episode_df: pd.DataFrame,
    thresholds: BinThresholds,
    cfg: Config,
    action_fn: ActionFn,
    reward_mode: str = "battery_aware",
) -> dict:
    """Roll out ``action_fn`` on one day and return episode-level KPIs."""
    env = MicrogridEnv(episode_df, thresholds, cfg, reward_mode=reward_mode)
    env.reset()
    total_reward = 0.0
    total_pv = 0.0
    total_load = 0.0
    evening_import = 0.0
    done = False

    while not done:
        row = env.episode_df.iloc[env._step_idx]
        total_pv += float(row["pv_kwh"])
        total_load += float(row["load_kwh"])
        action = action_fn(env)
        _, reward, done, info = env.step(action)
        total_reward += reward
        if _is_evening_step(row["timestamp"]):
            evening_import += info["grid_import_kwh"]

    solar_used = total_pv - env.total_solar_waste_kwh
    self_consumption_rate = solar_used / total_pv if total_pv > 0 else 0.0
    self_sufficiency = (total_load - env.total_grid_import_kwh) / total_load if total_load > 0 else 0.0

    oracle_cost = oracle_perfect_foresight_import(episode_df, cfg)
    no_bat_cost = no_battery_import_cost(episode_df, cfg)

    return {
        "episode_day": env._episode_day,
        "split": str(episode_df["split"].iloc[0]) if "split" in episode_df.columns else "",
        "total_reward": total_reward,
        "grid_cost_aud": env.total_grid_cost,
        "grid_import_kwh": env.total_grid_import_kwh,
        "solar_waste_kwh": env.total_solar_waste_kwh,
        "final_soc_pct": env._soc_pct,
        "total_pv_kwh": total_pv,
        "total_load_kwh": total_load,
        "self_consumption_rate": self_consumption_rate,
        "self_sufficiency": self_sufficiency,
        "evening_peak_import_kwh": evening_import,
        "oracle_cost_aud": oracle_cost,
        "no_battery_cost_aud": no_bat_cost,
    }


def evaluate_split(
    df: pd.DataFrame,
    thresholds: BinThresholds,
    split: DaySplit,
    split_name: str,
    action_fn: ActionFn,
    cfg: Config | None = None,
    reward_mode: str = "battery_aware",
) -> pd.DataFrame:
    """Evaluate ``action_fn`` on every day in the named split."""
    cfg = cfg or load_config()
    days = split.days(split_name)  # type: ignore[arg-type]
    rows = []
    for day in days:
        ep = get_episode(df, day)
        rows.append(
            run_episode_with_policy(ep, thresholds, cfg, action_fn, reward_mode)
        )
    return pd.DataFrame(rows)


def summarize(results: pd.DataFrame) -> dict:
    """Aggregate per-day evaluation rows into summary statistics."""
    out = {
        "n_days": len(results),
        "mean_reward": results["total_reward"].mean(),
        "total_grid_cost_aud": results["grid_cost_aud"].sum(),
        "mean_grid_import_kwh": results["grid_import_kwh"].mean(),
        "mean_solar_waste_kwh": results["solar_waste_kwh"].mean(),
    }
    for col in (
        "self_consumption_rate",
        "self_sufficiency",
        "evening_peak_import_kwh",
        "oracle_cost_aud",
        "no_battery_cost_aud",
    ):
        if col in results.columns:
            out[f"mean_{col}"] = results[col].mean()
    if "oracle_cost_aud" in results.columns and "no_battery_cost_aud" in results.columns:
        total_oracle = results["oracle_cost_aud"].sum()
        total_no_bat = results["no_battery_cost_aud"].sum()
        total_actual = results["grid_cost_aud"].sum()
        span = total_no_bat - total_oracle
        if span > 0:
            out["pct_of_oracle_savings"] = round((total_no_bat - total_actual) / span * 100, 2)
        else:
            out["pct_of_oracle_savings"] = None
    return out


def oracle_bounds_summary(results: pd.DataFrame) -> dict:
    """Aggregate oracle and no-battery bounds across days."""
    return {
        "total_no_battery_cost_aud": results["no_battery_cost_aud"].sum(),
        "total_oracle_cost_aud": results["oracle_cost_aud"].sum(),
    }
