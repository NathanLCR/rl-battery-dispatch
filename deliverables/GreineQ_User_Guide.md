# GréineQ — User Guide

**Word document:** [`GreineQ_User_Guide.docx`](GreineQ_User_Guide.docx)  
Regenerate: `python scripts/build_user_guide_docx.py`

Operate and explore the residential battery digital twin: compare controllers on historical days, play against a trained agent, check live wholesale prices, and review the CA2 experiment headline.

**Published app:** [https://greineq-agent.sudocod.com/](https://greineq-agent.sudocod.com/)  
**Brand:** GréineQ (filenames may use ASCII `GreineQ`)

---

## 1. Open the dashboard

### Online

Open the published URL above. Production may lag the latest `ca2_agent` branch — use a local run for the newest Twin / Play / Results UI.

### Local (recommended for demos)

From the repository root `rl-battery-dispatch/`:

```powershell
pip install -r requirements.txt
.\run_dashboard.ps1
```

Or:

```powershell
python -m streamlit run dashboard/app.py --server.port 8501
```

Then open **http://localhost:8501**.

Smoke check (optional): `python scripts/system_test.py`.

---

## 2. Navigation

Use the top bar:

| View | What it does |
|------|----------------|
| **Digital Twin** | Same-day replay of several controllers; KPIs, charts, timestep inspector |
| **Price Monitor** | Live AEMO NSW1 price + typical PV/load (informational) |
| **Agent Play** | You vs RL vs Greedy for 48 half-hour steps |
| **Results** | Curated CA2 experiment chart and interpretation |
| **Overview** | Landing page and heuristic animation preview |

The Overview animation is a **heuristic preview**, not the trained Q-Learning agent.

---

## 3. Digital Twin

Historical simulation only — one calendar day, 48 half-hour intervals. Controllers see the same PV, load, and prices for that day.

### Sidebar — Simulation setup

1. **Day split** — Test (default), Validation, or Train.
2. **Simulation day** — Pick a date from that split. Demo suggestion: `2012-07-14`.

### Sidebar — Controllers

Toggle which policies to compare (defaults are usually on):

| Controller | Meaning |
|------------|---------|
| **Greedy (5-action)** | Self-use surplus solar; price-timed grid-charge / export |
| **Current Q** | Tabular Q-Learning using current state + price only |
| **Privileged Q — true 4h signal** | Q-Learning plus the **true** next-four-hour three-bin price direction (information probe, not a realistic forecast) |

### Run comparison

- First open **auto-runs** once so the page is not blank.
- After you change day, split, or controllers, click **Run comparison** again.
- If settings changed but you have not re-run, a banner asks you to run again.

### Experiment settings (collapsed)

Optional extras:

- Reward function: battery-aware (default) vs cost-only  
- Extra baselines: solar-only greedy, tertile rule  
- Additional RL: SARSA, Double Q-Learning  
- Model pickers when those agents are enabled  
- Q-value diagnostics in the download section  

Trained weights live under `results/models/`. If none are present, RL checkboxes will error until you train.

### Main results layout

1. **Context bar** — Mode, day, preview policy  
2. **Winning agent strip** + four KPIs (net cost, savings vs no-battery, gap to best RL, final SOC)  
3. **Why did X win?** — Short explanation + perfect-foresight cost bound  
4. **Controller comparison** — Net cost, savings %, final SOC bars (lower cost is better)  
5. **Detailed metrics** — Cost / Energy / Battery tabs  
6. **Charts** — Cost, energy, and battery trajectories (hoverable when Plotly is installed)  
7. **Timestep inspector** — Step through 1–48; see each controller’s action, SOC, and step cost  
8. **Diagnostics & download** — Full step log; optional Q-values; JSON download  

**Live prices are not on this page** — use **Price Monitor**.

---

## 4. Live Price Monitor

Separate from the historical Twin.

| Field | Source |
|-------|--------|
| Wholesale / retail estimate | Live AEMO NSW1 |
| Typical PV / load | Historical medians for the current hour — **not** a live household meter |

If the feed is down, you will see a notice; Digital Twin still works offline on merged historical data.

An optional **Current Q recommendation** uses the live price with illustrative SOC and typical PV/load — for illustration only, not a metered home.

---

## 5. Agent Play (Play vs Agent)

Interactive oversight demo: you operate one battery; **Current Q** (or Privileged Q) and **Greedy** run identical twins in parallel. Lowest adjusted electricity cost wins.

### Game setup

1. Choose a **test day**.  
2. Choose **opponent**: Current Q or Privileged Q — true 4h signal.  
3. Choose a **trained model**.  
4. Click **Start game**.

**Information asymmetry (important):**

- **You** always see a **realistic** 4-hour price forecast.  
- **Privileged Q** may use a **true** four-hour direction feature.  
- This is an **oversight / teaching demo**, not a scientifically fair equal-information contest.

### During the game

- Four state cards: price, SOC, solar, load.  
- **Choose your action** (or keys **1–5**):

| # | Action | Intent |
|---|--------|--------|
| 1 | Hold | No battery movement |
| 2 | Solar charge | Store surplus solar |
| 3 | Discharge | Supply household demand |
| 4 | Grid charge | Buy from the grid for later |
| 5 | Export | Sell stored electricity |

Unavailable actions show a disable reason (e.g. empty battery, no surplus solar).

- Scoreboard: **You / RL / Greedy** running costs.  
- Tabs: forecast view and agent decision insight.  
- **Pause** / **Quit game** (or sidebar **Quit to setup**).

### End of day

Summary of who won, optional replay of decisions, try another day, and download of the match data.

---

## 6. Experiment Results

Read-only CA2 headline for the wholesale-export, true-direction privileged probe:

- KPI strip and bar chart (lower net cost is better)  
- Compact results table (mean ± std for Q agents across five seeds)  
- Collapsed **Experiment setup** and optional per-seed CSV  

**Takeaway under this setup:** Greedy remained the best evaluated deployable controller; the three-bin true direction feature did **not** improve Q-Learning on average.

Do not mix these totals with older fixed-FiT experiment numbers.

---

## 7. Controllers & metrics (quick glossary)

### Controllers

| Name | Role |
|------|------|
| No-battery reference | Cost if there were no battery |
| Perfect foresight / oracle | Information lower-cost bound |
| Greedy (5-action) | Strong rule baseline (often best deployable) |
| Current Q | Learns from current discretised state only |
| Privileged Q | Same + true 4h three-bin direction (headline probe) |

### Key metrics

| Metric | Meaning |
|--------|---------|
| Net cost (AUD) | Imports − export revenue + cycling / terminal effects (lower is better) |
| Savings | Improvement vs no-battery reference |
| Export revenue | Income under the configured export tariff |
| Grid-charge cost | Cost of deliberate grid charging |
| Final SOC | End-of-day battery level (condition, not the win criterion) |
| Throughput | How much energy moved through the battery |

**Reward** in training = negative adjusted cost (agents maximise reward by minimising cost).

### Tariff note

Export uses an **experimental wholesale-exposed** price (AEMO AUD/MWh ÷ 1000), not a typical Australian household FiT. Round-trip sell is hard; valuable foresight is mostly “buy cheap → serve load later.”

---

## 8. Suggested demo path (~10 minutes)

1. **Overview** — brand and what the twin is.  
2. **Results** — headline chart and “greedy still wins.”  
3. **Digital Twin** — day `2012-07-14`, default controllers, **Run comparison**; open winner explanation; step the inspector through a peak-price window.  
4. **Agent Play** — short stretch of decisions vs Current Q (call out forecast vs privileged if you switch opponents).  
5. **Price Monitor** — live vs historical twin distinction (optional).  

Keep verified models under `results/models/` for the demo; avoid mid-demo retrain.

---

## 9. Troubleshooting

| Issue | What to do |
|-------|------------|
| Blank Twin / stale numbers | Click **Run comparison** after changing settings |
| “No trained models” | Train or copy `.npy` models into `results/models/` |
| Incomplete day warning | Choose another day with full 48 intervals |
| Live feed unavailable | Expected on some networks; Twin still works |
| Charts missing | Ensure `plotly` is installed (`requirements.txt`) |
| Port in use | Change `--server.port` or stop the other Streamlit process |

---

## 10. Scope & ethics (short)

- Software twin and research demo — **not** a physical battery controller.  
- Live Price Monitor mixes live wholesale with **typical** PV/load.  
- Play vs Privileged Q is an **oversight** framing, not a fair RL contest.  
- Wholesale export tariff is experimental and disclosed in the write-up.

For experiment design and findings, see `deliverables/notebooklm/CA2_Forecast_Info_Experiment_Findings.md` and the presentation pack under `deliverables/presentation/`.
