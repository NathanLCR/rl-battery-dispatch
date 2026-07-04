"""Shared battery dispatch physics (used by environment and oracle)."""

from __future__ import annotations

from src.config import Config
from src.constants import CHARGE, DISCHARGE, HOLD, STEP_HOURS


def apply_battery_action(
    soc_pct: float,
    action: int,
    pv_kwh: float,
    load_kwh: float,
    cfg: Config,
) -> dict[str, float]:
    """Simulate one 30-min step and return post-action quantities."""
    capacity = cfg.battery_capacity_kwh
    soc_kwh = soc_pct / 100.0 * capacity
    min_soc_kwh = cfg.min_soc_pct / 100.0 * capacity
    max_soc_kwh = cfg.max_soc_pct / 100.0 * capacity
    max_charge_kwh = cfg.max_charge_kw * STEP_HOURS
    max_discharge_kwh = cfg.max_discharge_kw * STEP_HOURS

    charge_kwh = 0.0
    discharge_kwh = 0.0
    invalid = False

    surplus = max(0.0, pv_kwh - load_kwh)
    deficit = max(0.0, load_kwh - pv_kwh)

    if action == CHARGE:
        room = max(0.0, max_soc_kwh - soc_kwh)
        charge_kwh = min(max_charge_kwh, surplus, room)
        if surplus > 0 and room <= 0:
            invalid = True
    elif action == DISCHARGE:
        available = max(0.0, soc_kwh - min_soc_kwh)
        discharge_kwh = min(max_discharge_kwh, deficit, available)
        if deficit > 0 and available <= 0:
            invalid = True

    soc_kwh = soc_kwh + charge_kwh - discharge_kwh
    soc_kwh = max(0.0, min(capacity, soc_kwh))
    soc_pct_out = soc_kwh / capacity * 100.0

    grid_import_kwh = max(0.0, load_kwh - pv_kwh - discharge_kwh)
    solar_waste_kwh = max(0.0, pv_kwh - load_kwh - charge_kwh)

    battery_deg = 0.0
    if soc_pct_out < cfg.min_soc_pct:
        battery_deg += (cfg.min_soc_pct - soc_pct_out) / 100.0
    if soc_pct_out > cfg.max_soc_pct:
        battery_deg += (soc_pct_out - cfg.max_soc_pct) / 100.0

    return {
        "charge_kwh": charge_kwh,
        "discharge_kwh": discharge_kwh,
        "grid_import_kwh": grid_import_kwh,
        "solar_waste_kwh": solar_waste_kwh,
        "soc_pct": soc_pct_out,
        "soc_kwh": soc_kwh,
        "battery_deg": battery_deg,
        "invalid_action": float(invalid),
    }
