"""Evaluate a policy on train/val/test days."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from src.config import Config, load_config
from src.data_loader import DaySplit, get_episode, load_customer_dataset
from src.discretizer import BinThresholds, fit_discretizer
from src.environment import MicrogridEnv
from src.rule_baseline import run_rule_episode


ActionFn = Callable[[MicrogridEnv], int]
"""Policy callback: given the live environment, return an action index."""


def run_episode_with_policy(
    episode_df: pd.DataFrame,
    thresholds: BinThresholds,
    cfg: Config,
    action_fn: ActionFn,
    reward_mode: str = "battery_aware",
) -> dict:
    """Roll out ``action_fn`` on one day and return episode-level KPIs."""
    env = MicrogridEnv(episode_df, thresholds, cfg, reward_mode=reward_mode)
    state = env.reset()
    total_reward = 0.0
    done = False
    while not done:
        action = action_fn(env)
        state, reward, done, info = env.step(action)
        total_reward += reward

    return {
        "episode_day": env._episode_day,
        "split": str(episode_df["split"].iloc[0]),
        "total_reward": total_reward,
        "grid_cost_aud": env.total_grid_cost,
        "grid_import_kwh": env.total_grid_import_kwh,
        "solar_waste_kwh": env.total_solar_waste_kwh,
        "final_soc_pct": env._soc_pct,
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
    return {
        "n_days": len(results),
        "mean_reward": results["total_reward"].mean(),
        "total_grid_cost_aud": results["grid_cost_aud"].sum(),
        "mean_grid_import_kwh": results["grid_import_kwh"].mean(),
        "mean_solar_waste_kwh": results["solar_waste_kwh"].mean(),
    }


if __name__ == "__main__":
    from src.rule_baseline import rule_action

    cfg = load_config()
    df, day_split = load_customer_dataset(cfg)
    thresholds = fit_discretizer(df, cfg)

    def policy(env: MicrogridEnv) -> int:
        row = env.episode_df.iloc[env._step_idx]
        return rule_action(
            env._soc_pct,
            float(row["pv_kwh"]),
            float(row["load_kwh"]),
            env.thresholds,
        )

    test_results = evaluate_split(df, thresholds, day_split, "test", policy, cfg)
    stats = summarize(test_results)
    print("Rule baseline on TEST split:")
    for k, v in stats.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    print("\nFirst 5 test days:")
    print(test_results.head().to_string(index=False))
