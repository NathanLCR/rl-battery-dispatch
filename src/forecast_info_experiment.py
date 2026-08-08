"""CA2 forecast-information experiment (multi-agent).

Compares controllers under the wholesale-exposed export tariff:

  - greedy_five_action
  - {agent}_current          — current price only
  - {agent}_privileged       — current + 4h foresight (oracle or realistic forecast)
  - oracle / no_battery      — bounds

Foresight modes:
  - oracle   — true max(price next 4h) − current  (information upper bound)
  - forecast — climatology + persistence forecast (deployable-style)

Do not compare AUD totals against old fixed-FiT CA2 runs.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import Config, ensure_output_dirs, load_config
from src.data_loader import get_episode, load_customer_dataset
from src.discretizer import FUTURE_SIGNAL_NAMES, fit_discretizer, future_signal_bin, n_states_for
from src.environment import MicrogridEnv
from src.evaluate import evaluate_split, summarize
from src.oracle import no_battery_import_cost, oracle_perfect_foresight_import
from src.price_forecast import fit_price_forecast
from src.rule_baseline import price_arbitrage_action_fn
from src.train import greedy_action_fn, load_trained_agent, make_agent, train_agent


SUPPORTED_AGENTS = ("q_learning", "sarsa", "double_q_learning")


def _assert_wholesale(cfg: Config) -> None:
    if cfg.tariff.export_pricing != "wholesale":
        raise SystemExit(
            "Requires tariff.export_pricing: wholesale "
            f"(got {cfg.tariff.export_pricing!r})."
        )


def train_one(
    *,
    agent_name: str,
    privileged: bool,
    seed: int,
    df,
    day_split,
    thresholds,
    cfg: Config,
    reward_mode: str,
    tag: str,
    foresight_mode: str,
    forecast_model,
) -> Path:
    cfg.random_seed = seed
    agent = make_agent(agent_name, cfg, seed=seed, privileged=privileged)
    label = "privileged" if privileged else "current"
    print(
        f"\n=== Train {agent_name} ({label}, foresight={foresight_mode if privileged else 'none'}) "
        f"seed={seed} episodes={cfg.n_episodes} states={n_states_for(privileged)} ==="
    )
    logs, eval_logs = train_agent(
        agent,
        df,
        day_split.train,
        thresholds,
        cfg,
        reward_mode,
        val_days=day_split.val,
        eval_every=max(500, cfg.n_episodes // 10),
        privileged=privileged,
        foresight_mode=foresight_mode if privileged else "none",
        forecast_model=forecast_model if privileged and foresight_mode == "forecast" else None,
    )
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = cfg.results_models / f"Q_{agent_name}_{stamp}_{tag}_seed{seed}.npy"
    if agent_name == "double_q_learning":
        agent.save(model_path)
    else:
        agent.q.save(model_path)
    pd.DataFrame(logs).to_csv(
        cfg.results_logs / f"train_{agent_name}_{stamp}_{tag}_seed{seed}.csv", index=False
    )
    if eval_logs:
        pd.DataFrame(eval_logs).to_csv(
            cfg.results_logs / f"eval_{agent_name}_{stamp}_{tag}_seed{seed}.csv", index=False
        )
    print(f"Saved model -> {model_path}")
    return model_path


def _load_policy(agent_name: str, model_path: Path, cfg: Config, privileged: bool):
    agent = load_trained_agent(agent_name, model_path, cfg, privileged=privileged)
    return greedy_action_fn(agent), agent


def evaluate_controller(
    name: str,
    action_fn,
    df,
    thresholds,
    day_split,
    cfg: Config,
    reward_mode: str,
    privileged: bool,
    foresight_mode: str | None = None,
    forecast_model=None,
) -> pd.DataFrame:
    results = evaluate_split(
        df,
        thresholds,
        day_split,
        "test",
        action_fn,
        cfg,
        reward_mode,
        privileged=privileged,
        foresight_mode=foresight_mode,
        forecast_model=forecast_model,
    )
    results.insert(0, "controller", name)
    return results


def win_rate_table(per_day: pd.DataFrame, controllers: list[str]) -> pd.DataFrame:
    pivot = per_day.pivot_table(index="episode_day", columns="controller", values="grid_cost_aud")
    winners = pivot[controllers].idxmin(axis=1)
    counts = winners.value_counts()
    n = len(pivot)
    rows = []
    for c in controllers:
        wins = int(counts.get(c, 0))
        rows.append({"controller": c, "days_won": wins, "win_pct": round(100.0 * wins / n, 1)})
    return pd.DataFrame(rows)


def plot_cost_comparison(summary: pd.DataFrame, out_path: Path, order: list[str]) -> None:
    present = [c for c in order if c in set(summary["controller"])]
    if not present:
        return
    plot_df = summary.set_index("controller").loc[present]
    fig, ax = plt.subplots(figsize=(max(9, len(present) * 0.9), 4.8))
    ax.bar(plot_df.index.astype(str), plot_df["total_grid_cost_aud"], color="#2563eb")
    ax.set_ylabel("Total test-split net cost (AUD)")
    ax.set_title("Forecast-info experiment — wholesale export tariff")
    ax.tick_params(axis="x", rotation=25)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="CA2 forecast-information experiment")
    parser.add_argument("--episodes", type=int, default=None)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    parser.add_argument(
        "--agents",
        nargs="+",
        default=["q_learning"],
        choices=list(SUPPORTED_AGENTS),
        help="RL algorithms to train (default: q_learning only)",
    )
    parser.add_argument(
        "--foresight",
        choices=["oracle", "forecast"],
        default=None,
        help="Privileged signal type (default: config forecast.mode, else forecast)",
    )
    parser.add_argument("--reward-mode", default="battery_aware", choices=["battery_aware", "cost_only"])
    parser.add_argument("--tag", type=str, default="forecast_exp")
    parser.add_argument("--quick", action="store_true", help="3000 episodes, 2 seeds")
    parser.add_argument(
        "--skip-train",
        action="store_true",
        help="Evaluate only (pass model paths via --model-manifest JSON)",
    )
    parser.add_argument(
        "--model-manifest",
        type=Path,
        default=None,
        help="JSON {controller_key: [model_paths...]} for --skip-train",
    )
    args = parser.parse_args()

    cfg = load_config()
    _assert_wholesale(cfg)
    foresight = args.foresight or (
        cfg.forecast_mode if cfg.forecast_mode in ("oracle", "forecast") else "forecast"
    )
    if args.quick:
        cfg.n_episodes = 3000
        args.seeds = args.seeds[:2]
    if args.episodes is not None:
        cfg.n_episodes = args.episodes

    ensure_output_dirs(cfg)
    df, day_split = load_customer_dataset(cfg)

    forecast_model = None
    if foresight == "forecast":
        forecast_model = fit_price_forecast(
            df,
            horizon_steps=cfg.forecast_horizon_steps,
            persistence_alpha=cfg.forecast_persistence_alpha,
            noise_scale=cfg.forecast_noise_scale,
        )
        forecast_model.save(cfg.artifacts_dir / f"price_forecast_{args.tag}.json")
        forecast_model.save(cfg.artifacts_dir / "price_forecast.json")

    thresholds = fit_discretizer(
        df,
        cfg,
        foresight_mode=foresight,
        forecast_model=forecast_model,
    )
    thresholds.save(cfg.artifacts_dir / f"bin_thresholds_{args.tag}.json")
    thresholds.save(cfg.artifacts_dir / "bin_thresholds.json")

    print(
        f"Export pricing: {cfg.tariff.export_pricing} (wholesale-exposed experimental tariff)\n"
        f"Efficiencies: charge={cfg.charge_efficiency}, discharge={cfg.discharge_efficiency}, "
        f"cycling={cfg.cycling_cost_per_kwh} AUD/kWh\n"
        f"Privileged foresight: {foresight} | horizon={cfg.forecast_horizon_steps} steps\n"
        f"Future-signal edges (train): q33={thresholds.future_delta_q33:.5f}, "
        f"q66={thresholds.future_delta_q66:.5f}\n"
        f"Agents: {args.agents} | seeds: {args.seeds} | episodes: {cfg.n_episodes}\n"
        f"Train/val/test days: {len(day_split.train)}/{len(day_split.val)}/{len(day_split.test)}"
    )

    # models[controller_name] = [paths per seed]
    models: dict[str, list[Path]] = {}
    if args.skip_train:
        if not args.model_manifest:
            raise SystemExit("--skip-train requires --model-manifest")
        raw = json.loads(args.model_manifest.read_text(encoding="utf-8"))
        models = {k: [Path(p) for p in v] for k, v in raw.items()}
    else:
        for agent_name in args.agents:
            cur_key = f"{agent_name}_current"
            priv_key = f"{agent_name}_privileged"
            models[cur_key] = []
            models[priv_key] = []
            for seed in args.seeds:
                models[cur_key].append(
                    train_one(
                        agent_name=agent_name,
                        privileged=False,
                        seed=seed,
                        df=df,
                        day_split=day_split,
                        thresholds=thresholds,
                        cfg=cfg,
                        reward_mode=args.reward_mode,
                        tag=f"{args.tag}_{agent_name}_current",
                        foresight_mode=foresight,
                        forecast_model=forecast_model,
                    )
                )
                models[priv_key].append(
                    train_one(
                        agent_name=agent_name,
                        privileged=True,
                        seed=seed,
                        df=df,
                        day_split=day_split,
                        thresholds=thresholds,
                        cfg=cfg,
                        reward_mode=args.reward_mode,
                        tag=f"{args.tag}_{agent_name}_privileged_{foresight}",
                        foresight_mode=foresight,
                        forecast_model=forecast_model,
                    )
                )

    per_day_frames: list[pd.DataFrame] = []
    bound_rows = []
    for day in day_split.test:
        ep = get_episode(df, day)
        bound_rows.append(
            {
                "controller": "oracle",
                "episode_day": day,
                "grid_cost_aud": oracle_perfect_foresight_import(ep, cfg),
            }
        )
        bound_rows.append(
            {
                "controller": "no_battery",
                "episode_day": day,
                "grid_cost_aud": no_battery_import_cost(ep, cfg),
            }
        )
    per_day_frames.append(pd.DataFrame(bound_rows))

    greedy_res = evaluate_controller(
        "greedy_five_action",
        price_arbitrage_action_fn,
        df,
        thresholds,
        day_split,
        cfg,
        args.reward_mode,
        False,
    )
    per_day_frames.append(greedy_res)

    rl_controllers: list[str] = []
    for agent_name in args.agents:
        for kind, privileged in (("current", False), ("privileged", True)):
            key = f"{agent_name}_{kind}"
            rl_controllers.append(key)
            paths = models.get(key, [])
            for seed, path in zip(args.seeds[: len(paths)], paths):
                fn, _ = _load_policy(agent_name, path, cfg, privileged=privileged)
                res = evaluate_controller(
                    key,
                    fn,
                    df,
                    thresholds,
                    day_split,
                    cfg,
                    args.reward_mode,
                    privileged,
                    foresight_mode=foresight if privileged else "none",
                    forecast_model=forecast_model if privileged and foresight == "forecast" else None,
                )
                res["seed"] = seed
                res["model"] = str(path.name)
                per_day_frames.append(res)

    per_day = pd.concat(per_day_frames, ignore_index=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    per_day_path = cfg.results_logs / f"forecast_exp_per_day_{stamp}_{args.tag}.csv"
    per_day.to_csv(per_day_path, index=False)

    summary_rows = []
    for controller in ("no_battery", "oracle", "greedy_five_action"):
        g = per_day[per_day["controller"] == controller]
        if g.empty:
            continue
        if controller == "greedy_five_action":
            stats = summarize(g)
        else:
            stats = {
                "n_days": g["episode_day"].nunique(),
                "total_grid_cost_aud": float(g["grid_cost_aud"].sum()),
            }
        stats["controller"] = controller
        summary_rows.append(stats)

    for controller in rl_controllers:
        g = per_day[per_day["controller"] == controller]
        if g.empty:
            continue
        seed_totals = []
        for seed, sg in g.groupby("seed"):
            st = summarize(sg)
            st["seed"] = seed
            seed_totals.append(st)
        seed_df = pd.DataFrame(seed_totals)
        mean_stats = {
            c: float(seed_df[c].mean())
            for c in seed_df.columns
            if c != "seed" and pd.api.types.is_numeric_dtype(seed_df[c])
        }
        mean_stats["controller"] = controller
        mean_stats["n_seeds"] = int(seed_df["seed"].nunique())
        if "total_grid_cost_aud" in seed_df.columns and len(seed_df) > 1:
            mean_stats["std_grid_cost_aud"] = float(seed_df["total_grid_cost_aud"].std(ddof=1))
        summary_rows.append(mean_stats)

    summary = pd.DataFrame(summary_rows)
    summary_path = cfg.results_logs / f"forecast_exp_summary_{stamp}_{args.tag}.csv"
    summary.to_csv(summary_path, index=False)

    compare_controllers = ["greedy_five_action"] + rl_controllers
    day_costs = []
    for controller in compare_controllers:
        g = per_day[per_day["controller"] == controller]
        if g.empty:
            continue
        if "seed" in g.columns and g["seed"].notna().any():
            daily = g.groupby("episode_day")["grid_cost_aud"].mean().reset_index()
        else:
            daily = g[["episode_day", "grid_cost_aud"]].copy()
        daily["controller"] = controller
        day_costs.append(daily)
    day_cost_df = pd.concat(day_costs, ignore_index=True)
    wins = win_rate_table(day_cost_df, compare_controllers)
    wins_path = cfg.results_logs / f"forecast_exp_winrate_{stamp}_{args.tag}.csv"
    wins.to_csv(wins_path, index=False)

    order = ["no_battery", "oracle", "greedy_five_action"] + rl_controllers
    plot_cost_comparison(
        summary, cfg.results_plots / f"forecast_exp_cost_{stamp}_{args.tag}.png", order
    )

    meta = {
        "tag": args.tag,
        "export_pricing": cfg.tariff.export_pricing,
        "foresight": foresight,
        "episodes": cfg.n_episodes,
        "seeds": args.seeds,
        "agents": args.agents,
        "models": {k: [str(p) for p in v] for k, v in models.items()},
        "future_delta_q33": thresholds.future_delta_q33,
        "future_delta_q66": thresholds.future_delta_q66,
        "note": (
            "Experimental wholesale-exposed export tariff. "
            "Privileged foresight is oracle (true future) or realistic forecast."
        ),
    }
    meta_path = cfg.results_logs / f"forecast_exp_meta_{stamp}_{args.tag}.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print("\n========== FORECAST-INFO EXPERIMENT SUMMARY ==========")
    cols = [c for c in ("controller", "total_grid_cost_aud", "std_grid_cost_aud", "n_seeds") if c in summary.columns]
    print(summary[cols].to_string(index=False))
    print("\nWin rates:")
    print(wins.to_string(index=False))
    print(f"\nSaved summary -> {summary_path}")
    print(f"Saved per-day -> {per_day_path}")
    print(f"Saved winrate -> {wins_path}")
    print(f"Saved meta    -> {meta_path}")

    # Primary interpretation on Q-Learning if present
    try:
        g_cost = float(summary.loc[summary["controller"] == "greedy_five_action", "total_grid_cost_aud"].iloc[0])
        if "q_learning_current" in set(summary["controller"]) and "q_learning_privileged" in set(summary["controller"]):
            c_cost = float(summary.loc[summary["controller"] == "q_learning_current", "total_grid_cost_aud"].iloc[0])
            p_cost = float(summary.loc[summary["controller"] == "q_learning_privileged", "total_grid_cost_aud"].iloc[0])
            print("\nInterpretation (Q-Learning):")
            if p_cost < c_cost and p_cost < g_cost:
                print("  Privileged beats current and greedy — foresight helps substantially.")
            elif p_cost < c_cost:
                print("  Privileged improves on current-info but still loses to greedy.")
            else:
                print("  Privileged did not improve on current-info under this foresight mode.")
            print(f"  Costs AUD — greedy={g_cost:.2f}, current={c_cost:.2f}, privileged={p_cost:.2f}")
    except Exception as exc:  # noqa: BLE001
        print(f"(Could not auto-interpret: {exc})")


if __name__ == "__main__":
    main()
