# GréineQ CA1 Defence — Q&A Bank (B9AI105)

Ground truth for the 15-minute Q&A. All numbers match the final report (B9AI105_RL_CA01_final.docx). Format: 5-minute timed presentation + 15-minute Q&A. Every member can be asked any question; primary ownership is marked.

## Key numbers (memorise)

- Test split: 53 held-out days, Customer 1, month-stratified split (256 train / 54 val / 53 test, seed 50)
- No battery: 160.75 AUD total (3.03 AUD/day)
- Oracle (perfect foresight): 49.19 AUD — theoretical floor
- Greedy self-consumption: 52.15 AUD — captures 97.4% of the oracle gap
- Tertile rule: 92.40 AUD
- Q-Learning: 62.02 AUD (−32.9% vs tertile rule); SARSA: 63.75 AUD (−31.0%)
- Multi-seed (5 seeds × 10,000 episodes): Q-Learning 61.75 ± 2.14 AUD, SARSA 61.62 ± 0.86 AUD; paired t-test p = 0.90 — statistically tied
- γ = 0.99 variant: worse for both (QL 69.62, SARSA 66.66)
- Tariff sensitivity (margin 0.15 / 0.22 / 0.35 AUD/kWh): RL beats the tertile rule at every margin; at 0.35, SARSA (84.90) beats Q-Learning (95.06)
- v1 reward misalignment: QL better reward than rule but worse cost (23.02 vs 18.80 AUD on comparable run)
- State space: 324 states = SOC(3) × PV(3) × load(3) × price(3) × time(4); 3 actions; Q-table 972 entries
- Battery: 10 kWh, 5 kW limits, 2.5 kWh max per 30-min step, SOC 10–90% hard limits, starts 50% daily
- Training: α 0.1 (decay ×0.9995, floor 0.01), γ 0.95, ε 0.1→0.01 (×0.999/ep), 10,000 episodes, seed 42

## Member 1 (Nathan Lucio — Data & EDA): problem, data, MDP

**Q: Why RL instead of supervised learning?**
No labels exist for the "correct" battery action — you would need a perfect-foresight oracle to create them, and then you wouldn't need learning. RL learns a policy from cumulative reward over the day instead of per-step labels.

**Q: Why not just rules?**
Rules are myopic — they react to the current interval. The value of charging now depends on the rest of the day, because SOC carries consequences forward. That temporal coupling is exactly the MDP structure RL exploits.

**Q: Define your MDP.**
State: SOC × PV × load × price × time-of-day, discretised to 324 states. Actions: hold, charge from surplus solar, discharge to cover deficit. Reward: negative household cost in AUD (retail import + curtailed-solar opportunity cost + optional degradation). Transitions: deterministic battery physics plus exogenous historical PV/load/price. γ = 0.95, 48 half-hour steps, episode = one calendar day.

**Q: Why 324 states — isn't that coarse?**
Deliberate. One extra bin per continuous feature multiplies the table roughly 81×, and coverage goes sparse. Coarse but exact and interpretable. Known cost: time-of-day bins break the strict Markov property — 12:00 and 17:30 can share a bin with very different remaining solar. We say this before the panel does.

**Q: Walk me through the data pipeline.**
Ausgrid GC/GG renamed load_kwh/pv_kwh, unpivoted from 48-column wide format to one row per timestamp. AEMO NSW1 RRP divided by 1000 to AUD/kWh. Timezone alignment: Ausgrid uses local civil time with DST, AEMO fixed AEST — both converted to Australia/Sydney before the inner join. Two DST transition days had only 46 readings and were dropped. net_load = load − pv.

**Q: How did you split the data, and why month-stratified?**
70/15/15 by day (256/54/53), stratified by month, seed 50. PV peaks in summer, load in winter — a chronological cut would give seasonally biased splits. Discretiser thresholds fitted on training rows only, to avoid leakage.

**Q: Why only Customer 1?**
Depth over breadth for CA1. Customer 2 was excluded from split generation because it has only 284 complete days with whole months missing, which breaks monthly stratification. Cross-customer transfer scripts exist but are not central to the claims.

**Q: Why is price in the state if the agent can't do arbitrage?**
Honest answer: in the current physics there is no grid charging, so price is observed but barely actionable — partial observability of opportunity. Grid charging is the CA2 extension that makes price fully matter.

## Member 2 (Nadeesha Jayasuriya — RL core): algorithms, reward, numbers

**Q: Write the Q-Learning update.**
Q(s,a) ← Q(s,a) + α [ r + γ max_a′ Q(s′,a′) − Q(s,a) ]. At terminal steps (t = 47) the target reduces to r.

**Q: Q-Learning vs SARSA?**
Q-Learning is off-policy — bootstraps on the best next action regardless of what the behaviour policy does. SARSA is on-policy — uses the action actually taken, so exploration risk is priced into the values, which can produce more cautious policies. Here they tie: 5 seeds, p = 0.90. The bottleneck is problem structure, not the TD variant.

**Q: Why did the v1 reward fail?**
It penalised wholesale spot price without retail margin or feed-in treatment, so training reward diverged from the evaluation metric. The agent ranked above the rule on reward while losing on the bill (23.02 vs 18.80 AUD). v2 monetises everything in AUD; ranking by reward now matches ranking by cost. Reward design is the project's core methodological lesson.

**Q: Explain the reward function.**
r_t = −w_c·import_t·(wholesale + 0.22 margin) − w_s·waste_t·0.06 feed-in − w_d·deg_t − w_i·invalid_t. Default battery_aware profile: w_c = w_s = w_d = 1.0, w_i = 0.1. cost_only ablation sets w_d = 0.

**Q: How do you know it converged?**
Training reward plateaus after the first few thousand episodes; validation greedy grid cost (checked every 500 episodes) stabilises around 4,000 episodes. 10,000 episodes gives margin without wasted compute.

**Q: Multi-seed robustness?**
5 seeds (42–46) at full 10,000 episodes: Q-Learning 61.75 ± 2.14 AUD, SARSA 61.62 ± 0.86. Paired t-test p = 0.90 — no significant difference. SARSA has lower seed-to-seed variance, suggesting slightly more stable learning.

**Q: Why does γ = 0.99 hurt?**
Longer effective horizon without finer state resolution doesn't help — the coarse states can't support better long-term distinctions, so the extra bootstrapping mostly propagates noise (QL 69.62, SARSA 66.66).

**Q: Why doesn't RL beat greedy self-consumption?**
Solar-only charging plus discharge-to-deficit means "use every surplus, cover every deficit" is near-optimal by construction. Greedy captures 97.4% of the oracle gap; the remaining headroom is ~0.05 AUD/day. Coarse bins also alias states. It's a problem-structure ceiling, not an algorithm failure.

## Member 3 (Emmanuel Addoh — Report & demo): discussion, demo, limitations

**Q: Why not DQN/PPO?**
324 states — a tabular table is exact and interpretable, with no function-approximation instability. Deep RL is justified when the state space grows (finer bins, continuous SOC, grid charging) — scoped for CA2.

**Q: What is the Double Q-Learning situation?**
Implemented to reduce maximisation bias (two tables, alternating updates). A terminal-update bug was found and fixed, but it was not fully retrained afterwards, so it appears in the dashboard demo only and is excluded from primary results. Say this proactively.

**Q: So why use RL at all?**
"RL value increases with grid charging, export tariffs, or fleet-level aggregation — flagged as CA2 extensions, not because RL failed here." (All three members memorise this sentence.)

**Q: What are the main limitations?**
Single customer; solar-only action space; coarse discretisation (PV bin degeneracy at night); four time bins break strict Markov; 2012–13 data vs 2026 tariffs; deterministic physics without forecast error; simulation-only — not a controller for real batteries without safety certification.

**Q: Business takeaway?**
No-battery → greedy saves ~108 AUD over 53 days (~2.04 AUD/day); only ~0.05 AUD/day headroom remains under current physics. For installers: correct wiring plus a simple controller delivers most of the value. RL earns its keep when the problem gains arbitrage and coordination.

**Q: Ethics / responsible use?**
GréineQ is a simulation-based decision-support prototype. No live grid connection without safety certification, human oversight, SOC/fault protections, and validation on current tariffs.

## AI usage (any member — Level 4)

Declared level: AI-assisted task completion with human evaluation; AI-created content cited. Answer pattern, 20 seconds, specific not defensive: "We used [tool] for [task]. I verified it by [test/derivation]. One thing it got wrong was [example], which we fixed by [fix]." Strong examples of critical engagement: the v1→v2 reward redesign (caught because training reward and bill ranking diverged) and the Double Q-Learning terminal-update bug (found in code review, fixed, honestly excluded from results).

## Hard-question drills (any member)

**Q: Your greedy baseline nearly matches the oracle. Doesn't that make the whole project pointless?**
No — it's the finding. Without the oracle and greedy bounds we couldn't have known that; most published work compares RL only against weak rules and overstates value. Quantifying where RL is NOT needed is a scientific contribution, and it tells us exactly which problem changes (arbitrage, fleets) make RL worthwhile.

**Q: Is your environment actually Markovian?**
Not strictly — we approximate the step index with four time bins to keep the table at 324 states. We name it as a limitation and it likely caps policy quality below the greedy/oracle bounds.

**Q: Why ε-greedy and not softmax/UCB?**
Simple, standard, sufficient here: with 324 states and 10k episodes of 48 steps, coverage of the reachable state space is dense. Exploration strategy wasn't the bottleneck; state resolution was.

**Q: Couldn't you just solve this with dynamic programming?**
The oracle IS backward DP with a 101-point SOC grid — but it needs the full day's future PV/load/price. Online control doesn't have that. RL learns a causal policy from replayed real trajectories without foresight.

**Q: How would results change with 2026 prices?**
Directionally: higher retail margins widen the spread between good and bad dispatch — tariff sensitivity shows RL's advantage over the rule persists at 0.35 AUD/kWh margin. But absolute numbers would change; that's why we tested margins rather than claiming transfer.
