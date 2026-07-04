"""Compare rule baseline vs trained RL agents on the test split."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.config import load_config
from src.data_loader import load_customer_dataset
from src.discretizer import fit_discretizer
from src.environment import MicrogridEnv
from src.evaluate import evaluate_split, summarize
from src.rule_baseline import rule_action
from src.train import greedy_action_fn, make_agent


def load_agent(agent_name: str, model_path: Path, cfg):
    """Restore a trained Q-table and disable exploration for evaluation."""
    agent = make_agent(agent_name, cfg)
    agent.q = agent.q.load(model_path)
    agent.epsilon = 0.0
    return agent


def build_comparison_table(
    rows: list[dict],
) -> pd.DataFrame:
    """Add cost-saving vs rule baseline as a percentage column."""
    table = pd.DataFrame(rows)
    if not rows:
        return table

    rule_cost = rows[0]["total_grid_cost_aud"]
    savings = []
    for r in rows:
        if r["policy"] == "rule_baseline":
            savings.append(None)
        else:
            saving = (rule_cost - r["total_grid_cost_aud"]) / rule_cost * 100
            savings.append(round(saving, 2))
    table["cost_saving_vs_rule_pct"] = savings
    return table


def default_output_path(cfg) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return cfg.results_logs / f"comparison_test_{stamp}.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare rule baseline vs RL on test split")
    parser.add_argument("--q-model", type=Path, default=None, help="Path to Q-Learning .npy model")
    parser.add_argument("--sarsa-model", type=Path, default=None, help="Path to SARSA .npy model")
    parser.add_argument("--reward-mode", default="battery_aware", choices=["battery_aware", "cost_only"])
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Save comparison table to CSV (default: results/logs/comparison_test_<timestamp>.csv)",
    )
    args = parser.parse_args()

    cfg = load_config()
    df, split = load_customer_dataset(cfg)
    thresholds = fit_discretizer(df, cfg)

    def rule_policy(env: MicrogridEnv) -> int:
        row = env.episode_df.iloc[env._step_idx]
        return rule_action(
            env._soc_pct,
            float(row["pv_kwh"]),
            float(row["load_kwh"]),
            env.thresholds,
        )

    rows = []
    for name, policy in [("rule_baseline", rule_policy)]:
        res = evaluate_split(df, thresholds, split, "test", policy, cfg, args.reward_mode)
        stats = summarize(res)
        stats["policy"] = name
        rows.append(stats)

    if args.q_model:
        agent = load_agent("q_learning", args.q_model, cfg)
        res = evaluate_split(df, thresholds, split, "test", greedy_action_fn(agent), cfg, args.reward_mode)
        stats = summarize(res)
        stats["policy"] = "q_learning"
        rows.append(stats)

    if args.sarsa_model:
        agent = load_agent("sarsa", args.sarsa_model, cfg)
        res = evaluate_split(df, thresholds, split, "test", greedy_action_fn(agent), cfg, args.reward_mode)
        stats = summarize(res)
        stats["policy"] = "sarsa"
        rows.append(stats)

    table = build_comparison_table(rows)
    print("\n=== TEST SPLIT COMPARISON ===")
    print(table.to_string(index=False))

    if len(rows) >= 2:
        rule_cost = rows[0]["total_grid_cost_aud"]
        for r in rows[1:]:
            saving = (rule_cost - r["total_grid_cost_aud"]) / rule_cost * 100
            print(f"\n{r['policy']} cost saving vs rule: {saving:+.1f}%")

    out_path = args.output if args.output is not None else default_output_path(cfg)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out_path, index=False)
    print(f"\nSaved comparison -> {out_path}")


if __name__ == "__main__":
    main()
