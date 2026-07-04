"""Rule-based battery controllers for RL comparison."""

from __future__ import annotations

from src.constants import CHARGE, DISCHARGE, HOLD
from src.discretizer import BinThresholds, _feature_bin, soc_bin


def rule_tertile_action(
    soc_pct: float,
    pv_kwh: float,
    load_kwh: float,
    thresholds: BinThresholds,
) -> int:
    """
    Weak heuristic: charge only on top-PV tertile, discharge only on top-load tertile.
    """
    s = soc_bin(soc_pct, thresholds)
    p = _feature_bin(pv_kwh, thresholds.pv_q33, thresholds.pv_q66)
    l = _feature_bin(load_kwh, thresholds.load_q33, thresholds.load_q66)

    if p == 2 and s < 2:
        return CHARGE
    if l == 2 and s > 0:
        return DISCHARGE
    return HOLD


# Backward-compatible alias used elsewhere in the project.
rule_action = rule_tertile_action


def greedy_self_consumption_action(
    soc_pct: float,
    pv_kwh: float,
    load_kwh: float,
    thresholds: BinThresholds,
    min_soc_pct: float = 10.0,
    max_soc_pct: float = 90.0,
) -> int:
    """
    Strong myopic baseline: charge any surplus solar, discharge any load deficit.
    """
    _ = thresholds
    surplus = max(0.0, pv_kwh - load_kwh)
    deficit = max(0.0, load_kwh - pv_kwh)

    if surplus > 0 and soc_pct < max_soc_pct:
        return CHARGE
    if deficit > 0 and soc_pct > min_soc_pct:
        return DISCHARGE
    return HOLD


def no_battery_action(
    soc_pct: float,
    pv_kwh: float,
    load_kwh: float,
    thresholds: BinThresholds,
) -> int:
    """Always hold — upper bound on cost without a battery."""
    _ = (soc_pct, pv_kwh, load_kwh, thresholds)
    return HOLD


def run_rule_episode(env) -> dict:
    """Run one full episode with the tertile rule policy."""
    env.reset()
    total_reward = 0.0
    done = False
    while not done:
        row = env.episode_df.iloc[env._step_idx]
        action = rule_tertile_action(
            env._soc_pct,
            float(row["pv_kwh"]),
            float(row["load_kwh"]),
            env.thresholds,
        )
        _, reward, done, _ = env.step(action)
        total_reward += reward

    return {
        "episode_day": env._episode_day,
        "total_reward": total_reward,
        "grid_cost_aud": env.total_grid_cost,
        "grid_import_kwh": env.total_grid_import_kwh,
        "solar_waste_kwh": env.total_solar_waste_kwh,
        "final_soc_pct": env._soc_pct,
    }
