"""Perfect-foresight oracle and no-battery cost bounds."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import Config
from src.constants import CHARGE, DISCHARGE, EXPORT, GRID_CHARGE, HOLD
from src.physics import apply_battery_action

ALL_ACTIONS = (HOLD, CHARGE, DISCHARGE, GRID_CHARGE, EXPORT)


def _export_price(wholesale: float, cfg: Config) -> float:
    if cfg.tariff.export_pricing == "fixed":
        return cfg.tariff.feed_in_per_kwh
    return float(wholesale)


def no_battery_import_cost(episode_df: pd.DataFrame, cfg: Config) -> float:
    """Retail import bill if the battery never operates (no terminal SOC adjustment)."""
    margin = cfg.tariff.retail_margin_per_kwh
    total = 0.0
    for _, row in episode_df.iterrows():
        pv = float(row["pv_kwh"])
        load = float(row["load_kwh"])
        retail = float(row["price_per_kwh"]) + margin
        total += max(0.0, load - pv) * retail
    return total


def oracle_perfect_foresight_import(
    episode_df: pd.DataFrame,
    cfg: Config,
    n_soc_bins: int = 101,
    actions: tuple[int, ...] = ALL_ACTIONS,
) -> float:
    """
    Minimum net cost over 48 steps with perfect foresight (backward DP).

    Includes cycling cost and terminal SOC valuation matching ``MicrogridEnv``.
    Export priced per ``cfg.tariff.export_pricing`` (wholesale or fixed FiT).
    """
    n_steps = len(episode_df)
    capacity = cfg.battery_capacity_kwh
    min_soc_kwh = cfg.min_soc_pct / 100.0 * capacity
    max_soc_kwh = cfg.max_soc_pct / 100.0 * capacity
    soc_grid = np.linspace(min_soc_kwh, max_soc_kwh, n_soc_bins)
    terminal_value = cfg.tariff.terminal_soc_value_per_kwh
    initial_kwh = cfg.initial_soc_pct / 100.0 * capacity

    def soc_to_idx(soc_kwh: float) -> int:
        if soc_kwh <= min_soc_kwh:
            return 0
        if soc_kwh >= max_soc_kwh:
            return n_soc_bins - 1
        return int(round((soc_kwh - min_soc_kwh) / (max_soc_kwh - min_soc_kwh) * (n_soc_bins - 1)))

    # Terminal: cost of ending below initial SOC (credit if above)
    v = (initial_kwh - soc_grid) * terminal_value

    for t in range(n_steps - 1, -1, -1):
        row = episode_df.iloc[t]
        pv = float(row["pv_kwh"])
        load = float(row["load_kwh"])
        wholesale = float(row["price_per_kwh"])
        retail = wholesale + cfg.tariff.retail_margin_per_kwh
        export_px = _export_price(wholesale, cfg)
        v_next = np.full(n_soc_bins, np.inf, dtype=np.float64)

        for si, soc_kwh in enumerate(soc_grid):
            soc_pct = soc_kwh / capacity * 100.0
            best = np.inf
            for action in actions:
                physics = apply_battery_action(soc_pct, action, pv, load, cfg)
                step_cost = (
                    physics["grid_import_kwh"] * retail
                    - physics["export_kwh"] * export_px
                    + physics["cycling_cost_aud"]
                )
                nj = soc_to_idx(physics["soc_kwh"])
                best = min(best, step_cost + v[nj])
            v_next[si] = best
        v = v_next

    start_soc_kwh = cfg.initial_soc_pct / 100.0 * capacity
    return float(v[soc_to_idx(start_soc_kwh)])


# Backward-compatible aliases
no_battery_cost = no_battery_import_cost
oracle_perfect_foresight = oracle_perfect_foresight_import
