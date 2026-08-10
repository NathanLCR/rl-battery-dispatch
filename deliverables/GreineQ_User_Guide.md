# GréineQ — User Guide

**Reinforcement learning for solar battery dispatch**

GréineQ is a software digital twin of a residential solar + battery home. You can replay historical days, compare controllers side by side, play against a trained agent, and review the experiment headline results.

**Published app:** [https://greineq-agent.sudocod.com/](https://greineq-agent.sudocod.com/)  
**Brand:** GréineQ (filenames may use ASCII `GreineQ`)

This guide covers the **Web Twin**. Lower **net cost** is always better.

---

## Quick start

| Goal | Go to |
|------|--------|
| See how a day looks step by step | **Digital Twin** → scrub the timeline |
| Compare Greedy vs Q agents on one day | **Digital Twin** → select controllers → **Run comparison** |
| Make decisions yourself | **Agent Play** → **Start game** |
| Read the multi-day experiment headline | **Results** |
| Check live wholesale prices | **Price Monitor** |

**Suggested first path (~10 minutes):** Overview → Results → Digital Twin (`2012-07-14`) → Agent Play (a few steps vs Current Q).

---

## 1. Open the app

### Online

Open [https://greineq-agent.sudocod.com/](https://greineq-agent.sudocod.com/).

### Local Web Twin

```powershell
pip install -r requirements.txt
.\run_web.ps1
```

Then open **http://localhost:8080**.

### Docker

```bash
docker compose -f Dockerfile/docker-compose.yml up -d --build
```

You need `data/` and trained models under `results/models/` (540-state Current Q and 1620-state Privileged Q `forecast_exp` tables).

---

## 2. Landing page & navigation

The app opens on **Overview**: logo, short explanation, and a day-replay animation.

| Nav item | Purpose |
|----------|---------|
| **Overview** | Landing / brand entry |
| **Digital Twin** | Same-day controller comparison + step replay |
| **Price Monitor** | Live AEMO wholesale view |
| **Agent Play** | You vs Agent vs Greedy |
| **Results** | CA2 aggregate findings |

From Overview, use **Digital Twin →** or **Play vs Agent** to enter the main views. Top navigation appears after you leave the landing page.

**Note:** The landing animation is a greedy 5-action preview, not a live trained Q-agent rollout.

---

## 3. What the system controls

Each half-hour step, a controller chooses **one** of five actions:

| Action | Meaning |
|--------|---------|
| **Hold** | Do nothing with the battery |
| **Charge / Solar charge** | Store surplus solar in the battery |
| **Discharge** | Serve household demand from the battery |
| **Grid-charge** | Buy from the grid to charge the battery (arbitrage) |
| **Export** | Sell battery energy to the grid (arbitrage) |

A full day has **48** half-hour steps (00:00–23:30). Controllers minimise adjusted electricity cost under an experimental wholesale-exposed export setup.

---

## 4. Digital Twin

Use Digital Twin to inspect one historical day and compare controllers fairly on the **same** solar, demand, and prices.

### 4.1 Simulation setup (left sidebar)

1. **Day split** — prefer **Test days (held out)** for demos and evaluation.
2. **Simulation day** — pick a date (demo favourite: **2012-07-14**).
3. **Controllers** — tick the policies to compare. Defaults:
   - **Greedy (5-action)** — strong rule baseline (self-use + price-timed buy/sell)
   - **Current Q** — tabular Q-Learning using current state + price only
   - **Privileged Q — true 4h signal** — Q-Learning plus a true next-4h three-bin price direction (information probe)
4. Click **Run comparison**.
   - Results load automatically the first time.
   - After you change settings, click again (watch for the “settings changed” prompt).
5. Optional: open **Experiment settings** for reward mode and extra baselines (Solar-only greedy, Tertile rule, SARSA, Double Q).

After a run, the sidebar **System flow** diagram shows energy moving between Q-agent / solar / battery / home for the preview policy.

### 4.2 Reading the results (main panel)

1. **Winning agent banner** — lowest net cost wins (example: *Greedy · saved AUD X vs no-battery*).
2. **KPI cards** (typical):
   - **Net cost** — day electricity cost after exports and battery effects (**lower is better**)
   - **No-battery (baseline)** — cost with no storage
   - **Oracle bound** — theoretical best with perfect foresight (not deployable)
   - **Final SOC** — end-of-day battery % (condition, **not** the win criterion)
3. **Controller comparison table** — Net cost, Savings % vs no-battery, Final SOC.
4. **Detailed metrics** expander — Cost / Energy / Battery tabs.
5. **Charts** tabs:
   - **Energy** — solar generation vs household demand
   - **Price & SOC** — prices and battery state of charge
   - **Controller actions** — which action each policy took over the day
   - **Step cost** — cost progression through the day
6. **Timestep inspector** — use **Prev / Next** or the slider (steps 1–48) to scrub the day. Charts follow the selected step.
7. **Diagnostics & download** — step log and JSON export of traces.

### 4.3 Simulation replay view

On some layouts you will also see a full-screen style **Simulation replay**:

- Large **Q-Agent decision** (e.g. *Charge battery*)
- Live KPIs: Timestep, Time of day, Battery SOC, Grid import cost, Step score
- Icons for solar, demand, battery, and estimated grid price
- **Daily dispatch timeline** — 48 coloured cells (one per half-hour)

**Timeline colours (typical):**

| Colour | Action |
|--------|--------|
| Grey | Hold |
| Green | Charge battery |
| Orange | Discharge battery |
| Blue | Grid-charge (arbitrage) |
| Purple | Export to grid (arbitrage) |

---

## 5. Agent Play (Play vs Agent)

Play is a human-in-the-loop demo: **you**, the **RL opponent**, and **Greedy** run identical twins for 48 steps. Lowest adjusted cost wins.

### 5.1 Setup

1. Open **Agent Play**.
2. Choose a **Test day** (held-out test split only).
3. Choose **Opponent:** Current Q or Privileged Q — true 4h signal.
4. Choose the **trained model**.
5. Click **Start game**.

### 5.2 Information asymmetry (important)

- **You always** see a realistic 4-hour price forecast.
- **Current Q** uses current state only.
- **Privileged Q** may use a **true** four-hour direction feature.

Treat Play as an oversight / teaching demo — not a scientifically fair equal-information contest when the opponent is Privileged.

### 5.3 During the game

1. Read the status cards: **Battery**, **Solar / demand**, **Buy price**, **Sell price**. Watch for surplus/deficit badges.
2. Under **Choose your action**, pick one of:
   - **1 · Hold**
   - **2 · Solar charge**
   - **3 · Discharge**
   - **4 · Grid charge**
   - **5 · Export**
3. Unavailable actions explain why (e.g. no surplus solar, battery at min/max SOC).
4. Each click advances one half-hour. The agent and Greedy advance in lockstep.
5. Compare feedback: *You chose…* vs *Agent chose…* (with a short reason).
6. Scoreboard tracks **You / Agent / Greedy** — cost, SOC, last action.
7. Tabs:
   - **Forecast & energy** — next-4h price summary and context
   - **Agent decision** — Q-values / agent rationale
8. Use **Pause and inspect**, or **Quit to setup** to leave the day.

### 5.4 End of day

You get a winner summary plus cumulative cost and SOC charts for You / Agent / Greedy. Restart or pick another day to try again.

---

## 6. Experiment Results

**Results** is the evidence page for the CA2 headline — aggregate evaluation over **53 held-out days** and **five training seeds**. It is not the same as a single Digital Twin day.

### What to look at

1. Green finding banner (e.g. Greedy remained the best deployable controller).
2. Four KPIs: Best deployable · Savings vs no battery · Gap to oracle · Privileged vs Current.
3. **Aggregate net cost** bar chart — **lower is better**.
4. **What did we learn?** bullets (includes the coarse-foresight caveat).
5. Results table — mean ± std for Q agents.
6. Expand **Experiment setup** and optionally **Methodology notes**.

### Headline numbers (wholesale-export setup)

| Controller | Approx. mean net cost (AUD) |
|------------|-----------------------------|
| No-battery reference | 160.75 |
| Greedy (best deployable) | 90.39 (~43.8% savings) |
| Current Q | 124.23 ± 11.65 |
| Privileged Q (true 4h 3-bin) | 139.68 ± 5.55 |

**Takeaway:** Greedy remained the strongest deployable controller. The privileged coarse foresight feature did **not** help Q-Learning on average under this setup.

Do **not** mix these totals with older fixed-FiT experiment numbers.

---

## 7. Price Monitor

**Price Monitor** shows live wholesale / estimated retail from AEMO NSW1.

- PV and load shown here are **historical typicals for the current hour**, not a live household meter.
- If the AEMO feed is down, Twin and Play still work on historical data.
- Any “Current Q recommendation” here is illustrative only.

---

## 8. Controllers at a glance

| Name | Role |
|------|------|
| **No-battery** | Reference cost with no storage |
| **Oracle / perfect foresight** | Lower-cost information bound (not deployable) |
| **Greedy (5-action)** | Strong rule baseline; often the Twin / Results winner |
| **Current Q** | Q-Learning on current discretised state + price |
| **Privileged Q — true 4h signal** | Current features + true next-4h direction (probe) |
| Solar-only greedy / Tertile / SARSA / Double Q | Optional extras in Experiment settings |

---

## 9. Glossary

| Term | Meaning |
|------|---------|
| **Net cost (AUD)** | Day electricity cost after exports, grid-charging, and battery effects. Lower is better. |
| **Savings** | Improvement vs no-battery on that day (or aggregate). |
| **SOC** | State of charge — battery energy as a percentage. |
| **Held-out / test days** | Days not used for training; prefer these for demos. |
| **Current Q** | Agent that only sees the present state. |
| **Privileged Q** | Agent that also sees a true next-4h price-direction feature. |
| **Oracle** | Perfect-foresight bound for context, not a deployable controller. |
| **Wholesale export** | Experimental tariff framing used in the CA2 headline (not a typical household FiT). |

---

## 10. Troubleshooting

| Issue | What to try |
|-------|-------------|
| Settings changed but results look old | Click **Run comparison** again |
| Play actions greyed out | Check surplus/deficit and SOC limits — the UI explains why |
| Price Monitor empty / error | Feed may be down; Twin/Play still work historically |
| Missing models / empty controllers | Ensure `results/models/` has the expected 540 / 1620 `forecast_exp` tables |
| Day has fewer than 48 steps | Pick another day from the dropdown |

---

## 11. Important caveats

1. **Lower cost is better** — training reward is negative cost.
2. Prefer **Test / held-out** days for demos and fair evaluation.
3. **Play ≠ equal-information science contest** when the opponent is Privileged Q.
4. **Final SOC is not the win criterion** — net cost is.
5. GréineQ is a **research / demo twin**, not a physical battery controller.
6. Landing animation ≠ trained agent.
7. Live Price Monitor ≠ historical Twin simulation.
8. Do not mix CA2 wholesale-export totals with older fixed-FiT numbers.

---

## 12. Ethics & intended use

GréineQ is for teaching, research, and demonstration of battery dispatch policies. It does not replace a licensed energy product, installer advice, or a real home energy management system. Forecasts and live prices are illustrative; decisions in Play are for learning, not operational control.
