"""Microgrid battery environment — custom MDP for GréineQ."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.config import Config, RewardWeights, load_config
from src.constants import CHARGE, DISCHARGE, EXPORT, GRID_CHARGE, HOLD, N_ACTIONS
from src.discretizer import BinThresholds, future_price_delta, state_index
from src.physics import apply_battery_action
from src.price_forecast import PriceForecastModel

VALID_ACTIONS = (HOLD, CHARGE, DISCHARGE, GRID_CHARGE, EXPORT)
ACTION_NAME_LOOKUP = {
    HOLD: "hold",
    CHARGE: "charge",
    DISCHARGE: "discharge",
    GRID_CHARGE: "grid_charge",
    EXPORT: "export",
}


class MicrogridEnv:
    """One-day (48-step) battery dispatch MDP using Ausgrid load/PV and AEMO prices.

    Export pricing (``cfg.tariff.export_pricing``):
      - ``wholesale``: experimental wholesale-exposed tariff —
        export revenue = exported_kWh × current wholesale AUD/kWh
        (AEMO AUD/MWh ÷ 1000 already stored as ``price_per_kwh``).
        Not a normal Australian household feed-in tariff.
      - ``fixed``: legacy FiT at ``feed_in_per_kwh``.

    Privileged foresight (``foresight_mode`` when ``privileged=True``):
      - ``oracle``: true max(price next 4h) − current
      - ``forecast``: realistic climatology+persistence forecast delta
    """

    def __init__(
        self,
        episode_df: pd.DataFrame,
        thresholds: BinThresholds,
        cfg: Config | None = None,
        reward_mode: str = "battery_aware",
        privileged: bool = False,
        foresight_mode: str | None = None,
        forecast_model: PriceForecastModel | None = None,
        forecast_rng: np.random.Generator | None = None,
        forecast_noise: bool = False,
    ) -> None:
        if len(episode_df) != 48:
            raise ValueError(f"Episode must have 48 steps, got {len(episode_df)}")

        self.cfg = cfg or load_config()
        self.thresholds = thresholds
        self.episode_df = episode_df.reset_index(drop=True)
        self.reward_weights = self._resolve_reward_weights(reward_mode, self.cfg)
        self.privileged = privileged
        mode = foresight_mode if foresight_mode is not None else self.cfg.forecast_mode
        if not privileged:
            mode = "none"
        self.foresight_mode = mode
        self.forecast_model = forecast_model
        self.forecast_rng = forecast_rng
        self.forecast_noise = forecast_noise
        self._prices = self.episode_df["price_per_kwh"].to_numpy(dtype=np.float64)

        self._step_idx = 0
        self._soc_pct = self.cfg.initial_soc_pct
        self._episode_day = str(episode_df["episode_day"].iloc[0])
        self._reset_totals()

    def _reset_totals(self) -> None:
        self.total_grid_cost = 0.0
        self.total_grid_import_kwh = 0.0
        self.total_solar_waste_kwh = 0.0
        self.total_export_kwh = 0.0
        self.total_export_revenue = 0.0
        self.total_grid_charge_kwh = 0.0
        self.total_grid_charge_cost = 0.0
        self.total_household_import_cost = 0.0
        self.total_throughput_kwh = 0.0
        self.total_cycling_cost = 0.0
        self.n_grid_charge_actions = 0
        self.n_export_actions = 0
        self.terminal_soc_adjustment = 0.0

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

    def export_price(self, wholesale_per_kwh: float) -> float:
        """Export settlement price for the current step (AUD/kWh)."""
        if self.cfg.tariff.export_pricing == "fixed":
            return self.cfg.tariff.feed_in_per_kwh
        # wholesale-exposed experimental tariff
        return float(wholesale_per_kwh)

    def reset(self) -> int:
        self._step_idx = 0
        self._soc_pct = self.cfg.initial_soc_pct
        self._reset_totals()
        return self._observe()

    def step(self, action: int) -> tuple[int, float, bool, dict[str, Any]]:
        if action not in VALID_ACTIONS:
            raise ValueError(f"Invalid action {action}")

        row = self.episode_df.iloc[self._step_idx]
        pv_kwh = float(row["pv_kwh"])
        load_kwh = float(row["load_kwh"])
        price = float(row["price_per_kwh"])
        retail_price = price + self.cfg.tariff.retail_margin_per_kwh
        export_price = self.export_price(price)

        physics = apply_battery_action(self._soc_pct, action, pv_kwh, load_kwh, self.cfg)
        reward = self._compute_reward(physics, retail_price, export_price)

        household_import = max(0.0, load_kwh - pv_kwh - physics["discharge_kwh"])
        grid_charge = physics["grid_charge_kwh"]
        export_revenue = physics["export_kwh"] * export_price
        grid_charge_cost = grid_charge * retail_price
        household_import_cost = household_import * retail_price
        step_net_cost = (
            household_import_cost
            + grid_charge_cost
            - export_revenue
            + physics["cycling_cost_aud"]
        )

        self.total_grid_cost += step_net_cost
        self.total_grid_import_kwh += physics["grid_import_kwh"]
        self.total_solar_waste_kwh += physics["solar_waste_kwh"]
        self.total_export_kwh += physics["export_kwh"]
        self.total_export_revenue += export_revenue
        self.total_grid_charge_kwh += grid_charge
        self.total_grid_charge_cost += grid_charge_cost
        self.total_household_import_cost += household_import_cost
        self.total_throughput_kwh += physics["throughput_kwh"]
        self.total_cycling_cost += physics["cycling_cost_aud"]
        if action == GRID_CHARGE and grid_charge > 0:
            self.n_grid_charge_actions += 1
        if action == EXPORT and physics["export_kwh"] > 0:
            self.n_export_actions += 1

        self._soc_pct = physics["soc_pct"]
        self._step_idx += 1
        done = self._step_idx >= len(self.episode_df)

        if done:
            terminal = self._terminal_soc_adjustment()
            self.terminal_soc_adjustment = terminal
            self.total_grid_cost += terminal
            reward -= terminal  # cost → negative reward

        info = {
            "episode_day": self._episode_day,
            "step": self._step_idx,
            "action": action,
            "action_name": ACTION_NAME_LOOKUP[action],
            "soc_pct": self._soc_pct,
            "pv_kwh": pv_kwh,
            "load_kwh": load_kwh,
            "price_per_kwh": price,
            "retail_price_per_kwh": retail_price,
            "export_price_per_kwh": export_price,
            "export_revenue_aud": export_revenue,
            "grid_charge_cost_aud": grid_charge_cost,
            "household_import_cost_aud": household_import_cost,
            "future_price_delta": self._current_future_delta(),
            "oracle_future_delta": future_price_delta(
                self._prices,
                min(self._step_idx, len(self._prices) - 1),
                self.thresholds.forecast_horizon_steps,
            ),
            "foresight_mode": self.foresight_mode,
            "privileged": self.privileged,
            "terminal_soc_adjustment_aud": self.terminal_soc_adjustment if done else 0.0,
            **physics,
        }

        next_state = self._observe()
        return next_state, reward, done, info

    def _terminal_soc_adjustment(self) -> float:
        """Charge the agent for ending below the initial SOC (credit if above).

        Prevents 'winning' by emptying the battery on the last steps.
        Valuation uses ``terminal_soc_value_per_kwh`` (AUD/kWh of SOC energy).
        """
        capacity = self.cfg.battery_capacity_kwh
        initial_kwh = self.cfg.initial_soc_pct / 100.0 * capacity
        final_kwh = self._soc_pct / 100.0 * capacity
        # Positive when final < initial → added cost
        return (initial_kwh - final_kwh) * self.cfg.tariff.terminal_soc_value_per_kwh

    def _current_future_delta(self) -> float:
        idx = min(self._step_idx, len(self._prices) - 1)
        if self.foresight_mode == "forecast":
            if self.forecast_model is None:
                raise RuntimeError("foresight_mode='forecast' requires forecast_model")
            return self.forecast_model.future_delta(
                self._prices,
                idx,
                rng=self.forecast_rng,
                add_noise=self.forecast_noise,
                use_oracle=False,
            )
        if self.foresight_mode == "oracle":
            return future_price_delta(
                self._prices, idx, self.thresholds.forecast_horizon_steps
            )
        return 0.0

    def _observe(self) -> int:
        idx = min(self._step_idx, len(self.episode_df) - 1)
        row = self.episode_df.iloc[idx]
        ts = row["timestamp"]
        hour = ts.hour + ts.minute / 60.0
        delta = self._current_future_delta() if self.privileged else None
        return state_index(
            self._soc_pct,
            float(row["pv_kwh"]),
            float(row["load_kwh"]),
            float(row["price_per_kwh"]),
            hour,
            self.thresholds,
            future_delta=delta,
            privileged=self.privileged,
        )

    def _compute_reward(
        self,
        physics: dict[str, float],
        retail_price_per_kwh: float,
        export_price_per_kwh: float,
    ) -> float:
        """Negative household net cost (AUD), net of export revenue and cycling."""
        w = self.reward_weights
        tar = self.cfg.tariff
        capacity = self.cfg.battery_capacity_kwh

        import_cost = physics["grid_import_kwh"] * retail_price_per_kwh
        solar_opp_cost = physics["solar_waste_kwh"] * tar.feed_in_per_kwh
        deg_cost = physics["battery_deg"] * capacity * tar.battery_deg_cost_per_kwh
        export_revenue = physics["export_kwh"] * export_price_per_kwh
        cycling_cost = physics["cycling_cost_aud"]

        reward = 0.0
        reward -= w.w_grid_cost * import_cost
        reward -= w.w_solar_waste * solar_opp_cost
        reward -= w.w_battery_deg * deg_cost
        reward -= w.w_cycling * cycling_cost
        reward += w.w_export_revenue * export_revenue
        if physics["invalid_action"]:
            reward -= w.w_invalid_action
        return float(reward)

    @property
    def net_arbitrage_profit(self) -> float:
        """Export revenue minus grid-charging cost (positive = profitable arbitrage trades)."""
        return self.total_export_revenue - self.total_grid_charge_cost
