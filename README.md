# GreineGrid_Qagent — Battery Dispatch

Tabular reinforcement learning for home battery dispatch on a solar + grid microgrid. The agent learns when to **hold**, **charge** from surplus solar, or **discharge** to meet load, using real Ausgrid solar/load data and AEMO wholesale prices.

## Features

- Custom MDP environment (`MicrogridEnv`) with 48-step daily episodes (30-minute intervals)
- Tabular **Q-Learning** and **SARSA** agents with discretized state space
- Rule-based baseline for comparison
- Config-driven hyperparameters and reward shaping (`config.yaml`)
- Streamlit dashboard for episode replay and policy comparison

## Requirements

- Python 3.10+
- Dependencies in `requirements.txt`:

```bash
pip install -r requirements.txt
```

Run commands from the repository root so `src` imports resolve correctly.

## Data

| Source | Location | Purpose |
|--------|----------|---------|
| Ausgrid Solar Home Data | `Ausgrid_solar_home_data/` | PV generation and household load |
| AEMO NSW1 prices | `aemo/` | Wholesale electricity prices |
| Merged dataset | `data/merged_30min_v2.csv` | 30-min aligned episodes |
| Train/val/test split | `data/day_split.json` | Day-level split |

Notebooks for building the dataset:

- `build_dataset.ipynb` — merge Ausgrid + AEMO into 30-min rows
- `data_split.ipynb` — create day-level train/val/test split

## Project structure

```
├── config.yaml           # Battery, training, and reward settings
├── src/
│   ├── environment.py    # Microgrid MDP
│   ├── discretizer.py    # State binning
│   ├── train.py          # Training entry point
│   ├── evaluate.py       # Policy evaluation
│   ├── compare.py        # Rule vs RL comparison
│   ├── visualize.py      # Policy map and Q-table plots
│   ├── tariff_sensitivity.py  # Retail margin sweep
│   ├── replay.py         # Episode trace for dashboard
│   ├── rule_baseline.py  # Heuristic controller
│   └── agents/           # Q-Learning and SARSA
├── dashboard/app.py      # Streamlit digital twin
├── data/                 # Processed CSV + split JSON
├── aemo/                 # Raw AEMO price files
└── Ausgrid_solar_home_data/
```

Generated outputs (ignored by git) go to `results/` (logs, models, plots) and `artifacts/` (discretizer thresholds).

## Usage

### Train an agent

```bash
python -m src.train --agent q_learning
python -m src.train --agent sarsa --episodes 5000 --tag g99 --gamma 0.99
```

Options: `--reward-mode` (`battery_aware` | `cost_only`), `--gamma`, `--epsilon`, `--epsilon-decay`, `--tag`.

Saves:

- `results/models/Q_<agent>_<timestamp>.npy`
- `results/logs/train_*.csv` and `test_*.csv`
- `results/plots/learning_curve_*.png` and `eval_curve_*.png`
- `artifacts/bin_thresholds.json`

### Compare policies on the test split

```bash
python -m src.compare \
  --q-model results/models/Q_q_learning_20260704_115627_main.npy \
  --sarsa-model results/models/Q_sarsa_20260704_115834_main.npy \
  --output results/logs/comparison_main.csv
```

Omit `--output` to auto-save a timestamped CSV under `results/logs/`. The table includes `cost_saving_vs_rule_pct` for each RL policy.

### Tariff sensitivity

Retrain under several retail margins and compare test-set cost vs the rule baseline:

```bash
python -m src.tariff_sensitivity --margins 0.15 0.22 0.35 --episodes 10000
python -m src.tariff_sensitivity --quick   # 3000 episodes, faster
```

Output: `results/logs/tariff_sensitivity_<timestamp>.csv`

### Visualise a trained policy

```bash
python -m src.visualize --model results/models/Q_sarsa_20260704_115834_main.npy --tag sarsa_main
```

Writes policy-map and Q-table heatmap PNGs to `results/plots/`.

### Run the dashboard

```powershell
.\run_dashboard.ps1
```

Or:

```bash
streamlit run dashboard/app.py
```

Open [http://localhost:8501](http://localhost:8501) to replay episodes and compare rule-based vs RL policies.

## Configuration

Edit `config.yaml` for battery limits, learning rate, discount factor, exploration schedule, tariff rates, and reward weights. The primary customer ID and episode length are under `data:`.

## License

Course / research project — see Ausgrid and AEMO data terms for raw dataset usage.
