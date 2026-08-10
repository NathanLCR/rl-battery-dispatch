# Trained models (not always in git)

Place CA2 Q-tables here before running Digital Twin or Agent Play.

## Minimum set for demos

Prefer the `forecast_exp` seed-42 tables (540 current / 1620 privileged):

```text
Q_q_learning_*_forecast_exp_current_seed42.npy
Q_q_learning_*_forecast_exp_privileged_seed42.npy
```

The Web Twin and Streamlit Twin auto-prefer filenames containing `forecast_exp` and `seed42`.

## How to regenerate

From repo root (`rl-battery-dispatch/`):

```bash
# Headline framing (true-direction privileged probe)
python -m src.forecast_info_experiment --foresight oracle --agents q_learning \
  --episodes 10000 --seeds 42 43 44 45 46 --tag oracle_priv

# Deployable-style foresight tables (also used by Twin defaults when present)
python -m src.forecast_info_experiment --foresight forecast --agents q_learning \
  --episodes 10000 --seeds 42 43 44 45 46 --tag forecast_exp
```

Results page curated totals come from the oracle-style privileged evaluation
logged under `results/logs/` (see README headline table). Do not mix with older fixed-FiT runs.

## Check

```bash
python scripts/system_test.py
```
