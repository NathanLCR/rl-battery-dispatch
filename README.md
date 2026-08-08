# GréineQ

Tabular reinforcement learning for residential battery dispatch on a solar-connected microgrid. Agents learn when to **hold**, **solar-charge**, **discharge**, **grid-charge**, or **export**, using Ausgrid half-hourly household data and AEMO NSW1 wholesale prices (Customer 1; 48 steps per day).

**Brand spelling:** GréineQ (filenames may use ASCII `GreineQ`).

## Live dashboard

**Published instance:** [https://greineq-agent.sudocod.com/](https://greineq-agent.sudocod.com/)  
*(Production may lag `ca2_agent` — run locally for the latest Twin / Play / Results UI.)*

| View | Description |
|------|-------------|
| Overview | Landing page with heuristic replay preview (not the trained Q agent) |
| **Digital Twin** | Same-day controller comparison, KPIs, charts, timestep inspector |
| **Live Price Monitor** | Live AEMO NSW1 price + typical PV/load (informational; not historical Twin) |
| **Play vs Agent** | Human vs RL vs Greedy on identical twins — oversight demo |
| **Experiment Results** | Curated CA2 headline chart, KPIs, and interpretation |

```powershell
cd rl-battery-dispatch
.\run_dashboard.ps1
# or: python -m streamlit run dashboard/app.py --server.port 8501
```

Open **http://localhost:8501**. Smoke check: `python scripts/system_test.py`.

## CA2 contribution: forecast-information experiment

**Question:** Does a short **three-bin price-direction** foresight feature help tabular RL beat a strong greedy baseline under a fair, arbitrage-capable MDP?

### Controllers compared

| Controller | Information | Role |
|------------|-------------|------|
| No-battery reference | — | Cost reference (not an “upper bound”) |
| Perfect foresight | Full future prices | Lower-cost information bound |
| Greedy (5-action) | Current state + price | Best evaluated **deployable** controller |
| Current Q | Current state + price | Tabular Q-Learning |
| Privileged Q | Current + **true** 4h direction (3 bins) | Information probe on that feature |

Primary algorithm: **Q-Learning** (ε-greedy train, argmax eval). SARSA and Double Q-Learning are supported in the same pipeline and Twin “Experiment settings.”

### Modelling (wholesale-exposed tariff)

Experimental wholesale-exposed export — **not** a normal Australian household FiT:

```text
export revenue = exported_kWh × wholesale AUD/kWh
wholesale AUD/kWh = AEMO AUD/MWh ÷ 1000
```

Also: charge/discharge efficiency (0.95), cycling cost, SOC/power limits, no simultaneous charge+export, and terminal SOC valuation.  
**Reward** = negative adjusted electricity cost (so Q-Learning maximises reward by minimising cost).

### Privileged foresight signal

```text
future_signal = max(price over next 8 half-hours) − current price
→ FALL_OR_FLAT | MODERATE_RISE | STRONG_RISE   (train-only tertiles)
```

| Mode (`config.yaml` → `forecast.mode`) | Meaning |
|----------------------------------------|---------|
| `oracle` | **True** future direction (headline CA2 probe) |
| `forecast` | Realistic climatology + persistence (available in deployment; **not** the source of headline AUD totals) |

State sizes: Current **540** · Privileged **1620** (540 × 3 foresight bins).

### Headline results (true-direction privileged Q)

Wholesale-export · 53 held-out test days · Q-Learning 10k episodes × seeds 42–46:

| Controller | Net cost (AUD) |
|------------|----------------|
| Perfect foresight bound | 74.92 |
| **Greedy (5-action)** | **90.39** |
| Current Q (mean ± std) | 124.23 ± 11.65 |
| Privileged Q — true 4h direction | 139.68 ± 5.55 |
| No-battery reference | 160.75 |

**Finding:** Greedy remained the best evaluated deployable controller. A coarse three-bin true direction feature alone did **not** improve Q-Learning under this setup (privileged cost *more* than Current Q on average). The hypothesis was **not supported** under this experimental setup.

Do **not** mix these totals with older fixed-FiT CA2 runs.

### Run the experiment

```bash
# Realistic forecast mode (deployable-style signal)
python -m src.forecast_info_experiment --foresight forecast --agents q_learning \
  --episodes 10000 --seeds 42 43 44 45 46 --tag forecast_exp

# True-direction (oracle) privileged probe — matches headline framing
python -m src.forecast_info_experiment --foresight oracle --agents q_learning \
  --episodes 10000 --seeds 42 43 44 45 46 --tag oracle_priv

# Multi-agent + smoke
python -m src.forecast_info_experiment --foresight forecast \
  --agents q_learning sarsa double_q_learning \
  --episodes 10000 --seeds 42 43 44 45 46 --tag multi_agent
python -m src.forecast_info_experiment --quick --foresight forecast --tag smoke
```

Outputs: `results/logs/forecast_exp_*.csv`, plots under `results/plots/`, models under `results/models/`.  
Write-up: `deliverables/notebooklm/CA2_Forecast_Info_Experiment_Findings.md`.

## Dashboard notes (demo)

- **Digital Twin:** Auto-runs once on first open; after settings change, click **Run comparison** again.
- **Play vs Agent:** You receive a **realistic** 4h forecast; Privileged opponents may use a **true** direction signal — framed as an **interactive oversight demo**, not a scientifically fair contest.
- Suggested Twin/demo day: `2012-07-14` with forecast_exp models (seed 42) under `results/models/`.
- Landing animation = heuristic preview, not the trained Q-Learning agent.

### Presentation pack

```
deliverables/presentation/
  GreineQ_CA2_Presentation.pptx
  GreineQ_CA2_Speaker_Notes.docx
  GreineQ_CA2_Live_Demo_Plan.docx
```

Regenerate: `python scripts/build_ca2_presentation.py`.

## Earlier CA2 work (grid-charge / export MDP)

CA1 was solar-only (3 actions). CA2 first extended the MDP to 5 actions and showed that allowing arbitrage lowers the *oracle* ceiling, while reactive heuristics / coarse tabular RL can still underperform greedy self-use. See `deliverables/notebooklm/CA2_Arbitrage_Extension_Findings.md`.

## Requirements

- Python 3.10+

```bash
pip install -r requirements.txt
```

Includes Streamlit, matplotlib, plotly, pandas, numpy, scipy, PyYAML, Pillow.  
Run all commands from the repository root (`rl-battery-dispatch/`).

## Data

| Source | Location | Description |
|--------|----------|-------------|
| Ausgrid Solar Home Data | `Ausgrid_solar_home_data/` | Half-hourly PV and household load |
| AEMO NSW1 prices | `aemo/` | Regional reference price (RRP) |
| Merged dataset | `data/merged_30min_v2.csv` | Aligned 30-min rows (customers 1–5) |
| Day split | `data/day_split.json` | Chronological train / validation / test |

## Repository layout

```
├── config.yaml
├── requirements.txt
├── src/
│   ├── environment.py              # Microgrid MDP (5 actions, wholesale export)
│   ├── physics.py                  # Efficiencies, cycling, SOC limits
│   ├── discretizer.py              # 540 / 1620 states + three-bin foresight
│   ├── price_forecast.py           # Climatology + persistence forecasts
│   ├── forecast_info_experiment.py # Main CA2 experiment runner
│   ├── oracle.py / rule_baseline.py / train.py / replay.py
│   ├── live_feed.py                # Live AEMO NSW1
│   └── agents/                     # Q-Learning, SARSA, Double Q-Learning
├── dashboard/
│   ├── app.py                      # Routing + Digital Twin
│   ├── twin_panels.py              # Twin KPIs, charts, inspector, live panel
│   ├── play_vs_agent.py            # Play vs Agent game
│   ├── landing_page.py / theme.py / dispatch_widget.py
├── scripts/
│   ├── system_test.py
│   └── build_ca2_presentation.py
├── deliverables/
│   ├── presentation/               # PPTX + speaker notes + demo plan
│   └── notebooklm/                 # Findings + defence notes
├── Dockerfile/
└── data/
```

## Quick start (single-agent train)

```bash
python -m src.train --agent q_learning --episodes 10000 --tag current
python -m src.train --agent q_learning --episodes 10000 --privileged --tag privileged
python -m src.train --agent sarsa --episodes 10000 --tag current
python -m src.train --agent double_q_learning --episodes 10000 --tag current
```

## Configuration (`config.yaml`)

| Section | Key settings |
|---------|----------------|
| `battery` | Capacity, power, SOC bands, efficiencies, cycling cost |
| `tariff` | Retail margin, `export_pricing: wholesale\|fixed`, terminal SOC value |
| `forecast` | `mode` (`oracle` / `forecast`), horizon (8 steps), persistence α, noise |
| `reward` | Weights including export revenue and cycling |
| `training` | α, γ, ε schedule, episodes, seed |

## Metrics

| Metric | Description |
|--------|-------------|
| `grid_cost_aud` / `total_grid_cost_aud` | Net household cost (imports − export + cycling + terminal SOC) |
| `export_revenue_aud` | Export income under the configured tariff |
| `grid_charge_cost_aud` | Cost of deliberate grid charging |
| `net_arbitrage_profit_aud` | Arbitrage balance (export revenue − grid-charge cost) |
| Day win rate | % of test days with lowest cost vs other controllers |

## Design notes

- **Export honesty:** wholesale-exposed export is experimental. Round-trip sell is hard (retail margin ≈ 0.22 AUD/kWh + efficiency/cycling); profitable foresight is mostly “buy cheap → serve load later.”
- **Ethics / deployment:** experimental tariff and partial live inputs are disclosed; Live Price Monitor is informational; Play is an oversight demo; this is a software twin, not a physical battery.
- Chronological train/val/test; foresight thresholds fitted on **train only**.

## Docker

See [Dockerfile/README.md](Dockerfile/README.md).

```bash
docker compose -f Dockerfile/docker-compose.yml up -d --build
```

## License

Research and educational use. Raw Ausgrid and AEMO datasets are subject to their respective terms of use.
