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
# CA2: price gets finer resolution (quintiles, not tertiles) than PV/load.
# The 3-action solar-only environment didn't need to distinguish "cheap" from
# "very cheap" — arbitrage timing does. See README "CA2 extension" section.
N_PRICE_BINS = 5
N_TIME_BINS = 4
# State = (soc, pv, load, price, time_of_day) -> 3 * 3 * 3 * 5 * 4 = 540 discrete states
# Action space (5, incl. CA2 grid-charge/export) does not affect state count.
N_STATES = N_SOC_BINS * N_FEATURE_BINS**2 * N_PRICE_BINS * N_TIME_BINS  # 540


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

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "BinThresholds":
        with open(path, encoding="utf-8") as f:
            return cls(**json.load(f))

    @property
    def price_edges(self) -> tuple[float, float, float, float]:
        return (self.price_q20, self.price_q40, self.price_q60, self.price_q80)


def _tertiles(series: pd.Series) -> tuple[float, float]:
    q33, q66 = series.quantile([0.33, 0.66])
    return float(q33), float(q66)


def _quintile_edges(series: pd.Series) -> tuple[float, float, float, float]:
    q20, q40, q60, q80 = series.quantile([0.20, 0.40, 0.60, 0.80])
    return float(q20), float(q40), float(q60), float(q80)


def fit_discretizer(train_df: pd.DataFrame, cfg: Config | None = None) -> BinThresholds:
    """Compute bin edges from train-split rows only (no leakage)."""
    cfg = cfg or load_config()
    train_rows = train_df[train_df["split"] == "train"]
    pv_q33, pv_q66 = _tertiles(train_rows["pv_kwh"])
    load_q33, load_q66 = _tertiles(train_rows["load_kwh"])
    price_q20, price_q40, price_q60, price_q80 = _quintile_edges(train_rows["price_per_kwh"])
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
    )


def _feature_bin(value: float, q33: float, q66: float) -> int:
    """Map a continuous feature to a low / mid / high tertile bin."""
    if value <= q33:
        return 0
    if value <= q66:
        return 1
    return 2


def _quantile_bin(value: float, edges: tuple[float, ...]) -> int:
    """Map a value to a bin index given ``len(edges)`` sorted interior edges
    (i.e. ``len(edges) + 1`` bins). Generalises :func:`_feature_bin` to price's
    finer quintile resolution."""
    idx = 0
    for edge in edges:
        if value <= edge:
            return idx
        idx += 1
    return idx


def price_bin(price_per_kwh: float, thresholds: BinThresholds) -> int:
    """Map wholesale price to one of 5 quintile bins: 0=cheapest ... 4=priciest."""
    return _quantile_bin(price_per_kwh, thresholds.price_edges)


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
) -> int:
    """Encode (soc, pv, load, price, time) into a single tabular state index."""
    s = soc_bin(soc_pct, thresholds)
    p = _feature_bin(pv_kwh, thresholds.pv_q33, thresholds.pv_q66)
    l = _feature_bin(load_kwh, thresholds.load_q33, thresholds.load_q66)
    r = price_bin(price_per_kwh, thresholds)
    t = time_bin(hour)
    return int(
        np.ravel_multi_index((s, p, l, r, t), (N_SOC_BINS, N_FEATURE_BINS, N_FEATURE_BINS, N_PRICE_BINS, N_TIME_BINS))
    )


def decode_state_index(index: int) -> tuple[int, int, int, int, int]:
    """Reverse :func:`state_index` into individual bin indices."""
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
    idx = state_index(50.0, row["pv_kwh"], row["load_kwh"], row["price_per_kwh"], hour, thresholds)
    print(f"\nDay {day} step 0 -> state index {idx} (of {N_STATES - 1})")
    print(f"Decoded bins (soc,pv,load,price,time): {decode_state_index(idx)}")
    print(f"Q-table shape: ({N_STATES}, {N_ACTIONS}) = {N_STATES * N_ACTIONS} values")
