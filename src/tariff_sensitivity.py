"""Sweep retail margin, retrain agents, and compare test-set cost to the rule baseline."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.config import Config, ensure_output_dirs, load_config
from src.data_loader import load_customer_dataset
from src.discretizer import fit_discretizer
from src.environment import MicrogridEnv
from src.evaluate import evaluate_split, summarize
from src.rule_baseline import rule_action
from src.train import greedy_action_fn, make_agent, train_agent


def rule_policy_fn(thresholds):
    def policy(env: MicrogridEnv) -> int:
        row = env.episode_df.iloc[env._step_idx]
        return rule_action(
            env._soc_pct,
            float(row["pv_kwh"]),
            float(row["load_kwh"]),
            thresholds,
        )

    return policy


def with_margin(cfg: Config, margin: float) -> Config:
    """Return a shallow copy of ``cfg`` with an updated retail margin."""
    new_tariff = replace(cfg.tariff, retail_margin_per_kwh=margin)
    return replace(cfg, tariff=new_tariff)


def run_sweep(
    margins: list[float],
    agents: list[str],
    reward_mode: str,
    episodes: int,
) -> pd.DataFrame:
    base_cfg = load_config()
    ensure_output_dirs(base_cfg)

    df, day_split = load_customer_dataset(base_cfg)
    thresholds = fit_discretizer(df, base_cfg)

    rows: list[dict] = []

    for margin in margins:
        cfg_run = with_margin(base_cfg, margin)
        cfg_run.n_episodes = episodes

        rule_res = evaluate_split(
            df, thresholds, day_split, "test", rule_policy_fn(thresholds), cfg_run, reward_mode
        )
        rule_stats = summarize(rule_res)
        rows.append(
            {
                "retail_margin_per_kwh": margin,
                "feed_in_per_kwh": cfg_run.tariff.feed_in_per_kwh,
                "policy": "rule_baseline",
                "agent": None,
                "episodes": 0,
                "mean_reward": rule_stats["mean_reward"],
                "total_grid_cost_aud": rule_stats["total_grid_cost_aud"],
                "mean_grid_import_kwh": rule_stats["mean_grid_import_kwh"],
                "mean_solar_waste_kwh": rule_stats["mean_solar_waste_kwh"],
                "cost_saving_vs_rule_pct": None,
            }
        )
        rule_cost = rule_stats["total_grid_cost_aud"]

        for agent_name in agents:
            agent = make_agent(agent_name, cfg_run)
            train_agent(
                agent,
                df,
                day_split.train,
                thresholds,
                cfg_run,
                reward_mode,
                val_days=day_split.val,
                eval_every=500,
            )
            test_res = evaluate_split(
                df,
                thresholds,
                day_split,
                "test",
                greedy_action_fn(agent),
                cfg_run,
                reward_mode,
            )
            stats = summarize(test_res)
            saving = (rule_cost - stats["total_grid_cost_aud"]) / rule_cost * 100
            rows.append(
                {
                    "retail_margin_per_kwh": margin,
                    "feed_in_per_kwh": cfg_run.tariff.feed_in_per_kwh,
                    "policy": agent_name,
                    "agent": agent_name,
                    "episodes": episodes,
                    "mean_reward": stats["mean_reward"],
                    "total_grid_cost_aud": stats["total_grid_cost_aud"],
                    "mean_grid_import_kwh": stats["mean_grid_import_kwh"],
                    "mean_solar_waste_kwh": stats["mean_solar_waste_kwh"],
                    "cost_saving_vs_rule_pct": round(saving, 2),
                }
            )

    return pd.DataFrame(rows)


def save_results(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def print_summary(df: pd.DataFrame) -> None:
    print("\n=== TARIFF SENSITIVITY (test split) ===")
    cols = [
        "retail_margin_per_kwh",
        "policy",
        "total_grid_cost_aud",
        "cost_saving_vs_rule_pct",
        "mean_reward",
    ]
    print(df[cols].to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Retail margin sensitivity sweep")
    parser.add_argument(
        "--margins",
        type=float,
        nargs="+",
        default=[0.15, 0.22, 0.35],
        help="Retail margin values to sweep (AUD/kWh on top of wholesale)",
    )
    parser.add_argument(
        "--agents",
        nargs="+",
        choices=["q_learning", "sarsa"],
        default=["q_learning", "sarsa"],
    )
    parser.add_argument("--episodes", type=int, default=None)
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Use 3000 episodes per margin",
    )
    parser.add_argument("--reward-mode", default="battery_aware", choices=["battery_aware", "cost_only"])
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="CSV output path (default: results/logs/tariff_sensitivity_<timestamp>.csv)",
    )
    args = parser.parse_args()

    cfg = load_config()
    episodes = args.episodes or (3000 if args.quick else cfg.n_episodes)

    print(
        f"Sweeping retail margins {args.margins} | agents {args.agents} | "
        f"{episodes} episodes each | reward={args.reward_mode}"
    )

    results = run_sweep(args.margins, args.agents, args.reward_mode, episodes)
    print_summary(results)

    out = args.output or (
        cfg.results_logs / f"tariff_sensitivity_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )
    save_results(results, out)
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
