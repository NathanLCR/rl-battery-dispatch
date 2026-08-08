# CA2 Forecast-Information Experiment — Findings

Branch: `ca2_agent`  
Tag: `forecast_exp`  
Date: 2026-08-07  

## Setup (fair comparison)

All controllers were trained/evaluated under the **same** updated environment:

| Setting | Value |
|--------|--------|
| Export pricing | **Wholesale-exposed** — `export revenue = kWh × wholesale AUD/kWh` (AEMO MWh÷1000). Experimental tariff — **not** a household FiT |
| Charge / discharge efficiency | 0.95 / 0.95 |
| Cycling cost | 0.02 AUD/kWh throughput |
| Terminal SOC | Valued vs initial SOC at 0.15 AUD/kWh (prevents end-of-day emptying) |
| Privileged signal | `max(price next 8 steps) − current`, tertile-binned on **train only** → FALL_OR_FLAT / MODERATE_RISE / STRONG_RISE |
| State sizes | Current Q: **540** · Privileged Q: **1620** |
| Training | Q-Learning, 10 000 episodes, seeds **42–46**, identical hyperparameters |
| Split | Chronological train / val / test (256 / 54 / 53 days), Customer 1 |

Do **not** compare these AUD totals to older fixed-FiT CA2 runs.

## Headline results (53-day test split)

| Controller | Total net cost (AUD) | Notes |
|------------|---------------------|--------|
| No battery | 160.75 | Upper bound |
| Perfect-foresight oracle | 74.92 | Includes efficiencies, cycling, terminal SOC |
| **Greedy 5-action (current price)** | **90.39** | Best deployable policy |
| Q-Learning current-info (mean ± std over 5 seeds) | 124.23 ± 11.65 | Uses grid-charge/export |
| Q-Learning privileged 4h direction (mean ± std) | 139.68 ± 5.55 | Uses them **more**, costs **more** |

### Win rate (% of test days with lowest cost)

| Controller | Days won | Win % |
|------------|----------|-------|
| Greedy 5-action | 51 | 96.2% |
| Q current | 2 | 3.8% |
| Q privileged | 0 | 0.0% |

### Arbitrage behaviour (means over seeds where applicable)

| Controller | Export revenue | Grid-charge cost | Net arb. profit | Export kWh | Grid-charge kWh | #export acts | #grid-charge acts | Final SOC % |
|------------|----------------|------------------|-----------------|------------|-----------------|--------------|-------------------|-------------|
| Greedy | 2.97 | 20.03 | −17.06 | 37.5 | 75.0 | 15 | 30 | 36.3 |
| Q current | 13.30 | 8.50 | +4.80 | 238.4 | 30.6 | 114.8 | 15.4 | 26.8 |
| Q privileged | 18.13 | 13.24 | +4.89 | 309.9 | 47.9 | 162.2 | 19.4 | 20.7 |

Grid-charge and export **are used** by all three controllers. Privileged exports and grid-charges **more** than current-info Q, but ends with lower SOC and higher bill.

## Interpretation (pre-registered)

> **Future-price direction alone was insufficient;** the agent may need richer price **magnitude** information, a better state representation, or a different learning method.

Supporting observations:

1. **Privileged vs current:** privileged is *worse* (139.7 vs 124.2 AUD), so the ternary “will price rise?” signal did not help tabular Q-Learning under this tariff.
2. **Privileged vs greedy:** large gap remains (139.7 vs 90.4); greedy still wins 96% of days.
3. **Why direction may fail here:** retail import = wholesale + **0.22**, while export pays **wholesale**. Round-trip grid-charge→export loses the margin plus efficiency/cycling. Profitable foresight is mostly “charge cheap → **discharge to load** later,” not “sell high.” A coarse rise/flat/fall bit does not encode *how much* the spread justifies charging, nor load timing.
4. **Sample efficiency:** privileged tables are 3× larger (1620 vs 540); 10k episodes may still under-train relative to current-info (smoke run at 3k showed the same ordering).

## Artefacts

```
results/logs/forecast_exp_summary_20260807_181849_forecast_exp.csv
results/logs/forecast_exp_per_day_20260807_181849_forecast_exp.csv
results/logs/forecast_exp_winrate_20260807_181849_forecast_exp.csv
results/logs/forecast_exp_meta_20260807_181849_forecast_exp.json
results/logs/forecast_exp_days_20260807_181849_forecast_exp/
results/plots/forecast_exp_cost_20260807_181849_forecast_exp.png
results/plots/forecast_exp_actions_20260807_181849_forecast_exp.png
results/models/Q_q_learning_*_forecast_exp_{current,privileged}_seed{42..46}.npy
```

## How to reproduce

```bash
python -m src.forecast_info_experiment --episodes 10000 --seeds 42 43 44 45 46 --tag forecast_exp
# smoke:  python -m src.forecast_info_experiment --quick --tag forecast_smoke
```

Dashboard: select **Greedy 5-action**, **Current-price Q-Learning**, and **Privileged Q-Learning**; enable Q-value explanation on the Step Log tab.

## Follow-ups added on `ca2_agent`

- **Realistic forecasts** (`src/price_forecast.py`, `forecast.mode: forecast`): climatology + persistence replaces true future prices for privileged agents.
- **SARSA / Double Q-Learning**: same experiment runner —  
  `python -m src.forecast_info_experiment --foresight forecast --agents q_learning sarsa double_q_learning ...`
- **Play vs Agent**: `dashboard/play_vs_agent.py` (landing CTA + digital-twin sidebar).
- **README**: rewritten for CA2 forecast experiment, wholesale tariff honesty, Play mode, and multi-agent commands.
