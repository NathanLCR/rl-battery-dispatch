# GréineQ — User Guide (Web Twin)

**Word document:** [`GreineQ_User_Guide.docx`](GreineQ_User_Guide.docx)  
Regenerate: `python scripts/build_user_guide_docx.py`

Operate and explore the residential battery digital twin: compare controllers on historical days, play against a trained agent, check live wholesale prices, and review the CA2 experiment headline.

**Published app:** [https://greineq-agent.sudocod.com/](https://greineq-agent.sudocod.com/)  
**Brand:** GréineQ (filenames may use ASCII `GreineQ`)

This guide covers the **FastAPI Web Twin** (Docker / published site). Streamlit remains available for local research use only.

---

## 1. Open the app

### Online

Open the published URL above.

### Local Web Twin

```powershell
pip install -r requirements.txt
.\run_web.ps1
```

Open **http://localhost:8080**.

### Docker (server)

```bash
docker compose -f Dockerfile/docker-compose.yml up -d --build
# health: http://localhost:8501/api/health
```

Container port **8000** → host default **8501** (same public URL as before). Need `data/` + `results/models/` (540/1620 `forecast_exp` tables).

---

## 2. Landing page & navigation

Opens on **Overview**: logo, CTAs, Q-Agent hero replay, explain strip, action badges. Top nav appears after entering Twin / Play / Price / Results.

| View | What it does |
|------|----------------|
| **Overview** | Landing + control-centre animation |
| **Digital Twin** | Same-day controller comparison |
| **Price Monitor** | Live AEMO + typical PV/load |
| **Agent Play** | You vs Agent vs Greedy |
| **Results** | CA2 headline + What did we learn? |

Landing animation = greedy 5-action heuristic preview (not a live trained-agent roll-out).

---

## 3. Digital Twin

Historical day, 48 half-hours. Sidebar: day split, day, controllers, **Run comparison**, Experiment settings, **System flow** animation after a run.

Main: winner + KPIs, comparison table, detailed metrics, chart tabs (**Energy / Price & SOC / Controller actions / Step cost**), timestep scrubber, JSON download.

Experiment interpretation is on **Results**, not Twin. Live prices → **Price Monitor**.

---

## 4. Live Price Monitor

Live wholesale/retail from AEMO NSW1; PV/load are historical typicals for the hour. Twin still works if the feed is down.

---

## 5. Agent Play

Setup: test day, opponent (Current / Privileged Q), model → **Start game**.

You always see a realistic 4h forecast; Privileged may use a true direction signal (oversight demo).

Actions 1–5: Hold, Solar charge, Discharge, Grid charge, Export. Scoreboard You / Agent / Greedy. Tabs: Forecast & energy + Agent decision (Q-values). End-of-day cost/SOC charts.

---

## 6. Experiment Results

Finding, KPIs, chart, **What did we learn?**, results table, Experiment setup + Methodology.

**Takeaway:** Greedy remained best deployable; three-bin true direction did not improve Q-Learning on average. Do not mix with older fixed-FiT numbers.

---

## 7–10.

See the Word document for glossary, demo path (~10 min), troubleshooting, and ethics notes.
