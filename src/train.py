"""Train tabular Q-Learning or SARSA on daily microgrid episodes."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.agents.q_learning import QLearningAgent
from src.agents.sarsa import SARSAAgent
from src.agents.double_q_learning import DoubleQLearningAgent
from src.config import Config, ensure_output_dirs, load_config
from src.data_loader import DaySplit, get_episode, load_customer_dataset
from src.discretizer import BinThresholds, fit_discretizer
from src.environment import MicrogridEnv
from src.evaluate import evaluate_split, summarize


def _greedy_eval(
    agent,
    df: pd.DataFrame,
    days: list[str],
    thresholds: BinThresholds,
    cfg: Config,
    reward_mode: str,
    privileged: bool = False,
    foresight_mode: str | None = None,
    forecast_model=None,
) -> tuple[float, float]:
    """Roll out the current *greedy* (no-exploration) policy over a fixed set of
    days and return (mean total reward, mean grid-cost AUD). No Q-updates."""
    rewards, costs = [], []
    for day in days:
        env = MicrogridEnv(
            get_episode(df, day),
            thresholds,
            cfg,
            reward_mode=reward_mode,
            privileged=privileged,
            foresight_mode=foresight_mode,
            forecast_model=forecast_model,
        )
        env.reset()
        total_reward = 0.0
        done = False
        while not done:
            action = (
                agent.greedy_action(env._observe())
                if hasattr(agent, "greedy_action")
                else agent.q.greedy_action(env._observe())
            )
            _, reward, done, _ = env.step(action)
            total_reward += reward
        rewards.append(total_reward)
        costs.append(env.total_grid_cost)
    return float(np.mean(rewards)), float(np.mean(costs))


def _rule_eval(
    df: pd.DataFrame,
    days: list[str],
    thresholds: BinThresholds,
    cfg: Config,
    reward_mode: str,
) -> float:
    """Mean grid-cost AUD of the rule baseline on a fixed set of days (reference line)."""
    from src.rule_baseline import rule_action

    costs = []
    for day in days:
        env = MicrogridEnv(get_episode(df, day), thresholds, cfg, reward_mode=reward_mode)
        env.reset()
        done = False
        while not done:
            row = env.episode_df.iloc[env._step_idx]
            action = rule_action(env._soc_pct, float(row["pv_kwh"]), float(row["load_kwh"]), env.thresholds)
            _, _, done, _ = env.step(action)
        costs.append(env.total_grid_cost)
    return float(np.mean(costs))


def train_agent(
    agent,
    df: pd.DataFrame,
    train_days: list[str],
    thresholds: BinThresholds,
    cfg: Config,
    reward_mode: str = "battery_aware",
    val_days: list[str] | None = None,
    eval_every: int = 500,
    privileged: bool = False,
    foresight_mode: str | None = None,
    forecast_model=None,
) -> tuple[list[dict], list[dict]]:
    """
    Run episodic training by sampling random train days.

    Returns per-episode logs and periodic greedy validation metrics.
    """
    logs: list[dict] = []
    eval_logs: list[dict] = []
    rng = np.random.default_rng(cfg.random_seed)
    use_noise = bool(getattr(cfg, "forecast_train_noise", False))

    for episode_idx in range(1, cfg.n_episodes + 1):
        day = train_days[int(rng.integers(0, len(train_days)))]
        ep_df = get_episode(df, day)
        env = MicrogridEnv(
            ep_df,
            thresholds,
            cfg,
            reward_mode=reward_mode,
            privileged=privileged,
            foresight_mode=foresight_mode,
            forecast_model=forecast_model,
            forecast_rng=rng if use_noise else None,
            forecast_noise=use_noise,
        )

        if hasattr(agent, "reset_episode"):
            agent.reset_episode()

        if isinstance(agent, SARSAAgent):
            state = env.reset()
            action = agent.start_episode(state)
        else:
            state = env.reset()
            action = agent.select_action(state)

        total_reward = 0.0
        done = False

        while not done:
            next_state, reward, done, info = env.step(action)
            total_reward += reward

            # SARSA updates with the next on-policy action; Q-Learning bootstraps max Q(s',·)
            if isinstance(agent, SARSAAgent):
                action = agent.update(state, action, reward, next_state, done)
            else:
                agent.update(state, action, reward, next_state, done)
                action = agent.select_action(next_state) if not done else action

            state = next_state

        agent.decay_epsilon()
        if hasattr(agent, "decay_alpha"):
            agent.decay_alpha()
        logs.append(
            {
                "episode": episode_idx,
                "day": day,
                "total_reward": total_reward,
                "grid_cost_aud": env.total_grid_cost,
                "grid_import_kwh": env.total_grid_import_kwh,
                "solar_waste_kwh": env.total_solar_waste_kwh,
                "epsilon": agent.epsilon,
            }
        )

        if val_days and episode_idx % eval_every == 0:
            eval_reward, eval_cost = _greedy_eval(
                agent,
                df,
                val_days,
                thresholds,
                cfg,
                reward_mode,
                privileged=privileged,
                foresight_mode=foresight_mode,
                forecast_model=forecast_model,
            )
            eval_logs.append(
                {"episode": episode_idx, "val_mean_reward": eval_reward, "val_mean_grid_cost_aud": eval_cost}
            )

        if episode_idx % 500 == 0:
            recent = [r["total_reward"] for r in logs[-500:]]
            msg = (
                f"  ep {episode_idx:5d} | avg reward (last 500): {np.mean(recent):+.3f} | "
                f"epsilon: {agent.epsilon:.4f}"
            )
            if eval_logs:
                msg += f" | val greedy cost: {eval_logs[-1]['val_mean_grid_cost_aud']:.3f} AUD"
            print(msg)

    return logs, eval_logs


def save_training_log(logs: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(logs[0].keys()))
        writer.writeheader()
        writer.writerows(logs)


def plot_learning_curve(logs: list[dict], out_path: Path, window: int = 200) -> None:
    rewards = np.array([r["total_reward"] for r in logs], dtype=np.float64)
    if len(rewards) >= window:
        kernel = np.ones(window) / window
        smoothed = np.convolve(rewards, kernel, mode="valid")
        x = np.arange(window, len(rewards) + 1)
    else:
        smoothed = rewards
        x = np.arange(1, len(rewards) + 1)

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(x, smoothed, linewidth=1.2)
    ax.set_xlabel("Episode")
    ax.set_ylabel(f"Total reward (rolling mean, window={window})")
    ax.set_title("Training learning curve")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_eval_curve(
    eval_logs: list[dict], out_path: Path, rule_cost: float | None = None
) -> None:
    """Greedy validation reward and grid cost vs episode index."""
    if not eval_logs:
        return
    ep = [e["episode"] for e in eval_logs]
    rew = [e["val_mean_reward"] for e in eval_logs]
    cost = [e["val_mean_grid_cost_aud"] for e in eval_logs]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    ax1.plot(ep, rew, marker="o", ms=3, linewidth=1.4, color="#2563eb")
    ax1.set_ylabel("Val greedy mean reward")
    ax1.set_title("Learning progress on fixed validation set")
    ax1.grid(True, alpha=0.3)

    ax2.plot(ep, cost, marker="o", ms=3, linewidth=1.4, color="#16a34a", label="RL greedy")
    if rule_cost is not None:
        ax2.axhline(rule_cost, color="#dc2626", linestyle="--", linewidth=1.4, label="Rule baseline")
    ax2.set_xlabel("Episode")
    ax2.set_ylabel("Val mean grid cost (AUD/day)")
    ax2.legend(loc="best", fontsize=9)
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def save_eval_log(eval_logs: list[dict], path: Path) -> None:
    if not eval_logs:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(eval_logs[0].keys()))
        writer.writeheader()
        writer.writerows(eval_logs)


def make_agent(
    name: str,
    cfg: Config,
    seed: int | None = None,
    q_init: float = 0.0,
    privileged: bool = False,
    n_states: int | None = None,
):
    """Factory for supported tabular agents using training hyperparameters from config."""
    from src.discretizer import n_states_for

    agent_seed = cfg.random_seed if seed is None else seed
    ns = n_states if n_states is not None else n_states_for(privileged)
    common = dict(
        alpha=cfg.alpha,
        gamma=cfg.gamma,
        epsilon=cfg.epsilon,
        epsilon_min=cfg.epsilon_min,
        epsilon_decay=cfg.epsilon_decay,
        alpha_decay=cfg.alpha_decay,
        alpha_min=cfg.alpha_min,
        seed=agent_seed,
        q_init=q_init,
        n_states=ns,
    )
    if name == "q_learning":
        return QLearningAgent(**common)
    if name == "sarsa":
        return SARSAAgent(**common)
    if name == "double_q_learning":
        return DoubleQLearningAgent(**common)
    raise ValueError(f"Unknown agent: {name}")


def load_trained_agent(name: str, model_path: Path, cfg: Config, privileged: bool | None = None):
    """Restore a trained agent from disk and disable exploration."""
    import numpy as np

    arr = np.load(model_path)
    if name == "double_q_learning":
        n_states = int(arr.shape[1]) if arr.ndim == 3 else int(arr.shape[0])
        agent = make_agent(name, cfg, n_states=n_states)
        agent.load(model_path)
    else:
        n_states = int(arr.shape[0])
        agent = make_agent(name, cfg, n_states=n_states)
        agent.q = agent.q.load(model_path)
    agent.epsilon = 0.0
    if privileged is not None:
        agent.privileged = privileged  # type: ignore[attr-defined]
    else:
        from src.discretizer import N_STATES_PRIVILEGED

        agent.privileged = n_states == N_STATES_PRIVILEGED  # type: ignore[attr-defined]
    return agent


def greedy_action_fn(agent):
    """Wrap a trained agent as a deterministic policy for evaluation."""

    def policy(env: MicrogridEnv) -> int:
        state = env._observe()
        if hasattr(agent, "greedy_action"):
            return agent.greedy_action(state)
        return agent.q.greedy_action(state)

    return policy


def main() -> None:
    parser = argparse.ArgumentParser(description="Train GréineQ RL agent")
    parser.add_argument(
        "--agent",
        choices=["q_learning", "sarsa", "double_q_learning"],
        default="q_learning",
    )
    parser.add_argument("--episodes", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None, help="Random seed override")
    parser.add_argument("--reward-mode", choices=["battery_aware", "cost_only"], default="battery_aware")
    parser.add_argument("--gamma", type=float, default=None)
    parser.add_argument("--epsilon", type=float, default=None)
    parser.add_argument("--epsilon-decay", type=float, default=None)
    parser.add_argument("--tag", type=str, default="", help="Suffix on output filenames")
    parser.add_argument(
        "--q-init", type=float, default=0.0,
        help="Optimistic Q-table initial value (encourages exploring under-tried actions, e.g. grid_charge/export)",
    )
    parser.add_argument(
        "--privileged",
        action="store_true",
        help="Include 4-hour future price-direction signal in the state",
    )
    parser.add_argument(
        "--foresight",
        choices=["oracle", "forecast"],
        default=None,
        help="Privileged signal type (default: config forecast.mode)",
    )
    args = parser.parse_args()

    cfg = load_config()
    if args.episodes is not None:
        cfg.n_episodes = args.episodes
    if args.gamma is not None:
        cfg.gamma = args.gamma
    if args.epsilon is not None:
        cfg.epsilon = args.epsilon
    if args.epsilon_decay is not None:
        cfg.epsilon_decay = args.epsilon_decay
    if args.seed is not None:
        cfg.random_seed = args.seed

    ensure_output_dirs(cfg)
    df, day_split = load_customer_dataset(cfg)

    privileged = bool(args.privileged)
    foresight = args.foresight or (
        cfg.forecast_mode if cfg.forecast_mode in ("oracle", "forecast") else "forecast"
    )
    forecast_model = None
    if privileged and foresight == "forecast":
        from src.price_forecast import fit_price_forecast

        forecast_model = fit_price_forecast(
            df,
            horizon_steps=cfg.forecast_horizon_steps,
            persistence_alpha=cfg.forecast_persistence_alpha,
            noise_scale=cfg.forecast_noise_scale,
        )
        forecast_model.save(cfg.artifacts_dir / "price_forecast.json")

    thresholds = fit_discretizer(
        df,
        cfg,
        foresight_mode=foresight if privileged else "oracle",
        forecast_model=forecast_model,
    )
    thresholds.save(cfg.artifacts_dir / "bin_thresholds.json")

    agent = make_agent(
        args.agent, cfg, seed=cfg.random_seed, q_init=args.q_init, privileged=privileged
    )
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    priv_tag = f"_privileged_{foresight}" if privileged else "_current"
    tag = f"{priv_tag}_{args.tag}" if args.tag else priv_tag

    print(
        f"Training {args.agent} ({'privileged/'+foresight if privileged else 'current-info'}) "
        f"for {cfg.n_episodes} episodes on {len(day_split.train)} train days "
        f"(export={cfg.tariff.export_pricing}, gamma={cfg.gamma}, epsilon={cfg.epsilon})..."
    )
    logs, eval_logs = train_agent(
        agent, df, day_split.train, thresholds, cfg, args.reward_mode,
        val_days=day_split.val, eval_every=500, privileged=privileged,
        foresight_mode=foresight if privileged else "none",
        forecast_model=forecast_model,
    )

    model_path = cfg.results_models / f"Q_{args.agent}_{stamp}{tag}.npy"
    log_path = cfg.results_logs / f"train_{args.agent}_{stamp}{tag}.csv"
    plot_path = cfg.results_plots / f"learning_curve_{args.agent}_{stamp}{tag}.png"
    eval_log_path = cfg.results_logs / f"eval_{args.agent}_{stamp}{tag}.csv"
    eval_plot_path = cfg.results_plots / f"eval_curve_{args.agent}_{stamp}{tag}.png"

    if args.agent == "double_q_learning":
        agent.save(model_path)
    else:
        agent.q.save(model_path)
    save_training_log(logs, log_path)
    plot_learning_curve(logs, plot_path)

    rule_val_cost = _rule_eval(df, day_split.val, thresholds, cfg, args.reward_mode)
    save_eval_log(eval_logs, eval_log_path)
    plot_eval_curve(eval_logs, eval_plot_path, rule_cost=rule_val_cost)

    print(f"\nSaved model  -> {model_path}")
    print(f"Saved log    -> {log_path}")
    print(f"Saved plot   -> {plot_path}")
    print(f"Saved eval   -> {eval_log_path}")
    print(f"Saved eval plot -> {eval_plot_path}")

    policy = greedy_action_fn(agent)
    test_results = evaluate_split(
        df,
        thresholds,
        day_split,
        "test",
        policy,
        cfg,
        args.reward_mode,
        privileged=privileged,
        foresight_mode=foresight if privileged else "none",
        forecast_model=forecast_model,
    )
    test_stats = summarize(test_results)
    print("\nGreedy policy on TEST split:")
    for k, v in test_stats.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    test_out = cfg.results_logs / f"test_{args.agent}_{stamp}{tag}.csv"
    test_results.to_csv(test_out, index=False)
    print(f"Saved test   -> {test_out}")


if __name__ == "__main__":
    main()
