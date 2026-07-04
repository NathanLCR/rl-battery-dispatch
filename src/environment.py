"""Microgrid battery environment — custom MDP for GréineGrid RL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.config import Config, RewardWeights, load_config
from src.constants import CHARGE, DISCHARGE, HOLD, N_ACTIONS, STEP_HOURS
from src.discretizer import BinThresholds, state_index


@dataclass
class StepResult:
    state: int
    reward: float
    done: bool
    info: dict[str, Any]


class MicrogridEnv:
    """
    Gym-style MDP for home battery dispatch on a solar + grid microgrid.

    Episode structure:
        - One calendar day, 48 steps at 30-minute resolution.
        - State: discretised (SOC, PV, load, price, time-of-day).
        - Actions: hold, charge surplus solar, or discharge to offset load.
        - Exogenous inputs per step come from merged Ausgrid + AEMO data.

    Rewards are negative costs (grid import, solar curtailment, battery stress)
    weighted by ``reward_mode`` in ``config.yaml``.
    """

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
        self.reward_weights = self._resolve_reward_weights(reward_mode)

        self._step_idx = 0
        self._soc_pct = self.cfg.initial_soc_pct
        self._episode_day = str(episode_df["episode_day"].iloc[0])

        self.total_grid_cost = 0.0
        self.total_grid_import_kwh = 0.0
        self.total_solar_waste_kwh = 0.0

    @staticmethod
    def _resolve_reward_weights(mode: str) -> RewardWeights:
        if mode == "cost_only":
            return load_config().reward_cost_only
        if mode == "battery_aware":
            return load_config().reward_battery_aware
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

        physics = self._apply_action(action, pv_kwh, load_kwh)
        reward = self._compute_reward(physics, price)

        self.total_grid_cost += physics["grid_import_kwh"] * price
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
            **physics,
        }

        next_state = self._observe() if not done else self._observe()
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

    def _soc_kwh(self) -> float:
        return self._soc_pct / 100.0 * self.cfg.battery_capacity_kwh

    def _apply_action(self, action: int, pv_kwh: float, load_kwh: float) -> dict[str, float]:
        """Simulate one 30-min step: battery limits, grid import, and solar waste."""
        cfg = self.cfg
        capacity = cfg.battery_capacity_kwh
        soc_kwh = self._soc_kwh()
        min_soc_kwh = cfg.min_soc_pct / 100.0 * capacity
        max_soc_kwh = cfg.max_soc_pct / 100.0 * capacity
        max_charge_kwh = cfg.max_charge_kw * STEP_HOURS
        max_discharge_kwh = cfg.max_discharge_kw * STEP_HOURS

        charge_kwh = 0.0
        discharge_kwh = 0.0
        invalid = False

        surplus = max(0.0, pv_kwh - load_kwh)
        deficit = max(0.0, load_kwh - pv_kwh)

        if action == CHARGE:
            room = max(0.0, max_soc_kwh - soc_kwh)
            charge_kwh = min(max_charge_kwh, surplus, room)
            if surplus > 0 and room <= 0:
                invalid = True
        elif action == DISCHARGE:
            available = max(0.0, soc_kwh - min_soc_kwh)
            discharge_kwh = min(max_discharge_kwh, deficit, available)
            if deficit > 0 and available <= 0:
                invalid = True

        soc_kwh = soc_kwh + charge_kwh - discharge_kwh
        soc_kwh = max(0.0, min(capacity, soc_kwh))
        soc_pct = soc_kwh / capacity * 100.0

        # Residual load after PV and battery discharge; surplus after load and charging
        grid_import_kwh = max(0.0, load_kwh - pv_kwh - discharge_kwh)
        solar_waste_kwh = max(0.0, pv_kwh - load_kwh - charge_kwh)

        # Penalise operating outside configured SOC guard bands
        battery_deg = 0.0
        if soc_pct < cfg.min_soc_pct:
            battery_deg += (cfg.min_soc_pct - soc_pct) / 100.0
        if soc_pct > cfg.max_soc_pct:
            battery_deg += (soc_pct - cfg.max_soc_pct) / 100.0

        return {
            "charge_kwh": charge_kwh,
            "discharge_kwh": discharge_kwh,
            "grid_import_kwh": grid_import_kwh,
            "solar_waste_kwh": solar_waste_kwh,
            "soc_pct": soc_pct,
            "battery_deg": battery_deg,
            "invalid_action": float(invalid),
            "unmet_demand_kwh": 0.0,
        }

    def _compute_reward(self, physics: dict[str, float], price_per_kwh: float) -> float:
        """Return a scalar reward; higher is better (costs are subtracted)."""
        w = self.reward_weights
        grid_cost = physics["grid_import_kwh"] * price_per_kwh
        reward = 0.0
        reward -= w.w_grid_cost * grid_cost
        reward -= w.w_solar_waste * physics["solar_waste_kwh"]
        reward -= w.w_battery_deg * physics["battery_deg"]
        reward -= w.w_unmet_demand * physics["unmet_demand_kwh"]
        if physics["invalid_action"]:
            reward -= w.w_invalid_action
        return float(reward)


if __name__ == "__main__":
    from src.data_loader import get_episode, load_customer_dataset
    from src.discretizer import fit_discretizer

    cfg = load_config()
    df, split = load_customer_dataset(cfg)
    thresholds = fit_discretizer(df, cfg)

    day = split.train[0]
    ep = get_episode(df, day)
    env = MicrogridEnv(ep, thresholds, cfg)

    state = env.reset()
    print(f"Episode day: {day} | initial state index: {state} | SOC: {env._soc_pct}%")

    total_reward = 0.0
    for t in range(48):
        action = CHARGE if t < 12 else HOLD
        state, reward, done, info = env.step(action)
        total_reward += reward
        if t in (0, 11, 23, 47):
            print(
                f"  step {info['step']:2d} | {info['action_name']:8s} | "
                f"SOC {info['soc_pct']:5.1f}% | grid {info['grid_import_kwh']:.3f} kWh | "
                f"reward {reward:+.4f}"
            )
        if done:
            break

    print(f"\nEpisode totals:")
    print(f"  reward: {total_reward:.4f}")
    print(f"  grid cost (AUD): {env.total_grid_cost:.4f}")
    print(f"  grid import (kWh): {env.total_grid_import_kwh:.3f}")
    print(f"  solar waste (kWh): {env.total_solar_waste_kwh:.3f}")
