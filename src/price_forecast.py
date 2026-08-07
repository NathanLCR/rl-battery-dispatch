"""Realistic short-horizon wholesale price forecasts for privileged RL.

Uses a climatology + persistence hybrid fitted on the training split only
(no test leakage). This is a deployable-style signal — not perfect foresight.

Forecast at horizon step k (k = 1..H):
    f_{t+k} = (1 - α^k) * clim[tod(t+k)] + α^k * p_t
optional Gaussian noise ~ N(0, σ) during training for robustness.

``future_signal = max(f_{t+1:t+H}) - p_t`` mirrors the oracle privileged feature.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.discretizer import future_price_delta


def _tod_index(timestamp) -> int:
    """Half-hour-of-day index 0..47."""
    return int(timestamp.hour * 2 + timestamp.minute // 30)


@dataclass
class PriceForecastModel:
    """Train-only climatology persistence forecast."""

    climatology: list[float]  # length 48, mean wholesale AUD/kWh by half-hour
    residual_std: float
    persistence_alpha: float = 0.55
    horizon_steps: int = 8
    noise_scale: float = 1.0

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "PriceForecastModel":
        with open(path, encoding="utf-8") as f:
            return cls(**json.load(f))

    def forecast_prices(
        self,
        current_price: float,
        step_idx: int,
        horizon_steps: int | None = None,
        rng: np.random.Generator | None = None,
        add_noise: bool = False,
    ) -> np.ndarray:
        """Return length-H forecast of future wholesale prices (not including now)."""
        h = self.horizon_steps if horizon_steps is None else horizon_steps
        clim = np.asarray(self.climatology, dtype=np.float64)
        out = np.zeros(h, dtype=np.float64)
        alpha = float(self.persistence_alpha)
        for k in range(1, h + 1):
            tod = (step_idx + k) % 48
            w = alpha**k
            out[k - 1] = (1.0 - w) * clim[tod] + w * current_price
        if add_noise and rng is not None and self.residual_std > 0:
            sigma = self.residual_std * self.noise_scale
            out = out + rng.normal(0.0, sigma, size=h)
        return out

    def future_delta(
        self,
        prices: np.ndarray | list[float],
        step_idx: int,
        rng: np.random.Generator | None = None,
        add_noise: bool = False,
        use_oracle: bool = False,
    ) -> float:
        """Privileged feature: max(forecast next H) − current (or true max if oracle)."""
        if use_oracle:
            return future_price_delta(prices, step_idx, self.horizon_steps)
        current = float(prices[step_idx])
        end = min(len(prices), step_idx + 1 + self.horizon_steps)
        remaining = end - (step_idx + 1)
        if remaining <= 0:
            return 0.0
        forecast = self.forecast_prices(
            current, step_idx, horizon_steps=remaining, rng=rng, add_noise=add_noise
        )
        return float(np.max(forecast) - current)

    def forecast_series_for_episode(
        self,
        episode_df: pd.DataFrame,
        step_idx: int,
        rng: np.random.Generator | None = None,
        add_noise: bool = False,
    ) -> pd.DataFrame:
        """Table of upcoming true vs forecast prices for the Play-vs-Agent UI."""
        prices = episode_df["price_per_kwh"].to_numpy(dtype=np.float64)
        current = float(prices[step_idx])
        rows = []
        forecast = self.forecast_prices(current, step_idx, rng=rng, add_noise=add_noise)
        for k, f_price in enumerate(forecast, start=1):
            t = step_idx + k
            if t >= len(episode_df):
                break
            ts = episode_df.iloc[t]["timestamp"]
            rows.append(
                {
                    "step": t,
                    "time_label": ts.strftime("%H:%M"),
                    "forecast_price": float(f_price),
                    "true_price": float(prices[t]),
                    "abs_error": abs(float(prices[t]) - float(f_price)),
                }
            )
        return pd.DataFrame(rows)


def fit_price_forecast(
    train_df: pd.DataFrame,
    horizon_steps: int = 8,
    persistence_alpha: float = 0.55,
    noise_scale: float = 1.0,
) -> PriceForecastModel:
    """Fit climatology and residual scale from train-split rows only."""
    train_rows = train_df[train_df["split"] == "train"].copy()
    if "timestamp" not in train_rows.columns:
        raise ValueError("train_df must include timestamp")
    train_rows = train_rows.sort_values("timestamp")
    train_rows["_tod"] = train_rows["timestamp"].map(_tod_index)
    clim = (
        train_rows.groupby("_tod")["price_per_kwh"]
        .mean()
        .reindex(range(48))
        .interpolate()
        .bfill()
        .ffill()
    )
    # One-step residual vs climatology (proxy for forecast error scale)
    residuals = train_rows["price_per_kwh"].to_numpy() - clim.loc[train_rows["_tod"]].to_numpy()
    residual_std = float(np.std(residuals)) if len(residuals) else 0.01
    return PriceForecastModel(
        climatology=[float(x) for x in clim.tolist()],
        residual_std=max(residual_std, 1e-6),
        persistence_alpha=persistence_alpha,
        horizon_steps=horizon_steps,
        noise_scale=noise_scale,
    )


def collect_forecast_deltas(
    train_df: pd.DataFrame,
    model: PriceForecastModel,
    use_oracle: bool = False,
) -> np.ndarray:
    """Collect per-step future-signal values on train days for discretiser edges."""
    deltas: list[float] = []
    for _, day_df in train_df[train_df["split"] == "train"].groupby("episode_day", sort=False):
        day_df = day_df.sort_values("timestamp")
        prices = day_df["price_per_kwh"].to_numpy(dtype=np.float64)
        if len(prices) != 48:
            continue
        for t in range(len(prices)):
            deltas.append(model.future_delta(prices, t, use_oracle=use_oracle, add_noise=False))
    return np.asarray(deltas, dtype=np.float64)
