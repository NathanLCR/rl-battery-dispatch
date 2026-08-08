"""GreineQ web API — FastAPI twin / results (Streamlit-parity flow)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.config import load_config
from webapp.landing_hero import build_landing_dispatch_html
from src.data_loader import get_episode, load_customer_dataset
from src.discretizer import N_STATES, N_STATES_PRIVILEGED, fit_discretizer
from src.oracle import no_battery_import_cost, oracle_perfect_foresight_import
from src.replay import trace_episode
from src.rule_baseline import (
    greedy_self_consumption_action,
    price_arbitrage_action_fn,
    rule_tertile_action,
)
from src.train import greedy_action_fn, load_trained_agent

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="GréineQ Web Twin", version="1.1.0")

RESULTS_HEADLINE = {
    "no_battery": 160.75,
    "oracle": 74.92,
    "greedy": 90.39,
    "current_q": 124.23,
    "current_q_std": 11.65,
    "privileged_q": 139.68,
    "privileged_q_std": 5.55,
    "caption": "Wholesale-export · 53 held-out days · true 4h privileged probe · Q-Learning 10k × seeds 42–46",
}

REWARD_LABELS = {
    "battery_aware": "Battery-aware (cycling + terminal SOC)",
    "cost_only": "Cost only",
}


class TwinRequest(BaseModel):
    day: str = "2012-07-14"
    split: str = "test"
    show_greedy: bool = True  # Greedy 5-action (arbitrage)
    show_current_q: bool = True
    show_privileged_q: bool = True
    show_solar_only: bool = False
    show_rule: bool = False
    show_sarsa: bool = False
    show_double_q: bool = False
    current_model: str | None = None
    privileged_model: str | None = None
    sarsa_model: str | None = None
    double_q_model: str | None = None
    reward_mode: str = "battery_aware"
    include_q_values: bool = False


@lru_cache(maxsize=1)
def _resources():
    cfg = load_config()
    df, split = load_customer_dataset(cfg)
    thresholds = fit_discretizer(df, cfg)
    return cfg, df, split, thresholds


def _model_n_states(path: Path) -> int:
    arr = np.load(path)
    if arr.ndim == 3:
        return int(arr.shape[1])
    return int(arr.shape[0])


def _list_models(
    *,
    agent: str,
    privileged: bool | None = None,
) -> list[dict[str, Any]]:
    """List compatible Q_*.npy models for an agent family."""
    cfg, _, _, _ = _resources()
    out: list[dict[str, Any]] = []
    if not cfg.results_models.exists():
        return out
    for path in sorted(cfg.results_models.glob("Q_*.npy"), key=lambda p: p.stat().st_mtime, reverse=True):
        name = path.name.lower()
        if agent == "q_learning":
            if "double_q" in name or "sarsa" in name:
                continue
            if "q_learning" not in name:
                continue
        elif agent == "sarsa":
            if "sarsa" not in name:
                continue
        elif agent == "double_q_learning":
            if "double_q" not in name:
                continue
        else:
            continue

        is_priv = "privileged" in name
        if privileged is not None and is_priv != privileged:
            continue

        try:
            n = _model_n_states(path)
        except Exception:
            continue

        expected = N_STATES_PRIVILEGED if is_priv else N_STATES
        if n != expected:
            continue

        out.append(
            {
                "name": path.name,
                "n_states": n,
                "privileged": is_priv,
                "preferred": "forecast_exp" in name and "seed42" in name,
            }
        )
    out.sort(key=lambda m: (not m["preferred"], m["name"]))
    return out


def _pick_default(models: list[dict[str, Any]]) -> str | None:
    if not models:
        return None
    for m in models:
        if m.get("preferred"):
            return m["name"]
    return models[0]["name"]


def _require_shape(agent, *, privileged: bool, model_name: str) -> None:
    expected = N_STATES_PRIVILEGED if privileged else N_STATES
    if hasattr(agent, "q"):
        n = int(agent.q.n_states)
    elif hasattr(agent, "q1"):
        n = int(agent.q1.n_states)
    else:
        return
    if n != expected:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Model '{model_name}' has {n} states; need {expected}. "
                "Use forecast_exp Q-tables (540 current / 1620 privileged)."
            ),
        )


def _market_from_traces(traces: dict[str, list[dict[str, Any]]]) -> dict[str, list] | None:
    if not traces:
        return None
    first = next(iter(traces.values()))
    return {
        "time_label": [row["time_label"] for row in first],
        "pv_kwh": [row["pv_kwh"] for row in first],
        "load_kwh": [row["load_kwh"] for row in first],
        "price_per_kwh": [row["price_per_kwh"] for row in first],
    }


def _solar_only_policy(thresholds, cfg):
    def policy(env) -> int:
        row = env.episode_df.iloc[env._step_idx]
        return greedy_self_consumption_action(
            env._soc_pct,
            float(row["pv_kwh"]),
            float(row["load_kwh"]),
            thresholds,
            min_soc_pct=cfg.min_soc_pct,
            max_soc_pct=cfg.max_soc_pct,
        )

    return policy


def _tertile_policy(thresholds):
    def policy(env) -> int:
        row = env.episode_df.iloc[env._step_idx]
        return rule_tertile_action(
            env._soc_pct,
            float(row["pv_kwh"]),
            float(row["load_kwh"]),
            thresholds,
        )

    return policy


def _pick_demo_day(df, days: list[str]) -> str:
    """Choose a test day with strong solar (same rule as Streamlit landing)."""
    best_day, best_pv = days[0], -1.0
    for day in days:
        ep = df[df["episode_day"] == day]
        if len(ep) != 48:
            continue
        total_pv = float(ep["pv_kwh"].sum())
        if total_pv > best_pv:
            best_pv = total_pv
            best_day = day
    return best_day


def _demo_trace():
    cfg, df, split, thresholds = _resources()
    test_days = sorted(split.test)
    day = _pick_demo_day(df, test_days)
    episode_df = get_episode(df, day)
    trace_df, summary = trace_episode(episode_df, thresholds, price_arbitrage_action_fn, cfg)
    return trace_df, day, summary


@app.get("/api/health")
def health():
    return {"ok": True, "service": "greineq-web"}


@app.get("/api/meta")
def meta():
    cfg, _, split, _ = _resources()
    current = _list_models(agent="q_learning", privileged=False)
    privileged = _list_models(agent="q_learning", privileged=True)
    sarsa = _list_models(agent="sarsa", privileged=False)
    double_q = _list_models(agent="double_q_learning", privileged=False)
    return {
        "brand": "GréineQ",
        "default_day": "2012-07-14",
        "splits": {
            "test": sorted(split.test),
            "val": sorted(split.val),
            "train": sorted(split.train),
        },
        "models": {
            "current": current,
            "privileged": privileged,
            "sarsa": sarsa,
            "double_q": double_q,
            "default_current": _pick_default(current),
            "default_privileged": _pick_default(privileged),
            "default_sarsa": _pick_default(sarsa),
            "default_double_q": _pick_default(double_q),
        },
        "reward_modes": [
            {"value": "battery_aware", "label": REWARD_LABELS["battery_aware"]},
            {"value": "cost_only", "label": REWARD_LABELS["cost_only"]},
        ],
        "results_models_dir": str(cfg.results_models),
    }


@app.get("/api/results")
def results():
    h = RESULTS_HEADLINE
    no_bat = h["no_battery"]
    oracle = h["oracle"]
    greedy = h["greedy"]
    current = h["current_q"]
    priv = h["privileged_q"]
    sav_aud = no_bat - greedy
    sav_pct = sav_aud / no_bat * 100.0
    rows = [
        {
            "controller": "Perfect foresight bound",
            "net_cost": oracle,
            "std": None,
            "savings_pct": round((no_bat - oracle) / no_bat * 100.0, 2),
            "gap_to_oracle": None,
        },
        {
            "controller": "Greedy (5-action)",
            "net_cost": greedy,
            "std": None,
            "winner": True,
            "savings_pct": round(sav_pct, 2),
            "gap_to_oracle": round(greedy - oracle, 2),
        },
        {
            "controller": "Current Q",
            "net_cost": current,
            "std": h["current_q_std"],
            "savings_pct": round((no_bat - current) / no_bat * 100.0, 2),
            "gap_to_oracle": round(current - oracle, 2),
        },
        {
            "controller": "Privileged Q — true 4h",
            "net_cost": priv,
            "std": h["privileged_q_std"],
            "savings_pct": round((no_bat - priv) / no_bat * 100.0, 2),
            "gap_to_oracle": round(priv - oracle, 2),
        },
        {
            "controller": "No-battery reference",
            "net_cost": no_bat,
            "std": None,
            "savings_pct": 0.0,
            "gap_to_oracle": round(no_bat - oracle, 2),
        },
    ]
    rows_sorted = sorted(rows, key=lambda r: r["net_cost"])
    return {
        "caption": "Wholesale-export tariff · 53 held-out days · 5 training seeds · Lower cost is better",
        "finding": (
            "Greedy remained the best deployable controller. "
            "True four-hour price-direction information did not improve Q-Learning under this experimental setup."
        ),
        "rows": rows_sorted,
        "kpis": {
            "best_deployable": greedy,
            "best_label": "Greedy",
            "savings_vs_no_battery": round(sav_aud, 2),
            "savings_pct": round(sav_pct, 2),
            "gap_to_oracle": round(greedy - oracle, 2),
            "privileged_vs_current": round(priv - current, 2),
        },
        "learn": {
            "bullets": [
                f"Greedy captured {sav_pct:.2f}% savings against no battery.",
                f"Current Q cost AUD {current - greedy:.2f} more than Greedy.",
                f"Privileged Q cost AUD {priv - greedy:.2f} more than Greedy.",
                (
                    "A three-bin direction signal did not provide enough information about the "
                    "magnitude or timing of future price opportunities."
                ),
            ],
            "next": "Next experiment: add future peak magnitude and time-to-peak bins.",
            "caveat": (
                "Under this experimental wholesale export tariff, simple self-use + price heuristics "
                "often beat trained tabular agents when foresight is coarse."
            ),
        },
        "setup": [
            "Same tariff, battery physics and 53 held-out test days for every controller",
            "Greedy: current observations and fixed decision rules (self-use + price-timed buy/sell)",
            "Current Q: current-state features only (tabular Q-Learning, 10k episodes × 5 seeds)",
            "Privileged Q: additional true four-hour, three-bin price-direction feature",
            "Headline privileged results use the oracle-direction probe — not the realistic forecast mode",
        ],
        "methodology": [
            "Do not mix with older fixed-FiT CA2 numbers",
            "Q-Learning values show mean ± standard deviation across five training seeds",
            "Wholesale-export tariff · true 4h privileged probe · seeds 42–46",
        ],
        "std_note": "Q-Learning values show mean ± standard deviation across five training seeds.",
    }


@app.post("/api/twin/run")
def twin_run(req: TwinRequest):
    cfg, df, split, thresholds = _resources()
    days = set(getattr(split, req.split, split.test))
    if req.day not in days and req.day not in set(df["episode_day"].astype(str)):
        raise HTTPException(status_code=404, detail=f"Day {req.day} not found in split '{req.split}'.")

    step_count = int((df["episode_day"].astype(str) == req.day).sum())
    if step_count != 48:
        raise HTTPException(status_code=400, detail=f"Day has {step_count}/48 intervals.")

    episode_df = get_episode(df, req.day)
    no_bat = float(no_battery_import_cost(episode_df, cfg))
    oracle = float(oracle_perfect_foresight_import(episode_df, cfg))

    current_models = _list_models(agent="q_learning", privileged=False)
    priv_models = _list_models(agent="q_learning", privileged=True)
    sarsa_models = _list_models(agent="sarsa", privileged=False)
    dq_models = _list_models(agent="double_q_learning", privileged=False)

    current_name = req.current_model or _pick_default(current_models)
    priv_name = req.privileged_model or _pick_default(priv_models)
    sarsa_name = req.sarsa_model or _pick_default(sarsa_models)
    dq_name = req.double_q_model or _pick_default(dq_models)

    policies: dict[str, tuple[Any, bool, str | None]] = {}

    if req.show_solar_only:
        policies["Solar-only greedy"] = (_solar_only_policy(thresholds, cfg), False, "none")
    if req.show_rule:
        policies["Tertile rule"] = (_tertile_policy(thresholds), False, "none")
    if req.show_greedy:
        policies["Greedy (5-action)"] = (price_arbitrage_action_fn, False, "none")

    if req.show_current_q:
        if not current_name:
            raise HTTPException(status_code=400, detail="No compatible Current Q model (need 540 states).")
        agent = load_trained_agent("q_learning", cfg.results_models / current_name, cfg)
        _require_shape(agent, privileged=False, model_name=current_name)
        policies["Current Q"] = (greedy_action_fn(agent), False, "none")

    if req.show_privileged_q:
        if not priv_name:
            raise HTTPException(status_code=400, detail="No compatible Privileged Q model (need 1620 states).")
        agent = load_trained_agent("q_learning", cfg.results_models / priv_name, cfg, privileged=True)
        _require_shape(agent, privileged=True, model_name=priv_name)
        # Match Streamlit twin checkbox: true 4h direction for the privileged probe.
        policies["Privileged Q — true 4h"] = (greedy_action_fn(agent), True, "oracle")

    if req.show_sarsa:
        if not sarsa_name:
            raise HTTPException(status_code=400, detail="No compatible SARSA model.")
        agent = load_trained_agent("sarsa", cfg.results_models / sarsa_name, cfg)
        _require_shape(agent, privileged=False, model_name=sarsa_name)
        policies["SARSA"] = (greedy_action_fn(agent), False, "none")

    if req.show_double_q:
        if not dq_name:
            raise HTTPException(status_code=400, detail="No compatible Double Q model.")
        agent = load_trained_agent("double_q_learning", cfg.results_models / dq_name, cfg)
        _require_shape(agent, privileged=False, model_name=dq_name)
        policies["Double Q"] = (greedy_action_fn(agent), False, "none")

    if not policies:
        raise HTTPException(status_code=400, detail="Select at least one controller.")

    summaries: list[dict[str, Any]] = []
    traces: dict[str, list[dict[str, Any]]] = {}
    for name, (policy, privileged, foresight) in policies.items():
        trace_df, summary = trace_episode(
            episode_df,
            thresholds,
            policy,
            cfg,
            reward_mode=req.reward_mode,
            privileged=privileged,
            foresight_mode=foresight,
        )
        summary = dict(summary)
        summary["policy"] = name
        summary["savings_pct"] = ((no_bat - float(summary["grid_cost_aud"])) / no_bat * 100.0) if no_bat else 0.0
        summaries.append(summary)
        keep = [
            "step",
            "time_label",
            "action",
            "soc_pct",
            "reward",
            "pv_kwh",
            "load_kwh",
            "price_per_kwh",
            "grid_import_kwh",
            "export_kwh",
            "grid_charge_kwh",
        ]
        if req.include_q_values:
            for col in ("q_max", "q_chosen", "state_index"):
                if col in trace_df.columns:
                    keep.append(col)
        records = trace_df[[c for c in keep if c in trace_df.columns]].to_dict(orient="records")
        for row in records:
            for k, v in list(row.items()):
                if hasattr(v, "item"):
                    row[k] = v.item()
                elif isinstance(v, float):
                    row[k] = round(float(v), 4)
        traces[name] = records

    summaries.sort(key=lambda s: float(s["grid_cost_aud"]))
    winner = summaries[0]["policy"] if summaries else None

    return {
        "day": req.day,
        "split": req.split,
        "reward_mode": req.reward_mode,
        "no_battery_cost_aud": round(no_bat, 2),
        "oracle_cost_aud": round(oracle, 2),
        "winner": winner,
        "models_used": {
            "current": current_name if req.show_current_q else None,
            "privileged": priv_name if req.show_privileged_q else None,
            "sarsa": sarsa_name if req.show_sarsa else None,
            "double_q": dq_name if req.show_double_q else None,
        },
        "summaries": [
            {
                "policy": s["policy"],
                "grid_cost_aud": round(float(s["grid_cost_aud"]), 2),
                "savings_pct": round(float(s["savings_pct"]), 2),
                "final_soc_pct": round(float(s["final_soc_pct"]), 1),
                "export_revenue_aud": round(float(s["export_revenue_aud"]), 2),
                "grid_charge_cost_aud": round(float(s["grid_charge_cost_aud"]), 2),
                "net_arbitrage_profit_aud": round(float(s["net_arbitrage_profit_aud"]), 2),
                "battery_throughput_kwh": round(float(s["battery_throughput_kwh"]), 2),
                "grid_import_kwh": round(float(s["grid_import_kwh"]), 2),
                "export_kwh": round(float(s["export_kwh"]), 2),
                "self_consumption_rate": round(float(s["self_consumption_rate"]) * 100, 1),
                "self_sufficiency": round(float(s["self_sufficiency"]) * 100, 1),
                "n_grid_charge_actions": int(s["n_grid_charge_actions"]),
                "n_export_actions": int(s["n_export_actions"]),
            }
            for s in summaries
        ],
        "traces": traces,
        "market": _market_from_traces(traces),
    }


class PlayStart(BaseModel):
    day: str = "2012-07-14"
    use_privileged: bool = False
    model_name: str | None = None


class PlayStep(BaseModel):
    session_id: str
    action: str


@app.get("/api/overview")
def overview():
    """Landing meta — same demo day selection as Streamlit."""
    trace_df, day, summary = _demo_trace()
    return {
        "day": day,
        "note": "Landing animation uses the greedy 5-action heuristic — same as the Streamlit hero.",
        "tagline": "Reinforcement learning for solar battery dispatch",
        "summary": {
            "grid_cost_aud": round(float(summary["grid_cost_aud"]), 2),
            "final_soc_pct": round(float(summary["final_soc_pct"]), 1),
        },
        "preview": [
            {
                "time_label": str(r["time_label"]),
                "action": str(r["action"]),
                "soc_pct": round(float(r["soc_pct"]), 1),
                "price_per_kwh": round(float(r["price_per_kwh"]), 4),
            }
            for _, r in trace_df.iterrows()
        ],
    }


@app.get("/api/overview/hero", response_class=HTMLResponse)
def overview_hero():
    """Exact Streamlit Q-Agent control-centre HTML for the landing iframe."""
    trace_df, day, _ = _demo_trace()
    return HTMLResponse(build_landing_dispatch_html(trace_df, day))


@app.get("/api/live")
def live_monitor():
    from src.constants import ACTION_NAMES
    from src.discretizer import state_index
    from src.live_feed import LiveFeedError, current_local_hour, fetch_latest_price, typical_pv_load_for_time

    cfg, df, _, thresholds = _resources()
    try:
        live = fetch_latest_price()
    except LiveFeedError as exc:
        return {
            "available": False,
            "message": f"Live AEMO feed unavailable ({exc}). Historical Digital Twin still works.",
        }
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "message": f"Live AEMO feed unavailable ({exc})."}

    hour = current_local_hour()
    pv, load = typical_pv_load_for_time(df, hour)
    retail = float(live.rrp_aud_per_kwh) + float(cfg.tariff.retail_margin_per_kwh)
    recommendation = None
    models = _list_models(agent="q_learning", privileged=False)
    if models:
        try:
            agent = load_trained_agent("q_learning", cfg.results_models / models[0]["name"], cfg)
            state = state_index(
                float(cfg.initial_soc_pct),
                float(pv),
                float(load),
                float(live.rrp_aud_per_kwh),
                float(hour),
                thresholds,
            )
            action_id = agent.q.greedy_action(state)
            recommendation = ACTION_NAMES.get(action_id, str(action_id))
        except Exception as exc:  # noqa: BLE001
            recommendation = f"(unavailable: {exc})"

    return {
        "available": True,
        "note": "Price is live from AEMO. PV/load are historical typicals for this hour — not a live meter.",
        "wholesale_aud_per_kwh": round(float(live.rrp_aud_per_kwh), 4),
        "retail_aud_per_kwh": round(retail, 4),
        "typical_pv_kwh": round(float(pv), 3),
        "typical_load_kwh": round(float(load), 3),
        "fetched_at_utc": str(getattr(live, "fetched_at_utc", "—")),
        "settlement_time": str(getattr(live, "settlement_time", "—")),
        "region": getattr(live, "region", "NSW1"),
        "recommendation": recommendation,
    }


@app.post("/api/play/start")
def play_start(req: PlayStart):
    from webapp import play_engine

    cfg, df, split, _ = _resources()
    if req.day not in set(map(str, split.test)):
        raise HTTPException(status_code=400, detail="Play uses held-out test days only.")
    models = _list_models(agent="q_learning", privileged=req.use_privileged)
    model_name = req.model_name or _pick_default(models)
    if not model_name:
        raise HTTPException(status_code=400, detail="No compatible Q model for this opponent.")
    try:
        return play_engine.start_game(
            _resources(), day=req.day, use_privileged=req.use_privileged, model_name=model_name
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/play/{session_id}")
def play_get(session_id: str):
    from webapp import play_engine

    try:
        return play_engine.get_game(_resources(), session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Play session not found") from None


@app.post("/api/play/step")
def play_step(req: PlayStep):
    from webapp import play_engine

    try:
        return play_engine.step_game(_resources(), req.session_id, req.action)
    except KeyError:
        raise HTTPException(status_code=404, detail="Play session not found") from None
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/play/{session_id}/pause")
def play_pause(session_id: str):
    from webapp import play_engine

    try:
        return play_engine.toggle_pause(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Play session not found") from None


@app.post("/api/play/{session_id}/quit")
def play_quit(session_id: str):
    from webapp import play_engine

    play_engine.quit_game(session_id)
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
