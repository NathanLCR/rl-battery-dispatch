"""Ablation: cost_only vs battery_aware reward modes."""

from __future__ import annotations

import argparse
from datetime import datetime

import pandas as pd

from src.config import ensure_output_dirs, load_config
from src.data_loader import load_customer_dataset
from src.discretizer import fit_discretizer
from src.evaluate import evaluate_split, summarize
from src.rule_baseline import greedy_self_consumption_action
from src.train import greedy_action_fn, make_agent, train_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Reward mode ablation")
    parser.add_argument("--agent", default="q_learning", choices=["q_learning", "sarsa", "double_q_learning"])
    parser.add_argument("--episodes", type=int, default=None)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    cfg = load_config()
    episodes = args.episodes or (3000 if args.quick else cfg.n_episodes)
    ensure_output_dirs(cfg)

    df, split = load_customer_dataset(cfg)
    thresholds = fit_discretizer(df, cfg)
    cfg.n_episodes = episodes

    from src.environment import MicrogridEnv

    def greedy_policy(env: MicrogridEnv) -> int:
        row = env.episode_df.iloc[env._step_idx]
        return greedy_self_consumption_action(
            env._soc_pct,
            float(row["pv_kwh"]),
            float(row["load_kwh"]),
            env.thresholds,
            min_soc_pct=cfg.min_soc_pct,
            max_soc_pct=cfg.max_soc_pct,
        )

    rows = []
    greedy_res = evaluate_split(df, thresholds, split, "test", greedy_policy, cfg, "battery_aware")
    greedy_cost = summarize(greedy_res)["total_grid_cost_aud"]
    rows.append({"reward_mode": "baseline", "policy": "greedy_self_consumption", "total_grid_cost_aud": greedy_cost})

    for mode in ("cost_only", "battery_aware"):
        print(f"\nTraining {args.agent} with reward_mode={mode}...")
        agent = make_agent(args.agent, cfg)
        train_agent(
            agent, df, split.train, thresholds, cfg, mode,
            val_days=split.val, eval_every=500,
        )
        res = evaluate_split(df, thresholds, split, "test", greedy_action_fn(agent), cfg, mode)
        stats = summarize(res)
        stats["reward_mode"] = mode
        stats["policy"] = args.agent
        rows.append(stats)
        saving = (greedy_cost - stats["total_grid_cost_aud"]) / greedy_cost * 100
        print(f"  test cost {stats['total_grid_cost_aud']:.2f} AUD ({saving:+.1f}% vs greedy)")

    out = cfg.results_logs / f"ablation_reward_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
