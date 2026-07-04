"""Load merged Ausgrid+AEMO data and build daily RL episodes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

from src.config import Config, load_config

SplitName = Literal["train", "val", "test"]


@dataclass
class DaySplit:
    """Day-level train/validation/test partition stored in ``day_split.json``."""

    seed: int
    train: list[str]
    val: list[str]
    test: list[str]

    def label(self, day: str) -> SplitName | None:
        if day in self.train:
            return "train"
        if day in self.val:
            return "val"
        if day in self.test:
            return "test"
        return None

    def days(self, split: SplitName) -> list[str]:
        return getattr(self, split)


def load_day_split(path: Path) -> DaySplit:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return DaySplit(
        seed=raw["seed"],
        train=list(raw["train"]),
        val=list(raw["val"]),
        test=list(raw["test"]),
    )


def _parse_timestamps(series: pd.Series) -> pd.Series:
    """Normalise timestamps to Australia/Sydney local time."""
    ts = pd.to_datetime(series, utc=True)
    return ts.dt.tz_convert("Australia/Sydney")


def _episode_day(ts: pd.Series) -> pd.Series:
    """
    Map each 30-min interval to its operating calendar day.

    A one-minute offset aligns midnight-boundary intervals with the
    preceding trading day, consistent with the day-split logic in
    ``data_split.ipynb``.
    """
    return (ts - pd.Timedelta(minutes=1)).dt.date.astype(str)


def load_merged_csv(path: Path) -> pd.DataFrame:
    """Load the merged Ausgrid + AEMO dataset and derive episode-day labels."""
    df = pd.read_csv(path)
    df["timestamp"] = _parse_timestamps(df["timestamp"])
    df["episode_day"] = _episode_day(df["timestamp"])
    return df


def get_customer_episodes(
    df: pd.DataFrame,
    customer_id: int,
    steps_per_episode: int = 48,
    split: DaySplit | None = None,
) -> pd.DataFrame:
    """Filter one customer and keep only complete 48-step days."""
    out = df[df["customer_id"] == customer_id].copy()
    counts = out.groupby("episode_day").size()
    valid_days = counts[counts == steps_per_episode].index
    out = out[out["episode_day"].isin(valid_days)].copy()

    if split is not None:
        labeled = split.train + split.val + split.test
        out = out[out["episode_day"].isin(labeled)].copy()
        out["split"] = out["episode_day"].map(split.label)
        out = out[out["split"].notna()].copy()

    out = out.sort_values(["episode_day", "timestamp"]).reset_index(drop=True)
    return out


def get_episode(df: pd.DataFrame, episode_day: str) -> pd.DataFrame:
    """Return one complete daily episode (48 x 30-min steps) for ``episode_day``."""
    ep = df[df["episode_day"] == episode_day].copy()
    if len(ep) != 48:
        raise ValueError(f"Episode {episode_day} has {len(ep)} steps, expected 48")
    return ep.reset_index(drop=True)


def load_customer_dataset(cfg: Config | None = None) -> tuple[pd.DataFrame, DaySplit]:
    """Load merged data for the configured customer with split labels attached."""
    cfg = cfg or load_config()
    split = load_day_split(cfg.day_split_json)
    merged = load_merged_csv(cfg.merged_csv)
    customer_df = get_customer_episodes(
        merged,
        customer_id=cfg.primary_customer_id,
        steps_per_episode=cfg.steps_per_episode,
        split=split,
    )
    return customer_df, split


def split_summary(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("split")["episode_day"]
        .nunique()
        .rename("n_days")
        .reset_index()
    )


if __name__ == "__main__":
    cfg = load_config()
    df, day_split = load_customer_dataset(cfg)
    print(f"Customer {cfg.primary_customer_id}: {len(df):,} rows")
    print(f"Unique days: {df['episode_day'].nunique()}")
    print("\nSplit summary:")
    print(split_summary(df).to_string(index=False))
    sample_day = day_split.train[0]
    ep = get_episode(df, sample_day)
    print(f"\nSample train day {sample_day}: {len(ep)} steps")
    print(ep[["timestamp", "pv_kwh", "load_kwh", "price_per_kwh", "split"]].head(3))
