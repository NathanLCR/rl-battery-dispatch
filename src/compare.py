"""Compare rule baseline vs trained RL agents on the test split."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.agents.q_learning import QLearningAgent
from src.agents.sarsa import SARSAAgent
from src.config import load_config
from src.data_loader import load_customer_dataset
from src.discretizer import BinThresholds, fit_discretizer
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--q-model", type=Path, default=None)
    parser.add_argument("--sarsa-model", type=Path, default=None)
    parser.add_argument("--reward-mode", default="battery_aware")
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

    table = pd.DataFrame(rows)
    print("\n=== TEST SPLIT COMPARISON ===")
    print(table.to_string(index=False))

    if len(rows) >= 2:
        rule_cost = rows[0]["total_grid_cost_aud"]
        for r in rows[1:]:
            saving = (rule_cost - r["total_grid_cost_aud"]) / rule_cost * 100
            print(f"\n{r['policy']} cost saving vs rule: {saving:+.1f}%")


if __name__ == "__main__":
    main()
