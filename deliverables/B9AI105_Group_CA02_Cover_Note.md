# Dublin Business School
# B9AI105 Reinforcement Learning
# Master of Science in Artificial Intelligence - Group A
# Lecturer Name: Dr. Oleksandr Bezrukavyi
#
# CA02 – Group Assessment
# GréineQ — Reinforcement Learning for Solar Battery Dispatch
#
# Group Members:
# Nathan Lucio - 20082900
# Nadeesha Jayasuriya - 20093736
# Emmanuel Addoh - 10592825
# Bahadir Demir - 20098301
#
# Submission Date: 11th August 2026

---

# 1. Repository, deployed system, and presentation

| Item | Link |
|------|------|
| **GitHub** | https://github.com/NathanLCR/rl-battery-dispatch |
| **Deployed Web Twin** | https://greineq-agent.sudocod.com/ |
| **Final presentation (PPTX)** | `deliverables/presentation/GreineQ_CA2_Presentation.pptx` |
| **Presentation + recording (Google Drive)** | https://drive.google.com/drive/folders/12vc-RRwxKix4hWDKO1u6VhppgT2KjyNz?usp=sharing |
| **User guide** | `deliverables/GreineQ_User_Guide.md` |

Local run: from `rl-battery-dispatch/` use `.\run_web.ps1` → http://localhost:8080 (or Docker — see `Dockerfile/README.md`). Place trained models in `results/models/`.

---

# 2. Relationship to CA01

This CA02 submission is a **direct extension** of our CA01 group project (GréineQ).

## CA01 in brief

- Solar-only battery control with **three actions:** hold, solar-charge, discharge  
- Discretised tabular MDP (324 states in the CA01 formulation)  
- NumPy **Q-Learning / SARSA**, greedy + rule baselines  
- Monetised reward based on grid-import cost  
- **Finding:** RL beat a weak tertile rule (~33% lower import cost) but did **not** beat greedy self-consumption on held-out test days — strong baselines matter  
- Streamlit dashboard for day replay and controller comparison  

---

# 3. What CA02 added (extensions)

| Area | What we added |
|------|----------------|
| **Action space** | 3 → **5** actions (hold, solar-charge, discharge, **grid-charge**, **export**) |
| **Tariff / physics** | Experimental **wholesale-exposed export**, efficiencies, cycling cost, terminal SOC |
| **Research question** | Does a coarse **three-bin true 4-hour** price-direction feature help tabular Q-Learning beat a strong greedy baseline? |
| **Controllers** | Current Q (540) · Privileged Q (1620) · Greedy 5-action · no-battery · perfect-foresight bound |
| **Evaluation** | 53 held-out days × 5 seeds |
| **Headline result** | Greedy best deployable (**~90.39** AUD vs no-battery **160.75**). Privileged true-direction did **not** help (Current ~**124.23**; Privileged ~**139.68**) |
| **Product / demo** | FastAPI **Web Twin** (Overview, Digital Twin, Price Monitor, Agent Play, Results) + Streamlit research twin |
| **Play vs Agent** | Human vs RL vs Greedy on identical twins (oversight demo) |
| **Engineering** | Double Q, forecast modules, live AEMO monitor, Docker, user guide, presentation pack |

---

# 4. How to read this submission

1. **Page 1** of the Word file is the formal cover sheet (same layout pattern as CA01).  
2. This note links CA01 → CA02 and lists repository / demo / presentation links.  
3. Experiment write-up: `deliverables/notebooklm/CA2_Forecast_Info_Experiment_Findings.md`  
4. Code: `src/` · `webapp/` · `dashboard/`  
5. Reproduce: see `README.md`

*GréineQ is a software digital twin for research and demonstration — not a physical battery controller.*

---

**Word version:** `deliverables/B9AI105_Group_CA02_20082900_20093736_10592825_20098301_Cover_Note.docx`  
Regenerate: `python scripts/build_ca2_cover_note.py`
