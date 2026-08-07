# GréineQ

Tabular reinforcement learning for residential battery dispatch on a solar-connected microgrid. Agents learn when to **hold**, **charge** from surplus solar, **discharge** to offset load, **grid-charge**, or **export**, using Ausgrid half-hourly household data and AEMO NSW1 wholesale prices (Customer 1; 48 steps per day).

## Live dashboard

**Published instance:** [https://greineq-agent.sudocod.com/](https://greineq-agent.sudocod.com/)  
*(production may lag the `ca2_agent` branch — run locally for the latest forecast / Play-vs-Agent features.)*

| View | Description |
|------|-------------|
| Landing / control core | Animated day replay, KPI strip, dispatch timeline |
| Interactive digital twin | Policy comparison, Q-value inspection |
| **Play vs Agent** | Human operates one battery; RL + greedy run identical twins |

```powershell
.\run_dashboard.ps1
# or: streamlit run dashboard/app.py
```

## CA2 contribution: forecast-information experiment

The main CA2 question: **does forward-looking price information help a tabular agent time grid arbitrage?**

### Controllers compared

| Controller | Information | Actions |
|------------|-------------|---------|
| Greedy 5-action | Current state + price | All five |
| Current-info RL | Current state + price | All five |
| Privileged RL | Current + 4h price direction | All five |
| Perfect-foresight oracle | Full future prices | Benchmark only |

Primary algorithm: **Q-Learning**. SARSA and Double Q-Learning are supported in the same pipeline.

### Modelling (wholesale-exposed tariff)

This experiment uses an **experimental wholesale-exposed export price** — not a normal Australian household FiT:

```text
export revenue = exported_kWh × wholesale AUD/kWh
wholesale AUD/kWh = AEMO AUD/MWh ÷ 1000   # already stored as price_per_kwh
```

Also included: charge/discharge efficiency (0.95), cycling cost, SOC limits, no simultaneous charge+export, and terminal SOC valuation so agents cannot “win” by emptying the battery.

### Privileged foresight signal

```text
future_signal = max(price over next 8 half-hours) − current price
→ FALL_OR_FLAT | MODERATE_RISE | STRONG_RISE   (train-only tertiles)
```

Two modes (`config.yaml` → `forecast.mode`):

| Mode | Meaning |
|------|---------|
| `oracle` | True future prices (information upper bound) |
| `forecast` | **Realistic** climatology + persistence forecast (default, deployable-style) |

State sizes: current-info **540** · privileged **1620** (540 × 3 foresight bins).

### Run the experiment

```bash
# Q-Learning, realistic forecasts, 5 seeds (full)
python -m src.forecast_info_experiment --foresight forecast --agents q_learning \
  --episodes 10000 --seeds 42 43 44 45 46 --tag forecast_exp

# Also test SARSA and Double Q-Learning (same fair setup)
python -m src.forecast_info_experiment --foresight forecast \
  --agents q_learning sarsa double_q_learning \
  --episodes 10000 --seeds 42 43 44 45 46 --tag multi_agent

# Smoke test
python -m src.forecast_info_experiment --quick --foresight forecast --tag smoke

# Oracle foresight (true future) instead of realistic forecast
python -m src.forecast_info_experiment --foresight oracle --agents q_learning --tag oracle_priv
```

Outputs: `results/logs/forecast_exp_*.csv`, plots under `results/plots/`, models under `results/models/`.  
Write-up: `deliverables/notebooklm/CA2_Forecast_Info_Experiment_Findings.md`.

**Fairness rule:** retrain and evaluate everything under the wholesale tariff. Do not mix with older fixed-FiT numbers.

### Headline finding (oracle-direction privileged Q, 10k ep × 5 seeds)

Under wholesale export + efficiencies + terminal SOC, **greedy 5-action still wins**; privileged *direction* alone did not beat current-info Q. See findings doc for tables and interpretation branches.

## Earlier CA2 work (grid-charge / export MDP)

CA1 was solar-only (3 actions). CA2 first extended the MDP to 5 actions and showed that allowing arbitrage lowers the *oracle* ceiling, but reactive heuristics and tabular RL under coarse current-price discretisation underperformed greedy self-consumption. See `deliverables/notebooklm/CA2_Arbitrage_Extension_Findings.md`.

Live AEMO NSW1 feed (`src/live_feed.py`) shows the current wholesale price vs the agent’s action (PV/load are historical medians — disclosed in the UI).

## Requirements

- Python 3.10+

```bash
pip install -r requirements.txt
```

Run all commands from the repository root (`rl-battery-dispatch/`).

## Data

| Source | Location | Description |
|--------|----------|-------------|
| Ausgrid Solar Home Data | `Ausgrid_solar_home_data/` | Half-hourly PV and household load |
| AEMO NSW1 prices | `aemo/` | Regional reference price (RRP) |
| Merged dataset | `data/merged_30min_v2.csv` | Aligned 30-min rows (customers 1–5) |
| Day split | `data/day_split.json` | Chronological train / validation / test |

Notebooks: `build_dataset.ipynb`, `data_split.ipynb`.

## Repository layout

```
├── config.yaml                 # Battery, tariff, forecast, training, reward
├── requirements.txt
├── src/
│   ├── environment.py          # Microgrid MDP (5 actions, wholesale export)
│   ├── physics.py              # Efficiencies, cycling, SOC limits
│   ├── discretizer.py          # 540 / 1620 state encoding + foresight bins
│   ├── price_forecast.py       # Realistic climatology+persistence forecasts
│   ├── forecast_info_experiment.py  # Main CA2 experiment runner
│   ├── oracle.py               # Perfect-foresight DP bound
│   ├── rule_baseline.py        # Greedy 5-action + tertile / solar-only rules
│   ├── train.py                # --agent / --privileged training
│   ├── evaluate.py / replay.py / compare.py / visualize.py
│   ├── live_feed.py            # Live AEMO NSW1 price
│   └── agents/                 # Q-Learning, SARSA, Double Q-Learning
├── dashboard/
│   ├── app.py                  # Landing, digital twin, Play vs Agent
│   ├── play_vs_agent.py        # Human vs RL game
│   └── ...
├── deliverables/notebooklm/    # Findings + defence notes
├── Dockerfile/                 # Compose + nginx deploy
└── data/
```

## Quick start (single-agent train)

```bash
python -m src.train --agent q_learning --episodes 10000 --tag current
python -m src.train --agent q_learning --episodes 10000 --privileged --tag privileged
python -m src.train --agent sarsa --episodes 10000 --tag current
python -m src.train --agent double_q_learning --episodes 10000 --tag current
```

Options: `--reward-mode`, `--gamma`, `--epsilon`, `--epsilon-decay`, `--seed`, `--q-init`, `--privileged`, `--tag`.

## Play vs Agent

1. Train at least one Q-Learning model (current and/or privileged).
2. Open the dashboard → **Play vs Agent**.
3. Pick a test day and opponent model.
4. Each step, choose hold / solar charge / discharge / grid-charge / export.
5. You see a **realistic 4-hour price forecast**; the agent uses its trained policy on an identical battery.
6. At day end, compare cost, export revenue, grid-charge cost, net arbitrage, imports/exports, final SOC, reward, and action counts. Inspect Q-values per timestep.

## Configuration (`config.yaml`)

| Section | Key settings |
|---------|----------------|
| `battery` | Capacity, power, SOC bands, **efficiencies**, **cycling cost** |
| `tariff` | Retail margin, FiT (legacy), `export_pricing: wholesale\|fixed`, terminal SOC value |
| `forecast` | `mode`, horizon (8 steps), persistence α, noise |
| `reward` | Weights including export revenue and cycling |
| `training` | α, γ, ε schedule, episodes, seed |

## Metrics

| Metric | Description |
|--------|-------------|
| `total_grid_cost_aud` | Net household cost (imports − export revenue + cycling + terminal SOC) |
| `export_revenue_aud` | Export income under the configured tariff |
| `grid_charge_cost_aud` | Cost of deliberate grid charging |
| `net_arbitrage_profit_aud` | Export revenue − grid-charge cost |
| `pct_of_oracle_savings` | Share of no-battery → oracle gap captured |
| Day win rate | % of test days with lowest cost vs other controllers |

## Design notes

- **Export honesty:** wholesale-exposed export is labelled experimental. Round-trip grid-charge→export loses the retail margin (~0.22 AUD/kWh) plus efficiency/cycling, so profitable foresight is mostly “buy cheap → serve load later,” not “sell high.”
- State uses coarse time-of-day bins (not step index) for a compact tabular Q-table.
- Chronological train/val/test splits; foresight thresholds fitted on **train only**.

## Docker

See [Dockerfile/README.md](Dockerfile/README.md).

```bash
docker compose -f Dockerfile/docker-compose.yml up -d --build
docker compose -f Dockerfile/docker-compose.yml --profile with-nginx up -d --build
```

## License

Research and educational use. Raw Ausgrid and AEMO datasets are subject to their respective terms of use.
