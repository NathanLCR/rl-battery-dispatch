"""Cross-household generalisation: train on one customer, evaluate on others."""

from __future__ import annotations

import argparse
from datetime import datetime

import pandas as pd

from src.config import ensure_output_dirs, load_config
from src.data_loader import load_customer_dataset
from src.discretizer import fit_discretizer
from src.evaluate import evaluate_split, summarize
from src.rule_baseline import greedy_self_consumption_action, rule_tertile_action
from src.train import greedy_action_fn, make_agent, train_agent


def _make_policy(action_fn):
    from src.environment import MicrogridEnv

    def policy(env: MicrogridEnv) -> int:
        row = env.episode_df.iloc[env._step_idx]
        return action_fn(
            env._soc_pct,
            float(row["pv_kwh"]),
            float(row["load_kwh"]),
            env.thresholds,
        )

    return policy


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-customer transfer evaluation")
    parser.add_argument("--train-customer", type=int, default=1)
    parser.add_argument("--test-customers", type=int, nargs="+", default=[2, 3, 4, 5])
    parser.add_argument("--agent", default="q_learning", choices=["q_learning", "sarsa", "double_q_learning"])
    parser.add_argument("--episodes", type=int, default=None)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--reward-mode", default="battery_aware")
    args = parser.parse_args()

    cfg = load_config()
    episodes = args.episodes or (3000 if args.quick else cfg.n_episodes)
    ensure_output_dirs(cfg)

    train_df, split = load_customer_dataset(cfg, customer_id=args.train_customer)
    thresholds = fit_discretizer(train_df, cfg)

    print(f"Training {args.agent} on customer {args.train_customer} ({episodes} episodes)...")
    cfg.n_episodes = episodes
    agent = make_agent(args.agent, cfg)
    train_agent(
        agent, train_df, split.train, thresholds, cfg, args.reward_mode,
        val_days=split.val, eval_every=500,
    )

    rows = []
    for cid in args.test_customers:
        test_df, _ = load_customer_dataset(cfg, customer_id=cid)
        for policy_name, fn in [
            ("greedy_self_consumption", lambda s, p, l, t: greedy_self_consumption_action(
                s, p, l, t, min_soc_pct=cfg.min_soc_pct, max_soc_pct=cfg.max_soc_pct
            )),
            ("rule_tertile", rule_tertile_action),
            (args.agent, None),
        ]:
            if fn is None:
                action = greedy_action_fn(agent)
            else:
                action = _make_policy(fn)
            res = evaluate_split(test_df, thresholds, split, "test", action, cfg, args.reward_mode)
            stats = summarize(res)
            rows.append({
                "train_customer": args.train_customer,
                "test_customer": cid,
                "policy": policy_name,
                "total_grid_cost_aud": stats["total_grid_cost_aud"],
                "mean_self_sufficiency": stats.get("mean_self_sufficiency"),
                "pct_of_oracle_savings": stats.get("pct_of_oracle_savings"),
            })
            print(
                f"  customer {cid} | {policy_name:25s} | "
                f"cost {stats['total_grid_cost_aud']:.2f} AUD"
            )

    out = cfg.results_logs / f"cross_customer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
