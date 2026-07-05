"""Microgrid battery environment — custom MDP for GréineQ."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.config import Config, RewardWeights, load_config
from src.constants import CHARGE, DISCHARGE, HOLD, N_ACTIONS
from src.discretizer import BinThresholds, state_index
from src.physics import apply_battery_action


class MicrogridEnv:
    """One-day (48-step) battery dispatch MDP using Ausgrid load/PV and AEMO prices."""

    def __init__(
        self,
        episode_df: pd.DataFrame,
        thresholds: BinThresholds,
        cfg: Config | None = None,
        reward_mode: str = "battery_aware",
    ) -> None:
        if len(episode_df) != 48:
            raise ValueError(f"Episode must have 48 steps, got {len(episode_df)}")

        self.cfg = cfg or load_config()
        self.thresholds = thresholds
        self.episode_df = episode_df.reset_index(drop=True)
        self.reward_weights = self._resolve_reward_weights(reward_mode, self.cfg)

        self._step_idx = 0
        self._soc_pct = self.cfg.initial_soc_pct
        self._episode_day = str(episode_df["episode_day"].iloc[0])

        self.total_grid_cost = 0.0
        self.total_grid_import_kwh = 0.0
        self.total_solar_waste_kwh = 0.0

    @staticmethod
    def _resolve_reward_weights(mode: str, cfg: Config) -> RewardWeights:
        if mode == "cost_only":
            return cfg.reward_cost_only
        if mode == "battery_aware":
            return cfg.reward_battery_aware
        raise ValueError(f"Unknown reward_mode: {mode!r}")

    @property
    def n_actions(self) -> int:
        return N_ACTIONS

    def reset(self) -> int:
        self._step_idx = 0
        self._soc_pct = self.cfg.initial_soc_pct
        self.total_grid_cost = 0.0
        self.total_grid_import_kwh = 0.0
        self.total_solar_waste_kwh = 0.0
        return self._observe()

    def step(self, action: int) -> tuple[int, float, bool, dict[str, Any]]:
        if action not in (HOLD, CHARGE, DISCHARGE):
            raise ValueError(f"Invalid action {action}")

        row = self.episode_df.iloc[self._step_idx]
        pv_kwh = float(row["pv_kwh"])
        load_kwh = float(row["load_kwh"])
        price = float(row["price_per_kwh"])
        retail_price = price + self.cfg.tariff.retail_margin_per_kwh

        physics = apply_battery_action(self._soc_pct, action, pv_kwh, load_kwh, self.cfg)
        reward = self._compute_reward(physics, retail_price)

        self.total_grid_cost += physics["grid_import_kwh"] * retail_price
        self.total_grid_import_kwh += physics["grid_import_kwh"]
        self.total_solar_waste_kwh += physics["solar_waste_kwh"]

        self._soc_pct = physics["soc_pct"]
        self._step_idx += 1
        done = self._step_idx >= len(self.episode_df)

        info = {
            "episode_day": self._episode_day,
            "step": self._step_idx,
            "action": action,
            "action_name": {HOLD: "hold", CHARGE: "charge", DISCHARGE: "discharge"}[action],
            "soc_pct": self._soc_pct,
            "pv_kwh": pv_kwh,
            "load_kwh": load_kwh,
            "price_per_kwh": price,
            "retail_price_per_kwh": retail_price,
            **physics,
        }

        next_state = self._observe()
        return next_state, reward, done, info

    def _observe(self) -> int:
        row = self.episode_df.iloc[min(self._step_idx, len(self.episode_df) - 1)]
        ts = row["timestamp"]
        hour = ts.hour + ts.minute / 60.0
        return state_index(
            self._soc_pct,
            float(row["pv_kwh"]),
            float(row["load_kwh"]),
            float(row["price_per_kwh"]),
            hour,
            self.thresholds,
        )

    def _compute_reward(self, physics: dict[str, float], retail_price_per_kwh: float) -> float:
        """Negative household cost (AUD): import bill, curtailed solar, battery wear."""
        w = self.reward_weights
        tar = self.cfg.tariff
        capacity = self.cfg.battery_capacity_kwh

        import_cost = physics["grid_import_kwh"] * retail_price_per_kwh
        solar_opp_cost = physics["solar_waste_kwh"] * tar.feed_in_per_kwh
        deg_cost = physics["battery_deg"] * capacity * tar.battery_deg_cost_per_kwh

        reward = 0.0
        reward -= w.w_grid_cost * import_cost
        reward -= w.w_solar_waste * solar_opp_cost
        reward -= w.w_battery_deg * deg_cost
        if physics["invalid_action"]:
            reward -= w.w_invalid_action
        return float(reward)
