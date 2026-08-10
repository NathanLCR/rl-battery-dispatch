"""End-to-end system smoke tests for GréineQ CA2 stack."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config, ensure_output_dirs
from src.constants import HOLD, CHARGE, DISCHARGE, GRID_CHARGE, EXPORT, ACTION_NAMES
from src.data_loader import load_customer_dataset, get_episode
from src.discretizer import fit_discretizer, n_states_for
from src.environment import MicrogridEnv
from src.evaluate import run_episode_with_policy, evaluate_split
from src.oracle import no_battery_import_cost, oracle_perfect_foresight_import
from src.physics import apply_battery_action
from src.price_forecast import fit_price_forecast
from src.replay import trace_episode, q_values_for_state
from src.rule_baseline import price_arbitrage_action_fn, greedy_self_consumption_action
from src.train import make_agent, greedy_action_fn, load_trained_agent, train_agent


def ok(msg: str) -> None:
    print(f"  PASS  {msg}")


def fail(msg: str) -> None:
    print(f"  FAIL  {msg}")
    raise AssertionError(msg)


def main() -> None:
    print("=== GréineQ system test ===\n")
    cfg = load_config()
    ensure_output_dirs(cfg)

    # 1. Config
    assert cfg.tariff.export_pricing == "wholesale", cfg.tariff.export_pricing
    assert cfg.charge_efficiency == 0.95
    assert cfg.forecast_mode in ("forecast", "oracle")
    ok(f"config wholesale export, efficiencies, forecast.mode={cfg.forecast_mode}")

    # 2. Data
    df, split = load_customer_dataset(cfg)
    assert len(split.train) > 0 and len(split.test) > 0
    ep = get_episode(df, split.test[0])
    assert len(ep) == 48
    ok(f"dataset loaded train={len(split.train)} val={len(split.val)} test={len(split.test)}")

    # 3. Forecast + discretizer
    fm = fit_price_forecast(df, horizon_steps=cfg.forecast_horizon_steps)
    th = fit_discretizer(df, cfg, foresight_mode="forecast", forecast_model=fm)
    fm.save(cfg.artifacts_dir / "price_forecast.json")
    th.save(cfg.artifacts_dir / "bin_thresholds.json")
    series = fm.forecast_series_for_episode(ep, 0)
    assert len(series) == 8
    ok(f"forecast model + thresholds (future q33={th.future_delta_q33:.5f})")

    # 4. Physics: efficiencies + mutual exclusion
    phys = apply_battery_action(50.0, GRID_CHARGE, 0.0, 1.0, cfg)
    assert phys["grid_charge_kwh"] > 0
    assert phys["export_kwh"] == 0
    phys_e = apply_battery_action(80.0, EXPORT, 0.0, 0.0, cfg)
    assert phys_e["export_kwh"] > 0 or phys_e["invalid_action"]
    ok("physics grid_charge/export + no simultaneous charge+export")

    # 5. Environment wholesale export + terminal SOC
    env = MicrogridEnv(ep, th, cfg, privileged=False)
    env.reset()
    total_r = 0.0
    done = False
    while not done:
        _, r, done, info = env.step(HOLD)
        total_r += r
        if info["export_kwh"] > 0:
            assert abs(info["export_price_per_kwh"] - info["price_per_kwh"]) < 1e-9
    # HOLD for a full day: SOC stays at the initial level, so terminal adjustment ≈ 0.
    assert abs(env._soc_pct - cfg.initial_soc_pct) < 1e-6
    assert abs(env.terminal_soc_adjustment) < 1e-6
    ok(f"env episode HOLD cost={env.total_grid_cost:.3f} AUD export_pricing=wholesale")

    # 6. Privileged forecast foresight differs from oracle potentially
    env_f = MicrogridEnv(ep, th, cfg, privileged=True, foresight_mode="forecast", forecast_model=fm)
    env_o = MicrogridEnv(ep, th, cfg, privileged=True, foresight_mode="oracle")
    env_f.reset()
    env_o.reset()
    s_f, s_o = env_f._observe(), env_o._observe()
    assert 0 <= s_f < n_states_for(True)
    assert 0 <= s_o < n_states_for(True)
    ok(f"privileged states forecast={s_f} oracle={s_o} (n={n_states_for(True)})")

    # 7. Baselines + oracle
    no_bat = no_battery_import_cost(ep, cfg)
    ora = oracle_perfect_foresight_import(ep, cfg)
    assert ora <= no_bat + 1e-6
    greedy_res = run_episode_with_policy(ep, th, cfg, price_arbitrage_action_fn)
    ok(
        f"bounds no_bat={no_bat:.2f} oracle={ora:.2f} greedy_day={greedy_res['grid_cost_aud']:.2f} "
        f"exports={greedy_res['n_export_actions']} grid_charges={greedy_res['n_grid_charge_actions']}"
    )

    # 8. Short train + load
    cfg.n_episodes = 200
    cfg.random_seed = 42
    agent = make_agent("q_learning", cfg, seed=42, privileged=False)
    train_agent(
        agent, df, split.train[:30], th, cfg, "battery_aware",
        privileged=False, eval_every=1000,
    )
    model_path = cfg.results_models / "Q_q_learning_system_test_current.npy"
    agent.q.save(model_path)
    loaded = load_trained_agent("q_learning", model_path, cfg, privileged=False)
    policy = greedy_action_fn(loaded)
    trace, summary = trace_episode(ep, th, policy, cfg, privileged=False)
    assert len(trace) == 48
    qv = q_values_for_state(loaded.q, int(trace.iloc[0]["state"]))
    assert set(qv) == set(ACTION_NAMES.values())
    ok(f"train/load/replay OK cost={summary['grid_cost_aud']:.3f} Q-keys={list(qv)}")

    # 9. Privileged short train
    agent_p = make_agent("q_learning", cfg, seed=42, privileged=True)
    train_agent(
        agent_p, df, split.train[:30], th, cfg, "battery_aware",
        privileged=True, foresight_mode="forecast", forecast_model=fm, eval_every=1000,
    )
    priv_path = cfg.results_models / "Q_q_learning_system_test_privileged.npy"
    agent_p.q.save(priv_path)
    assert agent_p.q.n_states == n_states_for(True)
    ok(f"privileged train OK states={agent_p.q.n_states} model={priv_path.name}")

    # 10. Play-vs-agent core logic (no Streamlit)
    human_actions = []
    h_env = MicrogridEnv(ep, th, cfg, privileged=False)
    h_env.reset()
    rng = np.random.default_rng(0)
    done = False
    while not done:
        # naive human: greedy solar, else hold
        row = h_env.episode_df.iloc[h_env._step_idx]
        a = greedy_self_consumption_action(
            h_env._soc_pct, float(row["pv_kwh"]), float(row["load_kwh"]), th,
            min_soc_pct=cfg.min_soc_pct, max_soc_pct=cfg.max_soc_pct,
        )
        human_actions.append(a)
        _, _, done, _ = h_env.step(a)
    assert len(human_actions) == 48
    ok(f"play-vs-agent human rollout 48 steps final_soc={h_env._soc_pct:.1f}% cost={h_env.total_grid_cost:.3f}")

    # 11. Dashboard import
    import dashboard.app  # noqa: F401
    import dashboard.play_vs_agent  # noqa: F401
    ok("dashboard.app + play_vs_agent import cleanly")

    print("\n=== ALL SYSTEM TESTS PASSED ===")
    print(f"Models ready: {model_path.name}, {priv_path.name}")
    print("Start dashboard: streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
