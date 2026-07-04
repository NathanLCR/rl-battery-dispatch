"""Deterministic rule-based battery controller (baseline for RL comparison)."""

from __future__ import annotations

from src.constants import CHARGE, DISCHARGE, HOLD
from src.discretizer import BinThresholds, _feature_bin, soc_bin


def rule_action(
    soc_pct: float,
    pv_kwh: float,
    load_kwh: float,
    thresholds: BinThresholds,
) -> int:
    """
    Heuristic dispatch policy using the same discretised bins as the RL agents.

    Rules:
      - High solar and headroom in the battery -> charge
      - High load and available stored energy -> discharge
      - Otherwise -> hold
    """
    s = soc_bin(soc_pct, thresholds)
    p = _feature_bin(pv_kwh, thresholds.pv_q33, thresholds.pv_q66)
    l = _feature_bin(load_kwh, thresholds.load_q33, thresholds.load_q66)

    if p == 2 and s < 2:
        return CHARGE
    if l == 2 and s > 0:
        return DISCHARGE
    return HOLD


def run_rule_episode(env) -> dict:
    """Run one full episode with rule policy. env must be MicrogridEnv."""
    state = env.reset()
    total_reward = 0.0
    done = False
    while not done:
        row = env.episode_df.iloc[env._step_idx]
        action = rule_action(
            env._soc_pct,
            float(row["pv_kwh"]),
            float(row["load_kwh"]),
            env.thresholds,
        )
        state, reward, done, info = env.step(action)
        total_reward += reward

    return {
        "episode_day": env._episode_day,
        "total_reward": total_reward,
        "grid_cost_aud": env.total_grid_cost,
        "grid_import_kwh": env.total_grid_import_kwh,
        "solar_waste_kwh": env.total_solar_waste_kwh,
        "final_soc_pct": env._soc_pct,
    }
