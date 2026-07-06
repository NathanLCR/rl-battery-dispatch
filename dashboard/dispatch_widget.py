"""Sidebar + landing dispatch animation — mission-control / system-design layout."""

from __future__ import annotations

import json

import streamlit.components.v1 as components


def render_dispatch_widget(actions: list[str], times: list[str], soc: list[float]) -> None:
    """Compact animated dispatch panel for the digital-twin sidebar."""
    _render_dispatch_html(actions, times, soc, height=320)


def render_landing_dispatch(trace, demo_day: str = "") -> None:
    """Q-Agent control-centre hero animation for the landing page."""
    _render_landing_control_centre(trace, demo_day)


def _render_landing_control_centre(trace, demo_day: str = "") -> None:
    """Dark-themed Q-Agent hero with energy-flow animation (landing page only)."""
    payload = {
        "actions": trace["action"].tolist()[:48],
        "times": trace["time_label"].tolist()[:48],
        "soc": [float(x) for x in trace["soc_pct"].tolist()[:48]],
        "pv": [float(x) for x in trace["pv_kwh"].tolist()[:48]],
        "load": [float(x) for x in trace["load_kwh"].tolist()[:48]],
        "price": [float(x) for x in trace["price_per_kwh"].tolist()[:48]],
        "retail": [float(x) for x in trace["retail_price_per_kwh"].tolist()[:48]],
        "rewards": [float(x) for x in trace["reward"].tolist()[:48]],
        "gridImport": [float(x) for x in trace["grid_import_kwh"].tolist()[:48]],
        "day": demo_day,
    }
    data_json = json.dumps(payload)

    components.html(
        f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 0;
    background: linear-gradient(165deg, #0a1020 0%, #0c1424 45%, #070d1a 100%);
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    color: #e2e8f0;
  }}
  .wrap {{
    padding: 0.85rem 1rem 1rem;
    display: flex; flex-direction: column; gap: 0.65rem;
    min-height: 520px;
  }}
  .topbar {{
    display: flex; justify-content: space-between; align-items: center;
    font-size: 0.68rem; letter-spacing: 0.06em; text-transform: uppercase;
    color: #64748b;
  }}
  .replay-badge {{
    display: inline-flex; align-items: center; gap: 0.35rem;
    padding: 0.2rem 0.55rem; border-radius: 999px;
    border: 1px solid rgba(245,156,26,0.35);
    color: #fbbf24; background: rgba(245,156,26,0.08);
  }}
  .replay-dot {{
    width: 7px; height: 7px; border-radius: 50%; background: #f59e1a;
    animation: pulse-dot 2s ease-in-out infinite;
  }}
  @keyframes pulse-dot {{
    0%,100% {{ opacity: 0.55; transform: scale(1); }}
    50% {{ opacity: 1; transform: scale(1.15); }}
  }}
  .head-block {{ text-align: center; }}
  .core-title {{
    margin: 0; font-size: 1.05rem; font-weight: 700; letter-spacing: 0.04em;
    color: #f59e1a; text-transform: none;
  }}
  .core-sub {{
    margin: 0.2rem 0 0.55rem; font-size: 0.72rem; color: #94a3b8;
  }}
  .action-pill {{
    display: inline-block; min-width: 10rem;
    padding: 0.45rem 1.35rem; border-radius: 10px;
    font-size: 0.88rem; font-weight: 700; letter-spacing: 0.04em;
    color: #fff; margin-bottom: 0.45rem;
    box-shadow: 0 4px 18px rgba(0,0,0,0.35);
    transition: background 0.35s ease, box-shadow 0.35s ease;
  }}
  .action-pill.hold {{ background: #64748b; box-shadow: 0 0 16px rgba(100,116,139,0.35); }}
  .action-pill.charge {{ background: #22c55e; box-shadow: 0 0 18px rgba(34,197,94,0.4); }}
  .action-pill.discharge {{ background: #f59e1a; box-shadow: 0 0 18px rgba(245,156,26,0.45); }}
  .stats {{
    display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.4rem;
    margin-bottom: 0.35rem;
  }}
  .stat {{
    background: rgba(15,23,42,0.75); border: 1px solid rgba(148,163,184,0.14);
    border-radius: 8px; padding: 0.35rem 0.45rem; text-align: center;
  }}
  .stat span {{
    display: block; font-size: 0.52rem; color: #64748b;
    text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.15rem;
  }}
  .stat strong {{ font-size: 0.72rem; color: #f8fafc; font-weight: 600; }}
  .flow-stage {{
    position: relative; padding: 0.75rem 0.25rem 0.5rem;
    min-height: 200px;
  }}
  .flow-grid {{
    display: grid; grid-template-columns: 1fr auto 1fr auto 1fr;
    grid-template-rows: auto auto auto;
    align-items: center; justify-items: center; gap: 0.35rem 0.25rem;
  }}
  .node {{
    display: flex; flex-direction: column; align-items: center; gap: 0.3rem;
    z-index: 2;
  }}
  .node-lbl {{
    font-size: 0.58rem; color: #94a3b8; text-transform: uppercase;
    letter-spacing: 0.05em; text-align: center; line-height: 1.25;
  }}
  .node-val {{ font-size: 0.58rem; color: #64748b; }}
  .solar-icon {{
    width: 52px; height: 52px; border-radius: 50%;
    background: radial-gradient(circle, #fde68a 0%, #f59e1a 55%, #b45309 100%);
    box-shadow: 0 0 16px rgba(245,156,26,0.35);
    transition: all 0.45s ease;
  }}
  .solar-icon.glow {{
    box-shadow: 0 0 28px rgba(251,191,36,0.75), 0 0 48px rgba(245,156,26,0.35);
    transform: scale(1.06);
  }}
  .battery-wrap {{ display: flex; flex-direction: column; align-items: center; }}
  .battery-cap {{
    width: 18px; height: 5px; background: #64748b; border-radius: 2px 2px 0 0;
  }}
  .battery {{
    width: 48px; height: 72px; border: 2px solid rgba(148,163,184,0.4);
    border-radius: 8px; background: #0f1729; position: relative; overflow: hidden;
  }}
  .battery-fill {{
    position: absolute; bottom: 0; left: 0; right: 0;
    transition: height 0.5s ease, background 0.5s ease;
    display: flex; align-items: center; justify-content: center;
  }}
  .battery-pct {{ font-size: 0.62rem; font-weight: 700; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.5); }}
  .home-icon {{
    width: 50px; height: 34px;
    clip-path: polygon(0% 100%, 18% 52%, 38% 68%, 56% 28%, 76% 48%, 100% 12%, 100% 100%);
    background: linear-gradient(180deg, #6366f1, #4338ca);
    opacity: 0.75; transition: all 0.4s ease;
  }}
  .home-icon.pulse {{ opacity: 1; filter: drop-shadow(0 0 10px rgba(99,102,241,0.55)); transform: scale(1.05); }}
  .grid-card {{
    min-width: 58px; padding: 0.4rem 0.45rem; border-radius: 8px;
    background: rgba(245,156,26,0.08); border: 1px solid rgba(245,156,26,0.28);
    text-align: center;
  }}
  .grid-price {{ font-size: 0.72rem; font-weight: 700; color: #fbbf24; }}
  .grid-cost {{ font-size: 0.55rem; color: #94a3b8; margin-top: 0.12rem; }}
  .q-hub {{
    grid-column: 3; grid-row: 1 / span 3;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    position: relative; width: 96px; height: 96px;
  }}
  .q-ring {{
    position: absolute; inset: 0; border-radius: 50%;
    border: 1px solid rgba(245,156,26,0.25);
  }}
  .q-ring.r1 {{ animation: spin 14s linear infinite; }}
  .q-ring.r2 {{ inset: 10px; animation: spin 9s linear infinite reverse; border-color: rgba(99,102,241,0.3); }}
  .q-core {{
    position: relative; z-index: 2;
    width: 52px; height: 52px; border-radius: 50%;
    background: radial-gradient(circle, #fde68a 0%, #f59e1a 50%, #b45309 100%);
    box-shadow: 0 0 24px rgba(245,156,26,0.55);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.35rem; font-weight: 800; color: #1c1917;
    animation: core-pulse 2.5s ease-in-out infinite;
  }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  @keyframes core-pulse {{
    0%,100% {{ box-shadow: 0 0 20px rgba(245,156,26,0.45); }}
    50% {{ box-shadow: 0 0 32px rgba(245,156,26,0.75); }}
  }}
  .q-lbl {{
    position: absolute; bottom: -1.1rem; font-size: 0.58rem; font-weight: 700;
    letter-spacing: 0.12em; color: #f59e1a; text-transform: uppercase;
  }}
  .conn {{
    height: 3px; width: 100%; max-width: 42px; border-radius: 99px;
    background: rgba(148,163,184,0.15); position: relative; overflow: hidden;
  }}
  .conn-pulse {{
    position: absolute; top: 0; left: -30%; width: 30%; height: 100%;
    border-radius: 99px; animation: flow 1.2s linear infinite; opacity: 0;
  }}
  .conn.active .conn-pulse {{ opacity: 1; }}
  .conn.charge .conn-pulse {{ background: #22c55e; box-shadow: 0 0 8px #22c55e; }}
  .conn.discharge .conn-pulse {{ background: #f59e1a; box-shadow: 0 0 8px #f59e1a; }}
  .conn.hold .conn-pulse {{ background: #64748b; box-shadow: 0 0 6px #64748b; }}
  .conn.solar .conn-pulse {{ background: #fbbf24; box-shadow: 0 0 8px #fbbf24; }}
  @keyframes flow {{ 0% {{ left: -30%; }} 100% {{ left: 100%; }} }}
  .solar-node {{ grid-column: 1; grid-row: 2; }}
  .batt-node {{ grid-column: 5; grid-row: 2; }}
  .home-node {{ grid-column: 5; grid-row: 1; }}
  .grid-node {{ grid-column: 1; grid-row: 1; }}
  .c1 {{ grid-column: 2; grid-row: 2; }}
  .c2 {{ grid-column: 4; grid-row: 2; }}
  .c3 {{ grid-column: 3; grid-row: 3; width: 3px; height: 28px; max-width: none; }}
  .timeline-caption {{
    text-align: center; font-size: 0.62rem; color: #64748b; margin-top: 0.25rem;
  }}
  .timeline-grid {{
    display: grid; grid-template-columns: repeat(48, 1fr); gap: 2px;
  }}
  .cell {{
    height: 10px; border-radius: 2px; background: #334155;
    opacity: 0.35; transition: opacity 0.25s, box-shadow 0.25s, transform 0.2s;
  }}
  .cell.past {{ opacity: 0.95; }}
  .cell.charge {{ background: #22c55e; }}
  .cell.discharge {{ background: #f59e1a; }}
  .cell.hold {{ background: #64748b; }}
  .cell.active {{
    opacity: 1; transform: scale(1.12); z-index: 1; position: relative;
    box-shadow: 0 0 0 2px #f8fafc, 0 0 12px rgba(245,156,26,0.55);
  }}
  .legend {{
    display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap;
    font-size: 0.6rem; color: #64748b; margin-top: 0.35rem;
  }}
  .legend span {{ display: inline-flex; align-items: center; gap: 0.3rem; }}
  .legend i {{ width: 0.6rem; height: 0.6rem; border-radius: 2px; display: inline-block; }}
  .timeline-scroll {{
    width: 100%;
    overflow-x: auto;
    overflow-y: hidden;
    -webkit-overflow-scrolling: touch;
    padding-bottom: 0.15rem;
  }}
  .timeline-scroll .timeline-grid {{
    min-width: 420px;
  }}
  @media (max-width: 1024px) {{
    .stats {{ grid-template-columns: repeat(3, 1fr); }}
    .wrap {{ min-height: auto; }}
  }}
  @media (max-width: 768px) {{
    .stats {{ grid-template-columns: repeat(2, 1fr); }}
    .action-pill {{ min-width: 8rem; font-size: 0.82rem; padding: 0.4rem 1rem; }}
    .flow-stage {{ min-height: auto; padding: 0.5rem 0; }}
    .flow-grid {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.55rem;
    }}
    .conn {{ display: none; }}
    .solar-node, .batt-node, .home-node, .grid-node, .q-hub {{
      width: 100%;
      max-width: 220px;
    }}
    .q-hub {{ width: 88px; height: 88px; order: -1; margin-bottom: 0.25rem; }}
    .q-core {{ animation: none; box-shadow: 0 0 18px rgba(245,156,26,0.45); }}
    .replay-dot {{ animation: none; opacity: 0.85; }}
  }}
  @media (max-width: 430px) {{
    .stats {{ grid-template-columns: 1fr 1fr; gap: 0.3rem; }}
    .stat strong {{ font-size: 0.66rem; }}
    .core-title {{ font-size: 0.95rem; }}
    .wrap {{ padding: 0.65rem 0.55rem 0.85rem; gap: 0.5rem; }}
  }}
</style></head><body>
<div class="wrap">
  <div class="topbar">
    <span class="replay-badge"><span class="replay-dot"></span>Simulation Replay</span>
    <span id="day-label"></span>
  </div>
  <div class="head-block">
    <p class="core-title">GréineQ Control Core</p>
    <p class="core-sub">Reinforcement learning for solar battery dispatch</p>
    <div id="action-pill" class="action-pill hold">Hold</div>
    <div style="font-size:0.65rem;color:#64748b;margin-top:0.15rem;">Q-Agent decision</div>
  </div>
  <div class="stats">
    <div class="stat"><span>Timestep</span><strong id="s-step">1 / 48</strong></div>
    <div class="stat"><span>Time of day</span><strong id="s-time">--:--</strong></div>
    <div class="stat"><span>Battery state of charge</span><strong id="s-soc">--%</strong></div>
    <div class="stat"><span>Grid import cost</span><strong id="s-grid">$0.00</strong></div>
    <div class="stat"><span>Step reward</span><strong id="s-reward">0.000</strong></div>
  </div>
  <div class="flow-stage">
    <div class="flow-grid">
      <div class="node grid-node">
        <div class="grid-card">
          <div class="grid-price" id="grid-price">$0.00</div>
          <div class="grid-cost" id="grid-cost-lbl">Estimated grid cost</div>
        </div>
        <span class="node-lbl">Grid price</span>
      </div>
      <div class="conn solar" id="conn-grid"><div class="conn-pulse"></div></div>
      <div class="node solar-node">
        <div id="solar" class="solar-icon"></div>
        <span class="node-lbl">Solar generation</span>
        <span class="node-val" id="pv-val">0.00 kWh</span>
      </div>
      <div class="conn charge" id="conn-solar"><div class="conn-pulse"></div></div>
      <div class="q-hub">
        <div class="q-ring r1"></div><div class="q-ring r2"></div>
        <div class="q-core">Q</div>
        <span class="q-lbl">Q-Agent</span>
      </div>
      <div class="conn charge" id="conn-batt"><div class="conn-pulse"></div></div>
      <div class="node batt-node">
        <div class="battery-wrap">
          <div class="battery-cap"></div>
          <div class="battery"><div id="fill" class="battery-fill" style="height:30%"><span id="pct" class="battery-pct">30%</span></div></div>
        </div>
        <span class="node-lbl">Battery storage</span>
      </div>
      <div class="conn discharge" id="conn-home"><div class="conn-pulse"></div></div>
      <div class="node home-node">
        <div id="home" class="home-icon"></div>
        <span class="node-lbl">Household demand</span>
        <span class="node-val" id="load-val">0.00 kWh</span>
      </div>
    </div>
  </div>
  <div class="timeline-caption">Daily dispatch timeline — each cell represents one 30-minute interval</div>
  <div class="timeline-scroll"><div id="timeline" class="timeline-grid"></div></div>
  <div class="legend">
    <span><i style="background:#64748b"></i>Hold</span>
    <span><i style="background:#22c55e"></i>Charge battery</span>
    <span><i style="background:#f59e1a"></i>Discharge battery</span>
  </div>
</div>
<script>
const DATA = {data_json};
const ACTION_LABELS = {{ hold: 'Hold', charge: 'Charge battery', discharge: 'Discharge battery' }};
const actions = DATA.actions.length ? DATA.actions : Array(48).fill('hold');
const times = DATA.times.length ? DATA.times : [];
const soc = DATA.soc.length ? DATA.soc : Array(48).fill(30);
const pv = DATA.pv.length ? DATA.pv : Array(48).fill(0);
const load = DATA.load.length ? DATA.load : Array(48).fill(0);
const retail = DATA.retail.length ? DATA.retail : Array(48).fill(0.22);
const rewards = DATA.rewards.length ? DATA.rewards : Array(48).fill(0);
const gridImport = DATA.gridImport.length ? DATA.gridImport : Array(48).fill(0);
const maxPv = Math.max(...pv, 0.01);
if (DATA.day) document.getElementById('day-label').textContent = DATA.day;
const timeline = document.getElementById('timeline');
actions.forEach((a, i) => {{
  const c = document.createElement('div');
  c.className = 'cell ' + (a === 'charge' ? 'charge' : a === 'discharge' ? 'discharge' : 'hold');
  timeline.appendChild(c);
}});
function socColor(pct) {{
  if (pct >= 60) return 'linear-gradient(180deg,#4ade80,#16a34a)';
  if (pct >= 30) return 'linear-gradient(180deg,#fde68a,#f59e1a)';
  if (pct >= 15) return 'linear-gradient(180deg,#fb923c,#ea580c)';
  return 'linear-gradient(180deg,#f87171,#dc2626)';
}}
function setConn(id, on, cls) {{
  const el = document.getElementById(id);
  el.classList.toggle('active', on);
  el.className = 'conn ' + cls + (on ? ' active' : '');
  if (on) el.innerHTML = '<div class="conn-pulse"></div>';
}}
let idx = 0;
function tick() {{
  const act = actions[idx] || 'hold';
  const s = soc[idx] ?? 30;
  const pill = document.getElementById('action-pill');
  pill.textContent = ACTION_LABELS[act] || 'Hold';
  pill.className = 'action-pill ' + act;
  document.getElementById('s-step').textContent = (idx + 1) + ' / 48';
  document.getElementById('s-time').textContent = times[idx] || '--:--';
  document.getElementById('s-soc').textContent = Math.round(s) + '%';
  const stepCost = (gridImport[idx] || 0) * (retail[idx] || 0);
  document.getElementById('s-grid').textContent = '$' + stepCost.toFixed(3);
  document.getElementById('s-reward').textContent = (rewards[idx] || 0).toFixed(3);
  document.getElementById('grid-price').textContent = '$' + (retail[idx] || 0).toFixed(3);
  document.getElementById('pv-val').textContent = (pv[idx] || 0).toFixed(2) + ' kWh';
  document.getElementById('load-val').textContent = (load[idx] || 0).toFixed(2) + ' kWh';
  const fill = document.getElementById('fill');
  fill.style.height = Math.max(5, s) + '%';
  fill.style.background = socColor(s);
  document.getElementById('pct').textContent = Math.round(s) + '%';
  document.getElementById('solar').classList.toggle('glow', (pv[idx] || 0) > maxPv * 0.35);
  document.getElementById('home').classList.toggle('pulse', (load[idx] || 0) > 0.12 || act === 'discharge');
  setConn('conn-solar', act === 'charge' && (pv[idx] || 0) > 0.02, 'solar');
  setConn('conn-batt', act === 'charge' || act === 'discharge', act === 'charge' ? 'charge' : act === 'discharge' ? 'discharge' : 'hold');
  setConn('conn-home', act === 'discharge', 'discharge');
  setConn('conn-grid', (gridImport[idx] || 0) > 0.01, 'discharge');
  timeline.querySelectorAll('.cell').forEach((el, i) => {{
    el.classList.toggle('active', i === idx);
    el.classList.toggle('past', i <= idx);
  }});
  idx = (idx + 1) % actions.length;
}}
tick();
setInterval(tick, 650);
</script>
</body></html>
        """,
        height=520,
        scrolling=False,
    )


def _render_dispatch_html(
    actions: list[str],
    times: list[str],
    soc: list[float],
    *,
    height: int = 320,
) -> None:
    """Compact sidebar dispatch panel (digital twin)."""
    payload = {
        "actions": actions[:48],
        "times": times[:48],
        "soc": [float(s) for s in soc[:48]],
    }
    data_json = json.dumps(payload)
    css = """
  body { background: transparent; font-family: system-ui, sans-serif; }
  .wrap {
    background: linear-gradient(180deg, #0c1424 0%, #070d1a 100%);
    border: 1px solid rgba(245, 156, 26, 0.22);
    border-radius: 12px;
    padding: 0.75rem; color: #e2e8f0;
    min-height: 280px; display: flex; flex-direction: column; gap: 0.65rem;
  }
  .head { display: flex; justify-content: space-between; align-items: center; }
  .badge {
    font-size: 0.62rem; font-weight: 700;
    letter-spacing: 0.08em; padding: 0.22rem 0.55rem; border-radius: 6px; border: 1px solid;
  }
  .badge.charge { color: #4ade80; background: rgba(34,197,94,0.12); border-color: rgba(34,197,94,0.35); }
  .badge.discharge { color: #fbbf24; background: rgba(245,156,26,0.14); border-color: rgba(245,156,26,0.4); }
  .badge.hold { color: #94a3b8; background: rgba(100,116,139,0.16); border-color: rgba(100,116,139,0.35); }
  .step-line { font-size: 0.58rem; color: #64748b; }
  .flow { display: flex; align-items: center; justify-content: space-between; gap: 0.35rem; width: 100%; }
  .node { display: flex; flex-direction: column; align-items: center; gap: 0.2rem; flex-shrink: 0; }
  .node-lbl { font-size: 0.48rem; color: #64748b; letter-spacing: 0.06em; }
  .solar {
    width: 44px; height: 28px; border-radius: 50%;
    background: radial-gradient(circle, #fde68a 0%, #f59e1a 55%, #b45309 100%);
    box-shadow: 0 0 18px rgba(245,156,26,0.55); transition: all 0.4s;
  }
  .solar.dim { box-shadow: 0 0 6px rgba(245,156,26,0.2); transform: scale(0.85); opacity: 0.55; }
  .battery {
    width: 52px; height: 60px; border: 2px solid rgba(148,163,184,0.35);
    border-radius: 8px; background: #0f1729; position: relative; overflow: hidden;
  }
  .battery-fill {
    position: absolute; bottom: 0; left: 0; right: 0;
    background: linear-gradient(180deg, #4ade80, #16a34a);
    transition: height 0.5s ease; display: flex; align-items: center; justify-content: center;
  }
  .battery-pct { font-size: 0.52rem; font-weight: 600; color: #ecfdf5; }
  .load {
    width: 48px; height: 32px;
    clip-path: polygon(0% 100%, 20% 55%, 40% 70%, 58% 30%, 78% 50%, 100% 15%, 100% 100%);
    background: linear-gradient(180deg, #6366f1, #312e81); opacity: 0.75;
  }
  .load.active { opacity: 1; box-shadow: 0 0 12px rgba(99,102,241,0.5); }
  .grid-cost {
    min-width: 44px; padding: 0.35rem 0.4rem; border-radius: 6px;
    background: rgba(15,23,42,0.9); border: 1px solid rgba(148,163,184,0.25);
    font-size: 0.52rem; text-align: center; color: #94a3b8;
  }
  .grid-cost.alert { color: #fca5a5; border-color: rgba(248,113,113,0.4); background: rgba(127,29,29,0.25); }
  .arrow { flex: 1; height: 2px; background: rgba(148,163,184,0.25); position: relative; min-width: 12px; }
  .arrow-dot {
    width: 6px; height: 6px; border-radius: 50%; background: #f59e1a;
    position: absolute; top: -2px; left: 0; box-shadow: 0 0 8px rgba(245,156,26,0.8);
    animation: travel 1.2s linear infinite; opacity: 0;
  }
  .arrow.active .arrow-dot { opacity: 1; }
  @keyframes travel { 0% { left: 0; } 100% { left: calc(100% - 6px); } }
  .timeline-grid {
    display: grid; grid-template-columns: repeat(48, 1fr); gap: 2px; margin-top: auto;
  }
  .cell { height: 10px; border-radius: 2px; background: #334155; }
  .cell.charge { background: #22c55e; }
  .cell.discharge { background: #f59e1a; }
  .cell.hold { background: #64748b; }
  .cell.active { height: 16px; outline: 1px solid #f8fafc; }
  .title {
    font-size: 0.68rem; letter-spacing: 0.1em; color: #f59e1a;
    text-transform: uppercase; font-weight: 700;
  }
"""
    body = """
<div class="wrap">
  <div class="title">Simulation Replay</div>
  <div class="head">
    <span id="badge" class="badge hold">Hold</span>
    <span id="step" class="step-line">Step 1/48 · 00:00</span>
  </div>
  <div class="flow">
    <div class="node"><div id="solar" class="solar dim"></div><span class="node-lbl">SOLAR</span></div>
    <div id="arr1" class="arrow"><div class="arrow-dot"></div></div>
    <div class="node">
      <div class="battery"><div id="fill" class="battery-fill" style="height:30%"><span id="pct" class="battery-pct">30%</span></div></div>
      <span class="node-lbl">BATTERY</span>
    </div>
    <div id="arr2" class="arrow"><div class="arrow-dot"></div></div>
    <div class="node"><div id="load" class="load"></div><span class="node-lbl">LOAD</span></div>
    <div class="node"><div id="grid" class="grid-cost">$0.00</div><span class="node-lbl">GRID</span></div>
  </div>
  <div id="timeline" class="timeline-grid"></div>
</div>
"""

    components.html(
        f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{css}</style></head><body>
{body}
<script>
const DATA = {data_json};
const ACTION_LABELS = {{ hold: 'Hold', charge: 'Charge battery', discharge: 'Discharge battery' }};
const actions = DATA.actions.length ? DATA.actions : Array(48).fill('hold');
const times = DATA.times.length ? DATA.times : actions.map((_, i) => String(i).padStart(2,'0') + ':00');
const soc = DATA.soc.length ? DATA.soc : Array(48).fill(30);
const timeline = document.getElementById('timeline');
actions.forEach((a) => {{
  const c = document.createElement('div');
  c.className = 'cell ' + (a === 'charge' ? 'charge' : a === 'discharge' ? 'discharge' : 'hold');
  timeline.appendChild(c);
}});
let idx = 0;
function tick() {{
  const act = actions[idx] || 'hold';
  document.getElementById('step').textContent = 'Step ' + (idx+1) + '/48 · ' + (times[idx] || '');
  const s = soc[idx] ?? 30;
  document.getElementById('fill').style.height = Math.max(4, s) + '%';
  document.getElementById('pct').textContent = Math.round(s) + '%';
  document.getElementById('solar').classList.toggle('dim', idx < 12 || idx > 36);
  document.getElementById('load').classList.toggle('active', act === 'discharge');
  document.getElementById('arr1').classList.toggle('active', act === 'charge');
  document.getElementById('arr2').classList.toggle('active', act === 'discharge');
  const badge = document.getElementById('badge');
  badge.textContent = ACTION_LABELS[act] || 'Hold';
  badge.className = 'badge ' + act;
  const grid = document.getElementById('grid');
  grid.textContent = act === 'discharge' ? '$' + (0.08 + idx * 0.002).toFixed(2) : '$0.00';
  grid.classList.toggle('alert', act === 'discharge');
  document.getElementById('arr1').classList.toggle('active', act !== 'hold');
  timeline.querySelectorAll('.cell').forEach((el, i) => el.classList.toggle('active', i === idx));
  idx = (idx + 1) % actions.length;
}}
tick();
setInterval(tick, 600);
</script>
</body></html>
        """,
        height=height,
        scrolling=False,
    )


def render_topbar_dispatch(actions: list[str], times: list[str], soc: list[float]) -> None:
    """Compact Q-Agent energy-flow pipeline for the dashboard top bar."""
    payload = {
        "actions": actions[:48],
        "times": times[:48],
        "soc": [float(s) for s in soc[:48]],
    }
    data_json = json.dumps(payload)
    components.html(
        f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 0; background: transparent; font-family: system-ui, sans-serif; color: #e2e8f0; }}
  .pipeline {{
    display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: center;
    gap: 0 0.45rem; padding: 0.15rem 0.35rem; min-height: 88px; width: 100%;
  }}
  .segment {{
    display: flex; flex-direction: column; align-items: center; gap: 0.22rem;
    flex-shrink: 0;
  }}
  .icon-box {{
    height: 40px; min-width: 40px;
    display: flex; align-items: center; justify-content: center;
  }}
  .lbl {{
    font-size: 0.5rem; color: #64748b; letter-spacing: 0.05em; text-transform: uppercase;
    text-align: center; line-height: 1.1; white-space: nowrap; min-height: 0.55rem;
  }}
  .step {{
    font-size: 0.48rem; color: #64748b; white-space: nowrap; text-align: center;
    line-height: 1.1; min-height: 0.55rem;
  }}
  /* Q-Agent — letter Q only, no sun orb */
  .q-hub {{
    width: 38px; height: 38px; border-radius: 50%;
    background: #0f1729; border: 2px solid rgba(245,156,26,0.45);
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; font-weight: 800; color: #f59e1a;
    box-shadow: 0 0 10px rgba(245,156,26,0.2);
    position: relative;
  }}
  .q-hub::after {{
    content: ''; position: absolute; inset: -4px; border-radius: 50%;
    border: 1px solid rgba(245,156,26,0.18); animation: spin 14s linear infinite;
  }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  /* Solar panel — distinct from Q orb */
  .solar-panel {{
    width: 34px; height: 26px; padding: 3px;
    background: #1e293b; border: 1px solid rgba(148,163,184,0.35); border-radius: 4px;
    display: grid; grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(2, 1fr); gap: 2px;
    transition: border-color 0.35s, box-shadow 0.35s;
  }}
  .solar-panel .cell {{
    background: #334155; border-radius: 1px; transition: background 0.35s;
  }}
  .solar-panel.active {{ border-color: rgba(245,156,26,0.5); box-shadow: 0 0 8px rgba(245,156,26,0.25); }}
  .solar-panel.active .cell {{ background: rgba(245,156,26,0.75); }}
  .solar-panel.dim .cell {{ background: #334155; opacity: 0.6; }}
  /* Battery */
  .batt-wrap {{ display: flex; flex-direction: column; align-items: center; }}
  .batt-cap {{
    width: 14px; height: 3px; background: #64748b; border-radius: 2px 2px 0 0;
  }}
  .battery {{
    width: 28px; height: 36px; border: 1.5px solid rgba(148,163,184,0.4);
    border-radius: 4px; background: #0f1729; position: relative; overflow: hidden;
  }}
  .battery-fill {{
    position: absolute; bottom: 0; left: 0; right: 0;
    transition: height 0.45s ease, background 0.45s ease;
  }}
  .battery-pct {{
    position: absolute; inset: 0; z-index: 1;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.48rem; font-weight: 700;
    color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.6);
  }}
  /* Home / grid */
  .home-grid {{
    display: flex; flex-direction: column; align-items: center; gap: 1px;
  }}
  .home-roof {{
    width: 0; height: 0;
    border-left: 11px solid transparent; border-right: 11px solid transparent;
    border-bottom: 9px solid #6366f1;
  }}
  .home-body {{
    width: 22px; height: 13px; background: #4338ca; border-radius: 0 0 2px 2px;
    transition: box-shadow 0.35s, opacity 0.35s; opacity: 0.75;
  }}
  .home-grid.active .home-body {{ opacity: 1; box-shadow: 0 0 8px rgba(99,102,241,0.45); }}
  .grid-tick {{
    width: 14px; height: 2px; background: rgba(148,163,184,0.35); border-radius: 99px; margin-top: 2px;
  }}
  /* Connectors — vertically centred on icon row */
  .conn {{
    width: 24px; height: 3px; border-radius: 99px; background: rgba(148,163,184,0.18);
    position: relative; flex-shrink: 0; align-self: flex-start; margin-top: 18px;
  }}
  .conn-pulse {{
    position: absolute; top: 0; left: -20%; width: 35%; height: 100%; border-radius: 99px;
    opacity: 0; animation: flow 1.1s linear infinite;
  }}
  .conn.active .conn-pulse {{ opacity: 1; }}
  .conn.hold .conn-pulse {{ background: #64748b; }}
  .conn.charge .conn-pulse {{ background: #22c55e; box-shadow: 0 0 4px #22c55e; }}
  .conn.discharge .conn-pulse {{ background: #f59e1a; box-shadow: 0 0 4px #f59e1a; }}
  .conn.solar .conn-pulse {{ background: #fbbf24; box-shadow: 0 0 4px #fbbf24; }}
  @keyframes flow {{ 0% {{ left: -20%; }} 100% {{ left: 100%; }} }}
  /* Action badge — same icon row as other nodes */
  .action-segment {{ min-width: 68px; }}
  .badge {{
    font-size: 0.58rem; font-weight: 700; letter-spacing: 0.03em;
    padding: 0.2rem 0.5rem; border-radius: 6px; border: 1px solid; white-space: nowrap;
    line-height: 1.2;
  }}
  .badge.hold {{ color: #94a3b8; background: rgba(100,116,139,0.16); border-color: rgba(100,116,139,0.35); }}
  .badge.charge {{ color: #4ade80; background: rgba(34,197,94,0.12); border-color: rgba(34,197,94,0.35); }}
  .badge.discharge {{ color: #fbbf24; background: rgba(245,156,26,0.14); border-color: rgba(245,156,26,0.4); }}
  @media (max-width: 520px) {{
    .conn {{ width: 16px; }}
    .icon-box {{ min-width: 34px; }}
    .lbl, .step {{ font-size: 0.44rem; }}
  }}
</style></head><body>
<div class="pipeline">
  <div class="segment">
    <div class="icon-box"><div class="q-hub">Q</div></div>
    <span class="lbl">Q-Agent</span>
  </div>
  <div id="c1" class="conn hold"><div class="conn-pulse"></div></div>
  <div class="segment">
    <div class="icon-box">
      <div id="solar" class="solar-panel dim">
        <div class="cell"></div><div class="cell"></div><div class="cell"></div>
        <div class="cell"></div><div class="cell"></div><div class="cell"></div>
      </div>
    </div>
    <span class="lbl">Solar</span>
  </div>
  <div id="c2" class="conn hold"><div class="conn-pulse"></div></div>
  <div class="segment">
    <div class="icon-box">
      <div class="batt-wrap">
        <div class="batt-cap"></div>
        <div class="battery">
          <div id="fill" class="battery-fill" style="height:30%"></div>
          <span id="pct" class="battery-pct">30%</span>
        </div>
      </div>
    </div>
    <span class="lbl">Battery</span>
  </div>
  <div id="c3" class="conn hold"><div class="conn-pulse"></div></div>
  <div class="segment">
    <div class="icon-box">
      <div id="home" class="home-grid">
        <div class="home-roof"></div>
        <div class="home-body"></div>
        <div class="grid-tick"></div>
      </div>
    </div>
    <span class="lbl">Home / Grid</span>
  </div>
  <div id="c4" class="conn hold"><div class="conn-pulse"></div></div>
  <div class="segment action-segment">
    <div class="icon-box"><span id="badge" class="badge hold">Hold</span></div>
    <span id="step" class="step">Step 1/48 · --:--</span>
    <span class="lbl">Action</span>
  </div>
</div>
<script>
const DATA = {data_json};
const LABELS = {{ hold: 'Hold', charge: 'Charge', discharge: 'Discharge' }};
const actions = DATA.actions.length ? DATA.actions : Array(48).fill('hold');
const times = DATA.times.length ? DATA.times : [];
const soc = DATA.soc.length ? DATA.soc : Array(48).fill(30);
function socColor(p) {{
  if (p >= 60) return 'linear-gradient(180deg,#4ade80,#16a34a)';
  if (p >= 30) return 'linear-gradient(180deg,#fde68a,#f59e1a)';
  if (p >= 15) return 'linear-gradient(180deg,#fb923c,#ea580c)';
  return 'linear-gradient(180deg,#f87171,#dc2626)';
}}
function setConn(id, on, cls) {{
  const el = document.getElementById(id);
  el.className = 'conn ' + cls + (on ? ' active' : '');
  if (!el.querySelector('.conn-pulse')) el.innerHTML = '<div class="conn-pulse"></div>';
}}
let idx = 0;
function tick() {{
  const act = actions[idx] || 'hold';
  const s = soc[idx] ?? 30;
  const solarOn = idx >= 10 && idx <= 36;
  document.getElementById('badge').textContent = LABELS[act] || 'Hold';
  document.getElementById('badge').className = 'badge ' + act;
  document.getElementById('step').textContent = 'Step ' + (idx + 1) + '/48 · ' + (times[idx] || '--:--');
  const fill = document.getElementById('fill');
  fill.style.height = Math.max(8, s) + '%';
  fill.style.background = socColor(s);
  document.getElementById('pct').textContent = Math.round(s) + '%';
  const solar = document.getElementById('solar');
  solar.classList.toggle('active', solarOn);
  solar.classList.toggle('dim', !solarOn);
  document.getElementById('home').classList.toggle('active', act === 'discharge' || act === 'hold');
  setConn('c1', solarOn, 'solar');
  setConn('c2', act === 'charge', 'charge');
  setConn('c3', act === 'charge' || act === 'discharge', act === 'charge' ? 'charge' : act === 'discharge' ? 'discharge' : 'hold');
  setConn('c4', true, act === 'charge' ? 'charge' : act === 'discharge' ? 'discharge' : 'hold');
  idx = (idx + 1) % actions.length;
}}
tick();
setInterval(tick, 650);
</script>
</body></html>
        """,
        height=108,
        scrolling=False,
    )


def render_q_agent_orb() -> None:
    """Compact Q-Agent orb for sidebar header area."""
    components.html(
        """
<!DOCTYPE html>
<html><head>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700&display=swap" rel="stylesheet">
<style>
  body { margin:0; background:transparent; }
  .orb-wrap { display:flex; flex-direction:column; align-items:center; padding:0.5rem 0 0.75rem; }
  .orb-stage { position:relative; width:88px; height:88px; }
  .ring { position:absolute; inset:0; border-radius:50%; border:1px solid rgba(245,156,26,0.25); }
  .ring.r1 { animation: spin 12s linear infinite; }
  .ring.r2 { inset:10px; animation: spin 8s linear infinite reverse; border-color: rgba(99,102,241,0.3); }
  .ring.r3 { inset:20px; animation: spin 5s linear infinite; border-color: rgba(45,212,191,0.25); }
  .core {
    position:absolute; inset:28px; border-radius:50%;
    background: radial-gradient(circle, #fde68a 0%, #f59c1a 50%, #b45309 100%);
    box-shadow: 0 0 24px rgba(245,156,26,0.55);
    animation: pulse 2.4s ease-in-out infinite;
    display:flex; align-items:center; justify-content:center; font-size:1.1rem;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes pulse { 0%,100% { transform:scale(1); } 50% { transform:scale(1.06); } }
  .tag {
    margin-top:0.45rem; font-family:'Barlow Condensed',sans-serif;
    font-size:0.62rem; letter-spacing:0.16em; color:#f59c1a; font-weight:700;
  }
  .caps { font-size:0.48rem; color:#64748b; letter-spacing:0.08em; margin-top:0.2rem; text-align:center; }
</style></head><body>
<div class="orb-wrap">
  <div class="orb-stage">
    <div class="ring r1"></div><div class="ring r2"></div><div class="ring r3"></div>
    <div class="core">☀</div>
  </div>
  <div class="tag">Q-Learning Agent</div>
  <div class="caps">policy evaluation · replay</div>
</div>
</body></html>
        """,
        height=150,
        scrolling=False,
    )
