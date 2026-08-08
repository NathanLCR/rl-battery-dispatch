"""Digital Twin comparison panels — KPIs, tables, chart tabs, timestep inspector."""

from __future__ import annotations

import html as html_lib
from typing import Callable

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from dashboard.theme import ACTION_COLORS, HOLD

# Optional Plotly for unified hover within a chart tab
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    _HAS_PLOTLY = True
except ImportError:  # pragma: no cover
    _HAS_PLOTLY = False

DETAIL_COST = {
    "grid_cost_aud": "Net cost (AUD)",
    "export_revenue_aud": "Export revenue (AUD)",
    "grid_charge_cost_aud": "Grid-charge cost (AUD)",
    "net_arbitrage_profit_aud": "Arbitrage balance (AUD)",
}
DETAIL_ENERGY = {
    "grid_import_kwh": "Grid import (kWh)",
    "export_kwh": "Export (kWh)",
    "self_consumption_rate": "Solar self-use (%)",
    "self_sufficiency": "Self-sufficiency (%)",
    "solar_waste_kwh": "Solar waste (kWh)",
}
DETAIL_BATTERY = {
    "battery_throughput_kwh": "Throughput (kWh)",
    "final_soc_pct": "Final SOC (%)",
    "n_grid_charge_actions": "# grid-charge steps",
    "n_export_actions": "# export steps",
    "evening_peak_import_kwh": "Evening import (kWh)",
}

ACTION_BADGE_COLORS = {
    "hold": ("#64748b", "#e2e8f0"),
    "charge": ("#eab308", "#0f172a"),  # solar charge — yellow
    "grid_charge": ("#3b82f6", "#f8fafc"),  # blue
    "discharge": ("#a855f7", "#f8fafc"),  # purple
    "export": ("#22c55e", "#0f172a"),  # green
}


def _fmt_metric(column: str, value: float) -> str:
    x = float(value)
    if column in ("self_consumption_rate", "self_sufficiency"):
        return f"{x * 100:.2f}%"
    if column == "final_soc_pct":
        return f"{x:.2f}%"
    if column.endswith("_actions"):
        return f"{int(round(x))}"
    if "aud" in column or column.endswith("_cost") or "revenue" in column or "profit" in column:
        return f"{x:.2f}"
    return f"{x:.2f}"


def _best_rl_cost(summary_df: pd.DataFrame) -> float | None:
    rl_keys = ("Q-Learning", "SARSA", "Double Q")
    costs = [
        float(row["grid_cost_aud"])
        for name, row in summary_df.iterrows()
        if any(k in str(name) for k in rl_keys)
    ]
    return min(costs) if costs else None


def render_winner_kpi_strip(
    summary_df: pd.DataFrame,
    no_bat: float,
    short_policy: Callable[[str], str],
) -> None:
    """Single winner bar + four uniform KPI cards (no duplicate banners)."""
    if summary_df.empty:
        return
    best_name = summary_df["grid_cost_aud"].idxmin()
    best_cost = float(summary_df.loc[best_name, "grid_cost_aud"])
    best_label = short_policy(str(best_name))
    saved = no_bat - best_cost
    sav_pct = (saved / no_bat * 100.0) if no_bat > 0 else 0.0
    rl_best = _best_rl_cost(summary_df)
    gap = (rl_best - best_cost) if rl_best is not None else 0.0
    final_soc = float(summary_df.loc[best_name].get("final_soc_pct", 0.0))

    st.markdown(
        f"""
        <div class="gq-winner-strip">
          <span class="gq-winner-strip-badge">Winning agent</span>
          <span class="gq-winner-strip-name">🏆 {html_lib.escape(best_label)}</span>
          <span class="gq-winner-strip-meta">Saved AUD {saved:.2f} vs no-battery baseline</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Net cost", f"AUD {best_cost:.2f}", f"Baseline AUD {no_bat:.2f}")
    c2.metric("Savings", f"+{sav_pct:.1f}%", f"AUD {saved:.2f} saved")
    c3.metric(
        "Gap to best RL",
        f"AUD {gap:.2f}",
        f"Best RL AUD {rl_best:.2f}" if rl_best is not None else "No RL in run",
    )
    c4.metric("Final SOC", f"{final_soc:.1f}%", "End of day")


def _soc_bar(pct: float) -> str:
    p = max(0.0, min(100.0, float(pct)))
    filled = int(round(p / 10.0))
    return f"{'█' * filled}{'░' * (10 - filled)} {p:.1f}%"


def render_comparison_table(
    summary_df: pd.DataFrame,
    no_bat: float,
    short_policy: Callable[[str], str],
) -> None:
    """Sorted controller table — no debug columns; SOC bars; muted winner tint."""
    if summary_df.empty:
        st.info("No policies selected.")
        return

    best_idx = summary_df["grid_cost_aud"].idxmin()
    rows_html: list[str] = []
    ordered = summary_df.sort_values("grid_cost_aud")
    for policy, row in ordered.iterrows():
        cost = float(row["grid_cost_aud"])
        savings = ((no_bat - cost) / no_bat * 100.0) if no_bat > 0 else 0.0
        soc = float(row.get("final_soc_pct", 0.0))
        is_best = policy == best_idx
        label = short_policy(str(policy))
        if is_best:
            label = f"🏆 {label}"
        sign = "+" if savings >= 0 else "−"
        sav_cls = "pos" if savings >= 0 else "neg"
        row_cls = "winner" if is_best else ""
        rows_html.append(
            f"<tr class='{row_cls}'>"
            f"<td class='name'>{html_lib.escape(label)}</td>"
            f"<td class='num'>AUD {cost:.2f}</td>"
            f"<td class='num sav-{sav_cls}'>{sign}{abs(savings):.2f}%</td>"
            f"<td class='soc'><span class='soc-bar'>{html_lib.escape(_soc_bar(soc))}</span></td>"
            f"</tr>"
        )

    st.caption(
        "Lower net cost is better. Savings vs no-battery reference. "
        "Final SOC is an end-of-day condition, not a win criterion."
    )
    st.markdown(
        f"""
        <div class="gq-cmp-wrap">
          <table class="gq-cmp-table">
            <thead>
              <tr>
                <th class="name">Controller</th>
                <th class="num">Net cost</th>
                <th class="num">Savings</th>
                <th class="soc">Final SOC</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows_html)}
            </tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_context_toolbar(*, day: str, mode: str = "Historical replay", preview: str | None = None) -> None:
    """Compact context badges above Twin content (not a second brand header)."""
    bits = [
        f'<span class="gq-ctx-badge">{html_lib.escape(mode)}</span>',
        f'<span class="gq-ctx-badge">Day: {html_lib.escape(str(day))}</span>',
    ]
    if preview:
        bits.append(
            f'<span class="gq-ctx-badge">Preview: {html_lib.escape(preview)}</span>'
        )
    st.markdown(
        f'<div class="gq-context-bar">{"".join(bits)}</div>',
        unsafe_allow_html=True,
    )


def render_detailed_metrics_tabs(
    summary_df: pd.DataFrame,
    short_policy: Callable[[str], str],
) -> None:
    """Split detailed metrics into Cost / Energy / Battery (≤5 columns each)."""
    if summary_df.empty:
        return

    base = summary_df.reset_index().rename(columns={"policy": "Policy"})
    base["Policy"] = base["Policy"].map(lambda p: short_policy(str(p)))

    def _frame(mapping: dict[str, str]) -> pd.DataFrame:
        cols = [c for c in mapping if c in base.columns]
        out = base[["Policy"] + cols].copy()
        for c in cols:
            out[c] = out[c].map(lambda v, col=c: _fmt_metric(col, v))
        return out.rename(columns=mapping)

    with st.expander("Detailed metrics", expanded=False):
        t_cost, t_energy, t_batt = st.tabs(["Cost", "Energy", "Battery"])
        with t_cost:
            st.dataframe(_frame(DETAIL_COST), width="stretch", hide_index=True)
        with t_energy:
            st.dataframe(_frame(DETAIL_ENERGY), width="stretch", hide_index=True)
        with t_batt:
            st.dataframe(_frame(DETAIL_BATTERY), width="stretch", hide_index=True)


def _time_labels(episode_df: pd.DataFrame) -> list[str]:
    if "time_label" in episode_df.columns:
        return [str(x) for x in episode_df["time_label"].tolist()]
    if "timestamp" in episode_df.columns:
        return [pd.Timestamp(t).strftime("%H:%M") for t in episode_df["timestamp"]]
    return [str(i + 1) for i in range(len(episode_df))]


def render_chart_tabs(
    traces: dict[str, pd.DataFrame],
    episode_df: pd.DataFrame,
    retail_margin: float,
    short_policy: Callable[[str], str],
    highlight_step: int | None = None,
) -> None:
    """Energy | Price & SOC | Controller actions — Plotly when available."""
    st.markdown("##### Charts")
    tab_e, tab_p, tab_a = st.tabs(["Energy", "Price & SOC", "Controller actions"])
    labels = _time_labels(episode_df)
    steps = list(range(1, len(episode_df) + 1))
    retail = episode_df["price_per_kwh"] + retail_margin
    hl = highlight_step

    if _HAS_PLOTLY:
        with tab_e:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=labels, y=episode_df["pv_kwh"], name="Solar generation", fill="tozeroy", line=dict(color="#f59e1a")))
            fig.add_trace(go.Scatter(x=labels, y=episode_df["load_kwh"], name="Household demand", line=dict(color="#6366f1")))
            if hl is not None and 1 <= hl <= len(labels):
                fig.add_vline(x=labels[hl - 1], line_dash="dot", line_color="#94a3b8")
            fig.update_layout(
                template="plotly_dark",
                height=320,
                margin=dict(l=40, r=20, t=30, b=40),
                paper_bgcolor="#070d1a",
                plot_bgcolor="#0c1424",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                hovermode="x unified",
                yaxis_title="Energy (kWh)",
            )
            st.plotly_chart(fig, use_container_width=True)
        with tab_p:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(
                go.Scatter(x=labels, y=episode_df["price_per_kwh"], name="Wholesale", line=dict(color="#f87171", dash="dash")),
                secondary_y=False,
            )
            fig.add_trace(
                go.Scatter(x=labels, y=retail, name="Retail import", line=dict(color="#fb923c")),
                secondary_y=False,
            )
            for i, (name, trace) in enumerate(traces.items()):
                colors = ["#22c55e", "#38bdf8", "#f59e1a", "#a78bfa", "#e879f9"]
                fig.add_trace(
                    go.Scatter(
                        x=labels[: len(trace)],
                        y=trace["soc_pct"],
                        name=f"SOC · {short_policy(name)}",
                        line=dict(color=colors[i % len(colors)]),
                    ),
                    secondary_y=True,
                )
            if hl is not None and 1 <= hl <= len(labels):
                fig.add_vline(x=labels[hl - 1], line_dash="dot", line_color="#94a3b8")
            fig.update_layout(
                template="plotly_dark",
                height=360,
                margin=dict(l=40, r=40, t=30, b=40),
                paper_bgcolor="#070d1a",
                plot_bgcolor="#0c1424",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                hovermode="x unified",
            )
            fig.update_yaxes(title_text="Price (AUD/kWh)", secondary_y=False)
            fig.update_yaxes(title_text="SOC (%)", range=[0, 100], secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)
        with tab_a:
            fig = go.Figure()
            action_order = ["hold", "charge", "grid_charge", "discharge", "export"]
            y_map = {a: i for i, a in enumerate(action_order)}
            for i, (name, trace) in enumerate(traces.items()):
                ys = [y_map.get(a, 0) + i * 0.12 for a in trace["action"]]
                colors = [ACTION_COLORS.get(a, HOLD) for a in trace["action"]]
                fig.add_trace(
                    go.Scatter(
                        x=labels[: len(trace)],
                        y=ys,
                        mode="markers",
                        name=short_policy(name),
                        marker=dict(color=colors, size=10, symbol="square"),
                        customdata=trace["action"],
                        hovertemplate="%{x}<br>%{fullData.name}: %{customdata}<extra></extra>",
                    )
                )
            if hl is not None and 1 <= hl <= len(labels):
                fig.add_vline(x=labels[hl - 1], line_dash="dot", line_color="#94a3b8")
            fig.update_layout(
                template="plotly_dark",
                height=320,
                margin=dict(l=80, r=20, t=30, b=40),
                paper_bgcolor="#070d1a",
                plot_bgcolor="#0c1424",
                hovermode="x unified",
                yaxis=dict(
                    tickmode="array",
                    tickvals=list(range(len(action_order))),
                    ticktext=["Hold", "Solar charge", "Grid charge", "Discharge", "Export"],
                ),
            )
            st.plotly_chart(fig, use_container_width=True)
        return

    # Matplotlib fallback (one panel per tab)
    with tab_e:
        fig, ax = plt.subplots(figsize=(10, 3.2), facecolor="#070d1a")
        ax.set_facecolor("#0c1424")
        ax.plot(steps, episode_df["pv_kwh"], color="#f59e1a", label="Solar")
        ax.plot(steps, episode_df["load_kwh"], color="#6366f1", label="Demand")
        if hl:
            ax.axvline(hl, color="#94a3b8", linestyle="--", linewidth=1)
        ax.legend(fontsize=8)
        ax.tick_params(colors="#94a3b8")
        st.pyplot(fig, clear_figure=True, width="stretch")
        plt.close(fig)
    with tab_p:
        fig, ax = plt.subplots(figsize=(10, 3.2), facecolor="#070d1a")
        ax.set_facecolor("#0c1424")
        ax.plot(steps, episode_df["price_per_kwh"], color="#f87171", linestyle="--", label="Wholesale")
        ax.plot(steps, retail, color="#fb923c", label="Retail")
        ax2 = ax.twinx()
        for name, trace in traces.items():
            ax2.plot(trace["step"], trace["soc_pct"], label=short_policy(name), linewidth=1.6)
        if hl:
            ax.axvline(hl, color="#94a3b8", linestyle="--", linewidth=1)
        ax.legend(loc="upper left", fontsize=7)
        ax2.legend(loc="upper right", fontsize=7)
        st.pyplot(fig, clear_figure=True, width="stretch")
        plt.close(fig)
    with tab_a:
        fig, ax = plt.subplots(figsize=(10, 2.8), facecolor="#070d1a")
        ax.set_facecolor("#0c1424")
        bar_w = 0.25
        for i, (name, trace) in enumerate(traces.items()):
            offset = (i - len(traces) / 2 + 0.5) * bar_w
            colors = [ACTION_COLORS.get(a, HOLD) for a in trace["action"]]
            xs = trace["step"].tolist()
            ax.bar([xi + offset for xi in xs], [1] * len(xs), width=bar_w, color=colors, alpha=0.9, label=short_policy(name))
        if hl:
            ax.axvline(hl, color="#94a3b8", linestyle="--", linewidth=1)
        ax.set_yticks([])
        ax.legend(fontsize=7)
        st.pyplot(fig, clear_figure=True, width="stretch")
        plt.close(fig)


def _action_badge_html(action: str, format_action: Callable[[str], str]) -> str:
    bg, fg = ACTION_BADGE_COLORS.get(action, ("#64748b", "#e2e8f0"))
    label = html_lib.escape(format_action(action))
    return (
        f'<span class="gq-action-badge" style="background:{bg};color:{fg}">'
        f"{label}</span>"
    )


def render_timestep_inspector(
    traces: dict[str, pd.DataFrame],
    short_policy: Callable[[str], str],
    format_action: Callable[[str], str],
    *,
    key_prefix: str = "twin",
) -> int:
    """Slider + prev/next + per-controller cards for one timestep. Returns 1-based step."""
    st.markdown("##### Timestep inspector")
    n = len(next(iter(traces.values())))
    state_key = f"{key_prefix}_step"
    if state_key not in st.session_state:
        st.session_state[state_key] = min(24, n)
    st.session_state[state_key] = int(max(1, min(n, st.session_state[state_key])))

    c_prev, c_slider, c_next = st.columns([0.7, 4.6, 0.7])
    with c_prev:
        if st.button("← Prev", use_container_width=True, key=f"{key_prefix}_prev"):
            st.session_state[state_key] = max(1, st.session_state[state_key] - 1)
            st.rerun()
    with c_next:
        if st.button("Next →", use_container_width=True, key=f"{key_prefix}_next"):
            st.session_state[state_key] = min(n, st.session_state[state_key] + 1)
            st.rerun()
    with c_slider:
        step = st.slider(
            "Timestep",
            1,
            n,
            key=state_key,
        )

    ref = next(iter(traces.values())).iloc[step - 1]
    time_label = str(ref.get("time_label", f"step {step}"))
    st.markdown(f"**{time_label} · Step {step} of {n}**")

    rows_html = []
    for name, trace in traces.items():
        row = trace.iloc[step - 1]
        action = str(row["action"])
        soc = float(row["soc_pct"])
        # Reward is negative adjusted cost for the step — show as cost ≈ −reward
        cost = -float(row.get("reward", 0.0))
        rows_html.append(
            "<tr>"
            f"<td>{html_lib.escape(short_policy(name))}</td>"
            f"<td>{_action_badge_html(action, format_action)}</td>"
            f"<td style='text-align:right'>{soc:.0f}%</td>"
            f"<td style='text-align:right'>AUD {cost:.2f}</td>"
            "</tr>"
        )
    st.markdown(
        f"""
        <table class="gq-step-inspector">
          <thead><tr><th>Controller</th><th>Action</th><th>SOC</th><th>Cost this step</th></tr></thead>
          <tbody>{''.join(rows_html)}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )
    return int(step)


def render_live_price_monitor(cfg, df, thresholds, q_models, *, get_live_price, load_rl_agent, state_index_fn, action_names, action_display) -> None:
    """Standalone live AEMO view — clearly separated from historical Twin."""
    from src.live_feed import current_local_hour, typical_pv_load_for_time

    st.markdown("### Live Price Monitor")
    st.markdown(
        """
        <div class="gq-live-banner">
          <span class="gq-live-badge"><span class="gq-live-dot"></span>LIVE PRICE + HISTORICAL TYPICAL LOAD</span>
          <span class="gq-live-banner-note">Informational only — not the Digital Twin historical simulation.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    live = get_live_price()
    if live is None:
        st.info(
            "Live AEMO feed unavailable right now (network/API). Historical Digital Twin still works. "
            "A real deployment needs a defined fallback when the live feed drops."
        )
        return

    hour = current_local_hour()
    pv, load = typical_pv_load_for_time(df, hour)
    retail_price = live.rrp_aud_per_kwh + cfg.tariff.retail_margin_per_kwh

    # Local / settlement times
    try:
        fetched = str(live.fetched_at_utc)
    except Exception:
        fetched = "—"
    settlement = str(getattr(live, "settlement_time", "—"))

    st.info(
        "Price is **live** from AEMO. Solar and load below are **historical medians** for this hour — "
        "not a live household meter."
    )
    st.caption(f"Updated {fetched} · NSW1 settlement {settlement} · {getattr(live, 'region', 'NSW1')}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Live wholesale", f"{live.rrp_aud_per_kwh:.3f} AUD/kWh")
    c2.metric("Estimated retail import", f"{retail_price:.3f} AUD/kWh")
    c3.metric("Typical PV", f"{pv:.2f} kWh")
    c4.metric("Typical load", f"{load:.2f} kWh")

    if q_models:
        try:
            agent = load_rl_agent("q_learning", str(q_models[0]), q_models[0].name)
            soc_pct = cfg.initial_soc_pct
            state = state_index_fn(soc_pct, pv, load, live.rrp_aud_per_kwh, hour, thresholds)
            action_id = agent.greedy_action(state) if hasattr(agent, "greedy_action") else agent.q.greedy_action(state)
            action_name = action_display.get(action_names[action_id], action_names[action_id])
            st.markdown(
                f"""
                <div class="gq-decision-card">
                  <div class="gq-decision-title">Current Q recommendation: {html_lib.escape(action_name)}</div>
                  <div class="gq-decision-sub">
                    Wholesale price is {'low' if live.rrp_aud_per_kwh < 0.05 else 'elevated'}, but the selected policy
                    only sees the current discretised state (illustrative SOC, typical PV/load) — not a metered home.
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        except Exception as exc:  # noqa: BLE001
            st.caption(f"(Could not evaluate live agent decision: {exc})")
