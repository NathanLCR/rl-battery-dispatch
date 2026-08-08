/* GréineQ Web Twin — Streamlit-parity flow */

const state = {
  meta: null,
  twin: null,
  playSession: null,
  charts: {},
  detailTab: "cost",
  chartTab: "energy",
  twinAutoRan: false,
  enteredApp: false,
  sidebarTimer: null,
  sidebarIdx: 0,
  sidebarTrace: null,
};

const $ = (id) => document.getElementById(id);

function showError(msg) {
  const el = $("error");
  if (!msg) {
    el.classList.add("hidden");
    el.textContent = "";
    return;
  }
  el.textContent = typeof msg === "string" ? msg : JSON.stringify(msg);
  el.classList.remove("hidden");
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const msg = Array.isArray(detail)
      ? detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
      : detail || data.message || res.statusText;
    throw new Error(msg);
  }
  return data;
}

function destroyChart(key) {
  if (state.charts[key]) {
    state.charts[key].destroy();
    delete state.charts[key];
  }
}

function setView(name) {
  const onLanding = name === "overview";
  document.body.classList.toggle("landing-mode", onLanding);
  $("nav").classList.toggle("hidden", onLanding);
  if (!onLanding) state.enteredApp = true;

  document.querySelectorAll(".nav button").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === name);
  });
  ["overview", "twin", "live", "play", "results"].forEach((v) => {
    const el = $(`view-${v}`);
    if (el) el.classList.toggle("hidden", v !== name);
  });
  showError("");

  if (name === "overview") {
    const frame = $("heroFrame");
    if (frame && !frame.dataset.loaded) {
      frame.src = `/api/overview/hero?t=${Date.now()}`;
      frame.dataset.loaded = "1";
    }
  }
  if (name === "results") loadResults();
  if (name === "live") loadLive();
  if (name === "play") syncPlayModels();
  if (name === "twin" && !state.twinAutoRan) {
    state.twinAutoRan = true;
    runTwin();
  }
}

function fillSelect(sel, items, valueKey = "name", labelFn = null) {
  sel.innerHTML = "";
  for (const item of items) {
    const opt = document.createElement("option");
    const val = typeof item === "string" ? item : item[valueKey];
    opt.value = val;
    opt.textContent = labelFn ? labelFn(item) : val;
    sel.appendChild(opt);
  }
}

function fillDays() {
  const split = $("split").value;
  const days = state.meta.splits[split] || [];
  fillSelect($("day"), days);
  if (days.includes(state.meta.default_day)) $("day").value = state.meta.default_day;
  fillSelect($("playDay"), state.meta.splits.test || []);
  if ((state.meta.splits.test || []).includes(state.meta.default_day)) {
    $("playDay").value = state.meta.default_day;
  }
}

function syncPlayModels() {
  if (!state.meta) return;
  const priv = $("playOpponent").value === "privileged";
  const models = priv ? state.meta.models.privileged : state.meta.models.current;
  fillSelect($("playModel"), models, "name", (m) => (m.preferred ? `${m.name} ★` : m.name));
  const def = priv ? state.meta.models.default_privileged : state.meta.models.default_current;
  if (def) $("playModel").value = def;
  $("playOversight").textContent = priv
    ? "You see a realistic 4h forecast. Opponent uses a true four-hour direction signal — oversight demo."
    : "You see a realistic 4h forecast. Opponent is Current Q (current state only).";
}

function syncExtraModels() {
  const showS = $("showSarsa").checked;
  const showD = $("showDq").checked;
  document.querySelectorAll(".model-sarsa").forEach((el) => el.classList.toggle("hidden", !showS));
  document.querySelectorAll(".model-dq").forEach((el) => el.classList.toggle("hidden", !showD));
}

async function init() {
  document.querySelectorAll(".nav button").forEach((b) => {
    b.addEventListener("click", () => setView(b.dataset.view));
  });
  document.querySelectorAll("[data-goto]").forEach((b) => {
    b.addEventListener("click", () => setView(b.dataset.goto));
  });
  $("split").addEventListener("change", fillDays);
  $("runBtn").addEventListener("click", runTwin);
  $("step").addEventListener("input", renderStep);
  $("prevStep").addEventListener("click", () => {
    $("step").value = Math.max(1, Number($("step").value) - 1);
    renderStep();
  });
  $("nextStep").addEventListener("click", () => {
    $("step").value = Math.min(48, Number($("step").value) + 1);
    renderStep();
  });
  $("dlTwin").addEventListener("click", downloadTwin);
  $("refreshLive").addEventListener("click", loadLive);
  $("playOpponent").addEventListener("change", syncPlayModels);
  $("playStart").addEventListener("click", startPlay);
  $("showSarsa").addEventListener("change", syncExtraModels);
  $("showDq").addEventListener("change", syncExtraModels);
  document.querySelectorAll("[data-mtab]").forEach((b) => {
    b.addEventListener("click", () => {
      state.detailTab = b.dataset.mtab;
      document.querySelectorAll("[data-mtab]").forEach((x) => x.classList.toggle("active", x === b));
      renderDetails();
    });
  });
  document.querySelectorAll("[data-ctab]").forEach((b) => {
    b.addEventListener("click", () => {
      state.chartTab = b.dataset.ctab;
      document.querySelectorAll("[data-ctab]").forEach((x) => x.classList.toggle("active", x === b));
      ["energy", "price", "actions", "cost"].forEach((t) => {
        const el = $(`ctab-${t}`);
        if (el) el.classList.toggle("hidden", t !== state.chartTab);
      });
    });
  });

  try {
    state.meta = await api("/api/meta");
    fillDays();
    const pref = (m) => (m.preferred ? `${m.name} ★` : m.name);
    fillSelect($("modelCurrent"), state.meta.models.current, "name", pref);
    fillSelect($("modelPriv"), state.meta.models.privileged, "name", pref);
    fillSelect($("modelSarsa"), state.meta.models.sarsa || [], "name", pref);
    fillSelect($("modelDq"), state.meta.models.double_q || [], "name", pref);
    if (state.meta.models.default_current) $("modelCurrent").value = state.meta.models.default_current;
    if (state.meta.models.default_privileged) $("modelPriv").value = state.meta.models.default_privileged;
    if (state.meta.models.default_sarsa) $("modelSarsa").value = state.meta.models.default_sarsa;
    if (state.meta.models.default_double_q) $("modelDq").value = state.meta.models.default_double_q;
    syncPlayModels();
    syncExtraModels();
  } catch (err) {
    showError(`Failed to load meta: ${err.message}`);
  }

  setView("overview");
}

async function runTwin() {
  showError("");
  const btn = $("runBtn");
  btn.disabled = true;
  btn.textContent = "Running…";
  $("twinEmpty").textContent = "Running controllers on the selected day…";
  $("twinEmpty").classList.remove("hidden");
  $("twinOut").classList.add("hidden");
  try {
    state.twin = await api("/api/twin/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        day: $("day").value,
        split: $("split").value,
        show_greedy: $("showGreedy").checked,
        show_current_q: $("showCurrent").checked,
        show_privileged_q: $("showPriv").checked,
        show_solar_only: $("showSolarOnly").checked,
        show_rule: $("showRule").checked,
        show_sarsa: $("showSarsa").checked,
        show_double_q: $("showDq").checked,
        current_model: $("modelCurrent").value || null,
        privileged_model: $("modelPriv").value || null,
        sarsa_model: $("modelSarsa").value || null,
        double_q_model: $("modelDq").value || null,
        reward_mode: $("rewardMode").value,
        include_q_values: $("includeQvals").checked,
      }),
    });
    renderTwin();
  } catch (err) {
    showError(err.message);
    $("twinEmpty").textContent = "Comparison failed — fix settings and run again.";
  } finally {
    btn.disabled = false;
    btn.textContent = "Run comparison";
  }
}

function pickPreviewTrace(traces) {
  const preferred = [
    "Greedy (5-action)",
    "Current Q",
    "Privileged Q — true 4h",
    "Solar-only greedy",
    "SARSA",
    "Double Q",
    "Tertile rule",
  ];
  const name = preferred.find((n) => traces[n]) || Object.keys(traces)[0];
  return name ? { name, rows: traces[name] } : null;
}

function stopSidebarFlow() {
  if (state.sidebarTimer) {
    clearInterval(state.sidebarTimer);
    state.sidebarTimer = null;
  }
}

function startSidebarFlow(label, rows) {
  stopSidebarFlow();
  state.sidebarTrace = rows || null;
  state.sidebarIdx = 0;
  const cap = $("sidebarFlowCaption");
  if (!rows || !rows.length) {
    if (cap) cap.textContent = "System flow · run a comparison";
    $("sidebarFlowStep").textContent = "Step —";
    return;
  }
  if (cap) cap.textContent = `System flow · ${label}`;
  const tick = () => {
    const row = rows[state.sidebarIdx];
    const act = row.action || "hold";
    const soc = row.soc_pct ?? 30;
    $("spPct").textContent = `${Math.round(soc)}%`;
    $("spFill").style.height = `${Math.max(8, soc)}%`;
    $("spSolar").classList.toggle("on", state.sidebarIdx >= 10 && state.sidebarIdx <= 36);
    $("spHome").classList.toggle("on", act === "discharge" || act === "hold");
    const setConn = (id, on, cls) => {
      const el = $(id);
      el.className = `sp-conn ${cls}${on ? " active" : ""}`;
    };
    setConn("spC1", state.sidebarIdx >= 10 && state.sidebarIdx <= 36, "charge");
    setConn("spC2", act === "charge" || act === "grid_charge", act === "grid_charge" ? "grid_charge" : "charge");
    setConn("spC3", act !== "hold", act);
    $("sidebarFlowStep").textContent = `Step ${state.sidebarIdx + 1}/48 · ${row.time_label || ""}`;
    state.sidebarIdx = (state.sidebarIdx + 1) % rows.length;
  };
  tick();
  state.sidebarTimer = setInterval(tick, 650);
}

function renderTwin() {
  const data = state.twin;
  $("twinEmpty").classList.add("hidden");
  $("twinOut").classList.remove("hidden");
  const best = data.summaries[0];
  const saved = data.no_battery_cost_aud - best.grid_cost_aud;
  $("winner").textContent = `Winning agent · ${data.winner} · saved AUD ${saved.toFixed(2)} vs no-battery`;
  $("kpis").innerHTML = `
    <div class="kpi"><div class="label">Net cost</div><div class="value">AUD ${best.grid_cost_aud.toFixed(2)}</div></div>
    <div class="kpi"><div class="label">No-battery</div><div class="value">AUD ${data.no_battery_cost_aud.toFixed(2)}</div></div>
    <div class="kpi"><div class="label">Oracle bound</div><div class="value">AUD ${data.oracle_cost_aud.toFixed(2)}</div></div>
    <div class="kpi"><div class="label">Final SOC</div><div class="value">${best.final_soc_pct.toFixed(1)}%</div></div>`;
  $("sumBody").innerHTML = data.summaries
    .map(
      (s, i) => `<tr class="${i === 0 ? "win" : ""}">
      <td>${i === 0 ? "🏆 " : ""}${s.policy}</td>
      <td class="num">AUD ${s.grid_cost_aud.toFixed(2)}</td>
      <td class="num">${s.savings_pct >= 0 ? "+" : ""}${s.savings_pct.toFixed(2)}%</td>
      <td class="num">${s.final_soc_pct.toFixed(1)}%</td></tr>`
    )
    .join("");
  const mu = data.models_used || {};
  $("modelNote").textContent = `Reward: ${data.reward_mode || "battery_aware"} · Current: ${
    mu.current || "—"
  } · Privileged: ${mu.privileged || "—"} · SARSA: ${mu.sarsa || "—"} · Double Q: ${mu.double_q || "—"}`;
  renderDetails();

  const preview = pickPreviewTrace(data.traces);
  if (preview) startSidebarFlow(preview.name, preview.rows);

  const labels = Object.values(data.traces)[0].map((r) => r.time_label);
  const colors = ["#22c55e", "#38bdf8", "#f59e0b", "#a855f7", "#f472b6", "#94a3b8"];
  destroyChart("cost");
  destroyChart("soc");
  destroyChart("energy");
  destroyChart("actions");
  destroyChart("market");

  if (data.market) {
    state.charts.energy = new Chart($("energyChart"), {
      type: "line",
      data: {
        labels: data.market.time_label,
        datasets: [
          {
            label: "Solar generation",
            data: data.market.pv_kwh,
            borderColor: "#f59e1a",
            backgroundColor: "rgba(245,158,26,0.18)",
            fill: true,
            tension: 0.2,
            pointRadius: 0,
          },
          {
            label: "Household demand",
            data: data.market.load_kwh,
            borderColor: "#6366f1",
            tension: 0.2,
            pointRadius: 0,
          },
        ],
      },
      options: chartOpts(),
    });
  }

  state.charts.soc = new Chart($("socChart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        ...(data.market
          ? [
              {
                label: "Wholesale",
                data: data.market.price_per_kwh,
                borderColor: "#f87171",
                borderDash: [4, 4],
                tension: 0.2,
                pointRadius: 0,
                yAxisID: "y1",
              },
            ]
          : []),
        ...Object.entries(data.traces).map(([name, rows], i) => ({
          label: `SOC · ${name}`,
          data: rows.map((r) => r.soc_pct),
          borderColor: colors[i % colors.length],
          tension: 0.2,
          pointRadius: 0,
          yAxisID: "y",
        })),
      ],
    },
    options: {
      plugins: { legend: { labels: { color: "#cbd5e1", boxWidth: 12 } } },
      scales: {
        x: { ticks: { color: "#64748b", maxTicksLimit: 8 }, grid: { color: "rgba(51,65,85,.5)" } },
        y: { min: 0, max: 100, title: { display: true, text: "SOC %", color: "#94a3b8" }, ticks: { color: "#64748b" }, grid: { color: "rgba(51,65,85,.5)" } },
        y1: { position: "right", title: { display: true, text: "AUD/kWh", color: "#94a3b8" }, ticks: { color: "#64748b" }, grid: { drawOnChartArea: false } },
      },
    },
  });

  const actionOrder = ["hold", "charge", "grid_charge", "discharge", "export"];
  state.charts.actions = new Chart($("actionsChart"), {
    type: "scatter",
    data: {
      datasets: Object.entries(data.traces).map(([name, rows], i) => ({
        label: name,
        data: rows.map((r, idx) => ({
          x: idx + 1,
          y: actionOrder.indexOf(r.action) + i * 0.12,
          action: r.action,
        })),
        backgroundColor: colors[i % colors.length],
        pointRadius: 4,
        pointHoverRadius: 6,
      })),
    },
    options: {
      plugins: {
        legend: { labels: { color: "#cbd5e1", boxWidth: 12 } },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${ctx.raw.action || ""}`,
          },
        },
      },
      scales: {
        x: {
          min: 1,
          max: 48,
          title: { display: true, text: "Timestep", color: "#94a3b8" },
          ticks: { color: "#64748b", stepSize: 4 },
          grid: { color: "rgba(51,65,85,.5)" },
        },
        y: {
          min: -0.3,
          max: actionOrder.length - 0.5,
          ticks: {
            color: "#e2e8f0",
            callback: (v) => {
              const i = Math.round(v);
              return ["Hold", "Solar charge", "Grid charge", "Discharge", "Export"][i] || "";
            },
            stepSize: 1,
          },
          grid: { color: "rgba(51,65,85,.5)" },
        },
      },
    },
  });

  state.charts.cost = new Chart($("costChart"), {
    type: "line",
    data: {
      labels,
      datasets: Object.entries(data.traces).map(([name, rows], i) => ({
        label: name,
        data: rows.map((r) => -r.reward),
        borderColor: colors[i % colors.length],
        tension: 0.2,
        pointRadius: 0,
      })),
    },
    options: chartOpts(),
  });

  // Keep selected chart tab visible
  document.querySelectorAll("[data-ctab]").forEach((x) => x.classList.toggle("active", x.dataset.ctab === state.chartTab));
  ["energy", "price", "actions", "cost"].forEach((t) => {
    const el = $(`ctab-${t}`);
    if (el) el.classList.toggle("hidden", t !== state.chartTab);
  });

  $("step").value = 24;
  renderStep();
}

function chartOpts() {
  return {
    responsive: true,
    plugins: { legend: { labels: { color: "#cbd5e1", boxWidth: 12 } } },
    scales: {
      x: { ticks: { color: "#64748b", maxTicksLimit: 8 }, grid: { color: "rgba(51,65,85,.5)" } },
      y: { ticks: { color: "#64748b" }, grid: { color: "rgba(51,65,85,.5)" } },
    },
  };
}

function renderDetails() {
  if (!state.twin) return;
  const s = state.twin.summaries;
  const tab = state.detailTab;
  let cols = [];
  if (tab === "cost") {
    cols = [
      ["export_revenue_aud", "Export revenue"],
      ["grid_charge_cost_aud", "Grid-charge cost"],
      ["net_arbitrage_profit_aud", "Arbitrage balance"],
    ];
  } else if (tab === "energy") {
    cols = [
      ["grid_import_kwh", "Grid import kWh"],
      ["export_kwh", "Export kWh"],
      ["self_consumption_rate", "Solar self-use %"],
      ["self_sufficiency", "Self-sufficiency %"],
    ];
  } else {
    cols = [
      ["battery_throughput_kwh", "Throughput kWh"],
      ["final_soc_pct", "Final SOC %"],
      ["n_grid_charge_actions", "# grid-charge"],
      ["n_export_actions", "# export"],
    ];
  }
  $("detailTables").innerHTML = `<table><thead><tr><th>Controller</th>${cols
    .map((c) => `<th class="num">${c[1]}</th>`)
    .join("")}</tr></thead><tbody>${s
    .map(
      (row) =>
        `<tr><td>${row.policy}</td>${cols
          .map((c) => `<td class="num">${row[c[0]]}</td>`)
          .join("")}</tr>`
    )
    .join("")}</tbody></table>`;
}

function renderStep() {
  if (!state.twin) return;
  const step = Number($("step").value);
  $("stepLabel").textContent = `Step ${step}`;
  $("stepBody").innerHTML = Object.entries(state.twin.traces)
    .map(([name, trace]) => {
      const row = trace[step - 1];
      return `<tr><td>${name}</td><td><span class="badge">${row.action}</span></td>
        <td class="num">${row.soc_pct.toFixed(0)}%</td><td class="num">AUD ${(-row.reward).toFixed(2)}</td></tr>`;
    })
    .join("");
}

function downloadTwin() {
  if (!state.twin) return;
  const blob = new Blob([JSON.stringify(state.twin, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `GreineQ_replay_${state.twin.day}.json`;
  a.click();
}

async function loadLive() {
  try {
    const data = await api("/api/live");
    if (!data.available) {
      $("liveBody").innerHTML = `<p class="muted">${data.message}</p>`;
      return;
    }
    $("liveBody").innerHTML = `
      <p class="muted">${data.note}</p>
      <p class="muted">Updated ${data.fetched_at_utc} · ${data.region} settlement ${data.settlement_time}</p>
      <div class="kpis">
        <div class="kpi"><div class="label">Live wholesale</div><div class="value">${data.wholesale_aud_per_kwh.toFixed(3)}</div></div>
        <div class="kpi"><div class="label">Est. retail import</div><div class="value">${data.retail_aud_per_kwh.toFixed(3)}</div></div>
        <div class="kpi"><div class="label">Typical PV</div><div class="value">${data.typical_pv_kwh.toFixed(2)} kWh</div></div>
        <div class="kpi"><div class="label">Typical load</div><div class="value">${data.typical_load_kwh.toFixed(2)} kWh</div></div>
      </div>
      ${
        data.recommendation
          ? `<div class="decision-card"><div class="title">Current Q recommendation: ${data.recommendation}</div>
             <div class="sub">Illustrative SOC + typical PV/load — not a metered home.</div></div>`
          : ""
      }`;
  } catch (err) {
    showError(err.message);
  }
}

async function startPlay() {
  showError("");
  try {
    const data = await api("/api/play/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        day: $("playDay").value,
        use_privileged: $("playOpponent").value === "privileged",
        model_name: $("playModel").value || null,
      }),
    });
    state.playSession = data.session_id;
    $("playSetup").classList.add("hidden");
    $("playGame").classList.remove("hidden");
    renderPlay(data);
  } catch (err) {
    showError(err.message);
  }
}

async function playAction(key) {
  showError("");
  try {
    const data = await api("/api/play/step", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.playSession, action: key }),
    });
    renderPlay(data);
  } catch (err) {
    showError(err.message);
  }
}

async function playPause() {
  const data = await api(`/api/play/${state.playSession}/pause`, { method: "POST" });
  const cur = await api(`/api/play/${state.playSession}`);
  cur.paused = data.paused;
  renderPlay(cur);
}

async function playQuit() {
  await api(`/api/play/${state.playSession}/quit`, { method: "POST" });
  state.playSession = null;
  $("playGame").classList.add("hidden");
  $("playGame").innerHTML = "";
  $("playSetup").classList.remove("hidden");
}

function renderPlay(data) {
  const root = $("playGame");
  destroyChart("playForecast");
  destroyChart("playCost");
  destroyChart("playSoc");
  destroyChart("playQ");
  destroyChart("playEndCost");
  destroyChart("playEndSoc");

  if (data.done) {
    const s = data.summaries;
    root.innerHTML = `
      <h2>Day complete</h2>
      <div class="winner">Winner: ${data.winner}</div>
      <div class="scoreboard">
        <div class="score"><div class="who">You</div><div class="cost">AUD ${s.you.grid_cost_aud.toFixed(2)}</div></div>
        <div class="score"><div class="who">Agent (${data.agent_label})</div><div class="cost">AUD ${s.rl.grid_cost_aud.toFixed(2)}</div></div>
        <div class="score"><div class="who">Greedy</div><div class="cost">AUD ${s.greedy.grid_cost_aud.toFixed(2)}</div></div>
      </div>
      <div class="play-charts">
        <div class="chart-card"><h3>Cumulative net cost</h3><canvas id="playEndCost"></canvas></div>
        <div class="chart-card"><h3>Battery SOC %</h3><canvas id="playEndSoc"></canvas></div>
      </div>
      <p class="muted">${data.oversight_note}</p>
      <button class="btn inline" type="button" id="playAgain">Try another day</button>`;
    $("playAgain").onclick = playQuit;
    const traces = [
      { key: "you", label: "You", color: "#f59e0b" },
      { key: "rl", label: "Agent", color: "#38bdf8" },
      { key: "greedy", label: "Greedy", color: "#22c55e" },
    ];
    const labels = (s.you.trace || []).map((r) => r.time);
    state.charts.playEndCost = new Chart($("playEndCost"), {
      type: "line",
      data: {
        labels,
        datasets: traces.map((t) => ({
          label: t.label,
          data: (s[t.key].trace || []).map((r) => r.cost),
          borderColor: t.color,
          tension: 0.2,
          pointRadius: 0,
        })),
      },
      options: chartOpts(),
    });
    state.charts.playEndSoc = new Chart($("playEndSoc"), {
      type: "line",
      data: {
        labels,
        datasets: traces.map((t) => ({
          label: t.label,
          data: (s[t.key].trace || []).map((r) => r.soc_pct),
          borderColor: t.color,
          tension: 0.2,
          pointRadius: 0,
        })),
      },
      options: {
        ...chartOpts(),
        scales: {
          ...chartOpts().scales,
          y: { min: 0, max: 100, ticks: { color: "#64748b" }, grid: { color: "rgba(51,65,85,.5)" } },
        },
      },
    });
    return;
  }

  const st = data.state;
  const badge =
    st.deficit > 1e-9
      ? `<span class="energy-badge deficit">Energy deficit: ${st.deficit.toFixed(2)} kWh</span>`
      : st.surplus > 1e-9
        ? `<span class="energy-badge surplus">Energy surplus: ${st.surplus.toFixed(2)} kWh</span>`
        : `<span class="energy-badge flat">Solar ≈ demand</span>`;

  const acts = data.actions
    .map((a) => {
      const av = data.availability[a.key];
      return `<button class="act ${a.key}" type="button" data-act="${a.key}" ${
        !av.ok || data.paused ? "disabled" : ""
      } title="${av.ok ? a.help : av.reason}">${a.label}</button>`;
    })
    .join("");

  const fb = data.feedback
    ? `<div class="feedback-row">
        <div class="fb"><div class="t">You chose ${data.feedback.human_action}</div><div>${data.feedback.human_detail}</div></div>
        <div class="fb agent"><div class="t">Agent chose ${data.feedback.agent_action}</div><div>Reason: ${data.feedback.agent_reason}</div></div>
      </div>`
    : "";

  const fc = (data.forecast.points || [])
    .map((p) => `<tr><td>${p.time}</td><td class="num">${p.price.toFixed(4)}</td></tr>`)
    .join("");

  const qRows = (data.q_values || [])
    .map((r) => `<tr><td>${r.action}</td><td>${r.q.toFixed(3)}</td></tr>`)
    .join("");

  root.innerHTML = `
    <h2>Play vs Agent</h2>
    <p class="muted">Day ${data.day} · Opponent ${data.agent_label} · Step ${data.step} of 48 · ${data.time_label}</p>
    <div class="kpi" style="margin-bottom:0.75rem"><div class="label">Progress</div><div class="value">${data.progress_pct}%</div></div>
    <div class="kpis">
      <div class="kpi"><div class="label">Battery</div><div class="value">${st.soc_pct.toFixed(0)}% · ${st.soc_kwh} kWh</div></div>
      <div class="kpi"><div class="label">Solar / demand</div><div class="value">${st.pv_kwh} / ${st.load_kwh}</div></div>
      <div class="kpi"><div class="label">Buy price</div><div class="value">${st.retail.toFixed(3)}</div></div>
      <div class="kpi"><div class="label">Sell price</div><div class="value">${st.export.toFixed(3)}</div></div>
    </div>
    ${badge}
    <h3 style="margin:0.5rem 0;color:var(--amber);font-family:var(--display)">Choose your action</h3>
    <div class="play-actions">${acts}</div>
    <div class="cta-row">
      <button class="btn inline secondary" type="button" id="btnPause">${data.paused ? "Resume" : "Pause and inspect"}</button>
      <button class="btn inline secondary" type="button" id="btnQuit">Quit to setup</button>
    </div>
    ${fb}
    <h3 style="margin:1rem 0 0.4rem;color:var(--amber);font-family:var(--display)">Competition scoreboard</h3>
    <div class="scoreboard">
      <div class="score"><div class="who">You · last ${data.scoreboard.you.last || "—"}</div><div class="cost">AUD ${data.scoreboard.you.cost.toFixed(2)}</div><div class="muted">SOC ${data.scoreboard.you.soc}%</div></div>
      <div class="score"><div class="who">Agent · last ${data.scoreboard.rl.last}</div><div class="cost">AUD ${data.scoreboard.rl.cost.toFixed(2)}</div><div class="muted">SOC ${data.scoreboard.rl.soc}%</div></div>
      <div class="score"><div class="who">Greedy · last ${data.scoreboard.greedy.last}</div><div class="cost">AUD ${data.scoreboard.greedy.cost.toFixed(2)}</div><div class="muted">SOC ${data.scoreboard.greedy.soc}%</div></div>
    </div>

    <div class="play-tabs">
      <button type="button" class="play-tab active" data-ptab="forecast">Forecast &amp; energy</button>
      <button type="button" class="play-tab" data-ptab="agent">Agent decision</button>
    </div>
    <div id="playTabForecast">
      <p style="margin:0 0 0.35rem;font-weight:600;color:#fde68a">${data.forecast.headline || "Next 4 hours forecast"}</p>
      <p class="muted">${data.oversight_note}</p>
      <div class="play-charts">
        <div class="chart-card"><h3>Forecast AUD/kWh</h3><canvas id="playForecast"></canvas></div>
        <div class="chart-card"><h3>Cumulative net cost</h3><canvas id="playCost"></canvas></div>
        <div class="chart-card"><h3>Battery SOC %</h3><canvas id="playSoc"></canvas></div>
        <div class="chart-card"><h3>Current PV vs load</h3>
          <div class="kpis" style="margin:0.5rem 0 0">
            <div class="kpi"><div class="label">Solar</div><div class="value">${st.pv_kwh} kWh</div></div>
            <div class="kpi"><div class="label">Demand</div><div class="value">${st.load_kwh} kWh</div></div>
            <div class="kpi"><div class="label">Wholesale</div><div class="value">${(st.wholesale ?? st.retail).toFixed(3)}</div></div>
            <div class="kpi"><div class="label">Outlook</div><div class="value">${data.forecast.signal || "—"}</div></div>
          </div>
        </div>
      </div>
      <details class="details"><summary>View forecast values</summary>
        <table><thead><tr><th>Time</th><th class="num">Forecast price</th></tr></thead><tbody>${fc || "<tr><td colspan=2>No future steps</td></tr>"}</tbody></table>
      </details>
    </div>
    <div id="playTabAgent" class="hidden">
      <p class="muted"><strong>Opponent:</strong> ${data.agent_label}</p>
      <div class="chart-card"><h3>Q-values (current inspect state)</h3><canvas id="playQ"></canvas></div>
      <table class="q-table"><thead><tr><th>Action</th><th>Q-value</th></tr></thead><tbody>${qRows || "<tr><td colspan=2>No Q-values</td></tr>"}</tbody></table>
    </div>`;

  root.querySelectorAll("[data-act]").forEach((b) => {
    b.addEventListener("click", () => playAction(b.dataset.act));
  });
  $("btnPause").onclick = playPause;
  $("btnQuit").onclick = playQuit;

  root.querySelectorAll("[data-ptab]").forEach((b) => {
    b.addEventListener("click", () => {
      root.querySelectorAll("[data-ptab]").forEach((x) => x.classList.toggle("active", x === b));
      const tab = b.dataset.ptab;
      $("playTabForecast").classList.toggle("hidden", tab !== "forecast");
      $("playTabAgent").classList.toggle("hidden", tab !== "agent");
    });
  });

  const pts = data.forecast.points || [];
  if (pts.length) {
    state.charts.playForecast = new Chart($("playForecast"), {
      type: "line",
      data: {
        labels: pts.map((p) => p.time),
        datasets: [
          {
            label: "Forecast AUD/kWh",
            data: pts.map((p) => p.price),
            borderColor: "#f59e0b",
            backgroundColor: "rgba(245,158,11,0.15)",
            fill: true,
            tension: 0.25,
            pointRadius: 3,
          },
        ],
      },
      options: chartOpts(),
    });
  }

  const hist = data.history || {};
  const hLabels = hist.labels || [];
  if (hLabels.length) {
    state.charts.playCost = new Chart($("playCost"), {
      type: "line",
      data: {
        labels: hLabels,
        datasets: [
          { label: "You", data: hist.you_cost || [], borderColor: "#f59e0b", tension: 0.2, pointRadius: 0 },
          { label: "Agent", data: hist.rl_cost || [], borderColor: "#38bdf8", tension: 0.2, pointRadius: 0 },
          { label: "Greedy", data: hist.greedy_cost || [], borderColor: "#22c55e", tension: 0.2, pointRadius: 0 },
        ],
      },
      options: chartOpts(),
    });
    state.charts.playSoc = new Chart($("playSoc"), {
      type: "line",
      data: {
        labels: hLabels,
        datasets: [
          { label: "You", data: hist.you_soc || [], borderColor: "#f59e0b", tension: 0.2, pointRadius: 0 },
          { label: "Agent", data: hist.rl_soc || [], borderColor: "#38bdf8", tension: 0.2, pointRadius: 0 },
          { label: "Greedy", data: hist.greedy_soc || [], borderColor: "#22c55e", tension: 0.2, pointRadius: 0 },
        ],
      },
      options: {
        ...chartOpts(),
        scales: {
          ...chartOpts().scales,
          y: { min: 0, max: 100, ticks: { color: "#64748b" }, grid: { color: "rgba(51,65,85,.5)" } },
        },
      },
    });
  }

  const qv = data.q_values || [];
  if (qv.length) {
    state.charts.playQ = new Chart($("playQ"), {
      type: "bar",
      data: {
        labels: qv.map((r) => r.action),
        datasets: [
          {
            data: qv.map((r) => r.q),
            backgroundColor: ["#64748b", "#eab308", "#a855f7", "#3b82f6", "#22c55e"],
          },
        ],
      },
      options: {
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(51,65,85,.5)" } },
          y: { ticks: { color: "#e2e8f0" }, grid: { display: false } },
        },
      },
    });
  }
}

async function loadResults() {
  try {
    const data = await api("/api/results");
    $("resultsCaption").textContent = data.caption;
    $("resultsFinding").innerHTML = `<strong>${data.finding.split(". ")[0]}.</strong> ${data.finding
      .split(". ")
      .slice(1)
      .join(". ")}`;
    $("resultsKpis").innerHTML = `
      <div class="kpi"><div class="label">Best deployable</div><div class="value">${data.kpis.best_label} · ${data.kpis.best_deployable.toFixed(2)}</div></div>
      <div class="kpi"><div class="label">Savings vs no battery</div><div class="value">AUD ${data.kpis.savings_vs_no_battery.toFixed(2)}</div></div>
      <div class="kpi"><div class="label">Gap to oracle</div><div class="value">AUD ${data.kpis.gap_to_oracle.toFixed(2)}</div></div>
      <div class="kpi"><div class="label">Privileged vs Current</div><div class="value">+${data.kpis.privileged_vs_current.toFixed(2)}</div></div>`;
    $("resultsLearnBody").innerHTML = `<ul>${(data.learn?.bullets || [])
      .map((b) => `<li>${b}</li>`)
      .join("")}</ul>
      ${data.learn?.caveat ? `<p class="next">${data.learn.caveat}</p>` : ""}
      <p class="next">${data.learn?.next || ""}</p>`;
    $("resultsSetup").innerHTML = (data.setup || []).map((x) => `<li>${x}</li>`).join("");
    $("resultsMethod").innerHTML = (data.methodology || []).map((x) => `<li>${x}</li>`).join("");
    $("resultsStdNote").textContent = data.std_note || "";
    $("resultsBody").innerHTML = data.rows
      .map(
        (r) => `<tr class="${r.winner ? "win" : ""}"><td>${r.winner ? "🏆 " : ""}${r.controller}</td>
        <td class="num">AUD ${r.net_cost.toFixed(2)}${r.std != null ? ` ± ${r.std.toFixed(2)}` : ""}</td>
        <td class="num">${r.savings_pct != null ? `${r.savings_pct.toFixed(2)}%` : "—"}</td>
        <td class="num">${r.gap_to_oracle != null ? `AUD ${r.gap_to_oracle.toFixed(2)}` : "—"}</td></tr>`
      )
      .join("");
    destroyChart("results");
    state.charts.results = new Chart($("resultsChart"), {
      type: "bar",
      data: {
        labels: data.rows.map((r) => r.controller.replace(" — true 4h", "")),
        datasets: [
          {
            data: data.rows.map((r) => r.net_cost),
            backgroundColor: ["#6366f1", "#22c55e", "#38bdf8", "#f59e0b", "#64748b"],
          },
        ],
      },
      options: {
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(51,65,85,.5)" } },
          y: { ticks: { color: "#e2e8f0" }, grid: { display: false } },
        },
      },
    });
  } catch (err) {
    showError(err.message);
  }
}

init();
