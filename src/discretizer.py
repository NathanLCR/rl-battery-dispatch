"""Discretize continuous observations into tabular RL state indices."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import Config, load_config
from src.constants import N_ACTIONS

N_SOC_BINS = 3
N_FEATURE_BINS = 3  # PV, load
N_PRICE_BINS = 5
N_TIME_BINS = 4
# Privileged foresight: future_signal = max(price next 4h) − current price
N_FUTURE_BINS = 3
FALL_OR_FLAT = 0
MODERATE_RISE = 1
STRONG_RISE = 2
FUTURE_SIGNAL_NAMES = {
    FALL_OR_FLAT: "FALL_OR_FLAT",
    MODERATE_RISE: "MODERATE_RISE",
    STRONG_RISE: "STRONG_RISE",
}

# Base (current-info) state: (soc, pv, load, price, time) → 3*3*3*5*4 = 540
N_STATES = N_SOC_BINS * N_FEATURE_BINS**2 * N_PRICE_BINS * N_TIME_BINS  # 540
# Privileged state adds future-signal bin → 540 * 3 = 1620
N_STATES_PRIVILEGED = N_STATES * N_FUTURE_BINS


def n_states_for(privileged: bool) -> int:
    return N_STATES_PRIVILEGED if privileged else N_STATES


@dataclass
class BinThresholds:
    """Quantile and SOC boundaries used to map continuous observations to bins."""

    pv_q33: float
    pv_q66: float
    load_q33: float
    load_q66: float
    price_q20: float
    price_q40: float
    price_q60: float
    price_q80: float
    soc_low_pct: float
    soc_high_pct: float
    # Future-signal edges from training deltas (max_{t+1:t+H} p − p_t)
    future_delta_q33: float = 0.0
    future_delta_q66: float = 0.0
    forecast_horizon_steps: int = 8

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "BinThresholds":
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        # Backward compatible with pre-forecast threshold files
        raw.setdefault("future_delta_q33", 0.0)
        raw.setdefault("future_delta_q66", 0.0)
        raw.setdefault("forecast_horizon_steps", 8)
        return cls(**raw)

    @property
    def price_edges(self) -> tuple[float, float, float, float]:
        return (self.price_q20, self.price_q40, self.price_q60, self.price_q80)


def _tertiles(series: pd.Series) -> tuple[float, float]:
    q33, q66 = series.quantile([0.33, 0.66])
    return float(q33), float(q66)


def _quintile_edges(series: pd.Series) -> tuple[float, float, float, float]:
    q20, q40, q60, q80 = series.quantile([0.20, 0.40, 0.60, 0.80])
    return float(q20), float(q40), float(q60), float(q80)


def future_price_delta(
    prices: np.ndarray | list[float],
    step_idx: int,
    horizon_steps: int = 8,
) -> float:
    """max(price in next ``horizon_steps``) − current price (0 if no future steps)."""
    current = float(prices[step_idx])
    end = min(len(prices), step_idx + 1 + horizon_steps)
    future = prices[step_idx + 1 : end]
    if len(future) == 0:
        return 0.0
    return float(np.max(future) - current)


def _collect_train_future_deltas(
    train_df: pd.DataFrame,
    horizon_steps: int,
) -> np.ndarray:
    deltas: list[float] = []
    for _, day_df in train_df.groupby("episode_day", sort=False):
        prices = day_df.sort_values("timestamp")["price_per_kwh"].to_numpy(dtype=np.float64)
        if len(prices) != 48:
            continue
        for t in range(len(prices)):
            deltas.append(future_price_delta(prices, t, horizon_steps))
    return np.asarray(deltas, dtype=np.float64)


def fit_discretizer(
    train_df: pd.DataFrame,
    cfg: Config | None = None,
    foresight_mode: str = "oracle",
    forecast_model=None,
) -> BinThresholds:
    """Compute bin edges from train-split rows only (no leakage).

    ``foresight_mode``:
      - ``oracle`` — true future price deltas (privileged oracle experiments)
      - ``forecast`` — realistic forecast deltas (deployable privileged signal)
    """
    cfg = cfg or load_config()
    train_rows = train_df[train_df["split"] == "train"]
    pv_q33, pv_q66 = _tertiles(train_rows["pv_kwh"])
    load_q33, load_q66 = _tertiles(train_rows["load_kwh"])
    price_q20, price_q40, price_q60, price_q80 = _quintile_edges(train_rows["price_per_kwh"])

    horizon = cfg.forecast_horizon_steps
    if foresight_mode == "forecast" and forecast_model is not None:
        from src.price_forecast import collect_forecast_deltas

        deltas = collect_forecast_deltas(train_rows, forecast_model, use_oracle=False)
    else:
        deltas = _collect_train_future_deltas(train_rows, horizon)
    if len(deltas) == 0:
        future_q33, future_q66 = 0.0, 0.0
    else:
        future_q33, future_q66 = _tertiles(pd.Series(deltas))

    return BinThresholds(
        pv_q33=pv_q33,
        pv_q66=pv_q66,
        load_q33=load_q33,
        load_q66=load_q66,
        price_q20=price_q20,
        price_q40=price_q40,
        price_q60=price_q60,
        price_q80=price_q80,
        soc_low_pct=cfg.soc_low_pct,
        soc_high_pct=cfg.soc_high_pct,
        future_delta_q33=future_q33,
        future_delta_q66=future_q66,
        forecast_horizon_steps=horizon,
    )


def _feature_bin(value: float, q33: float, q66: float) -> int:
    """Map a continuous feature to a low / mid / high tertile bin."""
    if value <= q33:
        return 0
    if value <= q66:
        return 1
    return 2


def _quantile_bin(value: float, edges: tuple[float, ...]) -> int:
    """Map a value to a bin index given sorted interior edges."""
    idx = 0
    for edge in edges:
        if value <= edge:
            return idx
        idx += 1
    return idx


def price_bin(price_per_kwh: float, thresholds: BinThresholds) -> int:
    """Map wholesale price to one of 5 quintile bins: 0=cheapest ... 4=priciest."""
    return _quantile_bin(price_per_kwh, thresholds.price_edges)


def future_signal_bin(delta: float, thresholds: BinThresholds) -> int:
    """Discretise future price direction into FALL_OR_FLAT / MODERATE_RISE / STRONG_RISE."""
    return _feature_bin(delta, thresholds.future_delta_q33, thresholds.future_delta_q66)


def soc_bin(soc_pct: float, thresholds: BinThresholds) -> int:
    """Map battery SOC to empty / mid / full bin using configured thresholds."""
    if soc_pct < thresholds.soc_low_pct:
        return 0
    if soc_pct <= thresholds.soc_high_pct:
        return 1
    return 2


def time_bin(hour: float) -> int:
    """0=Night, 1=Morning, 2=Afternoon, 3=Evening."""
    if hour < 6:
        return 0
    if hour < 12:
        return 1
    if hour < 18:
        return 2
    return 3


def state_index(
    soc_pct: float,
    pv_kwh: float,
    load_kwh: float,
    price_per_kwh: float,
    hour: float,
    thresholds: BinThresholds,
    future_delta: float | None = None,
    privileged: bool = False,
) -> int:
    """Encode observations into a tabular state index.

    Current-info agents use 540 states (no future signal).
    Privileged agents append the 3-bin future-signal → 1620 states.
    """
    s = soc_bin(soc_pct, thresholds)
    p = _feature_bin(pv_kwh, thresholds.pv_q33, thresholds.pv_q66)
    l = _feature_bin(load_kwh, thresholds.load_q33, thresholds.load_q66)
    r = price_bin(price_per_kwh, thresholds)
    t = time_bin(hour)
    base = int(
        np.ravel_multi_index(
            (s, p, l, r, t),
            (N_SOC_BINS, N_FEATURE_BINS, N_FEATURE_BINS, N_PRICE_BINS, N_TIME_BINS),
        )
    )
    if not privileged:
        return base
    delta = 0.0 if future_delta is None else float(future_delta)
    f = future_signal_bin(delta, thresholds)
    return base * N_FUTURE_BINS + f


def decode_state_index(index: int, privileged: bool = False) -> tuple[int, ...]:
    """Reverse :func:`state_index` into individual bin indices."""
    if privileged:
        base, f = divmod(index, N_FUTURE_BINS)
        bins = np.unravel_index(
            base,
            (N_SOC_BINS, N_FEATURE_BINS, N_FEATURE_BINS, N_PRICE_BINS, N_TIME_BINS),
        )
        return tuple(int(x) for x in bins) + (int(f),)
    return tuple(
        int(x)
        for x in np.unravel_index(
            index,
            (N_SOC_BINS, N_FEATURE_BINS, N_FEATURE_BINS, N_PRICE_BINS, N_TIME_BINS),
        )
    )


if __name__ == "__main__":
    from src.config import ensure_output_dirs
    from src.data_loader import get_episode, load_customer_dataset

    cfg = load_config()
    ensure_output_dirs(cfg)
    df, split = load_customer_dataset(cfg)
    thresholds = fit_discretizer(df, cfg)
    out_path = cfg.artifacts_dir / "bin_thresholds.json"
    thresholds.save(out_path)
    print(f"Saved thresholds -> {out_path}")
    print(json.dumps(asdict(thresholds), indent=2))

    day = split.train[0]
    ep = get_episode(df, day)
    row = ep.iloc[0]
    hour = row["timestamp"].hour + row["timestamp"].minute / 60.0
    prices = ep["price_per_kwh"].to_numpy(dtype=np.float64)
    delta = future_price_delta(prices, 0, thresholds.forecast_horizon_steps)
    idx = state_index(50.0, row["pv_kwh"], row["load_kwh"], row["price_per_kwh"], hour, thresholds)
    idx_p = state_index(
        50.0, row["pv_kwh"], row["load_kwh"], row["price_per_kwh"], hour, thresholds,
        future_delta=delta, privileged=True,
    )
    print(f"\nDay {day} step 0 -> state {idx} / privileged {idx_p}")
    print(f"Future delta={delta:.5f} bin={future_signal_bin(delta, thresholds)}")
    print(f"Q-table shapes: ({N_STATES}, {N_ACTIONS}) or ({N_STATES_PRIVILEGED}, {N_ACTIONS})")
