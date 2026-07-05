"""Multi-seed training with aggregated test metrics and significance tests."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import ensure_output_dirs, load_config
from src.data_loader import load_customer_dataset
from src.discretizer import fit_discretizer
from src.evaluate import evaluate_split, summarize
from src.train import greedy_action_fn, make_agent, train_agent


def _paired_ttest(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Paired t-test; returns (t_statistic, p_value). Uses scipy if available."""
    try:
        from scipy import stats

        result = stats.ttest_rel(a, b, nan_policy="omit")
        return float(result.statistic), float(result.pvalue)
    except ImportError:
        d = a - b
        d = d[~np.isnan(d)]
        if len(d) < 2 or d.std(ddof=1) == 0:
            return 0.0, 1.0
        t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
        return float(t), float("nan")


def run_one_seed(
    agent_name: str,
    seed: int,
    df: pd.DataFrame,
    split,
    thresholds,
    cfg,
    reward_mode: str,
    episodes: int,
) -> dict:
    cfg_run = cfg
    cfg_run.n_episodes = episodes
    cfg_run.random_seed = seed

    agent = make_agent(agent_name, cfg_run, seed=seed)
    train_agent(
        agent, df, split.train, thresholds, cfg_run, reward_mode,
        val_days=split.val, eval_every=max(500, episodes // 20),
    )
    test_res = evaluate_split(
        df, thresholds, split, "test", greedy_action_fn(agent), cfg_run, reward_mode
    )
    stats = summarize(test_res)
    stats["seed"] = seed
    stats["agent"] = agent_name
    stats["per_day_costs"] = test_res["grid_cost_aud"].tolist()
    return stats


def plot_seed_band(all_logs: dict[str, list[list[dict]]], out_path: Path, window: int = 200) -> None:
    fig, ax = plt.subplots(figsize=(10, 4))
    colors = {"q_learning": "#2563eb", "sarsa": "#16a34a", "double_q_learning": "#9333ea"}

    for agent_name, seed_logs in all_logs.items():
        if not seed_logs:
            continue
        min_len = min(len(logs) for logs in seed_logs)
        rewards = np.array([[r["total_reward"] for r in logs[:min_len]] for logs in seed_logs])
        if min_len >= window:
            smoothed = np.array([
                np.convolve(row, np.ones(window) / window, mode="valid") for row in rewards
            ])
            x = np.arange(window, min_len + 1)
        else:
            smoothed = rewards
            x = np.arange(1, min_len + 1)

        mean = smoothed.mean(axis=0)
        std = smoothed.std(axis=0)
        color = colors.get(agent_name, "#64748b")
        ax.plot(x, mean, label=agent_name, color=color, linewidth=1.5)
        ax.fill_between(x, mean - std, mean + std, color=color, alpha=0.2)

    ax.set_xlabel("Episode")
    ax.set_ylabel("Total reward (rolling mean ± std across seeds)")
    ax.set_title("Multi-seed learning curves")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-seed RL training and evaluation")
    parser.add_argument(
        "--agents",
        nargs="+",
        default=["q_learning", "sarsa"],
        choices=["q_learning", "sarsa", "double_q_learning"],
    )
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    parser.add_argument("--episodes", type=int, default=None)
    parser.add_argument("--quick", action="store_true", help="3000 episodes per seed")
    parser.add_argument("--reward-mode", default="battery_aware", choices=["battery_aware", "cost_only"])
    parser.add_argument("--output", "-o", type=Path, default=None)
    args = parser.parse_args()

    cfg = load_config()
    episodes = args.episodes or (3000 if args.quick else cfg.n_episodes)
    ensure_output_dirs(cfg)

    df, split = load_customer_dataset(cfg)
    thresholds = fit_discretizer(df, cfg)

    all_results: list[dict] = []
    all_logs: dict[str, list[list[dict]]] = {a: [] for a in args.agents}

    for agent_name in args.agents:
        for seed in args.seeds:
            print(f"\n=== {agent_name} seed={seed} ({episodes} episodes) ===")
            cfg_run = load_config()
            cfg_run.n_episodes = episodes
            cfg_run.random_seed = seed
            agent = make_agent(agent_name, cfg_run, seed=seed)
            logs, _ = train_agent(
                agent, df, split.train, thresholds, cfg_run, args.reward_mode,
                val_days=split.val, eval_every=max(500, episodes // 20),
            )
            all_logs[agent_name].append(logs)
            test_res = evaluate_split(
                df, thresholds, split, "test", greedy_action_fn(agent), cfg_run, args.reward_mode
            )
            stats = summarize(test_res)
            row = {
                "agent": agent_name,
                "seed": seed,
                "episodes": episodes,
                "total_grid_cost_aud": stats["total_grid_cost_aud"],
                "mean_reward": stats["mean_reward"],
                "pct_of_oracle_savings": stats.get("pct_of_oracle_savings"),
            }
            all_results.append(row)
            print(f"  test cost: {stats['total_grid_cost_aud']:.2f} AUD")

    summary_rows = []
    for agent_name in args.agents:
        subset = [r for r in all_results if r["agent"] == agent_name]
        costs = np.array([r["total_grid_cost_aud"] for r in subset])
        summary_rows.append({
            "agent": agent_name,
            "n_seeds": len(costs),
            "mean_test_cost_aud": costs.mean(),
            "std_test_cost_aud": costs.std(ddof=1) if len(costs) > 1 else 0.0,
            "ci95_half_width": 1.96 * costs.std(ddof=1) / np.sqrt(len(costs)) if len(costs) > 1 else 0.0,
        })

    summary_df = pd.DataFrame(summary_rows)
    print("\n=== MULTI-SEED SUMMARY (test split total cost) ===")
    print(summary_df.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    if "q_learning" in args.agents and "sarsa" in args.agents:
        q_costs = []
        s_costs = []
        for seed in args.seeds:
            q_row = next(r for r in all_results if r["agent"] == "q_learning" and r["seed"] == seed)
            s_row = next(r for r in all_results if r["agent"] == "sarsa" and r["seed"] == seed)
            q_costs.append(q_row["total_grid_cost_aud"])
            s_costs.append(s_row["total_grid_cost_aud"])
        t_stat, p_val = _paired_ttest(np.array(q_costs), np.array(s_costs))
        print(f"\nPaired t-test Q-Learning vs SARSA: t={t_stat:.3f}, p={p_val:.4f}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = args.output or (cfg.results_logs / f"multi_seed_{stamp}.csv")
    pd.DataFrame(all_results).to_csv(out, index=False)
    summary_df.to_csv(out.with_name(out.stem + "_summary.csv"), index=False)
    plot_path = cfg.results_plots / f"multi_seed_curves_{stamp}.png"
    plot_seed_band(all_logs, plot_path)
    print(f"\nSaved -> {out}")
    print(f"Saved -> {plot_path}")


if __name__ == "__main__":
    main()
