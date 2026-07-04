# GreineGrid_Qagent — Battery Dispatch

Tabular reinforcement learning for home battery dispatch on a solar-connected microgrid. The agent learns when to **hold**, **charge** from surplus solar, or **discharge** to offset load, using real Ausgrid household data and AEMO wholesale prices (Customer 1, 48 steps per day at 30-minute resolution).

## Overview

GreineGrid_Qagent implements a custom MDP (`MicrogridEnv`), discretises continuous observations into 324 tabular states, and trains **Q-Learning**, **SARSA**, and **Double Q-Learning** agents. Policies are evaluated against several baselines and reported with energy KPIs, oracle bounds, and optional multi-seed statistics.

The reward is expressed in monetised household cost (retail import bill, curtailed-solar opportunity cost, and optional battery degradation), aligned with the grid-cost metric used in evaluation.

## Features

- Custom battery environment with solar-only dispatch physics (charge from surplus PV, discharge to meet deficit)
- Discretised state space: SOC, PV, load, price, and time-of-day (324 states, 3 actions)
- Tabular Q-Learning, SARSA, and Double Q-Learning with epsilon-greedy exploration and decaying learning rate
- Monetised reward under configurable retail tariff (`config.yaml`)
- Multiple baselines: tertile rule, greedy self-consumption, no-battery floor, perfect-foresight oracle ceiling
- Evaluation utilities: multi-seed runs, cross-customer transfer, reward ablation, tariff sensitivity
- Streamlit dashboard for day replay and side-by-side policy comparison
- Policy visualisation: greedy policy maps and Q-table heatmaps

## Requirements

- Python 3.10+
- Install dependencies from the repository root:

```bash
pip install -r requirements.txt
```

Run all commands from the repository root so `src` imports resolve correctly.

## Data

| Source | Location | Purpose |
|--------|----------|---------|
| Ausgrid Solar Home Data | `Ausgrid_solar_home_data/` | PV generation and household load |
| AEMO NSW1 prices | `aemo/` | Wholesale electricity prices |
| Merged dataset | `data/merged_30min_v2.csv` | 30-min aligned episodes (customers 1–5) |
| Train/val/test split | `data/day_split.json` | Day-level partition |

Dataset construction notebooks:

- `build_dataset.ipynb` — merge Ausgrid and AEMO into 30-min rows
- `data_split.ipynb` — create the day-level train/validation/test split

## Project structure

```
├── config.yaml              # Battery, tariff, training, and reward settings
├── requirements.txt
├── src/
│   ├── environment.py       # Microgrid MDP
│   ├── physics.py           # Shared battery step dynamics
│   ├── discretizer.py       # State binning (324 states)
│   ├── oracle.py            # No-battery floor and perfect-foresight oracle
│   ├── rule_baseline.py     # Tertile rule and greedy self-consumption
│   ├── train.py             # Training entry point
│   ├── evaluate.py          # Policy evaluation and KPI aggregation
│   ├── compare.py           # Full test-split comparison table
│   ├── run_seeds.py         # Multi-seed training and significance tests
│   ├── cross_customer.py    # Cross-household generalisation
│   ├── ablation_reward.py   # cost_only vs battery_aware ablation
│   ├── tariff_sensitivity.py
│   ├── visualize.py         # Policy map and Q-table plots
│   ├── replay.py            # Step-by-step trace for the dashboard
│   └── agents/
│       ├── q_learning.py
│       ├── sarsa.py
│       └── double_q_learning.py
├── dashboard/
│   ├── app.py               # Streamlit landing page + digital twin
│   └── landing_animation.py # Demo GIF builder (overview page)
├── run_dashboard.ps1        # Launch script (Windows)
├── data/                    # Processed CSV and split JSON
├── aemo/                    # Raw AEMO price files
└── Ausgrid_solar_home_data/
```

Training outputs are written to `results/` (logs, models, plots) and `artifacts/` (discretiser thresholds). These directories are excluded from git; reproduce them by running the training scripts.

## Usage

### Train an agent

```bash
python -m src.train --agent q_learning --episodes 10000 --tag main
python -m src.train --agent sarsa --episodes 10000 --tag main
python -m src.train --agent double_q_learning --episodes 10000 --tag main
```

Common options: `--reward-mode` (`battery_aware` | `cost_only`), `--gamma`, `--epsilon`, `--epsilon-decay`, `--seed`, `--tag`.

Each run saves:

- `results/models/Q_<agent>_<timestamp>_<tag>.npy`
- `results/logs/train_*.csv`, `eval_*.csv`, `test_*.csv`
- `results/plots/learning_curve_*.png`, `eval_curve_*.png`
- `artifacts/bin_thresholds.json`

Double Q-Learning stores two Q-tables in a single `.npy` file (shape `2 × states × actions`).

### Compare policies on the test split

The comparison script evaluates all baselines and any supplied trained models:

```bash
python -m src.compare \
  --q-model results/models/Q_q_learning_<timestamp>_main.npy \
  --sarsa-model results/models/Q_sarsa_<timestamp>_main.npy \
  --output results/logs/comparison_main.csv
```

Policies included:

| Policy | Description |
|--------|-------------|
| `no_battery` | Always hold; upper bound on cost without storage |
| `oracle_perfect_foresight` | Minimum import cost with perfect foresight (DP) |
| `rule_tertile` | Charge on top-PV tertile, discharge on top-load tertile |
| `greedy_self_consumption` | Charge any surplus, discharge any deficit |
| RL agents | Greedy policy from a trained Q-table |

The output CSV includes `cost_saving_vs_greedy_pct`, `pct_of_oracle_savings`, self-consumption rate, self-sufficiency, and evening-peak import.

### Multi-seed evaluation

```bash
python -m src.run_seeds --agents q_learning sarsa --seeds 42 43 44 45 46
python -m src.run_seeds --quick   # 3000 episodes per seed
```

Produces per-seed test costs, a summary with mean ± std and 95% CI half-width, shaded multi-seed learning curves, and a paired t-test between Q-Learning and SARSA (requires `scipy`).

### Cross-household generalisation

Train on Customer 1 and evaluate on Customers 2–5:

```bash
python -m src.cross_customer --train-customer 1 --test-customers 2 3 4 5
python -m src.cross_customer --quick
```

### Reward ablation

Compare `cost_only` and `battery_aware` reward modes:

```bash
python -m src.ablation_reward --agent q_learning
python -m src.ablation_reward --quick
```

### Tariff sensitivity

Retrain under several retail margins and compare test-set cost:

```bash
python -m src.tariff_sensitivity --margins 0.15 0.22 0.35 --episodes 10000
python -m src.tariff_sensitivity --quick
```

Output: `results/logs/tariff_sensitivity_<timestamp>.csv`

### Visualise a trained policy

```bash
python -m src.visualize --model results/models/Q_q_learning_<timestamp>_main.npy --tag main
```

Writes a policy-map PNG and Q-table heatmap to `results/plots/`.

### Run the dashboard

```powershell
.\run_dashboard.ps1
```

Or:

```bash
streamlit run dashboard/app.py
```

Open [http://localhost:8501](http://localhost:8501).

The app opens on an **overview page** with an animated day replay (hold / charge / discharge on a timeline grid), then **Open Digital Twin** for interactive replay. The twin view supports greedy self-consumption, tertile rule, Q-Learning, SARSA, and Double Q-Learning on any test/val/train day. The demo GIF is cached at `artifacts/demo_dispatch.gif` after the first load.

## Configuration

Edit `config.yaml` for:

- **Battery** — capacity, power limits, SOC guard bands
- **Tariff** — retail margin, feed-in rate, degradation cost (AUD/kWh)
- **Reward** — `cost_only` and `battery_aware` weight profiles
- **Training** — learning rate, discount factor, exploration schedule, episode count, seed, alpha decay

The primary customer ID and episode length are under `data:`.

## Evaluation metrics

| Metric | Meaning |
|--------|---------|
| `total_grid_cost_aud` | Sum of retail import bills over the split (primary KPI) |
| `cost_saving_vs_greedy_pct` | Saving relative to greedy self-consumption |
| `pct_of_oracle_savings` | Share of the no-battery → oracle cost gap captured |
| `mean_self_consumption_rate` | Fraction of PV generation used on-site |
| `mean_self_sufficiency` | Fraction of load met without grid import |
| `mean_evening_peak_import_kwh` | Grid import after 17:00 local time |

## Methodology notes

- **Dispatch model:** The battery charges only from surplus solar and discharges only to offset the current step's load deficit. Grid charging and export are not modelled; price is observed but arbitrage is limited to timing of solar self-consumption.
- **State approximation:** Time of day is encoded in four coarse bins rather than the step index, so the formal MDP is a deliberate Markov approximation.
- **Reference baseline:** Greedy self-consumption is the primary comparison policy; the tertile rule is retained as a weaker heuristic for historical comparison.

## Future work

Planned extensions documented for the project report:

1. **Price arbitrage** — Add grid charging and export actions so the agent can buy low and discharge during price peaks.
2. **Finer discretisation** — Increase SOC bins and revise PV binning (daytime-only tertiles) to reduce state aliasing.
3. **Formal MDP specification** — Full transition function and exogenous process description in the written methodology.

## License

Course / research project — see Ausgrid and AEMO data terms for raw dataset usage.
