"""Evaluate a policy on train/val/test days."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from src.config import Config, load_config
from src.data_loader import DaySplit, get_episode
from src.discretizer import BinThresholds
from src.environment import MicrogridEnv
from src.oracle import no_battery_import_cost, oracle_perfect_foresight_import


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
    privileged: bool = False,
    foresight_mode: str | None = None,
    forecast_model=None,
) -> dict:
    """Roll out ``action_fn`` on one day and return episode-level KPIs."""
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
    # Grid import includes arbitrage charging; self-sufficiency uses household import only
    household_import = env.total_grid_import_kwh - env.total_grid_charge_kwh
    self_sufficiency = (total_load - household_import) / total_load if total_load > 0 else 0.0

    oracle_cost = oracle_perfect_foresight_import(episode_df, cfg)
    no_bat_cost = no_battery_import_cost(episode_df, cfg)

    return {
        "episode_day": env._episode_day,
        "split": str(episode_df["split"].iloc[0]) if "split" in episode_df.columns else "",
        "total_reward": total_reward,
        "grid_cost_aud": env.total_grid_cost,
        "household_import_cost_aud": env.total_household_import_cost,
        "export_revenue_aud": env.total_export_revenue,
        "grid_charge_cost_aud": env.total_grid_charge_cost,
        "net_arbitrage_profit_aud": env.net_arbitrage_profit,
        "grid_import_kwh": env.total_grid_import_kwh,
        "export_kwh": env.total_export_kwh,
        "grid_charge_kwh": env.total_grid_charge_kwh,
        "battery_throughput_kwh": env.total_throughput_kwh,
        "cycling_cost_aud": env.total_cycling_cost,
        "terminal_soc_adjustment_aud": env.terminal_soc_adjustment,
        "n_grid_charge_actions": env.n_grid_charge_actions,
        "n_export_actions": env.n_export_actions,
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
    privileged: bool = False,
    foresight_mode: str | None = None,
    forecast_model=None,
) -> pd.DataFrame:
    """Evaluate ``action_fn`` on every day in the named split."""
    cfg = cfg or load_config()
    days = split.days(split_name)  # type: ignore[arg-type]
    rows = []
    for day in days:
        ep = get_episode(df, day)
        rows.append(
            run_episode_with_policy(
                ep,
                thresholds,
                cfg,
                action_fn,
                reward_mode,
                privileged=privileged,
                foresight_mode=foresight_mode,
                forecast_model=forecast_model,
            )
        )
    return pd.DataFrame(rows)


def summarize(results: pd.DataFrame) -> dict:
    """Aggregate per-day evaluation rows into summary statistics."""
    out: dict = {
        "n_days": len(results),
        "mean_reward": float(results["total_reward"].mean()),
        "total_grid_cost_aud": float(results["grid_cost_aud"].sum()),
        "mean_grid_import_kwh": float(results["grid_import_kwh"].mean()),
        "mean_solar_waste_kwh": float(results["solar_waste_kwh"].mean()),
    }
    sum_cols = (
        "export_revenue_aud",
        "grid_charge_cost_aud",
        "net_arbitrage_profit_aud",
        "export_kwh",
        "grid_charge_kwh",
        "battery_throughput_kwh",
        "n_grid_charge_actions",
        "n_export_actions",
        "household_import_cost_aud",
        "cycling_cost_aud",
        "terminal_soc_adjustment_aud",
    )
    mean_cols = (
        "final_soc_pct",
        "self_consumption_rate",
        "self_sufficiency",
        "evening_peak_import_kwh",
        "oracle_cost_aud",
        "no_battery_cost_aud",
    )
    for col in sum_cols:
        if col in results.columns:
            out[f"total_{col}"] = float(results[col].sum())
    for col in mean_cols:
        if col in results.columns:
            out[f"mean_{col}"] = float(results[col].mean())
    if "oracle_cost_aud" in results.columns and "no_battery_cost_aud" in results.columns:
        total_oracle = float(results["oracle_cost_aud"].sum())
        total_no_bat = float(results["no_battery_cost_aud"].sum())
        total_actual = float(results["grid_cost_aud"].sum())
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
