"""Compare baselines and trained RL agents on the test split."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.config import load_config
from src.data_loader import get_episode, load_customer_dataset
from src.discretizer import fit_discretizer
from src.environment import MicrogridEnv
from src.evaluate import evaluate_split, oracle_bounds_summary, summarize
from src.oracle import no_battery_import_cost, oracle_perfect_foresight_import
from src.rule_baseline import (
    greedy_self_consumption_action,
    no_battery_action,
    rule_tertile_action,
)
from src.train import greedy_action_fn, load_trained_agent


def build_comparison_table(
    rows: list[dict],
    reference_policy: str = "greedy_self_consumption",
) -> pd.DataFrame:
    """Add cost-saving vs a reference baseline as a percentage column."""
    table = pd.DataFrame(rows)
    if not rows:
        return table

    ref_rows = [r for r in rows if r["policy"] == reference_policy]
    ref_cost = ref_rows[0]["total_grid_cost_aud"] if ref_rows else rows[0]["total_grid_cost_aud"]

    savings = []
    for r in rows:
        if r["policy"] in (reference_policy, "oracle_perfect_foresight", "no_battery"):
            savings.append(None)
        else:
            saving = (ref_cost - r["total_grid_cost_aud"]) / ref_cost * 100
            savings.append(round(saving, 2))
    table["cost_saving_vs_greedy_pct"] = savings
    return table


def _policy_from_action_fn(action_fn):
    def policy(env: MicrogridEnv) -> int:
        row = env.episode_df.iloc[env._step_idx]
        return action_fn(
            env._soc_pct,
            float(row["pv_kwh"]),
            float(row["load_kwh"]),
            env.thresholds,
        )

    return policy


def default_output_path(cfg) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return cfg.results_logs / f"comparison_test_{stamp}.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare baselines vs RL on test split")
    parser.add_argument("--q-model", type=Path, default=None)
    parser.add_argument("--sarsa-model", type=Path, default=None)
    parser.add_argument("--double-q-model", type=Path, default=None)
    parser.add_argument("--reward-mode", default="battery_aware", choices=["battery_aware", "cost_only"])
    parser.add_argument("--output", "-o", type=Path, default=None)
    args = parser.parse_args()

    cfg = load_config()
    df, split = load_customer_dataset(cfg)
    thresholds = fit_discretizer(df, cfg)

    baseline_fns = [
        ("no_battery", lambda s, p, l, t: no_battery_action(s, p, l, t)),
        ("rule_tertile", rule_tertile_action),
        ("greedy_self_consumption", lambda s, p, l, t: greedy_self_consumption_action(
            s, p, l, t, min_soc_pct=cfg.min_soc_pct, max_soc_pct=cfg.max_soc_pct
        )),
    ]

    rows = []
    per_day_oracle = []
    for day in split.test:
        ep = get_episode(df, day)
        per_day_oracle.append({
            "oracle_cost_aud": oracle_perfect_foresight_import(ep, cfg),
            "no_battery_cost_aud": no_battery_import_cost(ep, cfg),
        })

    bounds = oracle_bounds_summary(pd.DataFrame(per_day_oracle))
    rows.append({
        "policy": "no_battery",
        **bounds,
        "total_grid_cost_aud": bounds["total_no_battery_cost_aud"],
        "n_days": len(split.test),
        "mean_self_consumption_rate": None,
        "mean_self_sufficiency": None,
        "mean_evening_peak_import_kwh": None,
        "pct_of_oracle_savings": 0.0,
    })
    rows.append({
        "policy": "oracle_perfect_foresight",
        **bounds,
        "total_grid_cost_aud": bounds["total_oracle_cost_aud"],
        "n_days": len(split.test),
        "mean_self_consumption_rate": None,
        "mean_self_sufficiency": None,
        "mean_evening_peak_import_kwh": None,
        "pct_of_oracle_savings": 100.0,
    })

    for name, fn in baseline_fns:
        if name == "no_battery":
            continue
        policy = _policy_from_action_fn(fn)
        res = evaluate_split(df, thresholds, split, "test", policy, cfg, args.reward_mode)
        stats = summarize(res)
        stats["policy"] = name
        rows.append(stats)

    model_specs = [
        ("q_learning", args.q_model),
        ("sarsa", args.sarsa_model),
        ("double_q_learning", args.double_q_model),
    ]
    for agent_name, model_path in model_specs:
        if model_path is None:
            continue
        agent = load_trained_agent(agent_name, model_path, cfg)
        res = evaluate_split(
            df, thresholds, split, "test", greedy_action_fn(agent), cfg, args.reward_mode
        )
        stats = summarize(res)
        stats["policy"] = agent_name
        rows.append(stats)

    table = build_comparison_table(rows)
    print("\n=== TEST SPLIT COMPARISON ===")
    display_cols = [
        c for c in [
            "policy", "total_grid_cost_aud", "cost_saving_vs_greedy_pct",
            "pct_of_oracle_savings", "mean_self_consumption_rate",
            "mean_self_sufficiency", "mean_evening_peak_import_kwh",
        ] if c in table.columns
    ]
    print(table[display_cols].to_string(index=False))

    greedy_rows = [r for r in rows if r["policy"] == "greedy_self_consumption"]
    if greedy_rows:
        ref = greedy_rows[0]["total_grid_cost_aud"]
        for r in rows:
            if r["policy"] in ("no_battery", "oracle_perfect_foresight", "greedy_self_consumption"):
                continue
            saving = (ref - r["total_grid_cost_aud"]) / ref * 100
            print(f"\n{r['policy']} vs greedy self-consumption: {saving:+.1f}%")

    out_path = args.output if args.output is not None else default_output_path(cfg)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out_path, index=False)
    print(f"\nSaved comparison -> {out_path}")


if __name__ == "__main__":
    main()
