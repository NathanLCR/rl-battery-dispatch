"""Load project configuration from config.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class RewardWeights:
    """Linear reward shaping coefficients (all penalties are subtracted)."""

    w_grid_cost: float
    w_solar_waste: float
    w_battery_deg: float
    w_unmet_demand: float
    w_invalid_action: float


@dataclass
class Config:
    """Typed view of ``config.yaml`` — battery, training, and I/O paths."""

    repo_root: Path
    merged_csv: Path
    day_split_json: Path
    primary_customer_id: int
    steps_per_episode: int
    battery_capacity_kwh: float
    initial_soc_pct: float
    max_charge_kw: float
    max_discharge_kw: float
    soc_low_pct: float
    soc_high_pct: float
    min_soc_pct: float
    max_soc_pct: float
    n_bins: int
    n_time_periods: int
    alpha: float
    gamma: float
    epsilon: float
    epsilon_min: float
    epsilon_decay: float
    n_episodes: int
    random_seed: int
    reward_cost_only: RewardWeights
    reward_battery_aware: RewardWeights
    artifacts_dir: Path
    results_logs: Path
    results_models: Path
    results_plots: Path


def load_config(path: Path | None = None) -> Config:
    """Parse ``config.yaml`` into a :class:`Config` instance."""
    cfg_path = path or (REPO_ROOT / "config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    def rw(block: dict[str, float]) -> RewardWeights:
        return RewardWeights(
            w_grid_cost=block["w_grid_cost"],
            w_solar_waste=block["w_solar_waste"],
            w_battery_deg=block["w_battery_deg"],
            w_unmet_demand=block["w_unmet_demand"],
            w_invalid_action=block["w_invalid_action"],
        )

    root = cfg_path.parent
    paths = raw["paths"]
    data = raw["data"]
    bat = raw["battery"]
    disc = raw["discretizer"]
    train = raw["training"]

    return Config(
        repo_root=root,
        merged_csv=root / data["merged_csv"],
        day_split_json=root / data["day_split_json"],
        primary_customer_id=data["primary_customer_id"],
        steps_per_episode=data["steps_per_episode"],
        battery_capacity_kwh=bat["capacity_kwh"],
        initial_soc_pct=bat["initial_soc_pct"],
        max_charge_kw=bat["max_charge_kw"],
        max_discharge_kw=bat["max_discharge_kw"],
        soc_low_pct=bat["soc_low_pct"],
        soc_high_pct=bat["soc_high_pct"],
        min_soc_pct=bat["min_soc_pct"],
        max_soc_pct=bat["max_soc_pct"],
        n_bins=disc["n_bins"],
        n_time_periods=disc["n_time_periods"],
        alpha=train["alpha"],
        gamma=train["gamma"],
        epsilon=train["epsilon"],
        epsilon_min=train["epsilon_min"],
        epsilon_decay=train["epsilon_decay"],
        n_episodes=train["n_episodes"],
        random_seed=train["random_seed"],
        reward_cost_only=rw(raw["reward"]["cost_only"]),
        reward_battery_aware=rw(raw["reward"]["battery_aware"]),
        artifacts_dir=root / paths["artifacts"],
        results_logs=root / paths["results_logs"],
        results_models=root / paths["results_models"],
        results_plots=root / paths["results_plots"],
    )


def ensure_output_dirs(cfg: Config) -> None:
    """Create artifact and results directories if they do not exist."""
    for d in (
        cfg.artifacts_dir,
        cfg.results_logs,
        cfg.results_models,
        cfg.results_plots,
    ):
        d.mkdir(parents=True, exist_ok=True)
