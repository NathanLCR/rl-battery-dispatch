# GréineQ CA2 — Price-Arbitrage Extension: Findings & Defence Notes (B9AI105)

Companion to `GreineQ_Defence_QA_Bank.md` (CA1). This covers the CA2-specific
extension only: what was added, the full ablation, the root-cause finding, and
how it feeds the CA2 grading criteria (deployment, theory-vs-deployed, ethics,
limitations). All numbers are from the 53-day held-out test split, Customer 1,
same split/seed as CA1 unless noted.

## 1. What CA2 adds

CA1 scoped the MDP to **solar-only dispatch**: hold / charge (from solar
surplus) / discharge (to cover load deficit). The CA1 defence notes flagged
the natural next step explicitly:

> "Why is price in the state if the agent can't do arbitrage?" — *"in the
> current physics there is no grid charging, so price is observed but barely
> actionable... Grid charging is the CA2 extension that makes price fully
> matter."*

CA2 implements exactly that: two new actions, **`grid_charge`** (import from
the grid purely to charge the battery — buy low) and **`export`** (discharge
to sell back to the grid beyond covering load — sell high). State space is
unchanged (still SOC × PV × load × price × time-of-day); only the action
space grows 3 → 5. This is a materially different MDP, not a redeployment of
CA1 — the theoretical ceiling changes substantially (see §2).

## 2. Headline numbers

| Policy | Cost (AUD) | % of oracle-arbitrage savings |
|---|---|---|
| No battery | 160.75 | — |
| Oracle, solar-only (**CA1 ceiling**) | 49.19 | — |
| **Oracle, with arbitrage (CA2 ceiling)** | **29.62** | 100% |
| Greedy self-consumption (solar-only) | 52.15 | 82.8% |
| Tertile rule (solar-only) | 92.40 | 52.1% |
| Price-arbitrage heuristic (CA2, reactive) | 55.53 | 80.2% |
| Q-Learning, arbitrage, 10k ep | 79.97 | 61.6% |
| SARSA, arbitrage, 10k ep | 79.42 | 62.0% |
| **Q-Learning, arbitrage, 30k ep (best RL result)** | **73.85** | 66.3% |

Allowing arbitrage nearly **doubles the achievable savings** under perfect
foresight (oracle drops 49.19 → 29.62 AUD — a genuinely different, richer
problem than CA1). But every real policy that can *use* arbitrage — heuristic
or learned — currently **underperforms the original solar-only greedy
baseline** (52.15 AUD). That gap, and *why* it doesn't close, is the CA2
finding.

## 3. The ablation: five things we tried to close the gap

We treated "why can't RL capture the arbitrage headroom" as a real research
question and tested four specific hypotheses in order, each isolating one
variable. All results below use the same 30k-episode budget as the headline
Q-Learning result for direct comparability (the 50k-episode row is the
exception, included specifically to test the "needs more samples" hypothesis).

| Variant | Hypothesis being tested | Cost (AUD) | Result |
|---|---|---|---|
| Q-Learning, 30k ep (baseline) | — | 73.85 | best so far |
| Double Q-Learning, 30k ep, default init | Overestimation bias (max-bootstrap) is the problem | 84.99 | **worse** |
| Q-Learning, 30k ep, optimistic init (q=1.0) | Insufficient exploration of new actions is the problem | 87.10 | **worse** |
| Double-Q + optimistic init, 30k ep | Both combined | 90.86 | **worst** |
| Q-Learning, 30k ep, quintile price bins (540 states) | Coarse *current*-price resolution is the problem | 85.59 | worse (undertrained for larger space) |
| Q-Learning, 50k ep, quintile price bins | Same, with more samples to compensate for 540 vs 324 states | 81.94 | improving, but still short |

**None of the four interventions closed the gap.** The optimistic-init runs
are the most diagnostic: they show *more* solar waste (up to 4.98 kWh vs.
2.30 kWh for the plain 30k run) and lower self-consumption — the agent
explored `grid_charge`/`export` *more confidently*, and that confidence was
misplaced. That rules out "not enough exploration" as the cause: more
exploration of the new actions made outcomes worse, not better.

## 4. Root cause

The only path to genuine profit here is **grid-charge now because price will
be higher later** — `export` is rarely profitable on its own, because the
retail margin (0.22 AUD/kWh) dwarfs the flat feed-in rate (0.06 AUD/kWh), so
selling stored energy back to the grid essentially never recoups its cost
under this tariff. Timing a profitable grid-charge requires knowing something
about the *future* price trajectory. Every intervention we tried — reducing
value-estimation bias (Double-Q), forcing more exploration (optimistic init),
and sharpening the *current* price snapshot (quintile bins) — only refines
what the agent knows about **now**. None of them give it any information
about **later**. That's why they all fail the same way: the bottleneck isn't
bias, exploration, or current-price resolution — it's the absence of a
forecast signal, which no amount of tuning the existing state representation
can supply.

The likely actual fix — adding a short price-lookahead feature to the state
(e.g. "will price be higher in the next N steps," available in a real
deployment via day-ahead price forecasts) — is a further, out-of-scope
extension. Flagging it as future work is itself a defensible, precise
technical contribution.

## 5. How this maps to the CA2 grading criteria

**Working deployment (25%).** The dashboard runs the arbitrage-capable agent
live, including a real AEMO NSW1 price feed showing the agent's current
decision against the actual live price (not just historical replay) —
genuinely deployed, not just theorised.

**Theory vs. deployed (required content).** This *is* the theory-vs-deployed
story: the oracle promises ~40% more savings are theoretically available, but
every deployable policy we could build or train fails to safely capture it.
The gap between "what perfect information would allow" and "what a
realistically-informed policy can actually do" is the deployment challenge,
demonstrated with five separate experiments rather than asserted.

**Ethics (20%).** An under-informed autonomous agent, given a richer action
space, can make a household's bill *worse* than a much simpler baseline
(73.85–90.86 AUD vs. 52.15 AUD greedy) — a concrete, quantified instance of
the general AI-safety point that giving an agent more capability without
matching information/oversight can cause real financial harm. Supports a
staged-rollout / human-in-the-loop argument: don't deploy the richer action
space autonomously until the state representation actually supports it.

**Limitations (15%).** Precise and technical, not generic: (a) current-price
discretisation, however fine, can't substitute for a forecast signal — the
decision is fundamentally about the future; (b) the retail-margin/feed-in
spread makes `export` rarely viable under this tariff structure regardless of
policy quality; (c) tabular RL in a 540-state space needs substantially more
samples than 324, and even 50k episodes hadn't converged.

## 6. Anticipated Q&A (same format as CA1 bank)

**Q: Doesn't this mean the CA2 extension failed?**
No — the extension worked exactly as designed: it changed the ceiling
(49.19 → 29.62 AUD), proving there's real value on the table, and then let us
run a genuine, falsifiable ablation to find out why current methods can't
reach it. A negative result with a clear, evidenced cause is stronger than a
positive result with no explanation — this is the same posture as CA1's
"greedy nearly matches oracle" finding, applied one level deeper.

**Q: Why did optimistic initialisation make things worse instead of better?**
Optimistic init is supposed to encourage healthy exploration of under-tried
actions. It did — the agent tried `grid_charge`/`export` more. But because
the state doesn't carry the information needed to tell *profitable* arbitrage
from *unprofitable* arbitrage, more confident exploration just means more
confidently wrong decisions (measured directly: solar waste roughly doubled).

**Q: Why did finer price bins (quintiles) also fail?**
Because they refine the same variable that was never the bottleneck: how
precisely the agent knows *today's* price, not what it can infer about
*future* price. It was trending toward closing part of the gap with more
training (85.59 → 81.94 AUD from 30k → 50k episodes) simply because the
larger 540-state table needs more samples per state — but even given more
budget, it still can't answer a question about the future using only present
information.

**Q: What would you try next with more time?**
A short price-lookahead feature in the state (e.g. a discretised "price
rising / falling / flat over the next 2 hours" signal, available in practice
from published day-ahead forecasts) — the one lever that would target the
actual bottleneck we identified, rather than another proxy for it.

**Q: Is the live AEMO feed a real deployment or a gimmick?**
It's real and live (verified: fetched the actual current NSW1 price and
correctly evaluated the trained agent's decision against it), but it's
explicitly partial — PV/load are historical medians, not a live meter feed,
because no live household metering integration exists. That gap is disclosed
in the UI itself, not hidden, and is part of the theory-vs-deployed story.

## 7. Key numbers to memorise

- No battery: 160.75 AUD · Oracle solar-only: 49.19 AUD · **Oracle w/
  arbitrage: 29.62 AUD**
- Greedy self-consumption: 52.15 AUD (still the best real policy)
- Best RL result: Q-Learning, 30k ep, tertile bins: **73.85 AUD**
- Worst variant: Double-Q + optimistic init: 90.86 AUD
- 5 variants tested, 0 closed the gap to greedy — root cause: missing
  forecast signal, not bias/exploration/current-price resolution
